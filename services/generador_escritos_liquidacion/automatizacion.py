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
PROMPT_LEGAL = r"""
Eres un asistente legal experto en analizar pdfs con cálculos de jubilaciones. Los siguientes documentos estan relacionados con un mismo caso. Analiza la informacion y proporciona una respuesta consolidado en formato JSON, Importante: NO uses acentos (reemplaza las vocales acentuadas por sus equivalentes sin acento) IMPORTANTE: Si algún dato solicitado no puede ser encontrado con certeza, deberás devolver "" (una cadena vacía), nunca null, None, "no encontrado", Esto es necesario para que el formulario automatizado funcione correctamente:

{
    "27.609_Si": "Si la liquidación es entre el periodo XXXX y el periodo XXXX devolver un True, sino devolver False",
    "27.541_Si": "Si la liquidación es entre el periodo XXXX y el periodo XXXX devolver un True, sino devolver False",
    "27.426_Si": "Si la liquidación es entre el periodo XXXX y el periodo XXXX devolver un True, sino devolver False",

    "cliente": "a este dato lo encontraras en el/los retroactivos, en un formato como el siguiente 'Liquidación del Retroactivo de Diferencias de Haber e Intereses. BARAGIOLA RITA MARGARITA', en este caso devolveras 'BARAGIOLA RITA MARGARITA' ",

    "fecha_inicial_pago": "Este dato lo conseguiras en la parte del retroactivo, aparece como 'Las diferencias mensuales se calcularon por los periodos comprendidos entre el 06/10/2016 y el 30/04/2025.', devuelve '06/10/2016' en formato YYYY-MM-DD",

    "Fecha_de_cierre_de_liquidacion": "Devuelve '30/04/2025' en formato YYYY-MM-DD del mismo enunciado de periodos.",

    "Fecha_de_cierre_de_intereses": "Devuelve '30/04/2025' (del enunciado de intereses) en formato YYYY-MM-DD",

    "Badaro_Si": "True si la movilidad menciona INDEC; sino False",
    "PBU_Si": "True si aparece P.B.U.; sino False",
    "Monto_PBU": "Devuelve el monto tal cual, ej '$2.674,54'",
    "Porcentaje_PBU": "Devuelve '26.59%'",

    "Percibido": "Devuelve el parrafo completo que inicia con 'Se parte de un Haber Percibido...'",
    "Reclamado": "Devuelve el parrafo completo que inicia con 'El Primer Haber Reclamado...'",

    "Movilidad": "Devuelve el primer texto completo de movilidad encontrado (entre comillas en el ejemplo).",
    "Haber_de_Alta": "Devuelve solo el monto, ej '1.577.573,12'",

    "pagos_Si": "True si hay pagos previos (frase 'Cantidad de Pagos Indicados')",

    "monto_descontado_1": "Si hay pagos previos, extrae el primer monto (ej '94.993,31')",
    "fecha_descuento_1": "Si hay pagos previos, extrae fecha (ej '01/04/2017') y devuelve YYYY-MM-DD",

    "Capital": "Ejemplo: '... 11.476.070,84 ...' => '11.476.070,84'",
    "Intereses": "Ejemplo: '... 10.512.805,77 ...' => '10.512.805,77'",
    "total_liquidacion": "Ejemplo: '... 21.893.883,30 ...' => '21.893.883,30'",

    "Segunda_Liquidacion_Si": "True si hay dos retroactivos con movilidades (Marquez vs Alanis Ley 27551); sino False",
    "Movilidad_Segunda_Liquidacion": "Texto completo de la segunda movilidad",
    "Haber_de_Alta_Segunda_Liquidacion": "Monto del haber de alta de esa movilidad",
    "Capital_Segunda_Liquidacion": "Capital de esa liquidacion",
    "Intereses_Segunda_Liquidacion": "Intereses de esa liquidacion",
    "Total_Segunda_Liquidacion": "Total de esa liquidacion",

    "IPC_Liquidacion_Si": "True si la movilidad contiene 'Ley 27551 (50 % IPC y 50% RIPTE Trimestral retrasado 3 meses)'",
    "Movilidad_Primera_Liquidacion_IPC": "Tercera movilidad con IPC (texto completo)",
    "Haber_de_Alta_Primera_Liquidacion_IPC": "Monto",
    "Capital_Primera_Liquidacion_IPC": "Monto",
    "Intereses_Primera_Liquidacion_IPC": "Monto",
    "Total_Primera_Liquidacion_IPC": "Monto",

    "Movilidad_Segunda_Liquidacion_IPC": "Cuarta movilidad con IPC (texto completo)",
    "Haber_de_Alta_Segunda_Liquidacion_IPC": "Monto",
    "Capital_Segunda_Liquidacion_IPC": "Monto",
    "Intereses_Segunda_Liquidacion_IPC": "Monto",
    "Total_Segunda_Liquidacion_IPC": "Monto"
}
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
