import google.generativeai as genai
import base64
import os
import json
from datetime import datetime
from sqlalchemy import text
from models.database import engine  # Verifica que la conexión esté bien configurada


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

# Configurar la API de Gemini
genai.configure(api_key="AIzaSyCGw6VPHjs6zIopfdQR6exHZXkKJdlZOCU")


def geminis_api_extract_data(front_image, back_image):
    modelo = genai.GenerativeModel("gemini-2.0-flash")
    try:
        # Convertir imágenes a base64
        front_b64 = base64.b64encode(front_image.read()).decode("utf-8")
        back_b64 = base64.b64encode(back_image.read()).decode("utf-8")

        print("✅ Imágenes convertidas a base64 correctamente")

        # Prepara el contenido para la API
        contenido = [
            {"mime_type": "image/jpeg", "data": front_b64},
            {"mime_type": "image/jpeg", "data": back_b64},
            {
                "text": """Eres un asistente legal experto en analizar imágenes de documentos. 
                Analiza las imágenes de DNI y proporciona la siguiente información en formato JSON:
                {
                    "dni_number": "Número de DNI",
                    "cuil_number": "Número de CUIL",
                    "name": "Nombre completo, por ejemplo no coloques MARIA PEREZ, coloca Maria Perez",
                    "date_of_birth": "YYYY-MM-DD",
                    "nationality": "Nacionalidad",
                    "address": "Dirección"
                }"""
            },
        ]

        print("📨 Enviando datos a la API de Gemini...")

        # Envía la solicitud a la API
        respuesta = modelo.generate_content(contenido)

        if not respuesta or not hasattr(respuesta, 'text'):
            print("❌ La API de Gemini no devolvió una respuesta válida.")
            return None, "Respuesta vacía o incorrecta de la API"

        print("✅ Respuesta recibida de Gemini:", respuesta.text)

        # Procesar los datos JSON
        return procesar_datos_extraidos(respuesta.text), None

    except Exception as e:
        print("❌ Error en geminis_api_extract_data:", str(e))
        return None, str(e)

def procesar_datos_extraidos(json_texto):
    try:
        # Limpiar el texto recibido, eliminando las comillas invertidas si están presentes
        json_texto = json_texto.strip().strip("```json").strip("```")

        print("📑 JSON limpio:", json_texto)  # Verificar que ahora es un JSON válido

        # Convertir la respuesta en JSON
        datos = json.loads(json_texto)

        # Validar claves necesarias
        claves_requeridas = ["dni_number", "cuil_number", "name", "date_of_birth", "nationality", "address"]
        for clave in claves_requeridas:
            datos.setdefault(clave, "")  # Si falta una clave, se asigna una cadena vacía

        return datos
    except json.JSONDecodeError as e:
        print("❌ Error al decodificar JSON en procesar_datos_extraidos:", str(e))
        return None

def update_cliente_in_db(data):
    fecha_str = data.get("fecha_de_nacimiento")
    fecha_date = convertir_fecha(fecha_str) if fecha_str else None
    cliente_data = {
        "id": data.get("id"),
        "nombre": data.get("nombre"),
        "numero_dni": data.get("numero_dni"),
        "fecha_de_nacimiento": fecha_date,
        "numero_cuil": data.get("numero_cuil"),
        "nacionalidad": data.get("nacionalidad"),
        "direccion": data.get("direccion"),
    }

    update_query = text("""
        UPDATE data_clientes SET
            nombre = :nombre,
            numero_dni = :numero_dni,
            fecha_de_nacimiento = :fecha_de_nacimiento,
            numero_cuil = :numero_cuil,
            nacionalidad = :nacionalidad,
            direccion = :direccion
        WHERE id = :id
    """)

    try:
        with engine.begin() as connection:
            result = connection.execute(update_query, cliente_data)
            print("Filas actualizadas:", result.rowcount)
        print("Datos actualizados en la base de datos.")
    except Exception as e:
        print("Error al actualizar en la base de datos:", e)
