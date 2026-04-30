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
from flask import Flask, render_template
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# Definir los alcances (scopes)
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# En vez de especificar la ruta al archivo JSON, obtenemos el JSON desde la variable de entorno
credentials_json = os.getenv("GOOGLE_CREDENTIALS")
if credentials_json is None:
    raise Exception("La variable de entorno 'GOOGLE_CREDENTIALS' no está definida.")

# Convertir la cadena JSON a un diccionario de Python
credentials_info = json.loads(credentials_json)

# Crear las credenciales usando la información del service account y los scopes definidos
CREDS = ServiceAccountCredentials.from_json_keyfile_name(credentials_info, SCOPE)
drive_service = build('drive', 'v3', credentials=credentials)