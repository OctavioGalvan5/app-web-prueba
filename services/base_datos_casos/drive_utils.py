# ================== Funciones para subir a Google Drive ==================

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import PyPDF2
import re
import json
import google.generativeai as genai
import hashlib
from datetime import datetime
from sqlalchemy import text
from models.database import engine  # Verifica que la conexión esté bien configurada
from services.base_datos_casos.pdf_gemini import analyze_legal_documents, extract_text_from_pdf, save_sentencia_to_db

# Configuración de la API de Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'services/base_datos_casos/estudiotye-16f681dda2bb.json'  # Actualiza esta ruta

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

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

def process_and_save_file(file_obj, file_name):
    """
    Realiza el siguiente flujo:
      1. Calcula el hash del archivo y verifica que no exista en la BD.
      2. Si no existe, extrae el texto del PDF y llama a analyze_legal_documents para obtener
         los datos (resumen, honorarios, etc.).
      3. Sube el archivo a Google Drive para obtener el link.
      4. Agrega drive_link y file_hash al diccionario obtenido y lo guarda en la BD.

    Retorna:
      - drive_link: En caso de éxito.
      - mensaje de error si el archivo ya existe o hubo problemas en el análisis.
    """
    # Calcula el hash del archivo
    file_hash = calculate_file_hash(file_obj)

    # Verifica si el archivo ya fue subido
    if file_hash_exists(file_hash):
        return None, f"El archivo {file_name} ya ha sido subido previamente."

    # Reinicia el puntero y extrae el texto del PDF para analizarlo
    file_obj.seek(0)
    texto = extract_text_from_pdf(file_obj)
    if not texto:
        return None, "No se pudo extraer texto del archivo PDF."

    # Llama a la función que analiza el documento con IA
    sentencia_data = analyze_legal_documents(texto)
    if not sentencia_data:
        return None, "Error al analizar el documento con la API."

    # Sube el archivo a Google Drive (se reinicia el puntero nuevamente)
    file_obj.seek(0)
    drive_link, drive_id = upload_file_to_drive(file_obj, file_name)

    # Agrega el link de Drive y el hash al diccionario obtenido por analyze_legal_documents
    sentencia_data['drive_link'] = drive_link
    sentencia_data['file_hash'] = file_hash

    # Inserta todos los datos en la base de datos
    save_sentencia_to_db(sentencia_data)

    return drive_link, None