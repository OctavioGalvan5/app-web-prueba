# -*- coding: utf-8 -*-
# Migrado al nuevo SDK "google-genai" (Developer API)
# Referencias: https://ai.google.dev/gemini-api/docs/quickstart  (SDK & quickstart)

import os
import json
import re
import time
import random
import fitz  # PyMuPDF

from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted

# ========== CONFIGURACIÓN ==========
PDF_PATH = "archivo.pdf"  # Cambia esto por el path real
# Leer la API key desde variable de entorno
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("❌ No se encontró la variable de entorno GOOGLE_API_KEY")

# Cliente del nuevo SDK (Developer API; sin Vertex, sin env vars)
client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(api_version="v1")  # versión estable del API
)


# ========== UTILIDADES ==========
def extraer_texto_pdf(ruta_pdf: str) -> str:
    doc = fitz.open(ruta_pdf)
    try:
        partes = []
        for pagina in doc:
            partes.append(pagina.get_text())
        print("Texto extraído del PDF.")
        return "\n".join(partes)
    finally:
        doc.close()


def limpiar_respuesta_json(respuesta: str) -> str:
    texto = (respuesta or "").strip()
    if texto.startswith("json"):
        texto = texto[4:].strip()
    if texto.startswith("```json"):
        texto = texto[7:].strip()
    elif texto.startswith("```"):
        texto = texto[3:].strip()
    if texto.endswith("```"):
        texto = texto[:-3].strip()
    return texto


def backoff_sleep(i: int) -> None:
    time.sleep(min(2**i + random.random(), 30))


def generar_con_backoff(model_name: str, prompt: str, retries: int = 5):
    for i in range(retries):
        try:
            return client.models.generate_content(model=model_name,
                                                  contents=prompt)
        except ResourceExhausted as e:
            # 429 / cuota: muestra región y límite si vienen en el mensaje
            s = str(e)
            loc = re.search(r'quota_location[^"]*"([^"]+)"', s)
            val = re.search(r'quota_limit_value[^"]*"([^"]+)"', s)
            print(
                f"[429] ResourceExhausted. region={loc.group(1) if loc else '?'} "
                f"limit={val.group(1) if val else '?'}  → reintento...")
            backoff_sleep(i)
            continue
        except Exception:
            raise
    raise RuntimeError(
        "429 persistente tras reintentos (revisá tu cuota en ai.google.dev).")


# ========== PROMPT ==========
# (Corregida una comilla extra en 'Fecha_de_cierre_de_intereses')
PROMPT_LEGAL = """
Eres un asistente legal experto en analizar pdfs con cálculos de jubilaciones. Los siguientes documentos estan relacionados con un mismo caso. Analiza la informacion y proporciona una respuesta consolidado en formato JSON, Importante: NO uses acentos (reemplaza las vocales acentuadas por sus equivalentes sin acento) IMPORTANTE: Si algún dato solicitado no puede ser encontrado con certeza, deberás devolver "" (una cadena vacía), nunca null, None, "no encontrado", Esto es necesario para que el formulario automatizado funcione correctamente:

{{
    "27.609_Si": "Si la liquidación es entre el periodo XXXX y el periodo XXXX devolver un True, sino devolver False",
    "27.541_Si": "Si la liquidación es entre el periodo XXXX y el periodo XXXX devolver un True, sino devolver False",
    "27.426_Si": "Si la liquidación es entre el periodo XXXX y el periodo XXXX devolver un True, sino devolver False",

    "cliente": "a este dato lo encontraras en el/los retroactivos, en un formato como el siguiente 'Liquidación del Retroactivo de Diferencias de Haber e Intereses. BARAGIOLA RITA MARGARITA', en este caso devolverás 'BARAGIOLA RITA MARGARITA' ",

    "expediente": "a este dato lo encontraras en la sentencia de juzgado, en un formato como el siguiente 'AUTOS Y VISTOS para dictar sentencia en este Expte. N° FSA 33872/2018 ', en este caso devolverás '33872/2018' solo los numeros, nada de FSA PRECAUCION NO SIEMPRE TENDRA JUZGADO O CAMARA EN CASO DE NO TENER DEVUELVE VACIO ES DECIR '' ",

    "Fecha_Sentencia_Primera": "Este dato lo conseguiras en la parte que dice juzgado, suele aparecer primero, aveces aparece como 'Salta, julio de 2024', por ejemplo lo que tienes que devolver en este caso es '01/07/2024' , o te puede aparecer el dia como por ejemplo 'Salta, 9 septiembre de 2024'por ejemplo lo que tienes que devolver en este caso es '09/09/2024' damela en formato YYYY-MM-DD PRECAUCION NO SIEMPRE TENDRA JUZGADO O CAMARA EN CASO DE NO TENER DEVUELVE VACIO ES DECIR '' ",

    "Sentencia_2da_Si": "Si tiene Sentencia de Camara en el texto encontraras algo que diga como 'Poder Judicial de la Nación
CAMARA FEDERAL DE SALTA - SALA II' eso significa que tiene sentencia de segunda, si tiene devolver True, si no tiene devolver False PRECAUCION NO SIEMPRE TENDRA JUZGADO O CAMARA",

    "Sentencia_de_Segunda": "Este dato lo conseguiras en la parte que dice camara, suele aparecer al principio, aveces aparece como 'Salta, julio de 2024', por ejemplo lo que tienes que devolver en este caso es '01/07/2024' , o te puede aparecer el dia como por ejemplo 'Salta, 9 septiembre de 2024'por ejemplo lo que tienes que devolver en este caso es '09/09/2024' damela en formato YYYY-MM-DD PRECAUCION NO SIEMPRE TENDRA JUZGADO O CAMARA EN CASO DE NO TENER DEVUELVE VACIO ES DECIR ''",

    "Sala": "Si en el texto aparece 'CAMARA FEDERAL DE SALTA - SALA I' o 'SALA II', devolver exactamente 'Sala I' o 'Sala II' (sin acentos). Si no se puede determinar con certeza, devolver ''.",

    "fecha_inicial_pago": "Este dato lo conseguiras en la parte del retroactivo, aparece como 'Las diferencias mensuales se calcularon por los períodos comprendidos entre el 06/10/2016 y el 30/04/2025.', por ejemplo lo que tienes que devolver en este caso es '06/10/2016' IMPORTANTE damela en formato YYYY-MM-DD no en DD/MM/YYYY, este dato siempre existira",

    "Fecha_de_cierre_de_liquidacion": "Este dato lo conseguiras en la parte del retroactivo, aparece como 'Las diferencias mensuales se calcularon por los períodos comprendidos entre el 06/10/2016 y el 30/04/2025.', por ejemplo lo que tienes que devolver en este caso es '30/04/2025' IMPORTANTE damela en formato YYYY-MM-DD no en DD/MM/YYYY, este dato siempre existira",

    "Fecha_de_cierre_de_intereses": "Este dato lo conseguiras en la parte del retroactivo, aparece como 'Los intereses por las diferencias de haber se calcularon hasta el 30/04/2025 con la tasa Pasiva para uso de la Justicia (Com. 14290 BCRA) .' es '30/04/2025', IMPORTANTE damela en formato YYYY-MM-DD no en DD/MM/YYYY , este dato siempre existira",
    
    "Badaro_Si": "En el retroactivo, buscaras la movilidad aplicada, si la movilidad menciona INDEC, significa que es badaro, y devolveras True, sino devolveras False",
    "PBU_Si": "Si tiene PBU en el haber reajustado encontraras algo como lo siguiente 'P.B.U. = 2.674,54', si tiene pbu devolver True, sino tiene PBU devolver False",
    "Monto_PBU": "El monto del PBU (si es que tiene) se encuentra en el haber reajustado, lo encontraras por ejemplo como 'P.B.U. = 2.674,54' , en este caso devolveras '$2.674,54'",
    "Porcentaje_PBU": "El porcentaje del PBU (si es que tiene) se encuentra en el haber reajustado, lo encontraras por ejemplo como 'Diferencia porcentual de la PBU : 26.59%' en este caso devolveras '26.59%'",
    "Percibido": "A este dato lo encontraras en el retroactivo (es el mismo para todos los retroactivos), por ejemplo lo encontraras como 'Se parte de un Haber Percibido de 16.869,55 Pesos del 06/10/2016 que el 01/04/2017 fué reajustado a 18.759,09 Pesos Y luego el 01/04/2025 fue reajustado a 1.137.306,69 Pesos.', debes devolver ese parrafo tal cual.",
    
    "Reclamado": "A este dato lo encontraras en el retroactivo (es el mismo para todos los retroactivos), por ejemplo lo encontraras como 'El Primer Haber Reclamado es de 20.022,59 Pesos del 06/10/2016', debes devolver ese parrafo tal cual.",
    
    "Movilidad": "Aqui buscaras en el texto que te pasare un parrafo como el siguiente (aparece en el retroactivo) 'La movilidad del haber reclamado es siguiendo el índice: Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2017 y desde ahí Aumento de Marzo 2018 Ley 26417 14% hasta el 30/06/2018 y desde ahí Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2019 y desde ahí Aumentos fallo Marquez, Raimundo por Ley 27551 hasta el 31/12/2020 y desde ahí fallo Palavecino, JosÚ hasta el 30/06/2024 y desde ahí Aumentos Generales de la ANSeS por movilidad' en este ejemplo la movilidad usada es 'Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2017 y desde ahí Aumento de Marzo 2018 Ley 26417 14% hasta el 30/06/2018 y desde ahí Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2019 y desde ahí Aumentos fallo Marquez, Raimundo por Ley 27551 hasta el 31/12/2020 y desde ahí fallo Palavecino, JosÚ hasta el 30/06/2024 y desde ahí Aumentos Generales de la ANSeS por movilidad' eso es lo que tienes que devolver, puede ser el caso que haya varias movilidades, en este apartado debes devolver la que aparezca primero",
    
    "Haber_de_Alta": "Este dato lo sacaras del retroactivo, aqui debes devolver el primer dato que te aparezca relacionado al haber de alta (ya que existe la posibilidad que haya varios), un ejemplo de como lo encontraras es 'Al 30/04/2025 el haber de Alta es de 1.577.573,12 Pesos' en este caso lo que debes devolver es '1.577.573,12'",

"pagos_Si": "Este dato lo sacaras del retroactivo, puede tener pagos previos o no, sabras que tiene pagos previos cuando veas algo como 'Fecha Importe Tipo Descontado del 01/04/2017 94.993,31 Efectivo Saldo acumulado a la fecha del pago. Cantidad de Pagos Indicados: 1',",

"monto_descontado_1": "Este dato lo sacaras del retroactivo (si es que tiene pagos previos), a este dato lo encontraras en algo como el siguiente ejemplo: 'Fecha Importe Tipo Descontado del 01/04/2017 94.993,31 Efectivo Saldo acumulado a la fecha del pago. Cantidad de Pagos Indicados: 1', en este caso el monto es '94.993,31' ",

"fecha_descuento_1": "Este dato lo sacaras del retroactivo (si es que tiene pagos previos), a este dato lo encontraras en algo como el siguiente ejemplo: 'Fecha Importe Tipo Descontado del 01/04/2017 94.993,31 Efectivo Saldo acumulado a la fecha del pago. Cantidad de Pagos Indicados: 1', en este caso la fecha es '01/04/2017' devuelvelo en formato YYYY-MM-DD ",

"monto_descontado_2": "Este dato lo sacaras del retroactivo (si es que tiene pagos previos), a este dato lo encontraras en algo como el siguiente ejemplo: 'Fecha Importe Tipo Descontado del 01/04/2017 94.993,31 Efectivo Saldo acumulado a la fecha del pago. Cantidad de Pagos Indicados: 1', en este caso el monto es '94.993,31', PRECAUCION aveces solo tiene un solo monto descontado, y ya lo colocaste en monto_descontado_1, entonces en ese caso no devolveras nada, en caso que tenga dos montos, aqui colocaras el segundo ",

"fecha_descuento_2": "Este dato lo sacaras del retroactivo (si es que tiene pagos previos), a este dato lo encontraras en algo como el siguiente ejemplo: 'Fecha Importe Tipo Descontado del 01/04/2017 94.993,31 Efectivo Saldo acumulado a la fecha del pago. Cantidad de Pagos Indicados: 1', en este caso la fecha es '01/04/2017' devuelvelo en formato YYYY-MM-DD, PRECAUCION aveces solo tiene un solo monto descontado, y ya lo colocaste en fecha_descuento_2, entonces en ese caso no devolveras nada, en caso que tenga dos montos, aqui colocaras la fecha del segundo monto descontado",

"monto_descontado_3": "Este dato lo sacaras del retroactivo (si es que tiene pagos previos), a este dato lo encontraras en algo como el siguiente ejemplo: 'Fecha Importe Tipo Descontado del 01/04/2017 94.993,31 Efectivo Saldo acumulado a la fecha del pago. Cantidad de Pagos Indicados: 1', en este caso el monto es '94.993,31', PRECAUCION aveces solo tiene un solo monto descontado, y ya lo colocaste en monto_descontado_1, entonces en ese caso no devolveras nada, en caso que tenga tres montos, aqui colocaras el tercero ",

"fecha_descuento_3": "Este dato lo sacaras del retroactivo (si es que tiene pagos previos), a este dato lo encontraras en algo como el siguiente ejemplo: 'Fecha Importe Tipo Descontado del 01/04/2017 94.993,31 Efectivo Saldo acumulado a la fecha del pago. Cantidad de Pagos Indicados: 1', en este caso la fecha es '01/04/2017' devuelvelo en formato YYYY-MM-DD, PRECAUCION aveces solo tiene un solo monto descontado, y ya lo colocaste en fecha_descuento_2, entonces en ese caso no devolveras nada, en caso que tenga tres montos, aqui colocaras la fecha del tercer monto descontado",

"Capital": "Este dato lo sacaras del retroactivo, a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '11.476.070,84'",

"Intereses": "Este dato lo sacaras del retroactivo, a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '10.512.805,77'",

"total_liquidacion": "Este dato lo sacaras del retroactivo, a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '21.893.883,30'",

"Segunda_Liquidacion_Si": "Devuelve un booleano (True o False, no string). 
Regla: devuelve True SOLO si detectas DOS retroactivos o DOS bloques de movilidad distintos, 
donde al menos uno contiene referencia explicita al fallo Marquez (p. ej. 'Marquez', 'Marquez, Raimundo') 
y al menos otro contiene referencia explicita al fallo Alanis (p. ej. 'Alanis', 'Alanis, Daniel', 'Alanis ... 35,55%/35.55% para 2020'). 
Si solo aparece uno de los fallos, o si en un UNICO bloque de movilidad aparecen menciones a ambos fallos, devuelve False. 
La presencia de IPC (p. ej. 'Ley 27551 (50 % IPC y 50% RIPTE ...)') NO implica segunda liquidacion por si sola: 
sin 'Alanis' explicito en un bloque de movilidad distinto, devuelve False. 
Se flexible ante mayusculas/minusculas y variantes tipograficas menores (comas vs puntos decimales, signos, espacios). 
Ambiguedad o duda => devuelve False. 

Ejemplos positivos (=> True):
- Retroactivo A: movilidad con '... fallo Marquez ...'; Retroactivo B: movilidad con '... fallo Alanis ... 35,55% ...'.
- Bloque 1: '... Marquez ...'; Bloque 2: '... Alanis ...'.

Ejemplos negativos (=> False):
- Solo 'Marquez' en todo el documento.
- Solo IPC sin 'Alanis'.
- Un unico bloque de movilidad que enumera historico y menciona 'Marquez' y 'Alanis' en el mismo parrafo."


"Movilidad_Segunda_Liquidacion": "Aqui buscaras en el texto que te pasare un parrafo como el siguiente (aparece en el retroactivo) 'La movilidad del haber reclamado es siguiendo el índice: Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2017 y desde ahí Aumento de Marzo 2018 Ley 26417 14% hasta el 30/06/2018 y desde ahí Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2019 y desde ahí Aumentos fallo Marquez, Raimundo por Ley 27551 hasta el 31/12/2020 y desde ahí fallo Palavecino, JosÚ hasta el 30/06/2024 y desde ahí Aumentos Generales de la ANSeS por movilidad' en este ejemplo la movilidad usada es 'Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2017 y desde ahí Aumento de Marzo 2018 Ley 26417 14% hasta el 30/06/2018 y desde ahí Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2019 y desde ahí Aumentos fallo Marquez, Raimundo por Ley 27551 hasta el 31/12/2020 y desde ahí fallo Palavecino, JosÚ hasta el 30/06/2024 y desde ahí Aumentos Generales de la ANSeS por movilidad' eso es lo que tienes que devolver, puede ser el caso que haya varias movilidades, en este apartado debes devolver la que aparezca segundo",

   "Haber_de_Alta_Segunda_Liquidacion": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Segunda_Liquidacion) , aqui debes devolver el primer dato que te aparezca relacionado al haber de alta (ya que existe la posibilidad que haya varios), un ejemplo de como lo encontraras es 'Al 30/04/2025 el haber de Alta es de 1.577.573,12 Pesos' en este caso lo que debes devolver es '1.577.573,12'",

"Capital_Segunda_Liquidacion": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Segunda_Liquidacion) , a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '11.476.070,84'",

"Intereses_Segunda_Liquidacion": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Segunda_Liquidacion) , a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '10.512.805,77'",

"Total_Segunda_Liquidacion": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Segunda_Liquidacion), a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '21.893.883,30'",

"IPC_Liquidacion_Si": "Para saber que devolver en este apartado debes fijarte en los retroactivos enviados y su movilidad, si encuentras un retroactivo cuya movilidad es algo como 'La movilidad del haber reclamado es siguiendo el índice: Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2017 y desde ahí Aumento de Marzo 2018 Ley 26417 14% hasta el 30/06/2018 y desde ahí Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2019 y desde ahí Aumentos fallo Marquez, Raimundo por Ley 27551 hasta el 31/12/2020 y desde ahí fallo Palavecino, JosÚ hasta el 30/06/2024 y desde ahí Ley 27551 (50 % IPC y 50% RIPTE Trimestral retrasado 3 meses) .', la pauta que te dira si tiene IPC, es la presencia de esta oracion en la movilidad 'Ley 27551 (50 % IPC y 50% RIPTE Trimestral retrasado 3 meses)', si encuentras eso significa que si hay IPC y debes devolver True, sino devolveras False ",

"Movilidad_Primera_Liquidacion_IPC": "Aqui buscaras en el texto que te pasare un parrafo como el siguiente (aparece en el retroactivo) 'La movilidad del haber reclamado es siguiendo el índice: 'Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2017 y desde ahí Aumento de Marzo 2018 Ley 26417 14% hasta el 30/06/2018 y desde ahí Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2019 y desde ahí Aumentos fallo Marquez, Raimundo por Ley 27551 hasta el 31/12/2020 y desde ahí fallo Palavecino, JosÚ hasta el 30/06/2024 y desde ahí Ley 27551 (50 % IPC y 50% RIPTE Trimestral retrasado 3 meses)' eso es lo que tienes que devolver, puede ser el caso que haya varias movilidades, en este apartado debes devolver la que aparezca tercera",

   "Haber_de_Alta_Primera_Liquidacion_IPC": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Primera_Liquidacion_IPC) , aqui debes devolver el primer dato que te aparezca relacionado al haber de alta (ya que existe la posibilidad que haya varios), un ejemplo de como lo encontraras es 'Al 30/04/2025 el haber de Alta es de 1.577.573,12 Pesos' en este caso lo que debes devolver es '1.577.573,12'",

"Capital_Primera_Liquidacion_IPC": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Primera_Liquidacion_IPC) , a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '11.476.070,84'",

"Intereses_Primera_Liquidacion_IPC": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Primera_Liquidacion_IPC) , a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '10.512.805,77'",

"Total_Primera_Liquidacion_IPC": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Primera_Liquidacion_IPC), a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '21.893.883,30'",

"Movilidad_Segunda_Liquidacion_IPC": "Aqui buscaras en el texto que te pasare un parrafo como el siguiente (aparece en el retroactivo) 'La movilidad del haber reclamado es siguiendo el índice: 'Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2017 y desde ahí Aumento de Marzo 2018 Ley 26417 14% hasta el 30/06/2018 y desde ahí Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2019 y desde ahí Aumentos fallo Marquez, Raimundo por Ley 27551 hasta el 31/12/2020 y desde ahí fallo Palavecino, JosÚ hasta el 30/06/2024 y desde ahí Ley 27551 (50 % IPC y 50% RIPTE Trimestral retrasado 3 meses)' eso es lo que tienes que devolver, puede ser el caso que haya varias movilidades, en este apartado debes devolver la que aparezca cuarta",

"Haber_de_Alta_Segunda_Liquidacion_IPC": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Segunda_Liquidacion_IPC) , aqui debes devolver el primer dato que te aparezca relacionado al haber de alta (ya que existe la posibilidad que haya varios), un ejemplo de como lo encontraras es 'Al 30/04/2025 el haber de Alta es de 1.577.573,12 Pesos' en este caso lo que debes devolver es '1.577.573,12'",

"Capital_Segunda_Liquidacion_IPC": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Segunda_Liquidacion_IPC) , a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '11.476.070,84'",

"Intereses_Segunda_Liquidacion_IPC": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Segunda_Liquidacion_IPC) , a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '10.512.805,77'",

"Total_Segunda_Liquidacion_IPC": "Este dato lo sacaras del retroactivo (el mismo donde sacaste la Movilidad_Segunda_Liquidacion_IPC), a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '21.893.883,30'",

}}

"""


# ========== LLAMADA A GEMINI ==========
def analizar_con_gemini(texto_pdf: str):
    model_name = "gemini-2.5-flash"  # modelo estable recomendado
    resp = generar_con_backoff(model_name, PROMPT_LEGAL + "\n\n" + texto_pdf)
    texto_limpio = limpiar_respuesta_json(getattr(resp, "text", ""))

    print("Respuesta de Gemini:")
    print(texto_limpio)

    try:
        return json.loads(texto_limpio)
    except json.JSONDecodeError as e:
        print("❌ Error al decodificar JSON:", e)
        print("Texto recibido:")
        print(texto_limpio)
        return None


if __name__ == "__main__":
    texto = extraer_texto_pdf(PDF_PATH)
    resultado = analizar_con_gemini(texto)
    print("Resultado JSON:", resultado)
