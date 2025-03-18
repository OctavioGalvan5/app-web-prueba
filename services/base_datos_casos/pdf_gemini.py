import PyPDF2
import pdfplumber
import re
import json
import google.generativeai as genai
import hashlib
from datetime import datetime
from sqlalchemy import text
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

def analyze_legal_documents(texto_pdfs):
    try:
        # Configura la API (actualiza la key según corresponda)
        genai.configure(api_key="AIzaSyCGw6VPHjs6zIopfdQR6exHZXkKJdlZOCU")
        prompt = f"""Eres un asistente legal experto en analizar sentencias judiciales. Los siguientes documentos estan relacionados con un mismo caso. Analiza la informacion y proporciona un resumen consolidado en formato JSON, Importante: NO uses acentos (reemplaza las vocales acentuadas por sus equivalentes sin acento):

{{
    "resumen": "resumen breve del caso considerando ambos documentos, minimo 200 palabras",
    "honorarios": "cantidad de honorarios mencionados en los documentos. Importante: deben ser los mas recientes, y deben ser devueltos de la siguiente manera, por ejemplo si los honorarios son $125.456,56, se devolvera como 125456.56 (si no se mencionan, indica devolver \"\" es decir null)",
    "instancia": "instancia (ejemplo: Primera Instancia, Segunda Instancia, Instancia extraordinaria, Ministerio Publico fiscal etc.)
    Si se habla de Juzgado Federal entonces se refiere a Primera Instancia, si habla de Camara Federal o Tribunal es una segunda instancia,",
    "jueces": "nombres de los jueces que dictaron la sentencia (se los mencionan en la firma digital al final del pdf) en juzgado hay solo un juez por lo general, mientras que en camara hay varios, si hay alguna abstencion de firma mencionarlo (el porque) ",
    "nombre_caso": "nombre del caso (No debes darlo todo en mayusculas, por ejemplo Si el Caso se llama PEDRO GUZMAN C/ANSES, Darlo como Pedro Guzman C/Anses, respeta la gramatica)",
    "numero_expediente": "numero de expediente",
    "fecha_sentencia": "fecha de la sentencia, damela en formato DD/MM/AAAA, en caso de no tener el dia, ponerlo como 01/MM/AAAA, tambien podes sacarlo en la firma digital al final del pdf",
    "palabras_clave": "palabras clave mas relevantes del caso (ten en cuenta si menciona algunas de la siguientes: movilidad, tope, PBU, cosa juzgada, vias de hecho, costas, honorarios, suma no remunerativas, error material, caducidad, jubilacion, pension, retiro por invalidez, regularidad, recurso directo, incapacidad, ganancias, acumulacion de beneficios, obra social)",
    "jurisdiccion": "jurisdiccion a la que pertenece la sentencia (pueden ser las siguientes: CSJ - Corte Suprema de Justicia de la Nación, CIV - Cámara Nacional de Apelaciones en lo Civil, CAF - Cámara Nacional de Apelaciones en lo Contencioso Administrativo Federal, CCF - Cámara Nacional de Apelaciones en lo Civil y Comercial Federal, CNE - Cámara Nacional Electoral, CSS - Cámara Federal de la Seguridad Social, CPE - Cámara Nacional de Apelaciones en lo Penal Económico, CNT - Cámara Nacional de Apelaciones del Trabajo, CFP - Cámara Criminal y Correccional Federal, CCC - Cámara Nacional de Apelaciones en lo Criminal y Correccional, COM - Cámara Nacional de Apelaciones en lo Comercial, CPF - Cámara Federal de Casación Penal, CPN - Cámara Nacional Casación Penal, FBB - Justicia Federal de Bahía Blanca, FCR - Justicia Federal de Comodoro Rivadavia, FCB - Justicia Federal de Córdoba, FCT - Justicia Federal de Corrientes, FGR - Justicia Federal de General Roca, FLP - Justicia Federal de La Plata, FMP - Justicia Federal de Mar del Plata, FMZ - Justicia Federal de Mendoza, FPO - Justicia Federal de Posadas, FPA - Justicia Federal de Paraná, FRE - Justicia Federal de Resistencia, FSA - Justicia Federal de Salta, FRO - Justicia Federal de Rosario, FSM - Justicia Federal de San Martín, FTU - Justicia Federal de Tucumán.)",
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
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        json_response = response.text

        # Buscar el bloque JSON en la respuesta
        match = re.search(r'\{.*\}', json_response.replace('\n', ''), re.DOTALL)
        if match:
            json_response = match.group(0)
            print("JSON extraido:", json_response)
        else:
            print("No se encontro un JSON valido en la respuesta")
            return None

        # Cargar y decodificar el JSON
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
