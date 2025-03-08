import PyPDF2
import re
import json
import google.generativeai as uwu

def extract_text_from_pdf(file):
    """
    Recibe un objeto FileStorage (archivo PDF subido) y retorna el texto extraído.
    """
    pdf_reader = PyPDF2.PdfReader(file)
    text = "".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
    return text

def analyze_legal_documents(texto_pdfs):
    """
    Recibe el texto concatenado de documentos legales, configura la API de Gemini usando
    la API key proporcionada y retorna un diccionario con la información extraída en formato JSON.
    """
    # Configura la API de Gemini usando la API key dada
    uwu.configure(api_key="AIzaSyCGw6VPHjs6zIopfdQR6exHZXkKJdlZOCU")

    prompt = f"""Eres un asistente legal experto en analizar sentencias judiciales. Los siguientes documentos están relacionados con un mismo caso. Analiza la información y proporciona un resumen consolidado en formato JSON:

{{
    "resumen": "resumen breve del caso considerando ambos documentos, minimo 200 palabras",
    "honorarios": "cantidad de honorarios mencionados en ambos documentos (si no se mencionan, indica: 'No se mencionan Honorarios')",
    "instancia": "instancia (ejemplo: Primera Instancia, Segunda Instancia, etc.)",
    "jueces": "nombres de los jueces que dictaron la sentencia",
    "nombre_caso": "nombre del caso",
    "numero_expediente": "número de expediente",
    "fecha_sentencia": "fecha de la sentencia (dos fechas en caso que haya dos sentencias), damela en formato DD/MM/AAAA, en caso de no tener el día, ponerlo como 01/MM/AAAA",
    "palabras_clave": "palabras clave más relevantes del caso"
}}

Texto de los documentos:
{texto_pdfs}
"""
    response = uwu.GenerativeModel("gemini-2.0-flash").generate_content(prompt)
    json_response = response.text

    # Escapar las comillas dobles dentro del texto
    json_response = json_response.replace('"', '\\"')

    # Busca el JSON dentro de la respuesta, si existe
    match = re.search(r'\{.*\}', json_response.replace('\n', ''), re.DOTALL)

    if match:
        json_response = match.group(0)
        print("JSON extraído:", json_response)  # Imprime el JSON extraído
    else:
        print("No se encontró un JSON válido en la respuesta")
        return None  # O cualquier otro valor predeterminado que desees

    # Reemplaza comillas escapadas si es necesario
    json_response = json_response.replace('\\"', '"').replace("'", '"')

    try:
        data = json.loads(json_response)
    except json.decoder.JSONDecodeError as e:
        print(f"Error al analizar JSON: {e}")
        print(f"JSON recibido: {json_response}")
        return None  # O cualquier otro valor predeterminado que desees

    return data