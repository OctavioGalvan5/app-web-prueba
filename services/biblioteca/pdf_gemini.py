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


def analyze_book_document(texto_pdfs):
    try:
        # Configurar la API (actualiza la key según corresponda)
        genai.configure(api_key="AIzaSyCGw6VPHjs6zIopfdQR6exHZXkKJdlZOCU")


        # Construir el prompt de análisis, incluyendo la imagen en base64 al inicio
        prompt = f"""Eres un asistente bibliotecario experto en analizar libros. A partir del texto extraído de un archivo PDF de un libro, extrae la siguiente información en formato JSON. Importante: NO uses acentos (reemplaza las vocales acentuadas por sus equivalentes sin acento). Si no se encuentra claramente un dato, devolvelo como cadena vacia ("").

        {{
            "autor": "apellido y nombre del autor o autores del libro (por ejemplo: Perez, Juan). Si hay varios, separalos por coma.",
            "titulo": "titulo del libro (respetando mayusculas y minusculas, sin todo en mayuscula)",
            "categoria": "categoria general del libro (por ejemplo: Derecho, Historia, Literatura, Ciencias Sociales, etc.)",
            "edicion": "informacion de la edicion (por ejemplo: Segunda edicion, Ediciones Jurídicas, etc.)",
            "anio_publicacion": "anio de publicacion (solo el año, por ejemplo: 2021. Si no se encuentra, devolver \"\")",
            "palabras_clave": "palabras clave relevantes del libro separadas por coma (por ejemplo: seguridad social, jurisprudencia, reforma previsional)",
            "resumen": "resumen breve del contenido del libro, minimo 100 palabras, redactado en tercera persona. No repetir titulo ni autor en el resumen"
        }}

        Texto extraido del libro:
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

def save_libro_to_db(data):
    """Inserta un libro en la tabla 'libros', incluyendo el drive_link y el file_hash."""

    libro_data = {
        "autor": data.get("autor"),
        "titulo": data.get("titulo"),
        "categoria": data.get("categoria"),
        "edicion": data.get("edicion"),
        "anio": int(data["anio_publicacion"]) if data.get("anio_publicacion") else None,
        "palabras_clave": data.get("palabras_clave"),
        "resumen": data.get("resumen"),
        "drive_link": data.get("drive_link"),
        "file_hash": data.get("file_hash")
    }

    insert_query = text("""
        INSERT INTO libros (
            autor, titulo, categoria, edicion, anio,
            palabras_clave, resumen, drive_link, file_hash
        ) VALUES (
            :autor, :titulo, :categoria, :edicion, :anio,
            :palabras_clave, :resumen, :drive_link, :file_hash
        )
    """)

    try:
        with engine.begin() as connection:
            result = connection.execute(insert_query, libro_data)
            print("Libro insertado correctamente:", result.rowcount)
    except Exception as e:
        print("Error al insertar el libro en la base de datos:", e)


def update_libro_in_db(data):
    """Actualiza un libro en la tabla 'libros' por su ID."""

    libro_data = {
        "id": data.get("id"),
        "autor": data.get("autor"),
        "titulo": data.get("titulo"),
        "categoria": data.get("categoria"),
        "edicion": data.get("edicion"),
        "anio": int(data["anio"]),
        "palabras_clave": data.get("palabras_clave"),
        "resumen": data.get("resumen"),
        "drive_link": data.get("drive_link"),
        "file_hash": data.get("file_hash")
    }

    update_query = text("""
        UPDATE libros SET
            autor = :autor,
            titulo = :titulo,
            categoria = :categoria,
            edicion = :edicion,
            anio = :anio,
            palabras_clave = :palabras_clave,
            resumen = :resumen,
            drive_link = :drive_link,
            file_hash = :file_hash
        WHERE id = :id
    """)

    try:
        with engine.begin() as connection:
            result = connection.execute(update_query, libro_data)
            print("Libro actualizado correctamente:", result.rowcount)
    except Exception as e:
        print("Error al actualizar el libro en la base de datos:", e)

