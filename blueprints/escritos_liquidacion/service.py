"""
Servicio para el módulo de escritos de liquidación.

Contiene la lógica de negocio: procesamiento de PDF con IA (OpenAI),
y cálculo de honorarios UMA.
"""

import os
import json
import time
import random
import tempfile

import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

load_dotenv()
from xhtml2pdf import pisa
from io import BytesIO
from PIL import Image
from flask import render_template

from models.database import engine
from sqlalchemy import text
from datetime import datetime

from services.calculos import (
    calcular_porcentajes,
    formatear_dinero,
)
from blueprints.escritos_liquidacion.schemas import DatosEscrito


# ========== CONFIGURACIÓN OPENAI ==========

_client = None


def _get_openai_client():
    """Lazy initialization del cliente OpenAI."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("No se encontró la variable de entorno OPENAI_API_KEY")
        _client = OpenAI(api_key=api_key)
    return _client


# ========== EXTRACCIÓN DE TEXTO PDF ==========

def extraer_texto_pdf(ruta_pdf: str) -> str:
    """Extrae todo el texto de un archivo PDF usando PyMuPDF."""
    doc = fitz.open(ruta_pdf)
    try:
        partes = [pagina.get_text() for pagina in doc]
        return "\n".join(partes)
    finally:
        doc.close()


# ========== LLAMADA A OPENAI ==========

def _limpiar_respuesta_json(respuesta: str) -> str:
    """Limpia la respuesta de OpenAI para obtener JSON puro."""
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


def _generar_con_backoff(prompt: str, retries: int = 5) -> str:
    """Llama a OpenAI con reintentos exponenciales ante rate limits."""
    client = _get_openai_client()
    for i in range(retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except RateLimitError as e:
            print(f"[OpenAI] Rate limit intento {i+1}/{retries}: {e}")
            time.sleep(min(2**i + random.random(), 30))
            continue
        except Exception as e:
            print(f"[OpenAI] Error inesperado: {type(e).__name__}: {e}")
            raise
    raise RuntimeError("Rate limit persistente tras reintentos.")


# Prompt adaptado al nuevo modelo docx
PROMPT_LEGAL = """
Eres un asistente legal experto en analizar PDFs con calculos de jubilaciones.
Los siguientes documentos estan relacionados con un mismo caso.
Analiza la informacion y proporciona una respuesta consolidada en formato JSON.

IMPORTANTE:
- NO uses acentos (reemplaza las vocales acentuadas por sus equivalentes sin acento)
- Si algun dato solicitado no puede ser encontrado con certeza, devolver "" (cadena vacia), nunca null ni None
- Las fechas deben estar en formato DD/MM/YYYY
- Los montos deben estar en formato argentino: 1.234.567,89 (puntos como separador de miles, coma para decimales)

{{
    "haber_reclamado": "El primer haber reclamado, lo encontraras como 'El Primer Haber Reclamado es de 20.022,59 Pesos del 06/10/2016', devolver solo el monto formateado: 20.022,59",

    "haber_percibido": "El haber percibido inicial. Buscar la frase 'Se parte de un Haber Percibido de X Pesos del DD/MM/YYYY'. Devolver SOLO el monto, ejemplo: 4.821,58. NO confundir con el haber reclamado ni con otros montos.",

    "fecha_haber_reclamado": "La fecha del haber reclamado, formato DD/MM/YYYY",

    "haber_de_alta": "El haber de alta mas reciente, lo encontraras como 'Al 30/04/2025 el haber de Alta es de 1.577.573,12 Pesos', devolver: 1.577.573,12",

    "fecha_inicial_de_pago": "Fecha de inicio del periodo de liquidacion, formato DD/MM/YYYY. La encontraras como 'Las diferencias mensuales se calcularon por los periodos comprendidos entre el 06/10/2016 y el 30/04/2025'",

    "fecha_de_cierre": "Fecha de cierre de la liquidacion, formato DD/MM/YYYY",

    "fecha_intereses": "Fecha hasta donde se calcularon los intereses, formato DD/MM/YYYY. La encontraras como 'Los intereses por las diferencias de haber se calcularon hasta el 30/04/2025'",

    "opciones": [
        {{
            "numero": 1,
            "movilidad": "Los indices de movilidad aplicados en el retroactivo. NO incluir el prefijo 'La movilidad del haber reclamado es siguiendo el indice:'. Devolver SOLO los indices, ejemplo: 'Aumentos Generales de la ANSeS por movilidad hasta el 31/12/2019 y desde ahi Aumentos fallo Marquez por Ley 27551 hasta el 31/12/2020'",
            "capital": "IMPORTANTE: Al final del retroactivo hay una seccion 'Detalle' con varias filas: 'Total Adeudado del periodo', posibles pagos descontados, e intereses acumulados. SIEMPRE tomar los valores de la fila 'Saldo al XX/XX/XXXX' que es la ULTIMA fila del Detalle, NO la fila 'Suma' ni 'Total Adeudado del periodo'. El capital del Saldo, ejemplo: 18.773.660,94",
            "intereses": "Los intereses de la fila 'Saldo' (ultima fila del Detalle), ejemplo: 13.320.942,92",
            "total": "El total de la fila 'Saldo' (ultima fila del Detalle), ejemplo: 31.148.161,45. Este monto SIEMPRE es mayor o igual al 'Total Adeudado del periodo'",
            "tope_9": "true si se aplico tope del art 9 inc 3 ley 24463, false si no"
        }},
        {{
            "numero": 2,
            "movilidad": "Si hay un segundo retroactivo, su movilidad. Si no hay, dejar vacio",
            "capital": "",
            "intereses": "",
            "total": "",
            "tope_9": false
        }},
        {{
            "numero": 3,
            "movilidad": "Si hay un tercer retroactivo, su movilidad. Si no hay, dejar vacio",
            "capital": "",
            "intereses": "",
            "total": "",
            "tope_9": false
        }},
        {{
            "numero": 4,
            "movilidad": "Si hay un cuarto retroactivo, su movilidad. Si no hay, dejar vacio",
            "capital": "",
            "intereses": "",
            "total": "",
            "tope_9": false
        }}
    ],

    "sala": "Si en el texto aparece CAMARA FEDERAL - SALA I devolver '1', si SALA II devolver '2'. Si no hay camara, devolver ''",

    "reparacion_historica": "true si en algun retroactivo se menciona Reparacion Historica, false si no",

    "tuvo_pagos": "true si se detectan pagos previos descontados en algun retroactivo, false si no"
}}
"""


def analizar_pdf_con_ia(texto_pdf: str) -> dict:
    """Analiza el texto de un PDF con OpenAI y devuelve un dict con los datos extraídos."""
    respuesta = _generar_con_backoff(PROMPT_LEGAL + "\n\n" + texto_pdf)
    texto_limpio = _limpiar_respuesta_json(respuesta)

    print("\n" + "="*60)
    print("[IA] RESPUESTA COMPLETA DE OPENAI:")
    print("="*60)
    print(texto_limpio)
    print("="*60 + "\n")

    try:
        resultado = json.loads(texto_limpio)
        # Log de campos clave
        print("[IA] Campos extraídos:")
        for key, value in resultado.items():
            if key == 'opciones':
                for op in value:
                    if op.get('total') or op.get('movilidad'):
                        print(f"  Opción {op.get('numero')}: capital={op.get('capital')} | intereses={op.get('intereses')} | total={op.get('total')}")
            else:
                print(f"  {key}: {value}")
        return resultado
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON de OpenAI: {e}")
        print(f"Texto recibido: {texto_limpio[:500]}")
        return None


def _extraer_texto_de_archivo(archivo) -> str:
    """Guarda un archivo subido en disco temporalmente y extrae su texto."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        archivo.save(tmp.name)
        tmp_path = tmp.name
    try:
        return extraer_texto_pdf(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _construir_datos_escrito(json_resultado: dict) -> DatosEscrito:
    """Construye un DatosEscrito desde el JSON devuelto por la IA."""
    from blueprints.escritos_liquidacion.schemas import OpcionLiquidacion

    datos = DatosEscrito()
    datos.nombre_caratula = json_resultado.get('nombre_caratula', '')
    datos.numero_expte = json_resultado.get('numero_expte', '')
    datos.anio_expte = json_resultado.get('anio_expte', '')
    datos.haber_reclamado = json_resultado.get('haber_reclamado', '')
    datos.haber_percibido = json_resultado.get('haber_percibido', '')
    datos.fecha_haber_reclamado = json_resultado.get('fecha_haber_reclamado', '')
    datos.haber_de_alta = json_resultado.get('haber_de_alta', '')
    datos.fecha_inicial_de_pago = json_resultado.get('fecha_inicial_de_pago', '')
    datos.fecha_de_cierre = json_resultado.get('fecha_de_cierre', '')
    datos.fecha_intereses = json_resultado.get('fecha_intereses', '')
    datos.sala = json_resultado.get('sala', '')
    datos.reparacion_historica = json_resultado.get('reparacion_historica', False) is True or json_resultado.get('reparacion_historica', '') == 'true'
    datos.tuvo_pagos = json_resultado.get('tuvo_pagos', False) is True or json_resultado.get('tuvo_pagos', '') == 'true'

    for op_raw in json_resultado.get('opciones', []):
        movilidad = op_raw.get('movilidad', '').strip()
        total = op_raw.get('total', '').strip()
        if movilidad or total:
            tope = op_raw.get('tope_9', False)
            if isinstance(tope, str):
                tope = tope.lower() == 'true'
            datos.opciones.append(OpcionLiquidacion(
                numero=op_raw.get('numero', 1),
                movilidad=movilidad,
                capital=op_raw.get('capital', ''),
                intereses=op_raw.get('intereses', ''),
                total=total,
                tope_9=tope,
            ))

    return datos


PROMPT_OPCION_EXTRA = """
Eres un asistente legal experto en liquidaciones judiciales.
Analiza el siguiente documento y extrae SOLO los datos del retroactivo.

IMPORTANTE:
- Los montos deben estar en formato argentino: 1.234.567,89
- Si un dato no se encuentra, devolver "" (cadena vacia)

Devuelve SOLO este JSON:
{{
    "movilidad": "Los indices de movilidad aplicados. Devolver SOLO los indices, sin el prefijo 'La movilidad del haber reclamado es siguiendo el indice:'",
    "capital": "El capital de la fila 'Saldo' (ultima fila del Detalle)",
    "intereses": "Los intereses de la fila 'Saldo'",
    "total": "El total de la fila 'Saldo'",
    "tope_9": "true si se aplico tope del art 9 inc 3 ley 24463, false si no"
}}
"""


def _extraer_opcion_de_texto(texto: str) -> dict | None:
    """Llama a la IA con el prompt simplificado para extraer solo los datos de una opción."""
    respuesta = _generar_con_backoff(PROMPT_OPCION_EXTRA + "\n\n" + texto)
    texto_limpio = _limpiar_respuesta_json(respuesta)
    try:
        return json.loads(texto_limpio)
    except json.JSONDecodeError:
        print(f"[IA] Error al parsear opción extra: {texto_limpio[:300]}")
        return None


def procesar_pdfs(archivos: list) -> DatosEscrito:
    """Procesa uno o varios PDFs.

    - 1 PDF: análisis completo (datos del caso + opciones internas del documento).
    - Varios PDFs: el primero se analiza completo; cada PDF adicional se analiza
      con un prompt simplificado para extraer solo su opción, y se agrega a la lista.
    """
    from blueprints.escritos_liquidacion.schemas import OpcionLiquidacion

    textos = [_extraer_texto_de_archivo(a) for a in archivos]

    # Analizar primer PDF completo
    json_resultado = analizar_pdf_con_ia(textos[0])
    if not json_resultado:
        return DatosEscrito()

    datos = _construir_datos_escrito(json_resultado)

    # Si hay más PDFs, extraer la opción de cada uno y agregarla
    for i, texto in enumerate(textos[1:], start=len(datos.opciones) + 1):
        if i > 4:
            break
        op_raw = _extraer_opcion_de_texto(texto)
        if not op_raw:
            continue
        movilidad = op_raw.get('movilidad', '').strip()
        total = op_raw.get('total', '').strip()
        if not movilidad and not total:
            continue
        tope = op_raw.get('tope_9', False)
        if isinstance(tope, str):
            tope = tope.lower() == 'true'
        datos.opciones.append(OpcionLiquidacion(
            numero=i,
            movilidad=movilidad,
            capital=op_raw.get('capital', ''),
            intereses=op_raw.get('intereses', ''),
            total=total,
            tope_9=tope,
        ))

    return datos


# ========== CÁLCULO DE HONORARIOS UMA ==========

def _obtener_valor_uma(fecha_str: str) -> float:
    """Obtiene el valor UMA vigente a una fecha dada desde la base de datos."""
    try:
        fecha_dt = datetime.strptime(fecha_str, '%d/%m/%Y').date()
    except ValueError:
        try:
            fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return 0

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM valor_uma"))
        fila_cercana = None
        fecha_cercana = None
        for row in result:
            fecha_fila = row[1]
            if fecha_fila <= fecha_dt:
                if fecha_cercana is None or fecha_fila > fecha_cercana:
                    fecha_cercana = fecha_fila
                    fila_cercana = row
    return float(fila_cercana[4]) if fila_cercana else 0


def _obtener_acordada(fecha_str: str) -> str:
    """Obtiene la acordada vigente a una fecha dada desde la base de datos."""
    try:
        fecha_dt = datetime.strptime(fecha_str, '%d/%m/%Y').date()
    except ValueError:
        try:
            fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return ""

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM valor_uma"))
        fila_cercana = None
        fecha_cercana = None
        for row in result:
            fecha_fila = row[1]
            if fecha_fila <= fecha_dt:
                if fecha_cercana is None or fecha_fila > fecha_cercana:
                    fecha_cercana = fecha_fila
                    fila_cercana = row
    return str(fila_cercana[3]) if fila_cercana else ""


def _monto_str_a_float(monto_str: str) -> float:
    """Convierte un monto en formato argentino '1.234.567,89' a float."""
    if not monto_str:
        return 0.0
    limpio = monto_str.replace('$', '').replace(' ', '').strip()
    limpio = limpio.replace('.', '').replace(',', '.')
    try:
        return float(limpio)
    except ValueError:
        return 0.0


def calcular_honorarios_opciones(datos: DatosEscrito) -> dict:
    """Calcula los honorarios UMA para cada opción de liquidación.

    Retorna un dict con los datos necesarios para generar el cuadro UMA.
    """
    fecha = datos.fecha_intereses or datos.fecha_de_cierre
    if not fecha:
        return {}

    valor_uma = _obtener_valor_uma(fecha)
    acordada = _obtener_acordada(fecha)

    if valor_uma == 0:
        return {}

    resultado = {
        'acordada': acordada,
        'valor_uma': formatear_dinero(valor_uma),
        'fecha': fecha,
        'columnas': [],
    }

    for opcion in datos.opciones:
        monto = _monto_str_a_float(opcion.total)
        if monto <= 0:
            continue

        (cantidad_uma, valor_dividido, porcentajes, porcentaje_anterior,
         porcentaje_maximo, primera_valor_uma, primera_valor_uma_final,
         segundo_valor_uma, porcentaje_minimo, segunda_valor_uma_final,
         total_uma, apoderado, reduccion_excepciones) = calcular_porcentajes(monto, valor_uma)

        col = {
            'titulo': f'Opción {opcion.numero}',
            'monto': formatear_dinero(monto),
            'cantidad_uma': cantidad_uma,
            'valor_dividido': valor_dividido,
            'porcentajes': porcentajes,
            'porcentaje_anterior': porcentaje_anterior,
            'porcentaje_maximo': porcentaje_maximo,
            'primera_valor_uma': primera_valor_uma,
            'primera_valor_uma_final': primera_valor_uma_final,
            'segundo_valor_uma': segundo_valor_uma,
            'porcentaje_minimo': porcentaje_minimo,
            'segunda_valor_uma_final': segunda_valor_uma_final,
            'total_uma': total_uma,
            'apoderado': apoderado,
            'reduccion_excepciones': reduccion_excepciones,
        }
        resultado['columnas'].append(col)

    return resultado


def generar_cuadro_uma_imagen(datos: DatosEscrito) -> str:
    """Genera el cuadro UMA como imagen PNG.

    1. Calcula honorarios para cada opción
    2. Renderiza un template HTML con la tabla
    3. Convierte a PDF con xhtml2pdf
    4. Recorta los 3/4 superiores como imagen
    5. Retorna la ruta de la imagen temporal
    """
    honorarios = calcular_honorarios_opciones(datos)
    if not honorarios or not honorarios.get('columnas'):
        return None

    # Renderizar HTML
    rendered = render_template(
        'escritos_liquidacion/cuadro_uma.html',
        **honorarios
    )

    # HTML → PDF
    pdf_buffer = BytesIO()
    pisa.CreatePDF(rendered, dest=pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()

    # PDF → Imagen (recortar 3/4 superiores)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)
    rect = page.rect
    tres_cuartos_alto = rect.height * (3 / 4)
    clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + tres_cuartos_alto)
    pix = page.get_pixmap(clip=clip, dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()

    # Guardar imagen temporal
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    tmp.close()

    return tmp.name
