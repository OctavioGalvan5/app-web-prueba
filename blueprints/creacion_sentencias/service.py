"""
Servicio para el módulo de creación de sentencias.

Extrae texto de los 3 PDFs (demanda, contestación, fiscalía) y los analiza
con GPT-4o para generar minutas y detectar checkpoints automáticamente.
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

from blueprints.creacion_sentencias.schemas import AnalisisIA, CHECKPOINTS_DISPONIBLES, CHECKPOINT_IDS


# ========== CONFIGURACIÓN OPENAI ==========

_client = None


def _get_openai_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("No se encontró la variable de entorno OPENAI_API_KEY")
        _client = OpenAI(api_key=api_key)
    return _client


# ========== EXTRACCIÓN DE TEXTO PDF ==========

def extraer_texto_pdf(ruta_pdf: str) -> str:
    doc = fitz.open(ruta_pdf)
    try:
        return "\n".join(pagina.get_text() for pagina in doc)
    finally:
        doc.close()


def _extraer_texto_de_archivo(archivo) -> str:
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


# ========== LLAMADA A OPENAI ==========

def _limpiar_respuesta_json(respuesta: str) -> str:
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
        except Exception as e:
            print(f"[OpenAI] Error inesperado: {type(e).__name__}: {e}")
            raise
    raise RuntimeError("Rate limit persistente tras reintentos.")


def _truncar_texto(texto: str, max_chars: int = 30000) -> str:
    if len(texto) <= max_chars:
        return texto
    return texto[:max_chars] + "\n[... texto truncado por longitud ...]"


def _construir_lista_checkpoints() -> str:
    return "\n".join(
        f'  - "{cp_id}": {cp_label}'
        for cp_id, cp_label in CHECKPOINTS_DISPONIBLES
    )


# ========== PROMPT ==========

PROMPT_SENTENCIA = """Eres un asistente legal experto en derecho previsional argentino (Ley 24.241 y normas concordantes).
Se te proporcionan tres documentos de un mismo expediente judicial previsional:

1. DEMANDA (escrito inicial del actor contra ANSES)
2. CONTESTACION DE ANSES (respuesta del organismo demandado)
3. DICTAMEN DE FISCALIA (puede estar vacío si no se proporcionó)

Analizalos cuidadosamente y devuelve EXCLUSIVAMENTE un JSON con esta estructura:
{{
    "nombre_caratula": "Apellido y nombre del actor tal como figura en el expediente, en mayúsculas",
    "numero_expte": "Número de expediente sin año ni barra (solo el número)",
    "anio_expte": "Año del expediente con 4 dígitos",
    "minuta_actor": "Redacción en tercera persona de TODOS los puntos reclamados por el actor. Enumerar punto por punto los temas, pretensiones y fundamentos de la demanda. Usar redacción judicial formal en castellano argentino.",
    "minuta_anses": "Redacción en tercera persona indicando: (a) qué puntos reconoce, admite o contesta ANSES argumentando, y (b) qué puntos guarda silencio o no responde expresamente. Distinguir claramente ambas categorías. Redacción judicial formal.",
    "resumen_conflicto": "Párrafo de síntesis del conflicto. Si hay dictamen de fiscalía, incorporar su posición. Redacción judicial formal.",
    "checkpoints_detectados": ["lista_de_ids_presentes"]
}}

Los checkpoints posibles son (incluir en la lista SOLO los que aparezcan efectivamente en los documentos):
{lista_checkpoints}

REGLAS OBLIGATORIAS:
- Devolver SOLO el JSON, sin texto previo ni posterior, sin bloques markdown ni triple backtick
- Si un dato no puede determinarse con certeza, usar cadena vacía ""
- Los textos de minuta_actor, minuta_anses y resumen_conflicto deben ser redacción judicial formal en castellano argentino
- Solo incluir en checkpoints_detectados los temas que aparezcan EFECTIVAMENTE en los documentos analizados
- Los IDs de checkpoints deben ser exactamente como se listan arriba (minúsculas, guiones bajos)
"""


# ========== FUNCIÓN PRINCIPAL ==========

def analizar_documentos_sentencia(
    archivo_demanda,
    archivo_contestacion,
    archivo_fiscalia=None,
) -> AnalisisIA:
    """Analiza los 3 PDFs con GPT-4o y devuelve un AnalisisIA con minutas y checkpoints."""
    texto_demanda = _truncar_texto(_extraer_texto_de_archivo(archivo_demanda))
    texto_contestacion = _truncar_texto(_extraer_texto_de_archivo(archivo_contestacion))

    texto_fiscalia = ""
    if archivo_fiscalia and getattr(archivo_fiscalia, 'filename', ''):
        texto_fiscalia = _truncar_texto(_extraer_texto_de_archivo(archivo_fiscalia))

    lista_checkpoints = _construir_lista_checkpoints()
    prompt = PROMPT_SENTENCIA.format(lista_checkpoints=lista_checkpoints)

    contenido = f"""=== DEMANDA ===
{texto_demanda}

=== CONTESTACION DE ANSES ===
{texto_contestacion}

=== DICTAMEN DE FISCALIA ===
{texto_fiscalia if texto_fiscalia else "(No se proporcionó dictamen de fiscalía)"}
"""

    respuesta = _generar_con_backoff(prompt + "\n\n" + contenido)
    texto_limpio = _limpiar_respuesta_json(respuesta)

    print("\n" + "=" * 60)
    print("[IA SENTENCIAS] Respuesta de OpenAI:")
    print("=" * 60)
    print(texto_limpio[:1500])
    print("=" * 60 + "\n")

    try:
        data = json.loads(texto_limpio)
        analisis = AnalisisIA.from_json(data)
        print(f"[IA SENTENCIAS] Checkpoints detectados: {analisis.checkpoints_detectados}")
        return analisis
    except json.JSONDecodeError as e:
        print(f"[IA SENTENCIAS] Error al parsear JSON: {e}")
        print(f"Texto recibido: {texto_limpio[:500]}")
        return AnalisisIA()
