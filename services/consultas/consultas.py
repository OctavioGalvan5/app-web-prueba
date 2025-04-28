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

# En consultas.py, define esta lista (puede ir al inicio del archivo, por ejemplo)
# Mapeo de nombres de checkboxes HTML a nombres de columnas en la base de datos
CHECKBOX_MAPPING = {
    "formularios_Reconocimiento_de_Servicios": "formularios_reconocimiento_servicios",
    "formularios_Jubilación": "formularios_jubilacion",
    "formularios_Jubilación_con_24.476": "formularios_jubilacion_con_24_476",
    "formularios_Jubilación_con_27.705": "formularios_jubilacion_con_27_705",
    "formularios_Jubilación_docente": "formularios_jubilacion_docente",
    "formularios_Jubilación_serv_diferenciales": "formularios_jubilacion_serv_diferenciales",
    "formularios_Jubilación_Servicio_Doméstico": "formularios_jubilacion_servicio_domestico",
    "formularios_Jubilación_HIV": "formularios_jubilacion_hiv",
    "formularios_Jubilación_trabajadores_minusvalidos_ceguera": "formularios_jubilacion_minusvalidos_ceguera",
    "formularios_Pension_Directa_casados": "formularios_pension_directa_casados",
    "formularios_Pension_Directa_convivientes": "formularios_pension_directa_convivientes",
    "formularios_Pension_Deriva_casados": "formularios_pension_derivada_casados",
    "formularios_Pension_Deriva_convivientes": "formularios_pension_derivada_convivientes",
    "formularios_Pension_Directa_Derivada_hijo_discapacitada": "formularios_pension_directa_derivada_hijo_discapacitada",
    "formularios_Retiro_Transitorio_por_invalidez": "formularios_retiro_transitorio_por_invalidez",
    "formularios_Retiro_Transitorio_por_invalidez_SDM": "formularios_retiro_transitorio_por_invalidez_sdm",
    "formularios_PUAM": "formularios_puam",
    "formularios_UCAP": "formularios_ucap",
    "formularios_Reajuste_de_Haberes": "formularios_reajuste_de_haberes",
    "formularios_asignacion_fliar_hijo_discapacitado": "formularios_asignacion_fliar_hijo_discapacitado",
    "(Beneficios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado": "beneficios_nuevo_convenio_de_honorarios_numerado",
    "(Juicios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado": "juicios_nuevo_convenio_de_honorarios_numerado",
    "CONVENIO_MAGISTRADOS": "convenio_magistrados",
    "CONVENIO_DE_GASTOS_ADMINISTRATIVOS_JUDICIALES": "convenio_de_gastos_administrativos_judiciales",
    "2.91_Guarda_Documental": "_2_91_guarda_documental",
    "6.18_Solicitud_Prestaciones_Previsionales": "_6_18_solicitud_prestaciones_previsionales",
    "6.18_Solicitud_Prestaciones_Previsionales_pension": "_6_18_solicitud_prestaciones_previsionales_pension",
    "Acta_Poder": "acta_poder",
    "Anexo_Baja_Puam": "anexo_baja_puam",
    "Anexo_I_Ley_27.625": "anexo_i_ley_27625",
    "Anexo_II_DEC_894_01": "anexo_ii_dec_894_01",
    "Anexo_II_980_05": "anexo_ii_980_05",
    "Anexo_II_Socioeconómico_24.476": "anexo_ii_socioeconomico_24_476",
    "Baja_PNC": "baja_pnc",
    "Carta_Poder_SRT": "carta_poder_srt",
    "DDJJ_de_salud_resol_300": "ddjj_de_salud_resol_300",
    "DDJJ_Ley_17562_6.9": "ddjj_ley_17562_6_9",
    "F_3283_Autorización_ARCA": "f_3283_autorizacion_arca",
    "Formulario_Carta_Poder_(CSS)": "formulario_carta_poder_css",
    "Formulario_encuesta_RTI": "formulario_encuesta_rti",
    "PS_1.75_Carta_Poder_Cap_III_27.705": "ps_1_75_carta_poder_cap_iii_27705",
    "PS_5.7_Derivacion_aportes_Obra_Social": "ps_5_7_derivacion_aportes_obra_social",
    "PS_5.11_Aceptacion_de_la_Obra_Social": "ps_5_11_aceptacion_de_la_obra_social",
    "PS_6.292_DDJJ_solicitante_SDM": "ps_6_292_ddjj_solicitante_sdm",
    "PS_6.293_DDJJ_Dador_de_trabajo_SDM": "ps_6_293_ddjj_dador_de_trabajo_sdm",
    "PS_6.294_DDJJ_renuncia_SDM": "ps_6_294_ddjj_renuncia_sdm",
    "PS_6.2_Certific_de_Servicios": "ps_6_2_certific_de_servicios",
    "PS_6.3_Nivel_de_estudios_RTI": "ps_6_3_nivel_de_estudios_rti",
    "PS_6.4_Carta_Poder": "ps_6_4_carta_poder",
    "PS_6.8_DDJJ_TESTIMONIAL_ACRED_SERVICIOS": "ps_6_8_ddjj_testimonial_acred_servicios",
    "PS_6.13_DDJJ_Testimonial_dependencia_economica": "ps_6_13_ddjj_testimonial_dependencia_economica",
    "PS_6.268_Certific_de_Servicios_(Ampliatoria)": "ps_6_268_certific_de_servicios_ampliatoria",
    "PS_6.273_Certific_complementaria_investigadores": "ps_6_273_certific_complementaria_investigadores",
    "PS_6.278_Dto_de_cuotas_jubilación": "ps_6_278_dto_de_cuotas_jubilacion",
    "PS_6.279_Dto_de_cuotas_pensión": "ps_6_279_dto_de_cuotas_pension",
    "PS_6.284_DDJJ_Fzas_Armadas": "ps_6_284_ddjj_fzas_armadas",
    "PS_6.305_Carta_Poder": "ps_6_305_carta_poder",
    "Renuncia_condicionada": "renuncia_condicionada",
    "Telegrama_revocando_poder": "telegrama_revocando_poder",
}

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
    "cuil_number": "Número de CUIL, si esta en formato por ejemplo 20-34979576-5, devolver 20349795765, el cuil suele encontrarse en el dorso del dni, donde se encuentran datos como la direccion, en esta parte no encontraras datos como nombre o apellido, en caso de no encontrar devolver vacio",
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
    "address": "lea el texto de la imagen y busque una dirección, extraé únicamente la dirección del domicilio como figura en el dorso del DNI argentino. Por ejemplo, si lees 'O' HIGGINS 1673 DT/C B° 20 DE FEBRERO - SALTA - SALTA CAPITAL - SALTA', deberás devolver únicamente 'Ohiggins 1673 DT/C B° 20 De Febrero'. La dirección suele estar en la esquina superior izquierda del dorso. No incluyas la ciudad, provincia ni repitas palabras como 'Salta', 'Buenos Aires', etc. Corregí las mayúsculas (por ejemplo, 'O' HIGGINS' se transforma en 'Ohiggins', y '20 DE FEBRERO' en '20 De Febrero'). Conservá abreviaciones como 'DT/C', 'B°', etc. Ignorá todo lo que venga después del segundo guion si está presente.",
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

        # Calcular el CUIL si el dni_number está presente
        if datos["dni_number"]:
            cuil = calcular_cuil(datos.get("sexo", ""), datos["dni_number"])
            datos["cuil_number"] = cuil
            print(f"✅ CUIL calculado: {cuil}")

        return datos
    except json.JSONDecodeError as e:
        print("❌ Error al decodificar JSON en procesar_datos_extraidos:", str(e))
        return None

def update_cliente_in_db(data):
    print("Datos recibidos para actualización:", data) # Para depurar los datos recibidos

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
        "sexo_femenino": data.get("sexo_femenino"), # <-- Mantienes estos si son campos de texto o cálculo
        "sexo_masculino": data.get("sexo_masculino"), # <-- Mantienes estos si son campos de texto o cálculo
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

    # --- Añadir el estado de los checkboxes al diccionario cliente_data ---
    for html_name, db_column_name in CHECKBOX_MAPPING.items():
        # Si el nombre del checkbox está en los datos del formulario, significa que estaba marcado ('on').
        # Si no está, significa que no estaba marcado.
        cliente_data[db_column_name] = (data.get(html_name) == 'on') # Esto evalúa a True o False

    # --- Construir dinámicamente la parte SET de la consulta SQL ---
    # Lista de columnas a actualizar (incluyendo las originales y las de los checkboxes)
    columns_to_update = [
        "nombre", "apellido", "numero_celular", "nombre_completo",
        "nombre_completo_2", "sexo", "sexo_femenino", "sexo_masculino",
        "numero_dni", "fecha_de_nacimiento", "fecha_de_ingreso",
        "numero_cuil", "nacionalidad", "direccion", "numero_direccion",
        "provincia", "departamento", "ciudad"
    ]
    # Añadir las columnas de checkboxes a la lista
    columns_to_update.extend(CHECKBOX_MAPPING.values())

    # Crear la parte 'SET columna = :parametro, ...' de la consulta
    set_clauses = [f"{col} = :{col}" for col in columns_to_update]
    set_sql = ", ".join(set_clauses)

    # Construir la consulta UPDATE completa
    update_query = text(f"""
        UPDATE data_clientes SET
            {set_sql}
        WHERE id = :id
    """)

    try:
        with engine.begin() as connection:
            result = connection.execute(update_query, cliente_data)
            print("Filas actualizadas:", result.rowcount)
        print("Datos del cliente y checkboxes actualizados en la base de datos.")
    except Exception as e:
        print("Error al actualizar en la base de datos:", e)
        # Considera si quieres re-lanzar la excepción o manejarla de otra manera
        # raise e



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


def calcular_cuil(sexo, dni):
    if not dni:
        return ""

    # Definir el prefijo dependiendo del sexo
    if sexo == "Femenino":
        cuil_prefix = "27"
    elif sexo == "Masculino":
        cuil_prefix = "20"
    else:
        cuil_prefix = "20"  # Para otros casos, usamos el código de hombre

    # Asegurarse de que el DNI sea un número de 8 dígitos
    dni = ''.join(filter(str.isdigit, dni))  # Extrae solo los dígitos
    if len(dni) != 8:
        return ""  # Si no tiene 8 dígitos, no es un DNI válido

    # Convertir el DNI en una lista de números
    dni_digits = list(map(int, dni[:8]))  # Solo tomamos los primeros 8 dígitos

    # El algoritmo para calcular el verificador se basa en los primeros 8 dígitos del DNI
    cuil_digits = [int(cuil_prefix[0]), int(cuil_prefix[1])] + dni_digits

    # Los coeficientes para calcular el verificador
    coef = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum([coef[i] * cuil_digits[i] for i in range(10)])

    # Calcular el verificador
    resto = suma % 11
    verificador = (11 - resto) if resto != 0 else 0

    # Formar el CUIL
    cuil = f"{cuil_prefix}{dni}{verificador}"

    return cuil
