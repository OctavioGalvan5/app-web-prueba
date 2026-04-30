"""
Servicio de análisis de sentencias usando GPT-4 y GPT-4 Vision
"""

import os
import json
import base64
from openai import OpenAI
import pdfplumber
from io import BytesIO
import fitz  # PyMuPDF

class GPT4Analyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def extract_text_from_pdf(self, file_obj, max_chars=50000):
        """
        Extrae texto de un PDF usando pdfplumber

        Args:
            file_obj: Archivo PDF
            max_chars: Máximo de caracteres a extraer

        Returns:
            str: Texto extraído
        """
        file_obj.seek(0)
        text_content = ""

        try:
            with pdfplumber.open(file_obj) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text_content += page_text + "\n"

                    # Limitar tamaño para no exceder tokens
                    if len(text_content) >= max_chars:
                        break

            print(f"✅ Texto extraído: {len(text_content)} caracteres")
            return text_content[:max_chars]

        except Exception as e:
            print(f"❌ Error extrayendo texto: {e}")
            return ""

    def extract_last_page_image(self, file_obj):
        """
        Extrae la última página del PDF como imagen JPEG

        Args:
            file_obj: Archivo PDF

        Returns:
            BytesIO: Imagen en formato JPEG
        """
        file_obj.seek(0)
        file_bytes = file_obj.read()

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")

            if doc.page_count == 0:
                return None

            # Cargar última página
            last_page = doc.load_page(doc.page_count - 1)

            # Renderizar a imagen (alta resolución para OCR)
            pix = last_page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolución
            image_bytes = pix.tobytes("jpeg")

            image_io = BytesIO(image_bytes)
            image_io.seek(0)

            print(f"✅ Última página extraída: {len(image_bytes)} bytes")
            return image_io

        except Exception as e:
            print(f"❌ Error extrayendo última página: {e}")
            return None

    def extract_judges_with_vision(self, image_bytes):
        """
        Extrae nombres de jueces usando GPT-4 Vision

        Args:
            image_bytes: Imagen de la última página

        Returns:
            list: Lista de nombres de jueces
        """
        if not image_bytes:
            return []

        try:
            image_bytes.seek(0)
            base64_image = base64.b64encode(image_bytes.read()).decode('utf-8')

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analiza esta imagen de la última página de una sentencia judicial argentina.

TAREA: Extraer ÚNICAMENTE los nombres de los jueces/vocales que firmaron digitalmente.

BUSCA:
- Texto "Digitally signed by" o "Firmado digitalmente por"
- Nombres que aparecen después de ese texto
- Pueden ser Dr., Dra., seguido del nombre completo

FORMATO DE SALIDA (JSON):
{
  "jueces": ["Dr. Juan Pérez", "Dra. María González"]
}

Si no encuentras firmas digitales, devuelve:
{
  "jueces": []
}"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }],
                max_tokens=500,
                temperature=0
            )

            result = json.loads(response.choices[0].message.content)
            jueces = result.get('jueces', [])

            print(f"✅ Jueces extraídos por Vision: {jueces}")
            return jueces

        except Exception as e:
            print(f"⚠️  Error extrayendo jueces con Vision: {e}")
            return []

    def analyze_sentencia(self, texto_pdf, jueces_vision):
        """
        Analiza sentencia con GPT-4 y extrae información estructurada

        Args:
            texto_pdf: Texto completo del PDF
            jueces_vision: Lista de jueces extraídos por Vision

        Returns:
            dict: Información estructurada de la sentencia
        """
        # Limitar texto para GPT-4
        texto_analizar = texto_pdf[:40000]  # ~10k tokens aprox

        prompt = f"""Eres un experto legal argentino especializado en sentencias del ámbito previsional.

JUECES IDENTIFICADOS (de firmas digitales): {jueces_vision}

TAREA: Extraer información estructurada de esta sentencia judicial.

INSTRUCCIONES CRÍTICAS:
- Extrae SOLO información EXPLÍCITA en el texto
- NO inventes ni supongas datos
- Si un campo no existe, devuelve null
- Para arrays vacíos, devuelve []

IMPORTANTE - VOCES:
- Las "voces" incluyen TANTO jueces como palabras clave temáticas
- Incluye TODOS los jueces en el array de voces
- Agrega palabras clave relevantes

PALABRAS CLAVE SUGERIDAS (solo si aplican):
movilidad, tope, PBU, cosa juzgada, vías de hecho, costas, honorarios,
suma no remunerativa, caducidad, jubilación, pensión, retiro por invalidez,
regularidad, recurso directo, incapacidad, ganancias, acumulación de beneficios,
obra social, ANSES, haber jubilatorio, reajuste, indexación, prescripción

FORMATO DE SALIDA (JSON):
{{
  "caratula": "Carátula completa del caso",
  "autos": "Formato: Actor c/ Demandado s/ materia",
  "numero_expediente": "Número de expediente",
  "fecha_sentencia": "YYYY-MM-DD",
  "instancia": "Primera Instancia | Segunda Instancia | Corte Suprema",
  "organo": "Nombre completo del tribunal",
  "juez_vocales": {json.dumps(jueces_vision)},
  "voces": ["juez1", "juez2", "palabra_clave1", "palabra_clave2"],
  "contenido_sumario": "Resumen ejecutivo en 2-3 oraciones",
  "resumen": "Resumen detallado (mínimo 200 palabras): hechos, argumentos, consideraciones, fallo",
  "numero_resolucion": "Número de resolución/sentencia",
  "normativa": "Leyes, decretos y normativa citada",
  "fundamentos": "Fundamentos legales principales",
  "estado_sentencia": "Firme | Sujeta a Revisión"
}}

TEXTO DE LA SENTENCIA:
{texto_analizar}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto legal argentino especializado en derecho previsional. Extraes información estructurada de sentencias judiciales. SIEMPRE devuelves JSON válido."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            data = json.loads(response.choices[0].message.content)

            # Post-procesamiento: asegurar que voces incluya jueces
            jueces = data.get('juez_vocales', [])
            voces = data.get('voces', [])

            # Combinar y eliminar duplicados
            voces_completas = list(set(jueces + voces))
            data['voces'] = voces_completas

            print(f"✅ Sentencia analizada por GPT-4")
            print(f"   Carátula: {data.get('caratula', 'N/A')[:50]}...")
            print(f"   Voces: {len(voces_completas)} encontradas")

            return data

        except Exception as e:
            print(f"❌ Error analizando con GPT-4: {e}")
            return None

    def process_pdf_complete(self, file_obj):
        """
        Proceso completo: extrae texto, imagen, analiza con GPT-4

        Args:
            file_obj: Archivo PDF

        Returns:
            dict: Datos estructurados de la sentencia
        """
        print("\n🔍 Iniciando análisis completo...")

        # 1. Extraer texto
        file_obj.seek(0)
        texto = self.extract_text_from_pdf(file_obj)
        if not texto:
            return {"error": "No se pudo extraer texto del PDF"}

        # 2. Extraer última página (para jueces)
        file_obj.seek(0)
        imagen = self.extract_last_page_image(file_obj)

        # 3. Extraer jueces con Vision
        jueces = self.extract_judges_with_vision(imagen) if imagen else []

        # 4. Analizar con GPT-4
        file_obj.seek(0)
        datos = self.analyze_sentencia(texto, jueces)

        if datos:
            datos['texto_completo'] = texto  # Guardar texto completo
            return datos
        else:
            return {"error": "Error al analizar con GPT-4"}

# Singleton
gpt4_analyzer = GPT4Analyzer()

if __name__ == "__main__":
    print("GPT-4 Analyzer inicializado")
    print(f"API Key configurada: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")
