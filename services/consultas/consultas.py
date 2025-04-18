import google.generativeai as genai
import base64
import os
import json
from datetime import datetime
from sqlalchemy import text
from models.database import engine  # Verifica que la conexión esté bien configurada
from io import BytesIO
import fitz  # PyMuPDF
from PIL import Image

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


def geminis_api_extract_data(image_streams):
    modelo = genai.GenerativeModel("gemini-2.0-flash")
    try:
        contenido = []
        # Iterar sobre cada archivo (imagen) y convertirlo a base64
        for stream in image_streams:
            # Aseguramos que el puntero esté al inicio
            stream.seek(0)
            image_b64 = base64.b64encode(stream.read()).decode("utf-8")
            contenido.append({"mime_type": "image/jpeg", "data": image_b64})

        # Agregar la instrucción de análisis como el último ítem
        contenido.append({
            "text": """Eres un asistente legal experto en analizar imágenes de documentos. 
Analiza las imágenes de DNI y proporciona la siguiente información en formato JSON:
{
    "dni_number": "Número de DNI, darlo de la siguiente manera, por ejemplo 45879598, es decir sin puntos",
    "cuil_number": "Número de CUIL, si esta en formato por ejemplo 20-34979576-5, devolver 20349795765",
    "phone_number": "Aqui siempre devolveras vacio",
    "name": "Nombre completo, por ejemplo no coloques MARIA LUCIA PEREZ GOMEZ, coloca Maria Lucia",
    "surname": "Apellido completo, por ejemplo no coloques MARIA LUCIA PEREZ GOMEZ, coloca Perez Gomez",
    "full_name": "Apellido y Nombre completo, por ejemplo Perez Gomez Maria Lucia",
    "full_name_2": "Nombre y Apellido completo, por ejemplo Maria Lucia Perez Gomez",
    "sexo": "Sexo, por ejemplo si lees 'F', pondras unicamente 'Femenino', si lees 'M' pondras unicamente 'Masculino'",
    "sexo_femenino": "si lees 'F' entonces devolveras unas 'X' sino devolveras '' es decir vacio",
    "sexo_masculino": "si lees 'M' entonces devolveras unas 'X' sino devolveras '' es decir vacio",
    "date_of_birth": "YYYY-MM-DD",
    "entry_date": "Fecha de ingreso al pais (no siempre tendra), devolver en formato YYYY-MM-DD",
    "nationality": "Nacionalidad, un ejemplo puede ser Argentina, Brasileña, Chilena, etc",
    "address": "Dirección, por ejemplo si lees 'O' HIGGINS 1673 DT/C B° 20 DE FEBRERO - SALTA - SALTA CAPITAL - SALTA', pondras unicamente 'Ohiggins 1673 DT/C B° 20 De Febrero'",
    "adress_number": "Numero de la dirección, por ejemplo si lees 'O' HIGGINS 1673 DT/C B° 20 DE FEBRERO - SALTA - SALTA CAPITAL - SALTA', pondras unicamente '1673'",
    "province": "Provincia, por ejemplo si lees 'O' HIGGINS 1673 DT/C B° 20 DE FEBRERO - SALTA - SALTA CAPITAL - SALTA', pondras unicamente 'Salta'",
    "department": "Provincia, por ejemplo si lees 'O' HIGGINS 1673 DT/C B° 20 DE FEBRERO - SALTA - SALTA CAPITAL - SALTA', pondras unicamente 'Salta Capital'",
    "city": "Provincia, por ejemplo si lees 'O' HIGGINS 1673 DT/C B° 20 DE FEBRERO - SALTA - SALTA CAPITAL - SALTA', pondras unicamente 'Salta'",


}"""
        })

        print("📨 Enviando datos a la API de Gemini...")

        # Enviar la solicitud a la API
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
        # Limpiar el texto recibido, eliminando posibles delimitadores
        json_texto = json_texto.strip().strip("```json").strip("```")
        print("📑 JSON limpio:", json_texto)

        # Convertir la respuesta en JSON
        datos = json.loads(json_texto)

        # Validar claves necesarias
        claves_requeridas = ["dni_number", "cuil_number", "phone_number", "name", "surname", "full_name", "full_name_2", "sexo", "sexo_femenino", "sexo_masculino", "date_of_birth", "entry_date", "nationality", "address", "adress_number", "province", "department", "city"]
        for clave in claves_requeridas:
            datos.setdefault(clave, "")

        return datos
    except json.JSONDecodeError as e:
        print("❌ Error al decodificar JSON en procesar_datos_extraidos:", str(e))
        return None

def update_cliente_in_db(data):
    fecha_str = data.get("fecha_de_nacimiento")
    fecha_date = convertir_fecha(fecha_str) if fecha_str else None
    fecha_str = data.get("fecha_de_ingreso")
    fecha_ingreso = convertir_fecha(fecha_str) if fecha_str else None
    cliente_data = {
        "id": data.get("id"),
        "nombre": data.get("nombre"),
        "apellido": data.get("apellido"),
        "numero_celular": data.get("numero_celular"),
        "nombre_completo": data.get("nombre_completo"),
        "nombre_completo_2": data.get("nombre_completo_2"),
        "sexo": data.get("sexo"),
        "sexo_femenino": data.get("sexo_femenino"),
        "sexo_masculino": data.get("sexo_masculino"),
        "numero_dni": data.get("numero_dni"),
        "fecha_de_nacimiento": fecha_date,
        "fecha_de_ingreso": fecha_ingreso,
        "numero_cuil": data.get("numero_cuil"),
        "nacionalidad": data.get("nacionalidad"),
        "direccion": data.get("direccion"),
        "numero_direccion": data.get("numero_direccion"),
        "provincia": data.get("provincia"),
        "departamento": data.get("departamento"),
        "ciudad": data.get("ciudad"),

    }

    update_query = text("""
        UPDATE data_clientes SET
            nombre = :nombre,
            apellido = :apellido,
            numero_celular = :numero_celular,
            nombre_completo = :nombre_completo,
            nombre_completo_2 = :nombre_completo_2,
            sexo = :sexo,
            sexo_femenino = :sexo_femenino,
            sexo_masculino = :sexo_masculino,
            numero_dni = :numero_dni,
            fecha_de_nacimiento = :fecha_de_nacimiento,
            fecha_de_ingreso = :fecha_de_ingreso,
            numero_cuil = :numero_cuil,
            nacionalidad = :nacionalidad,
            direccion = :direccion,
            numero_direccion = :numero_direccion,
            provincia = :provincia,
            departamento = :departamento,
            ciudad = :ciudad
        WHERE id = :id
    """)

    try:
        with engine.begin() as connection:
            result = connection.execute(update_query, cliente_data)
            print("Filas actualizadas:", result.rowcount)
        print("Datos actualizados en la base de datos.")
    except Exception as e:
        print("Error al actualizar en la base de datos:", e)



def convert_pdf_to_image(file):
    file_bytes = file.read()
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        print("Error al abrir el PDF:", e)
        return None
    if doc.page_count == 0:
        return None
    # Procesa la primera página
    page = doc.load_page(0)
    pix = page.get_pixmap()
    # Convertir el pixmap a bytes en formato JPEG
    image_bytes = pix.tobytes("jpeg")
    # Envolver en BytesIO para que se comporte como un stream
    image_io = BytesIO(image_bytes)
    image_io.seek(0)
    return image_io

# Función para procesar el archivo: si es PDF se convierte; si es imagen, se envuelve en BytesIO
def process_file(file):
    if file.filename.lower().endswith('.pdf'):
        return convert_pdf_to_image(file)
    else:
        file_bytes = file.read()
        file_io = BytesIO(file_bytes)
        file_io.seek(0)
        return file_io