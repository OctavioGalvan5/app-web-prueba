import openai
import base64
import os
import json
from datetime import datetime
from sqlalchemy import text
from models.database import engine
from io import BytesIO
import fitz  # PyMuPDF

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

FORMULARIOS_MAPPING = {
    # PDFs
    "2.91_Guarda_Documental":                               {"path": "datos/formularios/2.91_Guarda_Documental.pdf",                              "label": "2.91 Guarda Documental"},
    "6.18_Solicitud_Prestaciones_Previsionales":            {"path": "datos/formularios/6.18_Solicitud_Prestaciones_Previsionales.pdf",           "label": "6.18 Solicitud Prestaciones Previsionales"},
    "6.18_Solicitud_Prestaciones_Previsionales_pension":    {"path": "datos/formularios/6.18_Solicitud_Prestaciones_Previsionales_pension.pdf",   "label": "6.18 Solicitud Prestaciones Previsionales pension"},
    "Anexo_Baja_Puam":                                      {"path": "datos/formularios/Anexo_Baja_Puam.pdf",                                     "label": "Anexo Baja Puam"},
    "Anexo_I_Ley_27.625":                                   {"path": "datos/formularios/Anexo_I_Ley_27.625.pdf",                                  "label": "Anexo I Ley 27.625"},
    "Anexo_II_DEC_894_01":                                  {"path": "datos/formularios/Anexo_II_DEC_894_01.pdf",                                 "label": "Anexo II DEC 894 01"},
    "Anexo_II_980_05":                                      {"path": "datos/formularios/Anexo_II_980_05.pdf",                                     "label": "Anexo II 980 05"},
    "Anexo_II_Socioeconómico_24.476":                       {"path": "datos/formularios/Anexo_II_Socioeconómico_24.476.pdf",                      "label": "Anexo II Socioeconómico 24.476"},
    "Baja_PNC":                                             {"path": "datos/formularios/Baja_PNC.pdf",                                           "label": "Baja PNC"},
    "Carta_Poder_SRT":                                      {"path": "datos/formularios/Carta_Poder_SRT.pdf",                                     "label": "Carta Poder SRT"},
    "DDJJ_de_salud_resol_300":                              {"path": "datos/formularios/DDJJ_de_salud_resol_300.pdf",                             "label": "DDJJ de salud resol 300"},
    "DDJJ_Ley_17562_6.9":                                   {"path": "datos/formularios/DDJJ_Ley_17562_6.9.pdf",                                  "label": "DDJJ Ley 17562 6.9"},
    "F_3283_Autorización_ARCA":                             {"path": "datos/formularios/F_3283_Autorización_ARCA.pdf",                            "label": "F 3283 Autorización ARCA"},
    "Formulario_Carta_Poder_(CSS)":                         {"path": "datos/formularios/Formulario_Carta_Poder_(CSS).pdf",                        "label": "Formulario Carta Poder (CSS)"},
    "Formulario_encuesta_RTI":                              {"path": "datos/formularios/Formulario_encuesta_RTI.pdf",                             "label": "Formulario encuesta RTI"},
    "PS_1.75_Carta_Poder_Cap_III_27.705":                   {"path": "datos/formularios/PS_1.75_Carta_Poder_Cap_III_27.705.pdf",                  "label": "PS 1.75 Carta Poder Cap III 27.705"},
    "PS_5.7_Derivacion_aportes_Obra_Social":                {"path": "datos/formularios/PS_5.7_Derivacion_aportes_Obra_Social.pdf",              "label": "PS 5.7 Derivacion aportes Obra Social"},
    "PS_5.11_Aceptacion_de_la_Obra_Social":                 {"path": "datos/formularios/PS_5.11_Aceptacion_de_la_Obra_Social.pdf",               "label": "PS 5.11 Aceptacion de la Obra Social"},
    "PS_6.2_Certific_de_Servicios":                         {"path": "datos/formularios/PS_6.2_Certific_de_Servicios.pdf",                       "label": "PS 6.2 Certific de Servicios"},
    "PS_6.3_Nivel_de_estudios_RTI":                         {"path": "datos/formularios/PS_6.3_Nivel_de_estudios_RTI.pdf",                       "label": "PS 6.3 Nivel de estudios RTI"},
    "PS_6.4_Carta_Poder":                                   {"path": "datos/formularios/PS_6.4_Carta_Poder.pdf",                                  "label": "PS 6.4 Carta Poder"},
    "PS_6.8_DDJJ_TESTIMONIAL_ACRED_SERVICIOS":              {"path": "datos/formularios/PS_6.8_DDJJ_TESTIMONIAL_ACRED_SERVICIOS.pdf",             "label": "PS 6.8 DDJJ TESTIMONIAL ACRED SERVICIOS"},
    "PS_6.13_DDJJ_Testimonial_dependencia_económica":       {"path": "datos/formularios/PS_6.13_DDJJ_Testimonial_dependencia_económica.pdf",      "label": "PS 6.13 DDJJ Testimonial dependencia económica"},
    "PS_6.268_Certific_de_Servicios_(Ampliatoria)":         {"path": "datos/formularios/PS_6.268_Certific_de_Servicios_(Ampliatoria).pdf",        "label": "PS 6.268 Certific de Servicios (Ampliatoria)"},
    "PS_6.273_Certific_complementaria_investigadores":      {"path": "datos/formularios/PS_6.273_Certific_complementaria_investigadores.pdf",     "label": "PS 6.273 Certific complementaria investigadores"},
    "PS_6.278_Dto_de_cuotas_jubilación":                    {"path": "datos/formularios/PS_6.278_Dto_de_cuotas_jubilación.pdf",                   "label": "PS 6.278 Dto de cuotas jubilación"},
    "PS_6.279_Dto_de_cuotas_pensión":                       {"path": "datos/formularios/PS_6.279_Dto_de_cuotas_pensión.pdf",                      "label": "PS 6.279 Dto de cuotas pensión"},
    "PS_6.284_DDJJ_Fzas_Armadas":                           {"path": "datos/formularios/PS_6.284_DDJJ_Fzas_Armadas.pdf",                         "label": "PS 6.284 DDJJ Fzas Armadas"},
    "PS_6.292_DDJJ_solicitante_SDM":                        {"path": "datos/formularios/PS_6.292_DDJJ_solicitante_SDM.pdf",                      "label": "PS 6.292 DDJJ solicitante SDM"},
    "PS_6.293_DDJJ_Dador_de_trabajo_SDM":                   {"path": "datos/formularios/PS_6.293_DDJJ_Dador_de_trabajo_SDM.pdf",                  "label": "PS 6.293 DDJJ Dador de trabajo SDM"},
    "PS_6.294_DDJJ_renuncia_SDM":                           {"path": "datos/formularios/PS_6.294_DDJJ_renuncia_SDM.pdf",                         "label": "PS 6.294 DDJJ renuncia SDM"},
    "PS_6.305_Carta_Poder":                                 {"path": "datos/formularios/PS_6.305_Carta_Poder.pdf",                               "label": "PS 6.305 Carta Poder"},
    "Renuncia_condicionada":                                {"path": "datos/formularios/Renuncia_condicionada.pdf",                               "label": "Renuncia condicionada"},
    "Telegrama_revocando_poder":                            {"path": "datos/formularios/Telegrama_revocando_poder.pdf",                           "label": "Telegrama revocando poder"},
    # DOCX
    "Acta_Poder":                                           {"path": "datos/formularios/Acta_Poder.docx",                                        "label": "Acta Poder"},
    "(Beneficios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado":  {"path": "datos/formularios/(Beneficios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado.docx", "label": "(Beneficios) NUEVO CONVENIO DE HONORARIOS Numerado"},
    "(Juicios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado":     {"path": "datos/formularios/(Juicios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado.docx",    "label": "(Juicios) NUEVO CONVENIO DE HONORARIOS Numerado"},
    "CONVENIO_MAGISTRADOS":                                 {"path": "datos/formularios/CONVENIO_MAGISTRADOS.docx",                              "label": "CONVENIO MAGISTRADOS"},
    "CONVENIO_DE_GASTOS_ADMINISTRATIVOS_JUDICIALES":        {"path": "datos/formularios/CONVENIO_DE_GASTOS_ADMINISTRATIVOS_JUDICIALES.docx",     "label": "CONVENIO DE GASTOS ADMINISTRATIVOS JUDICIALES"},
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

# Configurar la API de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)


def openai_api_extract_data(image_streams):
    """Extrae datos de imágenes de DNI usando ChatGPT Vision (GPT-4o)"""
    try:
        # Preparar las imágenes en formato base64 para la API de OpenAI
        image_contents = []
        for stream in image_streams:
            stream.seek(0)
            image_b64 = base64.b64encode(stream.read()).decode("utf-8")
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}",
                    "detail": "high"
                }
            })

        # System message para establecer el contexto legítimo
        system_message = """Eres un asistente de transcripción de datos para un estudio jurídico previsional en Argentina. 
Tu función es actuar como un sistema OCR de alta precisión: leer documentos de identidad argentinos (DNI) 
que los propios clientes del estudio proporcionan voluntariamente como parte de sus trámites legales 
(jubilaciones, pensiones, reajustes de haberes, etc.).

Tu única tarea es transcribir los campos visibles del documento en formato JSON estructurado 
para cargarlos en el sistema interno de gestión de casos del estudio. 
Los clientes han autorizado el uso de sus datos para estos fines administrativos.

IMPORTANTE: Solo devuelve el objeto JSON solicitado, sin texto adicional, sin explicaciones, sin markdown."""

        # Prompt del usuario
        prompt = """Transcribí los datos visibles de este documento de identidad argentino (DNI) al siguiente formato JSON.
El cliente proporcionó este documento para su trámite previsional. Solo necesito la transcripción textual de los campos.

Devolvé ÚNICAMENTE el objeto JSON con esta estructura exacta:
{
    "dni_number": "Número de DNI sin puntos, por ejemplo 45879598",
    "cuil_number": "Número de CUIL sin guiones, por ejemplo 20349795765. El CUIL suele encontrarse en el dorso del DNI. Si no se encuentra, devolver vacío",
    "phone_number": "",
    "name": "Solo el/los nombre/s de pila con formato Título. Ejemplo: Maria Lucia",
    "surname": "Solo el/los apellido/s con formato Título. Ejemplo: Perez Gomez",
    "full_name": "Apellido y Nombre. Ejemplo: Perez Gomez Maria Lucia",
    "full_name_2": "Nombre y Apellido. Ejemplo: Maria Lucia Perez Gomez",
    "sexo": "Si lees 'F' devolvé 'Femenino', si lees 'M' devolvé 'Masculino'",
    "sexo_femenino": "Si es F devolvé 'X', sino devolvé vacío",
    "sexo_masculino": "Si es M devolvé 'X', sino devolvé vacío",
    "date_of_birth": "Formato YYYY-MM-DD, debe ser una fecha válida",
    "entry_date": "Fecha de ingreso al país en formato YYYY-MM-DD si existe, sino vacío",
    "nationality": "Nacionalidad, ejemplo: Argentina",
    "address": "Solo la dirección del domicilio del dorso del DNI, sin ciudad ni provincia. Corregir mayúsculas a formato Título. Conservar abreviaciones como DT/C, B°, etc.",
    "adress_number": "Solo el número de la dirección",
    "province": "Solo la provincia",
    "department": "Solo el departamento",
    "city": "Solo la ciudad"
}"""

        # Construir el mensaje con system message + imágenes y texto
        messages = [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *image_contents
                ]
            }
        ]

        print("📨 Enviando datos a la API de OpenAI (ChatGPT)...")

        # Llamar a la API de OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=2000
        )

        if not response or not response.choices:
            print("❌ La API de OpenAI no devolvió una respuesta válida.")
            return None, "Respuesta vacía o incorrecta de la API"

        respuesta_texto = response.choices[0].message.content
        print("✅ Respuesta recibida de ChatGPT:", respuesta_texto)

        # Procesar los datos JSON
        return procesar_datos_extraidos(respuesta_texto), None

    except Exception as e:
        print("❌ Error en chatgpt_api_extract_data:", str(e))
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
    """Convierte todas las páginas del PDF a imágenes JPEG. Retorna lista de BytesIO."""
    file_bytes = file.read()
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        print("Error al abrir el PDF:", e)
        return []
    pages = []
    for i in range(doc.page_count):
        pix = doc.load_page(i).get_pixmap()
        image_io = BytesIO(pix.tobytes("jpeg"))
        image_io.seek(0)
        pages.append(image_io)
    return pages

def process_file(file):
    """Retorna lista de BytesIO: una imagen por página (PDF) o una imagen directa."""
    if file.filename.lower().endswith('.pdf'):
        return convert_pdf_to_image(file)
    else:
        file_bytes = file.read()
        file_io = BytesIO(file_bytes)
        file_io.seek(0)
        return [file_io]


def calcular_cuil(sexo, dni):
    if not dni:
        return ""

    if sexo == "Femenino":
        cuil_prefix = "27"
    elif sexo == "Masculino":
        cuil_prefix = "20"
    else:
        cuil_prefix = "20"

    dni = ''.join(filter(str.isdigit, dni))
    if len(dni) != 8:
        return ""

    cuil_digits = [int(cuil_prefix[0]), int(cuil_prefix[1])] + list(map(int, dni))
    coef = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(coef[i] * cuil_digits[i] for i in range(10))
    resto = suma % 11

    if resto == 0:
        verificador = 0
    elif resto == 1:
        # Cuando el verificador sería 10 (dos dígitos), el estándar argentino
        # asigna prefijo "23" y verificador 9 para ambos sexos
        cuil_prefix = "23"
        verificador = 9
    else:
        verificador = 11 - resto

    return f"{cuil_prefix}{dni}{verificador}"
