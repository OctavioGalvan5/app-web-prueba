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
API_KEY = "AIzaSyDwxfjb8bdcxdp-5Bi3uEQi4jesX2ujXGQ"  # ⚠️ no publiques esta clave

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
    time.sleep(min(2 ** i + random.random(), 30))

def generar_con_backoff(model_name: str, prompt: str, retries: int = 5):
    for i in range(retries):
        try:
            return client.models.generate_content(model=model_name, contents=prompt)
        except ResourceExhausted as e:
            # 429 / cuota: muestra región y límite si vienen en el mensaje
            s = str(e)
            loc = re.search(r'quota_location[^"]*"([^"]+)"', s)
            val = re.search(r'quota_limit_value[^"]*"([^"]+)"', s)
            print(f"[429] ResourceExhausted. region={loc.group(1) if loc else '?'} "
                  f"limit={val.group(1) if val else '?'}  → reintento...")
            backoff_sleep(i)
            continue
        except Exception:
            raise
    raise RuntimeError("429 persistente tras reintentos (revisá tu cuota en ai.google.dev).")

# ========== PROMPT ==========
# (Corregida una comilla extra en 'Fecha_de_cierre_de_intereses')
PROMPT_LEGAL = """
Eres un asistente legal experto en analizar pdfs con cálculos de jubilaciones. Los siguientes documentos estan relacionados con un mismo caso. Analiza la informacion y proporciona una respuesta consolidado en formato JSON, Importante: NO uses acentos (reemplaza las vocales acentuadas por sus equivalentes sin acento) IMPORTANTE: Si algún dato solicitado no puede ser encontrado con certeza, deberás devolver "" (una cadena vacía), nunca null, None, "no encontrado", Esto es necesario para que el formulario automatizado funcione correctamente:

{{
    "27.609_Si": "Si la liquidación es entre el periodo XXXX y el periodo XXXX devolver un True, sino devolver False",
    "27.541_Si": "Si la liquidación es entre el periodo XXXX y el periodo XXXX devolver un True, sino devolver False",
    "27.426_Si": "Si la liquidación es entre el periodo XXXX y el periodo XXXX devolver un True, sino devolver False",

    "cliente": "a este dato lo encontraras en el/los retroactivos, en un formato como el siguiente 'Liquidación del Retroactivo de Diferencias de Haber e Intereses. BARAGIOLA RITA MARGARITA', en este caso devolverás 'BARAGIOLA RITA MARGARITA' ",

    "fecha_inicial_pago": "Este dato lo conseguiras en la parte del retroactivo, aparece como 'Las diferencias mensuales se calcularon por los períodos comprendidos entre el 06/10/2016 y el 30/04/2025.', por ejemplo lo que tienes que devolver en este caso es '06/10/2016'damela en formato YYYY-MM-DD",

    "Fecha_de_cierre_de_liquidación": "Este dato lo conseguiras en la parte del retroactivo, aparece como 'Las diferencias mensuales se calcularon por los períodos comprendidos entre el 06/10/2016 y el 30/04/2025.', por ejemplo lo que tienes que devolver en este caso es '30/04/2025' damela en formato YYYY-MM-DD",

    "Fecha_de_cierre_de_intereses": "Este dato lo conseguiras en la parte del retroactivo, aparece como 'Los intereses por las diferencias de haber se calcularon hasta el 30/04/2025 con la tasa Pasiva para uso de la Justicia (Com. 14290 BCRA) .' es '30/04/2025' damela en formato YYYY-MM-DD"",
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

"Capital": "Este dato lo sacaras del retroactivo, a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '11.476.070,84'",

"Intereses": "Este dato lo sacaras del retroactivo, a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '10.512.805,77'",

"total_liquidacion": "Este dato lo sacaras del retroactivo, a este dato lo encontraras en algo como el siguiente ejemplo: 'Período Capital Intereses Total Pagado en el Saldo Período Efectivo 11.476.070,84 10.512.805,77 21.988.876,61 94.993,31 21.893.883,30 al 30/04/2025 ', en este caso el monto es '21.893.883,30'",

"Segunda_Liquidacion_Si": "Tienes que saber si tiene una segunda liquidación, para hacerlo deberas ver la cantidad de retroactivos que tiene y sus movilidades, si ves que tiene dos movilidades y una tiene 'Aumentos fallo Marquez, Raimundo por Ley 27551' y la otra movilidad tiene 'Aumentos fallo Alanis, Daniel Ley 27551 35,55% para el año 2020' significa que tiene segunda liquidación y debes devolver True, sino devolveras False, la principal diferencia entre saber si tiene segunda liquidación o no, es ver si se hizo una liquidación con el fallo caliva y otra con el fallo alanis ",

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
    model_name = "gemini-2.0-flash-001"  # modelo estable recomendado
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
