import PyPDF2
import pdfplumber
import re
import json
import google.generativeai as genai
import hashlib
from datetime import datetime
from sqlalchemy import text
import base64
from models.database import engine  # Verifica que la conexión esté bien configurada

# ================== Funciones para extraer y analizar el PDF ==================

def convertir_fecha(fecha_str):
    formatos = [
        "%Y-%m-%d",  # Formato ISO (input date)
        "%d/%m/%Y",  # Formato original
        "%m/%Y",     # Formato sin día
        "%Y-%m"      # Formato ISO sin día
    ]
    for formato in formatos:
        try:
            fecha_obj = datetime.strptime(fecha_str, formato).date()
            return fecha_obj
        except ValueError:
            continue
    print(f"Formato de fecha no reconocido: {fecha_str}")
    return None

def extract_text_from_pdf(file_obj):
    text_content = ""
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            text_content += page.extract_text() or ""  # Evita errores con páginas vacías
    return text_content


def analyze_legal_documents(texto_pdfs, ultima_imagen):
    try:
        # Configurar la API (actualiza la key según corresponda)
        genai.configure(api_key="AIzaSyCGw6VPHjs6zIopfdQR6exHZXkKJdlZOCU")

        # Convertir la imagen de la última página a base64
        ultima_imagen.seek(0)
        image_b64 = base64.b64encode(ultima_imagen.read()).decode("utf-8")

        # Construir el prompt de análisis, incluyendo la imagen en base64 al inicio
        prompt = f"""Adjunto la imagen de la ultima pagina en base64:
{image_b64}

Eres un asistente legal experto en analizar sentencias judiciales. Los siguientes documentos estan relacionados con un mismo caso. Analiza la informacion y proporciona un resumen consolidado en formato JSON, Importante: NO uses acentos (reemplaza las vocales acentuadas por sus equivalentes sin acento):

{{
    "resumen": "resumen breve del caso considerando ambos documentos, minimo 200 palabras",
    "honorarios": "cantidad de honorarios mencionados en los documentos. Importante: deben ser los mas recientes, y deben ser devueltos de la siguiente manera, por ejemplo si los honorarios son $125.456,56, se devolvera como 125456.56 (si no se mencionan, indica devolver \"\" es decir null)",
    "instancia": "instancia (Puede ser: Primera Instancia, Segunda Instancia, Instancia extraordinaria, Ministerio Publico fiscal etc.) IMPORTANTE: Si se habla de Juzgado Federal entonces se refiere a Primera Instancia, si habla de Camara Federal o Tribunal es una segunda instancia,",
    "jueces": "Examina cuidadosamente la imagen adjunta y busca únicamente el patrón exacto 'Digitally signed by'. Inmediatamente después de este texto, extrae solo el nombre completo que aparece, hasta que se termine la línea o se encuentre un delimitador (por ejemplo, un salto de línea o un símbolo). Si existen varias ocurrencias de este patrón en distintas firmas digitales, extrae cada nombre de forma individual y sepáralos con comas. Es fundamental que no se incluyan otros textos ni se inventen nombres: solo extrae exactamente lo que sigue a 'Digitally signed by' en la imagen. Si no se encuentra ninguna firma digital, deja este campo vacío.",
    "nombre_caso": "nombre del caso (No debes darlo todo en mayusculas, por ejemplo Si el Caso se llama PEDRO GUZMAN C/ANSES, Darlo como Pedro Guzman C/Anses, respeta la gramatica)",
    "numero_expediente": "numero de expediente",
    "fecha_sentencia": "fecha de la sentencia, damela en formato DD/MM/AAAA, en caso de no tener el dia, ponerlo como 01/MM/AAAA, tambien podes sacarlo en la firma digital al final del pdf",
    "palabras_clave": "palabras clave mas relevantes del caso (ten en cuenta si menciona algunas de la siguientes: movilidad, tope, PBU, cosa juzgada, vias de hecho, costas, honorarios, suma no remunerativas, error material, caducidad, jubilacion, pension, retiro por invalidez, regularidad, recurso directo, incapacidad, ganancias, acumulacion de beneficios, obra social)",
    "jurisdiccion": "jurisdiccion a la que pertenece la sentencia (pueden ser las siguientes: CSJ - Corte Suprema de Justicia de la Nacion, CIV - Camara Nacional de Apelaciones en lo Civil, CAF - Camara Nacional de Apelaciones en lo Contencioso Administrativo Federal, CCF - Camara Nacional de Apelaciones en lo Civil y Comercial Federal, CNE - Camara Nacional Electoral, CSS - Camara Federal de la Seguridad Social, CPE - Camara Nacional de Apelaciones en lo Penal Economico, CNT - Camara Nacional de Apelaciones del Trabajo, CFP - Camara Criminal y Correccional Federal, CCC - Camara Nacional de Apelaciones en lo Criminal y Correccional, COM - Camara Nacional de Apelaciones en lo Comercial, CPF - Camara Federal de Casacion Penal, CPN - Camara Nacional Casacion Penal, FBB - Justicia Federal de Bahia Blanca, FCR - Justicia Federal de Comodoro Rivadavia, FCB - Justicia Federal de Cordoba, FCT - Justicia Federal de Corrientes, FGR - Justicia Federal de General Roca, FLP - Justicia Federal de La Plata, FMP - Justicia Federal de Mar del Plata, FMZ - Justicia Federal de Mendoza, FPO - Justicia Federal de Posadas, FPA - Justicia Federal de Parana, FRE - Justicia Federal de Resistencia, FSA - Justicia Federal de Salta, FRO - Justicia Federal de Rosario, FSM - Justicia Federal de San Martin, FTU - Justicia Federal de Tucuman.)",
    "juzgado": "juzgado que emitio la sentencia (No debes darlo todo en mayusculas, por ejemplo si el juzgado es CAMARA FEDERAL DE SALTA 1 , Darlo como Camara Federal de Salta 1, respeta la gramatica)",
    "caratula": "caratula de la sentencia",
    "fundamentos": "fundamentos legales de la sentencia",
    "normativa": "normativa aplicada en la sentencia (si no se menciona, indica: 'No se menciona normativa')",
    "numero_resolucion": "numero de resolucion (si no se menciona, indica: 'No se menciona numero de resolucion')",
    "estado_sentencia": "estado de la sentencia (ejemplo: Firme, Sujeta a Revision)"
}}

Texto de los documentos:
{texto_pdfs}
"""

        # En este caso se envía un único elemento con todo el contenido (imagen + prompt)
        contenido = [{"text": prompt}]
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(contenido)
        json_response = response.text

        # Buscar el bloque JSON en la respuesta
        match = re.search(r'\{.*\}', json_response.replace('\n', ''), re.DOTALL)
        if match:
            json_response = match.group(0)
            print("JSON extraido:", json_response)
        else:
            print("No se encontro un JSON valido en la respuesta")
            return None

        # Convertir la respuesta en JSON
        try:
            data = json.loads(json_response)
            return data
        except json.decoder.JSONDecodeError as e:
            print(f"Error al analizar JSON: {e}")
            print(f"JSON recibido: {json_response}")
            return None

    except Exception as e:
        print(f"Error al llamar a la API de Gemini: {e}")
        return None

def save_sentencia_to_db(data):
    """Inserta en la tabla 'sentencias' todos los datos extraidos,
    incluyendo el drive_link y file_hash."""
    fecha_str = data.get("fecha_sentencia")
    fecha_date = convertir_fecha(fecha_str) if fecha_str else None

    sentencia_data = {
        "resumen": data.get("resumen"),
        "honorarios": data.get("honorarios"),
        "instancia": data.get("instancia"),
        "jueces": data.get("jueces"),
        "nombre_caso": data.get("nombre_caso"),
        "numero_expediente": data.get("numero_expediente"),
        "fecha_sentencia": fecha_date,
        "palabras_clave": data.get("palabras_clave"),
        "jurisdiccion": data.get("jurisdiccion"),
        "juzgado": data.get("juzgado"),
        "caratula": data.get("caratula"),
        "fundamentos": data.get("fundamentos"),
        "normativa": data.get("normativa"),
        "numero_resolucion": data.get("numero_resolucion"),
        "estado_sentencia": data.get("estado_sentencia"),
        "drive_link": data.get("drive_link"),
        "file_hash": data.get("file_hash")
    }

    insert_query = text("""
        INSERT INTO sentencias (
            resumen, honorarios, instancia, jueces, nombre_caso, numero_expediente,
            fecha_sentencia, palabras_clave, jurisdiccion, juzgado, caratula,
            fundamentos, normativa, numero_resolucion, estado_sentencia,
            drive_link, file_hash
        ) VALUES (
            :resumen, :honorarios, :instancia, :jueces, :nombre_caso, :numero_expediente,
            :fecha_sentencia, :palabras_clave, :jurisdiccion, :juzgado, :caratula,
            :fundamentos, :normativa, :numero_resolucion, :estado_sentencia,
            :drive_link, :file_hash
        )
    """)
    try:
        with engine.begin() as connection:
            result = connection.execute(insert_query, sentencia_data)
            print("Filas insertadas:", result.rowcount)
        print("Datos insertados en la base de datos.")
    except Exception as e:
        print("Error al insertar en la base de datos:", e)


def update_sentencia_in_db(data):
    fecha_str = data.get("fecha_sentencia")
    fecha_date = convertir_fecha(fecha_str) if fecha_str else None

    sentencia_data = {
        "id": data.get("id"),
        "resumen": data.get("resumen"),
        "honorarios": data.get("honorarios"),
        "instancia": data.get("instancia"),
        "jueces": data.get("jueces"),
        "nombre_caso": data.get("nombre_caso"),
        "numero_expediente": data.get("numero_expediente"),
        "fecha_sentencia": fecha_date,
        "palabras_clave": data.get("palabras_clave"),
        "jurisdiccion": data.get("jurisdiccion"),
        "juzgado": data.get("juzgado"),
        "caratula": data.get("caratula"),
        "fundamentos": data.get("fundamentos"),
        "normativa": data.get("normativa"),
        "numero_resolucion": data.get("numero_resolucion"),
        "estado_sentencia": data.get("estado_sentencia"),
        "drive_link": data.get("drive_link"),  # Se agrega el drive_link
        "file_hash": data.get("file_hash")       # Se agrega el hash del archivo
    }

    update_query = text("""
        UPDATE sentencias SET
            resumen = :resumen,
            honorarios = :honorarios,
            instancia = :instancia,
            jueces = :jueces,
            nombre_caso = :nombre_caso,
            numero_expediente = :numero_expediente,
            fecha_sentencia = :fecha_sentencia,
            palabras_clave = :palabras_clave,
            jurisdiccion = :jurisdiccion,
            juzgado = :juzgado,
            caratula = :caratula,
            fundamentos = :fundamentos,
            normativa = :normativa,
            numero_resolucion = :numero_resolucion,
            estado_sentencia = :estado_sentencia,
            drive_link = :drive_link,
            file_hash = :file_hash
        WHERE id = :id
    """)

    try:
        with engine.begin() as connection:
            result = connection.execute(update_query, sentencia_data)
            print("Filas actualizadas:", result.rowcount)
        print("Datos actualizados en la base de datos.")
    except Exception as e:
        print("Error al actualizar en la base de datos:", e)
