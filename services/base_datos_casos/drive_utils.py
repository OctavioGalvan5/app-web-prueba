# ================== Funciones para subir a Google Drive ==================

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import PyPDF2
import re
import json
import os
import google.generativeai as genai
import hashlib
from datetime import datetime
from sqlalchemy import text
from models.database import engine  # Verifica que la conexión esté bien configurada
from services.base_datos_casos.pdf_gemini import analyze_legal_documents, extract_text_from_pdf, save_sentencia_to_db
import fitz  # PyMuPDF
from io import BytesIO

# Definir los alcances (scopes)
SCOPES = ['https://www.googleapis.com/auth/drive']

# En vez de especificar la ruta al archivo JSON, obtenemos el JSON desde la variable de entorno
credentials_json = os.getenv("GOOGLE_CREDENTIALS")
if credentials_json is None:
    raise Exception("La variable de entorno 'GOOGLE_CREDENTIALS' no está definida.")

# Convertir la cadena JSON a un diccionario de Python
credentials_info = json.loads(credentials_json)

# Crear las credenciales usando la información del service account y los scopes definidos
credentials = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

def extract_last_page_image(file_obj):
    """
    Extrae la última página del PDF y la devuelve como un objeto BytesIO en formato JPEG.
    """
    # Leer todo el contenido del archivo PDF
    file_bytes = file_obj.read()
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        print("Error al abrir el PDF:", e)
        return None

    if doc.page_count == 0:
        return None

    # Cargar la última página (índice: page_count - 1)
    last_page = doc.load_page(doc.page_count - 1)
    pix = last_page.get_pixmap()
    image_bytes = pix.tobytes("jpeg")

    image_io = BytesIO(image_bytes)
    image_io.seek(0)
    return image_io

def calculate_file_hash(file_obj):
    """
    Calcula el hash SHA256 de un archivo.
    Se asegura de resetear el puntero al inicio.
    """
    file_obj.seek(0)
    hash_obj = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(4096), b""):
        hash_obj.update(chunk)
    file_obj.seek(0)
    return hash_obj.hexdigest()

def upload_file_to_drive(file_obj, file_name, mime_type='application/pdf'):
    """
    Sube un archivo a Google Drive y lo hace público, devolviendo el link para visualizarlo.
    """
    file_metadata = {
        'name': file_name,
        'parents': ['11rZq1rXKIfU-W5kScExZzrGSAOJ7nFXk']  # Reemplaza 'ID_de_la_carpeta' con el ID real de la carpeta en Drive
    }


    media = MediaIoBaseUpload(file_obj, mimetype=mime_type, resumable=False)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    file_id = file.get('id')
    web_view_link = file.get('webViewLink')

    # Hacer el archivo público
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }
    drive_service.permissions().create(fileId=file_id, body=permission).execute()

    return web_view_link, file_id

def file_hash_exists(file_hash):
    """
    Verifica si el hash ya existe en la base de datos.
    Se asume que la tabla 'sentencias' tiene la columna 'file_hash'.
    """
    query = text("SELECT COUNT(*) FROM sentencias WHERE file_hash = :file_hash")
    with engine.connect() as connection:
        result = connection.execute(query, {"file_hash": file_hash})
        count = result.scalar()
    return count > 0

# ================== Función principal para procesar y guardar el PDF ==================

def process_and_save_file(file_obj, file_name, update=False):
    """
    Procesa y guarda un archivo PDF. Si update es False se inserta un nuevo registro;
    si es True se omite la inserción, dejando al usuario actualizar el registro existente.
    """
    # Calcular el hash del archivo
    file_hash = calculate_file_hash(file_obj)

    # Verificar si el archivo ya fue subido
    if file_hash_exists(file_hash):
        return None, f"El archivo {file_name} ya ha sido subido previamente."

    # Reinicia el puntero y extrae el texto del PDF
    file_obj.seek(0)
    texto = extract_text_from_pdf(file_obj)
    if not texto:
        return None, "No se pudo extraer texto del archivo PDF."

    # Extraer la imagen de la última página
    file_obj.seek(0)
    ultima_imagen = extract_last_page_image(file_obj)
    if not ultima_imagen:
        return None, "No se pudo extraer la imagen de la última página del PDF."

    # Llama a la función que analiza el documento con IA,
    # pasando tanto el texto como la imagen de la última página
    sentencia_data = analyze_legal_documents(texto, ultima_imagen)
    if not sentencia_data:
        return None, "Error al analizar el documento con la API."

    # Sube el archivo a Google Drive (se reinicia el puntero nuevamente)
    file_obj.seek(0)
    drive_link, drive_id = upload_file_to_drive(file_obj, file_name)

    # Agrega el link de Drive y el hash al diccionario obtenido
    sentencia_data['drive_link'] = drive_link
    sentencia_data['file_hash'] = file_hash

    # Si no se está actualizando, se inserta un nuevo registro en la base de datos.
    if not update:
        save_sentencia_to_db(sentencia_data)

    return drive_link, None


def delete_drive_file(drive_link):
    """
    Elimina un archivo de Google Drive utilizando el link proporcionado.
    Extrae el ID del archivo del link y llama a la API de Drive para borrarlo.

    Retorna:
        None si se eliminó correctamente,
        un mensaje de error en caso de fallo.
    """
    # Extraer el ID del archivo del link utilizando una expresión regular
    import re
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_link)
    if not match:
        return "No se pudo extraer el ID del archivo de Drive."
    file_id = match.group(1)

    try:
        # Llamar a la API para eliminar el archivo
        drive_service.files().delete(fileId=file_id).execute()
        return None
    except Exception as e:
        return str(e)
