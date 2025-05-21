import os
import zipfile
import tempfile
from docx import Document
from docx.shared import Inches
from datetime import datetime, timedelta
from flask import Flask, render_template, request, make_response, send_file, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import OperationalError
from docxtpl import DocxTemplate
from werkzeug.wrappers import response
from config import config
from xhtml2pdf import pisa
from io import BytesIO
from decimal import Decimal
import pandas as pd
import openpyxl
import google.generativeai as genai
import json
import gspread
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from dateutil.relativedelta import relativedelta
from pypdf import PdfReader, PdfWriter
import platform
from werkzeug.utils import secure_filename
from xhtml2pdf import pisa  # o import pisa
from io import BytesIO

#Models
from models.ModelUser import ModelUser
from sqlalchemy import text
from models.database import engine  # Verifica que la conexión esté bien configurada
#Services
from services.generador_demandas.demanda import Formulario
from services.calculadora_uma.generador_pdf import PDFGenerator
from services.calculadora_uma.generador_docx import Documento
from services.calculadora_movilidad.calculadora import CalculadorMovilidad
from services.calculos import formatear_dinero, transformar_fecha
from services.generador_regulacion.generador_regulacion import Regulacion
from services.generador_escritos_liquidacion.generador_escritos_liquidacion import Escrito_liquidacion
from services.calculadora_tope_maximo.generador_pdf import Comparativa
from services.comparador_productos.comparador_productos import Comparador_productos
from services.movilizador_de_haber.movilizador_de_haber import calculo_retroactivo
from services.planilla_docente.planilla_docente import Planilla_Docente
from services.herramientas_demandas.herramientas_demandas import HerramientasDemanda
from services.base_datos_casos.pdf_gemini import update_sentencia_in_db
from services.base_datos_casos.drive_utils import process_and_save_file, delete_drive_file, calculate_file_hash
from services.consultas.consultas import geminis_api_extract_data, update_cliente_in_db, convert_pdf_to_image, process_file, calcular_cuil
# Entities
from models.entities.User import User

# Importar la conexión a la base de datos


app = Flask(__name__)

app.secret_key = '3e5f7eaf0f9c4bcfa25c0a6e16d19743' 


csrf = CSRFProtect()
login_manager_app = LoginManager(app)

@login_manager_app.user_loader
def load_user(id):
    return ModelUser.get_by_id(id)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User(0, request.form['username'], request.form['password'])
        try:
            logged_user = ModelUser.login(user)
            if logged_user is not None and logged_user.password:  # Verifica que la contraseña sea correcta
                login_user(logged_user)
                return redirect(url_for('home'))
            else:
                flash("Usuario o contraseña incorrectos")
                return render_template('auth/login.html')
        except OperationalError as e:
            flash("Error al conectar con la base de datos. Por favor, inténtelo nuevamente.")
            return redirect(url_for('login'))
        except Exception as e:
            flash("Ocurrió un error inesperado. Por favor, inténtelo nuevamente.")
            return redirect(url_for('login'))
    else:
        return render_template('auth/login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Elimina el ID de usuario de la sesión
    return redirect(url_for('login'))  # Redirige a la página de inicio (ajusta según sea necesario)


@app.route('/home')
@login_required
def home():
    if current_user.is_authenticated:
        print(f'Usuario autenticado: {current_user.username}')  # Esto imprimirá el nombre de usuario en la consola
        return render_template('home.html')
    else:
        print('El usuario no está autenticado')  # Esto imprimirá si el usuario no está autenticado
        return redirect(url_for('login'))  # Redirige a la página de login si no está autenticado

@app.route('/calculadora_uma')
@login_required
def calculadora_uma():
    return render_template('calculadora_uma/calculadora_uma.html')

@app.route('/calculadora_uma_publica')
def calculadora_uma_publica():
    return render_template('calculadora_uma/calculadora_uma_publica.html')

@app.route('/resultado_uma', methods=['POST'])
@login_required
def generar_pdf_route():
    # Verificar si el usuario tiene suficientes créditos
    if current_user.credito <= 0:
        flash("No tienes suficientes créditos para realizar esta operación.")
        return redirect(url_for('calculadora_uma'))

    # Obtener los datos del formulario
    autos = request.form.get('Autos')
    expediente = request.form.get('Expediente')
    periodo_desde = request.form.get('PeriodoDesde')
    periodo_hasta = request.form.get('PeriodoHasta')
    fecha_de_cierre_de_liquidacion = request.form.get('Fecha_de_Cierre_de_Liquidacion')
    fecha_de_regulacion = request.form.get('Fecha_de_Regulacion')
    fecha_aprobacion_sentencia = request.form.get('Fecha_Aprobacion_Sentencia')
    monto_aprobado = request.form.get('Monto_Aprobado')
    monto_aprobado_actualizado = request.form.get('Monto_Aprobado_Actualizado')




    # Descontar 1 crédito al usuario
    current_user.credito -= 1
    ModelUser.update_credito(current_user.id, current_user.credito)  # Actualiza el crédito en la base de datos

    # Vuelve a cargar la información del usuario para reflejar el cambio en current_user
    login_user(ModelUser.get_by_id(current_user.id))  # Esto actualizará la información del usuario en Flask-Login
    # Verificar qué botón fue presionado
    action = request.form.get('action')

    if action == 'generar_pdf':
        # Generar el PDF
        pdf_generator = PDFGenerator(
            autos, expediente, periodo_desde, periodo_hasta,
            fecha_de_cierre_de_liquidacion, fecha_de_regulacion, 
            fecha_aprobacion_sentencia, monto_aprobado, monto_aprobado_actualizado
        )
        pdf = pdf_generator.generar_pdf()

        # Devolver el PDF para descarga
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=resultado.pdf'  # Cambia a 'attachment'
        return response
@app.route('/formulario_demandas', methods=['GET', 'POST'])
@login_required
def formulario_demandas():
    if request.method == 'POST':
        # Diccionario para almacenar todos los datos del formulario
        datos_formulario = {
            # Casillas de verificación
            'casillas_verificacion': {
                'opcion_error_material': 'opcion_error_material' in request.form,
                'opcion_sumas_remunerativas': 'opcion_sumas_remunerativas' in request.form,
                'opcion_reajuste_pbu': 'opcion_reajuste_pbu' in request.form,
                'opcion_tasa_complementacion': 'opcion_tasa_complementacion' in request.form,
                'opcion_integralidad_haber_actualizacion_remuneraciones': 'opcion_integralidad_haber_actualizacion_remuneraciones' in request.form,
                'opcion_movilidad_tope_haber_maximo': 'opcion_movilidad_tope_haber_maximo' in request.form,
                'opcion_inaplicabilidad_tope_art_14_res_06_09': 'opcion_inaplicabilidad_tope_art_14_res_06_09' in request.form,
                'opcion_movilidad_haber_jubilatorio': 'opcion_movilidad_haber_jubilatorio' in request.form,
                'opcion_inaplicabilidad_impuesto_ganancias': 'opcion_inaplicabilidad_impuesto_ganancias' in request.form,
                'opcion_inaplicabilidad_tope_ley_24241': 'opcion_inaplicabilidad_tope_ley_24241' in request.form,
                'opcion_inco_articulo_3_ley_27426_y_4_ley_27609': 'opcion_inco_articulo_3_ley_27426_y_4_ley_27609' in request.form,
                'opcion_inco_articulo_3_ley_27426': 'opcion_inco_articulo_3_ley_27426' in request.form,
            },
            # Datos del cliente
            'datos_cliente': {
                'genero': request.form.get('genero'),
                'nombre': request.form.get('nombre'),
                'dni': request.form.get('DNI'),
                'fecha_adquisicion_derecho': request.form.get('fecha_adquisicion_derecho'),
                'garcia_vidal': 'garciaVidal' in request.form,
                'domicilio': request.form.get('domicilio'),
                'localidad': request.form.get('localidad'),
            },
            # Beneficio
            'beneficio': {
                'fecha_reajuste': request.form.get('fechaReajuste'),
                'expediente_reajuste': request.form.get('expedienteReajuste'),
                'beneficio': request.form.get('Beneficio'),
                'fecha_inicio_remuneraciones': request.form.get('fecha_inicio_remuneraciones'),
                'fecha_fin_remuneraciones': request.form.get('fecha_fin_remuneraciones'),
                'fecha_cese': request.form.get('fechaCese'),
                'ultima_remuneracion_actividad': float(request.form.get('Ultima_Remuneracion_Actividad')),
                'fecha_ultima_remuneracion_actividad': request.form.get('fecha_Ultima_Remuneracion_Actividad'),
                'ultima_remuneracion_actualizada_anses': float(request.form.get('Ultima_remuneracion_actualizada_Anses')),
                'fecha_alta_primer_haber': request.form.get('fecha_alta_primer_haber'),
                'monto_primer_haber': float(request.form.get('Monto_primer_haber')),
                'taza_de_reemplazo': request.form.get('Taza_de_reemplazo'),
                'ultimo_haber': float(request.form.get('Ultimo_haber')),
                'fecha_ultimo_haber': request.form.get('fecha_Ultimo_haber'),
                'fecha_reclamo': request.form.get('fecha_reclamo'),
            },
            # Servicios
            'servicios': {
                'servicios_autonomos': 'Servicios_Autonomos' in request.form,
                'servicios_dependencia': 'Servicios_Dependencia' in request.form,
            },
            # Datos de Servicios Autónomos (si aplica)
            'servicios_autonomos': {
                'autonomo_input1': request.form.get('Autonomos1') if 'Servicios_Autonomos' in request.form else None,
                'autonomo_input2': request.form.get('Autonomos2') if 'Servicios_Autonomos' in request.form else None,
            },
            # Datos de Servicios en Dependencia (si aplica)
            'servicios_dependencia': {
                'cargo_desempleado': request.form.get('cargo_desempleado') if 'Servicios_Dependencia' in request.form else None,
                'empleador': request.form.get('empleador') if 'Servicios_Dependencia' in request.form else None,
            },
            # Otros datos adicionales
            'otros_datos_adicionales': {
                'ultimo_haber': request.form.get('Ultimo_haber'),
                'fecha_ultimo_haber': request.form.get('fecha_Ultimo_haber'),
                'fecha_reclamo': request.form.get('fecha_reclamo'),
            },
            # Zona de Error Material
            "error_material": {
                "Lugar_error": request.form.get('Lugar_error', ''),  # Valor del input 1 recibido del formulario
                "fecha_inicio_remuneraciones_error": request.form.get('fecha_inicio_remuneraciones_error', ''),
                "fecha_fin_remuneraciones_error": request.form.get('fecha_fin_remuneraciones_error', ''),
                "W_error": request.form.get('W_error', ''),
                "W_sin_error": request.form.get('W_sin_error', ''),

                "Imagen": {
                    "Imagen": request.files['imagenError']  # Destino del oficio
                },

            },

            # Zona de Sumas No Remunerativas
            "sumas_no_remunerativas": {
                "recibos": {
                    "Recibos_Si": 'Recibos_Si' in request.form,  # Si el checkbox está marcado
                    "Recibos_No": 'Recibos_No' in request.form   # Si el checkbox está marcado
                },

                "recibos_si": {
                    "Cargo_Desempeñado": request.form.get('Cargo_Desempeñado', ''),  # Cargo desempeñado
                    "Lugar_Desempeñado": request.form.get('Lugar_Desempeñado', ''),  # Lugar donde se desempeñó
                    "Años_antiguedad": request.form.get('Años_antiguedad', '')       # Años de antigüedad
                },

                "recibos_no": {
                    "Librar_oficio_a": request.form.get('Librar_oficio_a', ''),  # Destino del oficio
                    "inicio_periodo_sumas": request.form.get('inicio_periodo_sumas', ''),  # Fecha de inicio
                    "fin_periodo_sumas": request.form.get('fin_periodo_sumas', '')         # Fecha de fin
                },
                "Imagen": {
                    "Imagen": request.files['imageUploadSumas']  # Destino del oficio
                },
            },

                # Zona de PBU
            "PBU": {
                "porcentaje_haber_reemplazo": request.form.get('porcentaje_haber_reemplazo', ''),  
                "porcentaje_quita_Soule": request.form.get('porcentaje_quita_Soule', ''), 

                "quita_menor_15": {
                        "quita_menor_15": 'quita_menor_15' in request.form,  # Si el checkbox está marcado
                        "quita_menor_15_1": request.form.get('quita_menor_15_1', ''), 
                        "quita_menor_15_2": request.form.get('quita_menor_15_2', ''), 

                },

                "Imagen": {
                        "Imagen1": request.files['imagenPBU1'],  # Destino del oficio
                        "Imagen2": request.files['imagenPBU2']  # Destino del oficio

                },

                },
            # Zona de Taza de complementacion
            "Taza_complementacion": {
                "haber_menor_ripte": 'haber_menor_ripte' in request.form,

                "print_equiparacion": {
                    "print_equiparacion": 'print_equiparacion' in request.form,
                    "taza_ex_empleador": request.form.get('taza_ex_empleador', ''),
                    "ultimo_cargo_ejercido": request.form.get('ultimo_cargo_ejercido', ''),

                    # Intentar convertir a float con manejo de valores vacíos
                    "monto_cargo_ejercido": float(request.form.get("monto_cargo_ejercido", 0) or 0),
                    "fecha_monto_cargo_ejercido": request.form.get('fecha_monto_cargo_ejercido', ''),

                    # Manejar la conversión a float de manera segura
                    "monto_jubilacion_taza": float(request.form.get("monto_jubilacion_taza", 0) or 0),
                },

                "Imagen": {
                    "Imagen": request.files['imagenTaza'],  # Destino del oficio
                },
            },
                # Zona de Tope Haber Maximo
            "Tope_haber_maximo": {
                "Tope_haber_maximo": {
                    "fecha_haber_actual": request.form.get('fecha_haber_actual', ''),  # Si el checkbox está marcado

                    # Intentar convertir a float con manejo de valores vacíos
                    "reajustado_cf_ley_27551_mensual": float(request.form.get('reajustado_cf_ley_27551_mensual', 0) or 0),
                    "reajustado_cf_ley_27551_tres_meses": float(request.form.get('reajustado_cf_ley_27551_tres_meses', 0) or 0),
                    "reajustado_IPC_sin_topes": float(request.form.get('reajustado_IPC_sin_topes', 0) or 0),
                    "tope_haber_maximo_anses": float(request.form.get('tope_haber_maximo_anses', 0) or 0),
                    "tope_actualizado_cf_badaro_mas_caliva_marquez": float(request.form.get('tope_actualizado_cf_badaro_mas_caliva_marquez', 0) or 0),
                },

                "Imagen": {
                    "Imagen": request.files['imagenHaberMaximo'],  # Destino del oficio
                },
            },

            # Manejo de la imagen
            'imagenes': []  # Lista para almacenar las rutas de las imágenes subidas
        }



        # Llama a la función para crear el documento Word
        demanda = Formulario(datos_formulario)
        response = demanda.procesar_imagenes()

        return response

    return render_template('formulario_demanda.html')

@app.route('/calculadora_movilidad')
@login_required
def prueba():
    return render_template('calculadora_movilidad/calculadora_movilidad.html')


@app.route('/resultado_calculado_movilidad', methods=['POST'])
def resultado_calculado_movilidad():
        #if current_user.credito <= 0:
            #flash("No tienes suficientes créditos para realizar esta operación.")
            #return redirect(url_for('prueba'))
        #current_user.credito -= 1
        #ModelUser.update_credito(current_user.id, current_user.credito)  # Actualiza el crédito en la base de datos

        # Vuelve a cargar la información del usuario para reflejar el cambio en current_user
        #login_user(ModelUser.get_by_id(current_user.id))  # Esto actualizará la información del usuario en Flask-Login
        # Recibir los datos necesarios del formulario
        datos_del_actor =  request.form['datos_del_actor']
        fallecido = request.form.get('fallecido', False)
        #
        fecha_fallecimiento = request.form['fecha_fallecimiento']
        if fecha_fallecimiento == '':
            fecha_fallecimiento = "2022-02-01"
        #
        cobrador_pension = request.form['cobrador_pension']
        expediente =  request.form['expediente']
        cuil_expediente = request.form['cuil_expediente']
        beneficio =  request.form['beneficio']
        num_beneficio =  request.form['num_beneficio']    
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']
        fecha_adquisicion_del_derecho= transformar_fecha(request.form['fecha_adquisicion_del_derecho'])
        monto = float(request.form['monto'])

        ipc = request.form.get('ipc')
        ripte = request.form.get('ripte', False)
        uma = request.form.get('uma', False)
        movilidad_sentencia = request.form.get('movilidad_sentencia', False)
        Ley_27426_rezago = request.form.get('Ley_27426_rezago', False)
        caliva_mas_anses= request.form.get('caliva_mas_anses', False)
        Caliva_Marquez_con_27551_con_3_rezago = request.form.get('Caliva_Marquez_con_27551_con_3_rezago', False)
        Caliva_Marquez_con_27551_con_6_rezago= request.form.get('Caliva_Marquez_con_27551_con_6_rezago', False)
        Alanis_Mas_Anses= request.form.get('Alanis_Mas_Anses', False)
        Alanis_con_27551_con_3_meses_rezago= request.form.get('Alanis_con_27551_con_3_meses_rezago', False)
        fallo_martinez= request.form.get('fallo_martinez', False)
        alanis_ipc= request.form.get('alanis_ipc', False)
        alanis_ripte= request.form.get('alanis_ripte', False)
        Caliva_Palavecino = request.form.get('Caliva_Palavecino', False)
        Anses_Palavecino= request.form.get('Anses_Palavecino', False)
        movilidad_personalizada = request.form.get('movilidad_personalizada', False)

        comparacion_mov_sentencia_si = request.form.get('comparacion_mov_sentencia_si', False)
        comparacion_mov_sentencia_no = request.form.get('comparacion_mov_sentencia_no', False)

        comparacion_mov_caliva= request.form.get('comparacion_mov_caliva', False)
        comparacion_mov_alanis= request.form.get('comparacion_mov_alanis', False)

        #movilidad personalizada
    
        primer_fecha_fin = datetime.strptime(request.form.get('primer_fecha_fin'), '%Y-%m-%d') if request.form.get('primer_fecha_fin') else None
        segunda_fecha_fin = datetime.strptime(request.form.get('segunda_fecha_fin'), '%Y-%m-%d') if request.form.get('segunda_fecha_fin') else None
        tercer_fecha_fin = datetime.strptime(request.form.get('tercer_fecha_fin'), '%Y-%m-%d') if request.form.get('tercer_fecha_fin') else None
        cuarta_fecha_fin = datetime.strptime(request.form.get('cuarta_fecha_fin'), '%Y-%m-%d') if request.form.get('cuarta_fecha_fin') else None
        quinta_fecha_fin = datetime.strptime(request.form.get('quinta_fecha_fin'), '%Y-%m-%d') if request.form.get('quinta_fecha_fin') else None
        sexta_fecha_fin = datetime.strptime(request.form.get('sexta_fecha_fin'), '%Y-%m-%d') if request.form.get('sexta_fecha_fin') else None

        monto = Decimal(request.form['monto'])
        movilidad_1 = request.form.get('movilidad_1')
        movilidad_2 = request.form.get('movilidad_2')
        movilidad_3 = request.form.get('movilidad_3')
        movilidad_4 = request.form.get('movilidad_4')
        movilidad_5 = request.form.get('movilidad_5')
        movilidad_6 = request.form.get('movilidad_6')
        tupla=((primer_fecha_fin,movilidad_2),(segunda_fecha_fin,movilidad_3),(tercer_fecha_fin,movilidad_4), (cuarta_fecha_fin,movilidad_5), (quinta_fecha_fin,movilidad_6))


        #Haber reajustado
        haber_reajustado = request.form.get('haber_reajustado', False)
        fecha_haber_reajustado_1 = datetime.strptime(request.form.get('fecha_haber_reajustado_1'), '%Y-%m-%d') if request.form.get('fecha_haber_reajustado_1') else None
        fecha_haber_reajustado_2= datetime.strptime(request.form.get('fecha_haber_reajustado_2'), '%Y-%m-%d') if request.form.get('fecha_haber_reajustado_2') else None
        fecha_haber_reajustado_3 = datetime.strptime(request.form.get('fecha_haber_reajustado_3'), '%Y-%m-%d') if request.form.get('fecha_haber_reajustado_3') else None
        fecha_haber_reajustado_4 = datetime.strptime(request.form.get('fecha_haber_reajustado_4'), '%Y-%m-%d') if request.form.get('fecha_haber_reajustado_4') else None

        # Obtener los valores del formulario
        monto_reajustado_1 = request.form.get('monto_reajustado_1', '0')  # Usar '0' como valor por defecto si está vacío
        monto_reajustado_2 = request.form.get('monto_reajustado_2', '0')
        monto_reajustado_3 = request.form.get('monto_reajustado_3', '0')
        monto_reajustado_4 = request.form.get('monto_reajustado_4', '0')

        # Convertir a Decimal solo si el valor no está vacío
        monto_reajustado_1 = Decimal(monto_reajustado_1) if monto_reajustado_1 else Decimal('0')
        monto_reajustado_2 = Decimal(monto_reajustado_2) if monto_reajustado_2 else Decimal('0')
        monto_reajustado_3 = Decimal(monto_reajustado_3) if monto_reajustado_3 else Decimal('0')
        monto_reajustado_4 = Decimal(monto_reajustado_4) if monto_reajustado_4 else Decimal('0')

        tupla_haber_reajustado=((fecha_haber_reajustado_1,monto_reajustado_1),(fecha_haber_reajustado_2,monto_reajustado_2), (fecha_haber_reajustado_3,monto_reajustado_3),(fecha_haber_reajustado_4,monto_reajustado_4))


        calculo = CalculadorMovilidad(datos_del_actor, fallecido, fecha_fallecimiento,cobrador_pension,  expediente,cuil_expediente, beneficio,num_beneficio, fecha_inicio, fecha_fin,fecha_adquisicion_del_derecho,monto, ipc, ripte, uma, movilidad_sentencia, Ley_27426_rezago,caliva_mas_anses, Caliva_Marquez_con_27551_con_3_rezago,Caliva_Marquez_con_27551_con_6_rezago,Alanis_Mas_Anses,Alanis_con_27551_con_3_meses_rezago, fallo_martinez, alanis_ipc, alanis_ripte, comparacion_mov_sentencia_si, comparacion_mov_sentencia_no, comparacion_mov_caliva, comparacion_mov_alanis, movilidad_personalizada, Caliva_Palavecino, Anses_Palavecino, movilidad_1, tupla, tupla_haber_reajustado, haber_reajustado)

        resultado = calculo.generar_pdf()
        return resultado

@app.route('/generador_regulacion')
@login_required
def generador_regulacion():
    return render_template('escritos_regulacion/formulario_regulacion.html')

@app.route('/resultado_regulacion', methods=['POST'])
def resultado_regulacion():
    # Recoge los datos enviados desde el formulario
    datos_formulario = {
        "autos": request.form.get("autos"),
        "expediente": request.form.get("expediente"),
        "fecha_aprobacion_planilla": request.form.get("fecha_aprobacion_planilla"),
        "monto_aprobacion_planilla": request.form.get("monto_aprobacion_planilla"),
        "fecha_comienzo_planilla": request.form.get("fecha_comienzo_planilla"),
        "fecha_corte_planilla": request.form.get("fecha_corte_planilla"),
        "interes_planilla": request.form.get("interes_planilla"),
        "monto_interes_planilla": request.form.get("monto_interes_planilla"),
        "costas_orden": request.form.get("costas_orden") == "on",
        "sentencia_interlocutoria_costas": request.form.get("sentencia_interlocutoria_costas") or "2022-02-01",
        "sentencia_apelacion" : request.form.get("sentencia_apelacion") == "on",
        "fecha_sentencia_apelacion": request.form.get("fecha_sentencia_apelacion") or "2022-02-01",
        ## sentencia trance liquidacion
        "sentencia_trance_liquidacion": request.form.get("sentencia_trance_liquidacion") == "on",
        "fecha_sentencia_trance_liquidacion": request.form.get("fecha_sentencia_trance_liquidacion") or "2022-02-01",
        "fecha_pago_planilla": request.form.get("fecha_pago_planilla") or "2022-02-01",
        "interes_planilla_trance": request.form.get("interes_planilla_trance"),
        "monto_interes_planilla_trance": request.form.get("monto_interes_planilla_trance") or 100,
        ## planilla ampliacion
        "planilla_ampliacion" : request.form.get("planilla_ampliacion") == "on",
        "fecha_aprobacion_planilla_ampliacion": request.form.get("fecha_aprobacion_planilla_ampliacion") or "2022-02-01",
        "monto_ampliacion" : request.form.get("monto_ampliacion") or 0,
        "fecha_inicio" : request.form.get("fecha_inicio") or "2022-02-01",
        "fecha_corte" : request.form.get("fecha_corte") or "2022-02-01",
        "interes" : request.form.get("interes"),
        "monto_interes" : request.form.get("monto_interes") or 0,
        "costas_a_su_orden" : request.form.get("costas_a_su_orden") == "on",
        "fecha_sentencia_interlocutoria" : request.form.get("fecha_sentencia_interlocutoria") or "2022-02-01",
        ## sentencia trance planilla ampliacion 
        "sentencia_trance" : request.form.get("sentencia_trance") == "on",
        "sentencia_trance_fecha" : request.form.get("sentencia_trance_fecha") or "2022-02-01",
        "fecha_pago" : request.form.get("fecha_pago") or "2022-02-01",
        "interes_trance" : request.form.get("interes_trance"),
        "monto_interes_trance" : request.form.get("monto_interes_trance") or 0,
        ## planilla ampliacion 2
        "planilla_ampliacion_2": request.form.get("planilla_ampliacion_2") == "on",
        "fecha_aprobacion_planilla_ampliacion_2": request.form.get("fecha_aprobacion_planilla_ampliacion_2") or "2022-02-01",
        "monto_ampliacion_2": request.form.get("monto_ampliacion_2") or 0,
        "fecha_inicio_2": request.form.get("fecha_inicio_2") or "2022-02-01",
        "fecha_corte_2": request.form.get("fecha_corte_2") or "2022-02-01",
        "interes_2": request.form.get("interes_2"),
        "monto_interes_2": request.form.get("monto_interes_2") or 0,
        "costas_a_su_orden_2": request.form.get("costas_a_su_orden_2") == "on",
        "fecha_sentencia_interlocutoria_2": request.form.get("fecha_sentencia_interlocutoria_2") or "2022-02-01",
        ## sentencia trance planilla ampliacion 2
        "sentencia_trance_2": request.form.get("sentencia_trance_2") == "on",
        "sentencia_trance_fecha_2": request.form.get("sentencia_trance_fecha_2") or "2022-02-01",
        "fecha_pago_2": request.form.get("fecha_pago_2") or "2022-02-01",
        "interes_trance_2": request.form.get("interes_trance_2"),
        "monto_interes_trance_2": request.form.get("monto_interes_trance_2") or 0,

        ## planilla ampliacion 3
        "planilla_ampliacion_3": request.form.get("planilla_ampliacion_3") == "on",
        "fecha_aprobacion_planilla_ampliacion_3": request.form.get("fecha_aprobacion_planilla_ampliacion_3") or '2022-02-01',
        "monto_ampliacion_3": request.form.get("monto_ampliacion_3") or 0,
        "fecha_inicio_3": request.form.get("fecha_inicio_3") or "2022-02-01",
        "fecha_corte_3": request.form.get("fecha_corte_3") or "2022-02-01",
        "interes_3": request.form.get("interes_3"),
        "monto_interes_3": request.form.get("monto_interes_3") or 0,
        "costas_a_su_orden_3": request.form.get("costas_a_su_orden_3") == "on",
        "fecha_sentencia_interlocutoria_3": request.form.get("fecha_sentencia_interlocutoria_3") or "2022-02-01",
        ## sentencia trance planilla ampliacion 3
        "sentencia_trance_3": request.form.get("sentencia_trance_3") == "on",
        "sentencia_trance_fecha_3": request.form.get("sentencia_trance_fecha_3") or "2022-02-01",
        "fecha_pago_3": request.form.get("fecha_pago_3") or "2022-02-01",
        "interes_trance_3": request.form.get("interes_trance_3"),
        "monto_interes_trance_3": request.form.get("monto_interes_trance_3") or 0,



    }

    regulacion = Regulacion(datos_formulario)
    response = regulacion.crear_documento()

    return response

@app.route('/generador_tope_maximo')
@login_required
def generador_tope_maximo():
    return render_template('calculadora_tope_maximo/calculadora_tope_maximo.html')

@app.route('/resultado_comparativa_tope_maximo', methods=['POST'])
def resultado_comparativa_tope_maximo():
    # Recoge los datos enviados desde el formulario
    autos = request.form.get("Autos")
    expediente = request.form.get("Expediente")
    haber_reclamado = request.form.get("haber_reclamado")
    segunda_fecha = request.form.get("segunda_fecha")

    caliva_mas_anses= request.form.get('caliva_mas_anses', False)
    badaro_mas_anses= request.form.get('badaro_mas_anses', False)
    badaro_mas_caliva= request.form.get('badaro_mas_caliva', False)
    remuneracion_maxima= request.form.get('remuneracion_maxima', False)
    ochentaidos_remuneracion_maxima= request.form.get('ochentaidos_remuneracion_maxima', False)
    rem_max_caliva_27551= request.form.get('rem_max_caliva_27551', False)
    martinez_mas_anses= request.form.get('martinez_mas_anses', False)
    anses_mas_palavecino= request.form.get('anses_mas_palavecino', False)
    caliva_marquez_mas_palavecino= request.form.get('caliva_marquez_mas_palavecino',False)
    badaro_cm_palavecino= request.form.get('badaro_cm_palavecino',False)
    RM_Badaro_FP_CM_P_Anses = request.form.get('RM_Badaro_FP_CM_P_Anses',False)

    

    pdf_generator = Comparativa(
        autos, expediente, segunda_fecha, haber_reclamado,caliva_mas_anses,badaro_mas_anses, badaro_mas_caliva, remuneracion_maxima, ochentaidos_remuneracion_maxima, rem_max_caliva_27551, martinez_mas_anses, anses_mas_palavecino, caliva_marquez_mas_palavecino, badaro_cm_palavecino, RM_Badaro_FP_CM_P_Anses
    )
    pdf = pdf_generator.generar_pdf()

    # Devolver el PDF para descarga
    responsee = make_response(pdf)
    responsee.headers['Content-Type'] = 'application/pdf'
    responsee.headers['Content-Disposition'] = 'attachment; filename=resultado.pdf'  # Cambia a 'attachment'
    return responsee

@app.route('/movilizador_de_haber')
@login_required
def movilizador_de_haber():
    return render_template('movilizador_de_haber/movilizador_de_haber.html')

@app.route('/resultado_movilizador_de_haber', methods=['POST'])
@login_required
def resultado_movilizador_de_haber():
    datos_del_actor = request.form['datos_del_actor']
    expediente = request.form['expediente']
    cuil_expediente = request.form['cuil_expediente']
    beneficio = request.form['beneficio']
    num_beneficio = request.form['num_beneficio']

    # Convertir las fechas solo si no son None
    fecha_inicio = datetime.strptime(request.form['fecha_inicio'], '%Y-%m-%d') if request.form.get('fecha_inicio') else None
    fecha_fin = datetime.strptime(request.form['fecha_fin'], '%Y-%m-%d') if request.form.get('fecha_fin') else None
    fecha_adquisicion_del_derecho = transformar_fecha(request.form['fecha_adquisicion_del_derecho']) if request.form.get('fecha_adquisicion_del_derecho') else None
    primer_fecha_fin = datetime.strptime(request.form.get('primer_fecha_fin'), '%Y-%m-%d') if request.form.get('primer_fecha_fin') else None
    segunda_fecha_fin = datetime.strptime(request.form.get('segunda_fecha_fin'), '%Y-%m-%d') if request.form.get('segunda_fecha_fin') else None
    tercer_fecha_fin = datetime.strptime(request.form.get('tercer_fecha_fin'), '%Y-%m-%d') if request.form.get('tercer_fecha_fin') else None
    cuarta_fecha_fin = datetime.strptime(request.form.get('cuarta_fecha_fin'), '%Y-%m-%d') if request.form.get('cuarta_fecha_fin') else None
    quinta_fecha_fin = datetime.strptime(request.form.get('quinta_fecha_fin'), '%Y-%m-%d') if request.form.get('quinta_fecha_fin') else None
    sexta_fecha_fin = datetime.strptime(request.form.get('sexta_fecha_fin'), '%Y-%m-%d') if request.form.get('sexta_fecha_fin') else None


    monto = Decimal(request.form['monto'])
    movilidad_1 = request.form.get('movilidad_1')
    movilidad_2 = request.form.get('movilidad_2')
    movilidad_3 = request.form.get('movilidad_3')
    movilidad_4 = request.form.get('movilidad_4')
    movilidad_5 = request.form.get('movilidad_5')
    movilidad_6 = request.form.get('movilidad_6')




    tupla=((primer_fecha_fin,movilidad_2),(segunda_fecha_fin,movilidad_3),(tercer_fecha_fin,movilidad_4), (cuarta_fecha_fin,movilidad_5), (quinta_fecha_fin,movilidad_6))

    
    calculo = calculo_retroactivo(datos_del_actor, expediente, cuil_expediente, beneficio, 
                                  num_beneficio, fecha_inicio, fecha_fin, 
                                  fecha_adquisicion_del_derecho, monto, movilidad_1, tupla)
    resultado = calculo.generar_pdf()
    return resultado

@app.route('/generador_escrito_liquidacion')
@login_required
def generador_escrito_liquidacion():
    return render_template('generador_escritos/generador_escritos_liquidacion.html')

@app.route('/resultado_escrito_liquidacion', methods=['POST'])
@login_required
def resultado_escrito_liquidacion():
    datos = {}

    #Tipo de liquidacion
    datos['tipo_escrito'] = request.form.get('tipo_escrito')

    #Inconstitucionalidades
    datos['ley_27609_Si'] = request.form.get('27.609_Si', False) == 'on'
    datos['ley_27541_Si'] = request.form.get('27.541_Si', False) == 'on'
    datos['ley_27426_Si'] = request.form.get('27.426_Si', False) == 'on'

    
    #Datos Cliente
    datos['cliente'] = request.form.get('cliente')
    datos['expediente'] = request.form.get('expediente')

    # Fechas clave y sentencias
    datos['Fecha_Sentencia_Primera'] = request.form.get('Fecha_Sentencia_Primera') or "2022-02-01"
    datos['Sentencia_2da_Si'] = request.form.get('Sentencia_2da_Si', False) == 'on'
    datos['Sentencia_2da_No'] = request.form.get('Sentencia_2da_No', False) == 'on'
    datos['Sentencia_de_Segunda'] = request.form.get('Sentencia_de_Segunda') or "2022-02-01"
    datos['Sala'] = request.form.get('Sala')

    # Fechas relacionadas a liquidaciones
    datos['Fecha_Inicial_de_Pago'] = request.form.get('Fecha_Inicial_de_Pago') or "2022-02-01"
    datos['Fecha_de_cierre_de_liquidación'] = request.form.get('Fecha_de_cierre_de_liquidación') or "2022-02-01"
    datos['Fecha_de_cierre_de_intereses'] = request.form.get('Fecha_de_cierre_de_intereses') or "2022-02-01"
    datos['fecha_aprobacion_planilla'] = request.form.get('fecha_aprobacion_planilla') or "2022-02-01"
    
    #Badaro
    datos['Badaro_Si'] = request.form.get('Badaro_Si', False) == 'on'
    
    #Honorarios
    datos['Honorarios_No'] = request.form.get('Honorarios_No', False) == 'on'

    # Pensiones y fallecimientos
    datos['Pension_Si'] = request.form.get('Pension_Si', False) == 'on'
    datos['Sumas_No'] = request.form.get('Sumas_No', False) == 'on'
    datos['fecha_fallecimiento'] = request.form.get('fecha_fallecimiento') or "2022-02-01"
    datos['nombre_receptor'] = request.form.get('nombre_receptor')
    datos['Receptor'] = request.form.get('Receptor')
    datos['Porcentaje_Pension'] = request.form.get('Porcentaje_Pension')

    # Edad avanzada
    datos['Edad_Avanzada_Si'] = request.form.get('Edad_Avanzada_Si', False) == 'on'

    # Error material
    datos['Error_Material_Si'] = request.form.get('Error_Material_Si', False) == 'on'
    datos['Error_Material_No'] = request.form.get('Error_Material_No', False) == 'on'
    datos['Error_Material_primer_fecha'] = request.form.get('Error_Material_primer_fecha') or "2022-02-01"
    datos['Error_Material_ultima_fecha'] = request.form.get('Error_Material_ultima_fecha') or "2022-02-01"

    # Sumas, PBU y otros conceptos
    datos['Sumas_Si'] = request.form.get('Sumas_Si', False) == 'on'
    datos['PBU_Si'] = request.form.get('PBU_Si', False) == 'on'
    datos['Monto_PBU'] = request.form.get('Monto_PBU')
    datos['Porcentaje_PBU'] = request.form.get('Porcentaje_PBU')

    # Montos y reclamaciones
    datos['Percibido'] = request.form.get('Percibido')
    datos['Reclamado'] = request.form.get('Reclamado')

    # Fechas y periodos adicionales (RH y AC)
    datos['RH_Si'] = request.form.get('RH_Si', False) == 'on'
    datos['primer_fecha_RH'] = request.form.get('primer_fecha_RH') or "2022-02-01"
    datos['ultima_fecha_RH'] = request.form.get('ultima_fecha_RH') or "2022-02-01"
    datos['AC_Si'] = request.form.get('AC_Si', False) == 'on'
    datos['primer_fecha_AC'] = request.form.get('primer_fecha_AC') or "2022-02-01"
    datos['ultima_fecha_AC'] = request.form.get('ultima_fecha_AC') or "2022-02-01"

    # Liquidación principal
    datos['SP_Si'] = request.form.get('SP_Si', False) == 'on'
    datos['Movilidad'] = request.form.get('Movilidad')
    datos['Haber_de_Alta'] = request.form.get('Haber_de_Alta') or "25022"
    datos['Capital'] = request.form.get('Capital')
    datos['Intereses'] = request.form.get('Intereses')
    datos['total_liquidacion'] = request.form.get('total_liquidacion')

    # Descuentos y pagos
    datos['pagos_Si'] = request.form.get('pagos_Si', False) == 'on'
    datos['monto_descontado_1'] = request.form.get('monto_descontado_1')
    datos['fecha_descuento_1'] = request.form.get('fecha_descuento_1') or "2022-02-01"
    datos['monto_descontado_2'] = request.form.get('monto_descontado_2')
    datos['fecha_descuento_2'] = request.form.get('fecha_descuento_2') or "2022-02-01"
    datos['monto_descontado_3'] = request.form.get('monto_descontado_3')
    datos['fecha_descuento_3'] = request.form.get('fecha_descuento_3') or "2022-02-01"
    datos['monto_descontado_4'] = request.form.get('monto_descontado_4')
    datos['fecha_descuento_4'] = request.form.get('fecha_descuento_4') or "2022-02-01"
    datos['tupla_descuentos'] = ((datos['monto_descontado_1'], datos['fecha_descuento_1']), (datos['monto_descontado_2'], datos['fecha_descuento_2']), (datos['monto_descontado_3'], datos['fecha_descuento_3']), (datos['monto_descontado_4'], datos['fecha_descuento_4']))
    datos['parrafo_descuentos'] = ""

    

    # Segunda liquidación
    datos['Segunda_Liquidacion_Si'] = request.form.get('Segunda_Liquidacion_Si', False) == 'on'
    datos['Segunda_Liquidacion_No'] = request.form.get('Segunda_Liquidacion_No', False) == 'on'
    datos['Movilidad_Segunda_Liquidacion'] = request.form.get('Movilidad_Segunda_Liquidacion')
    datos['Haber_de_Alta_Segunda_Liquidacion'] = request.form.get('Haber_de_Alta_Segunda_Liquidacion') or "5256"
    datos['Capital_Segunda_Liquidacion'] = request.form.get('Capital_Segunda_Liquidacion')
    datos['Intereses_Segunda_Liquidacion'] = request.form.get('Intereses_Segunda_Liquidacion')
    datos['Total_Segunda_Liquidacion'] = request.form.get('Total_Segunda_Liquidacion') or "0"

    # Liquidación IPC
    datos['IPC_Liquidacion_Si'] = request.form.get('IPC_Liquidacion_Si', False) == 'on'
    datos['IPC_Liquidacion_No'] = request.form.get('IPC_Liquidacion_No', False) == 'on'
    datos['Movilidad_Primera_Liquidacion_IPC'] = request.form.get('Movilidad_Primera_Liquidacion_IPC')
    datos['Haber_de_Alta_Primera_Liquidacion_IPC'] = request.form.get('Haber_de_Alta_Primera_Liquidacion_IPC') or "25252"
    datos['Capital_Primera_Liquidacion_IPC'] = request.form.get('Capital_Primera_Liquidacion_IPC')
    datos['Intereses_Primera_Liquidacion_IPC'] = request.form.get('Intereses_Primera_Liquidacion_IPC')
    datos['Total_Primera_Liquidacion_IPC'] = request.form.get('Total_Primera_Liquidacion_IPC') or "0"

    # Segunda liquidación IPC
    datos['Movilidad_Segunda_Liquidacion_IPC'] = request.form.get('Movilidad_Segunda_Liquidacion_IPC')
    datos['Haber_de_Alta_Segunda_Liquidacion_IPC'] = request.form.get('Haber_de_Alta_Segunda_Liquidacion_IPC') or "250250"
    datos['Capital_Segunda_Liquidacion_IPC'] = request.form.get('Capital_Segunda_Liquidacion_IPC')
    datos['Intereses_Segunda_Liquidacion_IPC'] = request.form.get('Intereses_Segunda_Liquidacion_IPC')
    datos['Total_Segunda_Liquidacion_IPC'] = request.form.get('Total_Segunda_Liquidacion_IPC') or "0"

    datos['Diferencias'] = ""
    datos['Porcentaje'] = ""
    datos['Diferencias_2'] = ""
    datos['Porcentaje_2'] = ""

    datos['Tope_Si'] = request.form.get('Tope_Haber_Maximo_Si', False) == 'on'
    datos['haber_tope_maximo'] = request.form.get('haber_tope_maximo') or 10
    datos['Daños_Si'] = request.form.get('Daños_Si', False) == 'on'
    datos['Sancionatorios_Si'] = request.form.get('Sancionatorios_Si', False) == 'on'
    
    escrito = Escrito_liquidacion(datos)
    resultado = escrito.crear_documento()
    
    return resultado
    
@app.route('/comparador_productos')
@login_required
def comparador_productos():
    return render_template('comparador_productos/comparador_productos.html')

@app.route('/comparador_productos_resultado', methods=['POST'])
def comparador_productos_resultado():
    # Recoge los datos enviados desde el formulario
    autos = request.form.get("Autos")
    expediente = request.form.get("Expediente")
    primer_haber_reclamado= request.form.get("primer_haber_reclamado")
    primer_fecha= request.form.get("primer_fecha")
    segundo_haber_reclamado = request.form.get("segundo_haber_reclamado")
    segunda_fecha= request.form.get("segunda_fecha")

    pdf_generator = Comparador_productos(
        autos, expediente, primer_haber_reclamado, primer_fecha, segundo_haber_reclamado, segunda_fecha
    )
    pdf = pdf_generator.generar_pdf()

    # Devolver el PDF para descarga
    responsee = make_response(pdf)
    responsee.headers['Content-Type'] = 'application/pdf'
    responsee.headers['Content-Disposition'] = 'attachment; filename=resultado.pdf'  # Cambia a 'attachment'
    return responsee
    
@app.route('/planilla_docente')
@login_required
def planilla_docente():
    return render_template('planilla_docente/formulario_planilla_docente.html')

@app.route('/descargar_planilla_docente')
def descargar_planilla_docente():
    excel_file = 'datos/planilla_docente/Excel_planilla_planilla_docente.xlsx'
    # Enviar el archivo como respuesta para que el usuario lo descargue
    return send_file(excel_file, as_attachment=True)

@app.route("/procesar", methods=["POST"])
def procesar():
    datos = {}
    datos['autos'] = request.form.get("autos")
    datos['expediente']= request.form.get("expediente")
    datos['Nro_Beneficio']= request.form.get("Nro_Beneficio")
    datos['planilla_percibidos'] = request.files["excelFile"]
    datos['Cargo_1'] = request.form.get("Cargo_1")
    datos['Porcentaje_Cargo_1'] = request.form.get("Porcentaje_Cargo_1")
    datos['planilla_Cargo_1'] = request.files["excelFile_2"]
    datos['Cargo_2_Si'] = request.form.get('Cargo_2_Si', False) == 'on'
    datos['Cargo_2'] = request.form.get("Cargo_2")
    datos['Porcentaje_Cargo_2'] = request.form.get("Porcentaje_Cargo_2")
    datos['planilla_Cargo_2'] = request.files["excelFile_3"]
    datos['Cargo_3_Si'] = request.form.get('Cargo_3_Si', False) == 'on'
    datos['Cargo_3'] = request.form.get("Cargo_3")
    datos['Porcentaje_Cargo_3'] = request.form.get("Porcentaje_Cargo_3")
    datos['planilla_Cargo_3'] = request.files["excelFile_3"]

    
    planilla_docente = Planilla_Docente(datos)
    resultado = planilla_docente.crear_documento('planilla_percibidos')

    return resultado

@app.route('/herramientas_demanda')
@login_required
def herramientas_demanda():
    return render_template('herramientas_demanda/herramientas_demanda.html')


@app.route('/resultado_herramientas_demandas', methods=['POST'])
@login_required
def resultado_herramientas_demandas():
        if current_user.credito <= 0:
            flash("No tienes suficientes créditos para realizar esta operación.")
            return redirect(url_for('prueba'))
        current_user.credito -= 1
        ModelUser.update_credito(current_user.id, current_user.credito)
        login_user(ModelUser.get_by_id(current_user.id))

        datos_del_actor =  request.form['datos_del_actor']
        expediente =  request.form['expediente']
        cuil_expediente = request.form['cuil_expediente']
        beneficio =  request.form['beneficio']
        num_beneficio =  request.form['num_beneficio']    
        fecha_comparacion_repa= request.form['fecha_comparacion_repa'] or "2022-02-01"
        fecha_comparacion_repa = transformar_fecha(fecha_comparacion_repa)

        # Extracción de valores con un valor predeterminado de 0 si están vacíos
        comparacion_reparacion_historica = request.form.get('comparacion_reparacion_historica', False)
    
        def obtener_valor(form_value):
            valor = float(form_value)
            return valor if valor != 0 else 1

        PBU_repa = obtener_valor(request.form.get('PBU_repa', 1))
        PC_repa = obtener_valor(request.form.get('PC_repa', 1))
        PAP_repa = obtener_valor(request.form.get('PAP_repa', 1))
        REPA_repa = obtener_valor(request.form.get('REPA_repa', 1))
        OTROS_repa = obtener_valor(request.form.get('OTROS_repa', 1))

        PBU_reclamado = obtener_valor(request.form.get('PBU_reclamado', 1))
        PC_reclamado = obtener_valor(request.form.get('PC_reclamado', 1))
        PAP_reclamado = obtener_valor(request.form.get('PAP_reclamado', 1))
        REPA_reclamado = obtener_valor(request.form.get('REPA_reclamado', 1))
        OTROS_reclamado = obtener_valor(request.form.get('OTROS_reclamado', 1))

        comparacion_repa_movilizado = request.form.get('comparacion_repa_movilizado', False)
        comparacion_repa_movilizado_No = request.form.get('comparacion_repa_movilizado_No', False)

        PBU_repa_movilizado = obtener_valor(request.form.get('PBU_repa_movilizado', 1))
        PC_repa_movilizado = obtener_valor(request.form.get('PC_repa_movilizado', 1))
        PAP_repa_movilizado = obtener_valor(request.form.get('PAP_repa_movilizado', 1))
        REPA_repa_movilizado = obtener_valor(request.form.get('REPA_repa_movilizado', 1))
        OTROS_repa_movilizado = obtener_valor(request.form.get('OTROS_repa_movilizado', 1))

        diccionario_sumas = {
            "sumas_remunerativas": request.form.get('sumas_remunerativas', False),

            "instituto_provincial_de_vivienda": request.form.get('instituto_provincial_de_vivienda', False),
            "ipv_adic_ac_salarial_2010": request.form.get('ipv_adic_ac_salarial_2010', False),
            "ipv_adic_ac_salarial_2016": request.form.get('ipv_adic_ac_salarial_2016', False),
            "ipv_retroactivo_adic": request.form.get('ipv_retroactivo_adic', False),
            "ipv_ac_salarial_2016": request.form.get('ipv_ac_salarial_2016', False),
            "ipv_adic_respons_cargo": request.form.get('ipv_adic_respons_cargo', False),
            "ipv_adic": request.form.get('ipv_adic', False),
            "ipv_dto_2857_04": request.form.get('ipv_dto_2857_04', False),
            "ipv_monto_extraordinario": request.form.get('ipv_monto_extraordinario', False),
            "ipv_extraord_acta_04_13": request.form.get('ipv_extraord_acta_04_13', False),
            "ipv_adic_ipv": request.form.get('ipv_adic_ipv', False),



            

            "massalin_particulares": request.form.get('massalin_particulares', False),
            "Concepto_Asig_No_Rem_Ac_07_SUETRA_No_Remunerativo": request.form.get('Concepto_Asig_No_Rem_Ac_07_SUETRA_No_Remunerativo', False),
            "Concepto_Asig_Acuerdo_2015_No_Remunerativo": request.form.get('Concepto_Asig_Acuerdo_2015_No_Remunerativo', False),
            "Concepto_Asig_Acuerdo_2016_No_remunerativo": request.form.get('Concepto_Asig_Acuerdo_2016_No_remunerativo', False),


            "municipalidad_salta": request.form.get('municipalidad_salta', False),
            "municipalidad_salta_47_hijo": request.form.get('municipalidad_salta_47_hijo', False),
            "municipalidad_salta_52_conyuge": request.form.get('municipalidad_salta_52_conyuge', False),
            "municipalidad_salta_54_escuela_secundaria": request.form.get('municipalidad_salta_54_escuela_secundaria', False),
            "municipalidad_salta_147_acuerdo_salarial_2010": request.form.get('municipalidad_salta_147_acuerdo_salarial_2010', False),
            "municipalidad_salta_163_acuerdo_salarial_2011": request.form.get('municipalidad_salta_163_acuerdo_salarial_2011', False),
            "municipalidad_salta_165_acuerdo_salarial_2012": request.form.get('municipalidad_salta_165_acuerdo_salarial_2012', False),
            "municipalidad_salta_166_acuerdo_salarial_2013": request.form.get('municipalidad_salta_166_acuerdo_salarial_2013', False),
            "municipalidad_salta_297_suma_fija_sin_ap": request.form.get('municipalidad_salta_297_suma_fija_sin_ap', False),
            "municipalidad_salta_324_ac_2011_12_13_s_ap": request.form.get('municipalidad_salta_324_ac_2011_12_13_s_ap', False),
            "municipalidad_salta_326_ac_2_semestre_16_s_ap": request.form.get('municipalidad_salta_326_ac_2_semestre_16_s_ap', False),
            "municipalidad_salta_517_presentismo": request.form.get('municipalidad_salta_517_presentismo', False),
            "municipalidad_salta_decreto_768_04": request.form.get('municipalidad_salta_decreto_768_04', False),
            "municipalidad_salta_decreto_0025_05": request.form.get('municipalidad_salta_decreto_0025_05', False),
            "municipalidad_salta_dc_1208_025_1131_05": request.form.get('municipalidad_salta_dc_1208_025_1131_05', False),

            "todo_obras_srl": request.form.get('todo_obras_srl', False),
            "todo_obras_srl_507_viatico": request.form.get('todo_obras_srl_507_viatico', False),
            "todo_obras_srl_511_bonif_uso_corr_electrica": request.form.get('todo_obras_srl_511_bonif_uso_corr_electrica', False),
            "todo_obras_srl_514_compens_gas": request.form.get('todo_obras_srl_514_compens_gas', False),

            "hospital_materno_infantil": request.form.get('hospital_materno_infantil', False),
            "hospital_materno_infantil_328_adic_acu_sal_2010_remune": request.form.get('hospital_materno_infantil_328_adic_acu_sal_2010_remune', False),
            "hospital_materno_infantil_370_ad_inc_d_2589_04_r_1893": request.form.get('hospital_materno_infantil_370_ad_inc_d_2589_04_r_1893', False),
            "hospital_materno_infantil_612_equiparador_res_1474_11": request.form.get('hospital_materno_infantil_612_equiparador_res_1474_11', False),
            "hospital_materno_infantil_627_adic_acu_sal_2010_remune": request.form.get('hospital_materno_infantil_627_adic_acu_sal_2010_remune', False),
            "hospital_materno_infantil_628_adic_acu_sal_2010_no_remune": request.form.get('hospital_materno_infantil_628_adic_acu_sal_2010_no_remune', False),
            "hospital_materno_infantil_632_adic_acu_sal_2010_no_remune": request.form.get('hospital_materno_infantil_632_adic_acu_sal_2010_no_remune', False),
            "hospital_materno_infantil_645_nivelador_res_2665_07": request.form.get('hospital_materno_infantil_645_nivelador_res_2665_07', False),
            "hospital_materno_infantil_657_adicional_extraordinario": request.form.get('hospital_materno_infantil_657_adicional_extraordinario', False),
            "hospital_materno_infantil_696_ticket_alimentario": request.form.get('hospital_materno_infantil_696_ticket_alimentario', False),

            "ministerio_salud_publica": request.form.get('ministerio_salud_publica', False),
            "ministerio_salud_370": request.form.get('ministerio_salud_370', False),
            "ministerio_salud_569": request.form.get('ministerio_salud_569', False),
            "ministerio_salud_612": request.form.get('ministerio_salud_612', False),
            "ministerio_salud_626": request.form.get('ministerio_salud_626', False),
            "ministerio_salud_627_628_328": request.form.get('ministerio_salud_627_628_328', False),
            "ministerio_salud_632": request.form.get('ministerio_salud_632', False),
            "ministerio_salud_645": request.form.get('ministerio_salud_645', False),
            "ministerio_salud_650": request.form.get('ministerio_salud_650', False),
            "ministerio_salud_653": request.form.get('ministerio_salud_653', False),
            "ministerio_salud_654": request.form.get('ministerio_salud_654', False),
            "ministerio_salud_656": request.form.get('ministerio_salud_656', False),
            "ministerio_salud_670": request.form.get('ministerio_salud_670', False),
            "ministerio_salud_682": request.form.get('ministerio_salud_682', False),
            "ministerio_salud_685": request.form.get('ministerio_salud_685', False),

            "tomografia_computada": request.form.get('tomografia_computada', False),
            "tomografia_400": request.form.get('tomografia_400', False),
            "tomografia_405": request.form.get('tomografia_405', False),
            "tomografia_406": request.form.get('tomografia_406', False),
            "tomografia_2011": request.form.get('tomografia_2011', False),
            "tomografia_2014": request.form.get('tomografia_2014', False),

            "cruz_roja_salta": request.form.get('cruz_roja_salta', False),
            "cruz_roja_301": request.form.get('cruz_roja_301', False),
            "cruz_roja_307": request.form.get('cruz_roja_307', False),
            "cruz_roja_351": request.form.get('cruz_roja_351', False),
            "cruz_roja_399": request.form.get('cruz_roja_399', False),

            "gobierno_provincia_salta": request.form.get('gobierno_provincia_salta', False),
            "gobierno_628": request.form.get('gobierno_628', False),
            "gobierno_680": request.form.get('gobierno_680', False),
            "gobierno_690": request.form.get('gobierno_690', False),


            "ministerio_educacion_salta": request.form.get('ministerio_educacion_salta', False),
            "ministerio_educacion_salta_627_adic_acu_sal_2010_no_remune": request.form.get('ministerio_educacion_salta_627_adic_acu_sal_2010_no_remune', False),

            "hospital_senor_del_milagro": request.form.get('hospital_senor_del_milagro', False),
            "hospital_senor_del_milagro_569_adic_hs_guardia_sin_aportes": request.form.get('hospital_senor_del_milagro_569_adic_hs_guardia_sin_aportes', False),
            "hospital_senor_del_milagro_612_adic_equip_no_profesional": request.form.get('hospital_senor_del_milagro_612_adic_equip_no_profesional', False),
            "hospital_senor_del_milagro_628_adic_acu_sal_2010_no_remune": request.form.get('hospital_senor_del_milagro_628_adic_acu_sal_2010_no_remune', False),
            "hospital_senor_del_milagro_645_nivelador_res_2665_07": request.form.get('hospital_senor_del_milagro_645_nivelador_res_2665_07', False),
            "hospital_senor_del_milagro_657_adicional_extraordinario_2011": request.form.get('hospital_senor_del_milagro_657_adicional_extraordinario_2011', False),
            "hospital_senor_del_milagro_682_adicional_res_0460_16": request.form.get('hospital_senor_del_milagro_682_adicional_res_0460_16', False),
            "hospital_senor_del_milagro_653_adic_dif_actividad_critica": request.form.get('hospital_senor_del_milagro_653_adic_dif_actividad_critica', False),
            "hospital_senor_del_milagro_565_adic_hs_guardia_sin_aportes_4_2014": request.form.get('hospital_senor_del_milagro_565_adic_hs_guardia_sin_aportes_4_2014', False),
            "hospital_senor_del_milagro_644_nivelador": request.form.get('hospital_senor_del_milagro_644_nivelador', False),

            "edesa_sa": request.form.get('edesa_sa', False),
            "edesa_sa_40004_art_31_bonif_uso_corriente_elec": request.form.get('edesa_sa_40004_art_31_bonif_uso_corriente_elec', False),
            "edesa_sa_40006_compensacion_gas": request.form.get('edesa_sa_40006_compensacion_gas', False),
            "edesa_sa_40007_viaticos": request.form.get('edesa_sa_40007_viaticos', False),
            "edesa_sa_40095_gratif_ect_no_rem": request.form.get('edesa_sa_40095_gratif_ect_no_rem', False),
            "edesa_sa_40100_40103_suma_fija_no_rem": request.form.get('edesa_sa_40100_40103_suma_fija_no_rem', False),

            "hospital_san_bernardo": request.form.get('hospital_san_bernardo', False),
            "hospital_san_bernardo_628_adic_acu_sal_2010": request.form.get('hospital_san_bernardo_628_adic_acu_sal_2010', False),
            "hospital_san_bernardo_632_adic_fijo_no_rem_ni_bonif": request.form.get('hospital_san_bernardo_632_adic_fijo_no_rem_ni_bonif', False),
            "hospital_san_bernardo_612_equiparador_res_1474_11": request.form.get('hospital_san_bernardo_612_equiparador_res_1474_11', False),
            "hospital_san_bernardo_657_adic_extraordinario_2011": request.form.get('hospital_san_bernardo_657_adic_extraordinario_2011', False),
            "hospital_san_bernardo_619_fdo_de_emer_adic_hs": request.form.get('hospital_san_bernardo_619_fdo_de_emer_adic_hs', False),
            "hospital_san_bernardo_677_adic_dec_1922_14_gdias": request.form.get('hospital_san_bernardo_677_adic_dec_1922_14_gdias', False),
            "hospital_san_bernardo_568_adic_hs_guardia_sin_aportes": request.form.get('hospital_san_bernardo_568_adic_hs_guardia_sin_aportes', False),
            "hospital_san_bernardo_682_adic_acu_sal_2010_no_remune": request.form.get('hospital_san_bernardo_682_adic_acu_sal_2010_no_remune', False),
            "hospital_san_bernardo_670_ad_inc_d_2589_04_r_1893": request.form.get('hospital_san_bernardo_670_ad_inc_d_2589_04_r_1893', False),
            "hospital_san_bernardo_653_adic_dif_actividad_critica": request.form.get('hospital_san_bernardo_653_adic_dif_actividad_critica', False),
            "hospital_san_bernardo_627_adic_acu_sal_2010": request.form.get('hospital_san_bernardo_627_adic_acu_sal_2010', False),
            "hospital_san_bernardo_626_ad_acu_sal_guardia_10": request.form.get('hospital_san_bernardo_626_ad_acu_sal_guardia_10', False),
            "hospital_san_bernardo_565_fondo_de_emer_adic_hs_guardia": request.form.get('hospital_san_bernardo_565_fondo_de_emer_adic_hs_guardia', False),
            "hospital_san_bernardo_599_ad_incum_prescrip_y_certif": request.form.get('hospital_san_bernardo_599_ad_incum_prescrip_y_certif', False),
            "hospital_san_bernardo_685_reintegro_imp_ganancias": request.form.get('hospital_san_bernardo_685_reintegro_imp_ganancias', False),

            "ips_salta": request.form.get('ips_salta', False),
            "ips_salta_402_cuo_dev_gcias_rg_5008": request.form.get('ips_salta_402_cuo_dev_gcias_rg_5008', False),
            "ips_salta_470_ajuste_credito_no_rem": request.form.get('ips_salta_470_ajuste_credito_no_rem', False),
            "ips_salta_482_acu_sal_2010_no_rem": request.form.get('ips_salta_482_acu_sal_2010_no_rem', False),
            "ips_salta_483_gratif_d_4118_art_13": request.form.get('ips_salta_483_gratif_d_4118_art_13', False),
            "ips_salta_499_aj_liqui_anual_imp_gana": request.form.get('ips_salta_499_aj_liqui_anual_imp_gana', False),
            "ips_salta_decre_1055": request.form.get('ips_salta_decre_1055', False),
            "ips_salta_decre_1587_04": request.form.get('ips_salta_decre_1587_04', False),
            "ips_salta_decreto_2857_08": request.form.get('ips_salta_decreto_2857_08', False),
            "ips_salta_decre_3718_08": request.form.get('ips_salta_decre_3718_08', False),
            "ips_salta_decre_1579_08": request.form.get('ips_salta_decre_1579_08', False),
            "ips_salta_acuerdo_salarial_2010": request.form.get('ips_salta_acuerdo_salarial_2010', False),

            "alliance_one_tobacco": request.form.get('alliance_one_tobacco', False),
            "alliance_one_tobacco_261_165_bono_no_reintegrable": request.form.get('alliance_one_tobacco_261_165_bono_no_reintegrable', False),
            "alliance_one_tobacco_182_anticipo_acuerdo_sot": request.form.get('alliance_one_tobacco_182_anticipo_acuerdo_sot', False),
            "alliance_one_tobacco_194_acuerdo_no_rem_retroactivo": request.form.get('alliance_one_tobacco_194_acuerdo_no_rem_retroactivo', False),
            "alliance_one_tobacco_481_responsabilidad_gerencial": request.form.get('alliance_one_tobacco_481_responsabilidad_gerencial', False),
            "alliance_one_tobacco_482_acuerdo_salarial_2010_no_rem": request.form.get('alliance_one_tobacco_482_acuerdo_salarial_2010_no_rem', False),

            "servicios_privados_postales": request.form.get('servicios_privados_postales', False),
            "servicios_privados_postales_500_sal_susp_art_221_lct": request.form.get('servicios_privados_postales_500_sal_susp_art_221_lct', False),
            "servicios_privados_postales_513_item_4_1_12_comida": request.form.get('servicios_privados_postales_513_item_4_1_12_comida', False),
            "servicios_privados_postales_514_item_4_1_13_viatico_especial": request.form.get('servicios_privados_postales_514_item_4_1_13_viatico_especial', False),
            "servicios_privados_postales_535_item_4_1_12_comida": request.form.get('servicios_privados_postales_535_item_4_1_12_comida', False),
            "servicios_privados_postales_549_item_4_1_13_viatico_especial": request.form.get('servicios_privados_postales_549_item_4_1_13_viatico_especial', False),
            "servicios_privados_postales_588_adic_10_porc_s_4_1_12_y_4_1_13": request.form.get('servicios_privados_postales_588_adic_10_porc_s_4_1_12_y_4_1_13', False),
            "servicios_privados_postales_40000_sal_susp_art_221_lct": request.form.get('servicios_privados_postales_40000_sal_susp_art_221_lct', False),
            "servicios_privados_postales_40013_item_4_1_12_comida": request.form.get('servicios_privados_postales_40013_item_4_1_12_comida', False),
            "servicios_privados_postales_40014_item_4_1_13_viatico_especial": request.form.get('servicios_privados_postales_40014_item_4_1_13_viatico_especial', False),
            "servicios_privados_postales_40015_adic_10_porc_s_4_1_12_y_4_1_13": request.form.get('servicios_privados_postales_40015_adic_10_porc_s_4_1_12_y_4_1_13', False),

            "banco_nacion_argentina": request.form.get('banco_nacion_argentina', False),
            "banco_nacion_argentina_adicional_mensual_por_product": request.form.get('banco_nacion_argentina_adicional_mensual_por_product', False),
            "banco_nacion_argentina_adicional_zona_desfavorable_no": request.form.get('banco_nacion_argentina_adicional_zona_desfavorable_no', False),
            "banco_nacion_argentina_dif_unificacion_a_a_27_01_2011": request.form.get('banco_nacion_argentina_dif_unificacion_a_a_27_01_2011', False),
            "banco_nacion_argentina_adicional_mensual_por_product_2": request.form.get('banco_nacion_argentina_adicional_mensual_por_product_2', False),
            "banco_nacion_argentina_adicional_por_funcion": request.form.get('banco_nacion_argentina_adicional_por_funcion', False),
            "banco_nacion_argentina_acta_acuerdo_29_03_07": request.form.get('banco_nacion_argentina_acta_acuerdo_29_03_07', False),
            "banco_nacion_argentina_titulo_secundario": request.form.get('banco_nacion_argentina_titulo_secundario', False),
            "banco_nacion_argentina_adicional_cajero_integral_p": request.form.get('banco_nacion_argentina_adicional_cajero_integral_p', False),
            "banco_nacion_argentina_adic_fall_de_caja_mon_extr_per": request.form.get('banco_nacion_argentina_adic_fall_de_caja_mon_extr_per', False),
            "banco_nacion_argentina_gratificacion_extraordinaria": request.form.get('banco_nacion_argentina_gratificacion_extraordinaria', False),

            "ypf_sa": request.form.get('ypf_sa', False),
            "ypf_sa_vianda_alimentaria": request.form.get('ypf_sa_vianda_alimentaria', False),

            "camara_senadores_salta": request.form.get('camara_senadores_salta', False),
            "camara_senadores_salta_510_retroact_ac_salarial": request.form.get('camara_senadores_salta_510_retroact_ac_salarial', False),
            "camara_senadores_salta_511_ac_salarial_2010": request.form.get('camara_senadores_salta_511_ac_salarial_2010', False),
            "camara_senadores_salta_516_sac_dcto_1922_14": request.form.get('camara_senadores_salta_516_sac_dcto_1922_14', False),
            "camara_senadores_salta_900_retencion_de_imp_ganancias": request.form.get('camara_senadores_salta_900_retencion_de_imp_ganancias', False),

            "hospital_onativia": request.form.get('hospital_onativia', False),
            "hospital_onativia_328_adic_acu_sal_2010_remune": request.form.get('hospital_onativia_328_adic_acu_sal_2010_remune', False),
            "hospital_onativia_370_ad_inc_d_2589_04_r_1893": request.form.get('hospital_onativia_370_ad_inc_d_2589_04_r_1893', False),
            "hospital_onativia_612_equiparador_res_1474_11": request.form.get('hospital_onativia_612_equiparador_res_1474_11', False),
            "hospital_onativia_628_adic_acu_sal_2010_no_remune": request.form.get('hospital_onativia_628_adic_acu_sal_2010_no_remune', False),
            "hospital_onativia_670_ad_inc_d_2589_04_r_1893": request.form.get('hospital_onativia_670_ad_inc_d_2589_04_r_1893', False),
            "hospital_onativia_682_adic_acu_sal_2010_no_remune": request.form.get('hospital_onativia_682_adic_acu_sal_2010_no_remune', False),

            "politi_hector_armando": request.form.get('politi_hector_armando', False),
            "politi_hector_armando_503_decreto_38": request.form.get('politi_hector_armando_503_decreto_38', False),
            "politi_hector_armando_504_asig_no_rem": request.form.get('politi_hector_armando_504_asig_no_rem', False),
            "politi_hector_armando_505_bono_ext_fin_de_ano": request.form.get('politi_hector_armando_505_bono_ext_fin_de_ano', False),
            "politi_hector_armando_507_dia_de_la_sanidad": request.form.get('politi_hector_armando_507_dia_de_la_sanidad', False),
            "politi_hector_armando_508_asig_no_rem_ant_38_porc": request.form.get('politi_hector_armando_508_asig_no_rem_ant_38_porc', False),
            "politi_hector_armando_509_asig_no_rem_ant_8_porc": request.form.get('politi_hector_armando_509_asig_no_rem_ant_8_porc', False),
            "politi_hector_armando_512_1_sac_no_rem_2020": request.form.get('politi_hector_armando_512_1_sac_no_rem_2020', False),

            "hospital_campo_quijano": request.form.get('hospital_campo_quijano', False),
            "hospital_campo_quijano_612_equiparador_res_1474_11": request.form.get('hospital_campo_quijano_612_equiparador_res_1474_11', False),
            "hospital_campo_quijano_628_adic_acu_sal_2010": request.form.get('hospital_campo_quijano_628_adic_acu_sal_2010', False),
            "hospital_campo_quijano_645_equiparador_res_2665_07": request.form.get('hospital_campo_quijano_645_equiparador_res_2665_07', False),
            "hospital_campo_quijano_657_adicional_extraordinario_2011": request.form.get('hospital_campo_quijano_657_adicional_extraordinario_2011', False),
            "hospital_campo_quijano_682_adicional_res_0460_16": request.form.get('hospital_campo_quijano_682_adicional_res_0460_16', False),

            "hospital_la_poma": request.form.get('hospital_la_poma', False),
            "hospital_la_poma_31_zona_desfavorable": request.form.get('hospital_la_poma_31_zona_desfavorable', False),
            "hospital_la_poma_328_adic_acu_sal_2010_remune": request.form.get('hospital_la_poma_328_adic_acu_sal_2010_remune', False),
            "hospital_la_poma_569_adic_hs_guardia_sin_aportes": request.form.get('hospital_la_poma_569_adic_hs_guardia_sin_aportes', False),
            "hospital_la_poma_599_ad_incum_prescrip_y_certif": request.form.get('hospital_la_poma_599_ad_incum_prescrip_y_certif', False),
            "hospital_la_poma_612_equiparador_res_1474_11": request.form.get('hospital_la_poma_612_equiparador_res_1474_11', False),
            "hospital_la_poma_620_radic_prof_d_2075_10": request.form.get('hospital_la_poma_620_radic_prof_d_2075_10', False),
            "hospital_la_poma_628_adic_acu_sal_2010": request.form.get('hospital_la_poma_628_adic_acu_sal_2010', False),
            "hospital_la_poma_645_nivelador_res_2665_07": request.form.get('hospital_la_poma_645_nivelador_res_2665_07', False),
            "hospital_la_poma_653_adic_dif_actividad_critica": request.form.get('hospital_la_poma_653_adic_dif_actividad_critica', False),
            "hospital_la_poma_670_ad_inc_d_2589_04_r_1893": request.form.get('hospital_la_poma_670_ad_inc_d_2589_04_r_1893', False),
            "hospital_la_poma_682_adicional_res_0460_16": request.form.get('hospital_la_poma_682_adicional_res_0460_16', False),

            "hospital_nazareno": request.form.get('hospital_nazareno', False),
            "hospital_nazareno_612_equiparador_res_1474_11": request.form.get('hospital_nazareno_612_equiparador_res_1474_11', False),
            "hospital_nazareno_628_adic_acu_sal_2010": request.form.get('hospital_nazareno_628_adic_acu_sal_2010', False),
            "hospital_nazareno_645_equiparador_res_2665_07": request.form.get('hospital_nazareno_645_equiparador_res_2665_07', False),
            "hospital_nazareno_653_adic_dif_actividad_critica": request.form.get('hospital_nazareno_653_adic_dif_actividad_critica', False),
            "hospital_nazareno_682_adicional_res_0460_16": request.form.get('hospital_nazareno_682_adicional_res_0460_16', False),

            "ente_parques_industriales": request.form.get('ente_parques_industriales', False),
            "ente_parques_industriales_202_adicional_628": request.form.get('ente_parques_industriales_202_adicional_628', False),
            "ente_parques_industriales_600_adic_adm_publica_central": request.form.get('ente_parques_industriales_600_adic_adm_publica_central', False),
            "ente_parques_industriales_628_adic_acu_sal_2010": request.form.get('ente_parques_industriales_628_adic_acu_sal_2010', False),
            "ente_parques_industriales_639_adic_dif_compensatorio": request.form.get('ente_parques_industriales_639_adic_dif_compensatorio', False),
            "ente_parques_industriales_680_adic_fijo_dto_2857_04": request.form.get('ente_parques_industriales_680_adic_fijo_dto_2857_04', False),
            "ente_parques_industriales_690_adic_fijo_dto_1880_05": request.form.get('ente_parques_industriales_690_adic_fijo_dto_1880_05', False),

            "hospital_la_caldera": request.form.get('hospital_la_caldera', False),
            "hospital_la_caldera_569_adic_hs_guardia_sin_aportes": request.form.get('hospital_la_caldera_569_adic_hs_guardia_sin_aportes', False),
            "hospital_la_caldera_612_equiparador_res_1474_11": request.form.get('hospital_la_caldera_612_equiparador_res_1474_11', False),
            "hospital_la_caldera_628_adic_acu_sal_2010": request.form.get('hospital_la_caldera_628_adic_acu_sal_2010', False),
            "hospital_la_caldera_682_adicional_res_0460_16": request.form.get('hospital_la_caldera_682_adicional_res_0460_16', False),

            "hospital_san_antonio_cobres": request.form.get('hospital_san_antonio_cobres', False),
            "hospital_san_antonio_cobres_612_equiparador_res_1474_11": request.form.get('hospital_san_antonio_cobres_612_equiparador_res_1474_11', False),
            "hospital_san_antonio_cobres_628_adic_acu_sal_2010": request.form.get('hospital_san_antonio_cobres_628_adic_acu_sal_2010', False),
            "hospital_san_antonio_cobres_645_nivelador_res_2665_07": request.form.get('hospital_san_antonio_cobres_645_nivelador_res_2665_07', False),
            "hospital_san_antonio_cobres_682_adicional_res_0460_16": request.form.get('hospital_san_antonio_cobres_682_adicional_res_0460_16', False),

            "hospital_general_guemes": request.form.get('hospital_general_guemes', False),
            "hospital_general_guemes_573_adic_hs_guardia_sin_aportes": request.form.get('hospital_general_guemes_573_adic_hs_guardia_sin_aportes', False),
            "hospital_general_guemes_599_ad_incum_prescrip_y_certif": request.form.get('hospital_general_guemes_599_ad_incum_prescrip_y_certif', False),
            "hospital_general_guemes_619_fondo_de_emer_adic_guardia_sdf": request.form.get('hospital_general_guemes_619_fondo_de_emer_adic_guardia_sdf', False),
            "hospital_general_guemes_628_adic_acu_sal_2010": request.form.get('hospital_general_guemes_628_adic_acu_sal_2010', False),
            "hospital_general_guemes_653_ad_dif_actividad_critica": request.form.get('hospital_general_guemes_653_ad_dif_actividad_critica', False),
            "hospital_general_guemes_656_dto_nac_651_19_art_4": request.form.get('hospital_general_guemes_656_dto_nac_651_19_art_4', False),
            "hospital_general_guemes_670_ad_inc_d_2589_04_r_1893": request.form.get('hospital_general_guemes_670_ad_inc_d_2589_04_r_1893', False),
            "hospital_general_guemes_682_adicional_res_0460_16": request.form.get('hospital_general_guemes_682_adicional_res_0460_16', False),

            "merceria_salta": request.form.get('merceria_salta', False),
            "merceria_salta_301_acuerdo_no_remune": request.form.get('merceria_salta_301_acuerdo_no_remune', False),
            "merceria_salta_331_ant_s_no_remune": request.form.get('merceria_salta_331_ant_s_no_remune', False),
            "merceria_salta_351_present_s_no_remune": request.form.get('merceria_salta_351_present_s_no_remune', False),
            "merceria_salta_481_sac_s_no_remune": request.form.get('merceria_salta_481_sac_s_no_remune', False),

            "trans_gol_srl": request.form.get('trans_gol_srl', False),
            "trans_gol_srl_40510_asignacipn_por_cruce": request.form.get('trans_gol_srl_40510_asignacipn_por_cruce', False),
            "trans_gol_srl_40511_viatico_po_km_recorrido": request.form.get('trans_gol_srl_40511_viatico_po_km_recorrido', False),
            "trans_gol_srl_40513_permanencias": request.form.get('trans_gol_srl_40513_permanencias', False),
            "trans_gol_srl_40609_adicional_carga_peligrosa": request.form.get('trans_gol_srl_40609_adicional_carga_peligrosa', False),

            "el_sol_transporte": request.form.get('el_sol_transporte', False),
            "el_sol_transporte_814_viaticos": request.form.get('el_sol_transporte_814_viaticos', False),

            "provincia_salta_derechos_humanos": request.form.get('provincia_salta_derechos_humanos', False),
            "provincia_salta_derechos_humanos_608_adic_fijo_no_rem_ni_bonif": request.form.get('provincia_salta_derechos_humanos_608_adic_fijo_no_rem_ni_bonif', False),
            "provincia_salta_derechos_humanos_628_adic_acu_sal_2010": request.form.get('provincia_salta_derechos_humanos_628_adic_acu_sal_2010', False),
            "provincia_salta_derechos_humanos_680_adic_fijo_dto_2857_04": request.form.get('provincia_salta_derechos_humanos_680_adic_fijo_dto_2857_04', False),
            "provincia_salta_derechos_humanos_690_adic_fijo_dto_1880_05": request.form.get('provincia_salta_derechos_humanos_690_adic_fijo_dto_1880_05', False),
            "provincia_salta_derechos_humanos_695_tickets_alimentarios": request.form.get('provincia_salta_derechos_humanos_695_tickets_alimentarios', False),

            "hospital_del_milagro": request.form.get('hospital_del_milagro', False),
            "hospital_del_milagro_612_equiparador_res_1474_11": request.form.get('hospital_del_milagro_612_equiparador_res_1474_11', False),
            "hospital_del_milagro_627_adic_acu_sal_2010": request.form.get('hospital_del_milagro_627_adic_acu_sal_2010', False),
            "hospital_del_milagro_628_adic_acu_sal_2010_no_remune": request.form.get('hospital_del_milagro_628_adic_acu_sal_2010_no_remune', False),
            "hospital_del_milagro_632_adic_fijo_no_rem_ni_bonif": request.form.get('hospital_del_milagro_632_adic_fijo_no_rem_ni_bonif', False),
            "hospital_del_milagro_645_nivelador_res_2665_07": request.form.get('hospital_del_milagro_645_nivelador_res_2665_07', False),
            "hospital_del_milagro_657_adicional_extraordinario_2011": request.form.get('hospital_del_milagro_657_adicional_extraordinario_2011', False),

            "hospital_nino_jesus": request.form.get('hospital_nino_jesus', False),
            "hospital_nino_jesus_561_redondeo": request.form.get('hospital_nino_jesus_561_redondeo', False),
            "hospital_nino_jesus_645_nivelador_res_2665_07": request.form.get('hospital_nino_jesus_645_nivelador_res_2665_07', False),
            
            "codigo_1" : request.form.get('codigo_1'),
            "concepto_1" : request.form.get('concepto_1'),
            "codigo_2" : request.form.get('codigo_2'),
            "concepto_2" : request.form.get('concepto_2'),
            "codigo_3" : request.form.get('codigo_3'),
            "concepto_3" : request.form.get('concepto_3'),
            "codigo_4" : request.form.get('codigo_4'),
            "concepto_4" : request.form.get('concepto_4'),
            "codigo_5" : request.form.get('codigo_5'),
            "concepto_5" : request.form.get('concepto_5'),


            
        }



        pdf = HerramientasDemanda(datos_del_actor, expediente, cuil_expediente, beneficio, num_beneficio,comparacion_reparacion_historica, fecha_comparacion_repa, PBU_repa, PC_repa, PAP_repa, REPA_repa,OTROS_repa, PBU_reclamado, PC_reclamado, PAP_reclamado,REPA_reclamado, OTROS_reclamado, comparacion_repa_movilizado,comparacion_repa_movilizado_No, PBU_repa_movilizado, PC_repa_movilizado,PAP_repa_movilizado, REPA_repa_movilizado, OTROS_repa_movilizado, diccionario_sumas)

        resultado = pdf.generar_pdf()
        return resultado

@app.route('/base_datos_casos')
@login_required
def base_datos_casos():
    return render_template('base_datos_casos/casos.html')

@app.route('/calculadora_movilidad_publica')
def calculadora_movilidad_publica():
    return render_template('herramientas_publicas/calculadora_movilidad_publica.html')

@app.route('/calculadora_tope_maximo_publica')
def calculadora_tope_maximo_publica():
    return render_template('herramientas_publicas/calculadora_tope_maximo_publica.html')

@app.route('/comparador_productos_publica')
def comparador_productos_publica():
    return render_template('herramientas_publicas/comparador_productos_publica.html')

# Agrega esto en tu archivo principal de Flask (app.py o similar)
@app.template_filter('formato_moneda')
def formato_moneda(value):
    try:
        if value is None:
            return ""
        # Convertir a float por si viene como string desde la BD
        amount = float(value)
        # Formatear con separadores de miles y decimales
        return "${:,.2f}".format(amount).replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return ""

@app.route('/ver_casos')
@login_required
def ver_casos():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM sentencias"))
        casos = [dict(row._mapping) for row in result]
    return render_template('base_datos_casos/casos.html', casos=casos)

@app.route('/casos_publicos')
def casos_publicos():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM sentencias"))
        casos = [dict(row._mapping) for row in result]
    return render_template('base_datos_casos/casos_publicos.html', casos=casos)

@app.route('/ver_casos_publicos/<int:id>', methods=['GET', 'POST'])
def ver_casos_publicos(id):
    if request.method == 'POST':
        # Primero, obtenemos el caso existente para contar con el link anterior y otros datos.
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT * FROM sentencias WHERE id = :id"),
                {"id": id}
            )
            caso = result.mappings().first()
        if not caso:
            flash("Caso no encontrado", "error")
            return redirect(url_for('ver_casos'))

        # Procesamos los datos del formulario
        data = request.form.to_dict()
        data['id'] = id

        # Mantenemos los valores previos de drive_link y file_hash en caso de que no se suba un nuevo archivo.
        if not data.get('drive_link'):
            data['drive_link'] = caso.get('drive_link')
        if not data.get('file_hash'):
            data['file_hash'] = caso.get('file_hash')

        # Si se envía uno o varios archivos nuevos desde el formulario de edición.
        if 'documentos[]' in request.files:
            archivos = request.files.getlist('documentos[]')
            for archivo in archivos:
                if archivo.filename == '':
                    continue

                # Calcular el hash del archivo utilizando la función calculate_file_hash.
                file_hash = calculate_file_hash(archivo.stream)
                archivo.stream.seek(0)

                # Verificar si el hash ya existe en otro caso (excluyendo el registro actual)
                with engine.connect() as connection:
                    result = connection.execute(
                        text("SELECT id FROM sentencias WHERE file_hash = :file_hash AND id != :id"),
                        {"file_hash": file_hash, "id": id}
                    )
                    existing_id = result.scalar()

                if existing_id:
                    flash(f"El archivo {archivo.filename} ya fue subido previamente.", "warning")
                    continue  # No se procesa este archivo

                # Si existe un archivo anterior en Drive, se elimina.
                if caso.get('drive_link'):
                    delete_drive_file(caso.get('drive_link'))

                # Procesa y sube el archivo en modo actualización
                new_drive_link, error = process_and_save_file(archivo.stream, archivo.filename, update=True)
                if error:
                    flash(error, "danger")
                else:
                    # Actualizamos el link y el hash en los datos que se guardarán en la DB.
                    data['drive_link'] = new_drive_link
                    data['file_hash'] = file_hash

        # Actualizamos la sentencia/caso en la base de datos.
        update_sentencia_in_db(data)
        flash("Caso actualizado correctamente", "success")
        return redirect(url_for('ver_casos'))

    # Para el método GET, se obtiene el caso existente.
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT * FROM sentencias WHERE id = :id"),
            {"id": id}
        )
        caso = result.mappings().first()

    if not caso:
        flash("Caso no encontrado", "error")
        return redirect(url_for('ver_casos'))

    return render_template('base_datos_casos/ver_casos_publicos.html', caso=caso)

@app.route('/editar_caso/<int:id>', methods=['GET', 'POST'])
def editar_caso(id):
    if request.method == 'POST':
        # Primero, obtenemos el caso existente para contar con el link anterior y otros datos.
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT * FROM sentencias WHERE id = :id"),
                {"id": id}
            )
            caso = result.mappings().first()
        if not caso:
            flash("Caso no encontrado", "error")
            return redirect(url_for('ver_casos'))

        # Procesamos los datos del formulario
        data = request.form.to_dict()
        data['id'] = id

        # Mantenemos los valores previos de drive_link y file_hash en caso de que no se suba un nuevo archivo.
        if not data.get('drive_link'):
            data['drive_link'] = caso.get('drive_link')
        if not data.get('file_hash'):
            data['file_hash'] = caso.get('file_hash')

        # Si se envía uno o varios archivos nuevos desde el formulario de edición.
        if 'documentos[]' in request.files:
            archivos = request.files.getlist('documentos[]')
            for archivo in archivos:
                if archivo.filename == '':
                    continue

                # Calcular el hash del archivo utilizando la función calculate_file_hash.
                file_hash = calculate_file_hash(archivo.stream)
                archivo.stream.seek(0)

                # Verificar si el hash ya existe en otro caso (excluyendo el registro actual)
                with engine.connect() as connection:
                    result = connection.execute(
                        text("SELECT id FROM sentencias WHERE file_hash = :file_hash AND id != :id"),
                        {"file_hash": file_hash, "id": id}
                    )
                    existing_id = result.scalar()

                if existing_id:
                    flash(f"El archivo {archivo.filename} ya fue subido previamente.", "warning")
                    continue  # No se procesa este archivo

                # Si existe un archivo anterior en Drive, se elimina.
                if caso.get('drive_link'):
                    delete_drive_file(caso.get('drive_link'))

                # Procesa y sube el archivo en modo actualización
                new_drive_link, error = process_and_save_file(archivo.stream, archivo.filename, update=True)
                if error:
                    flash(error, "danger")
                else:
                    # Actualizamos el link y el hash en los datos que se guardarán en la DB.
                    data['drive_link'] = new_drive_link
                    data['file_hash'] = file_hash

        # Actualizamos la sentencia/caso en la base de datos.
        update_sentencia_in_db(data)
        flash("Caso actualizado correctamente", "success")
        return redirect(url_for('ver_casos'))

    # Para el método GET, se obtiene el caso existente.
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT * FROM sentencias WHERE id = :id"),
            {"id": id}
        )
        caso = result.mappings().first()

    if not caso:
        flash("Caso no encontrado", "error")
        return redirect(url_for('ver_casos'))

    return render_template('base_datos_casos/editar_caso.html', caso=caso)


@app.route('/upload_file', methods=['POST'])
def upload_file():
    origen = request.form.get('origen', 'privado')  # Por defecto asumimos privado

    if 'documentos[]' not in request.files:
        flash("No se enviaron archivos", "danger")
        if origen == 'publico':
            return redirect(url_for('casos_publicos'))  # cambia esto por la ruta real
        return redirect(url_for('ver_casos'))

    archivos = request.files.getlist('documentos[]')
    processed = False
    new_file_hash = None

    for archivo in archivos:
        if archivo.filename == '':
            continue

        file_hash = calculate_file_hash(archivo.stream)
        archivo.stream.seek(0)

        drive_link, error = process_and_save_file(archivo.stream, archivo.filename)
        if error:
            flash(error, "danger")
        else:
            processed = True
            new_file_hash = file_hash
            flash(f"Archivo {archivo.filename} subido y analizado correctamente.", "success")
            break

    if not processed:
        flash("No se pudo procesar ningún archivo.", "danger")
        if origen == 'publico':
            return redirect(url_for('casos_publicos'))  # cambia esto por la ruta real
        return redirect(url_for('ver_casos'))

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT id FROM sentencias WHERE file_hash = :file_hash"),
            {"file_hash": new_file_hash}
        )
        new_id = result.scalar()

    if new_id:
        if origen == 'publico':
            return redirect(url_for('ver_casos_publicos', id=new_id))
        else:
            return redirect(url_for('editar_caso', id=new_id))
    else:
        flash("No se encontró el caso subido.", "danger")
        if origen == 'publico':
            return redirect(url_for('casos_publicos'))  # cambia esto por la ruta real
        return redirect(url_for('ver_casos'))

@app.route('/eliminar_caso/<int:id>', methods=['POST'])
@login_required
def eliminar_caso(id):
    try:
        with engine.begin() as connection:
            # Primero verificar que existe el caso y obtener sus datos
            result = connection.execute(
                text("SELECT * FROM sentencias WHERE id = :id"),
                {"id": id}
            )
            caso = result.mappings().first()
            if not caso:
                return redirect(url_for('ver_casos'))

            # Si existe un archivo en Drive, lo eliminamos
            drive_link = caso.get("drive_link")
            if drive_link:
                delete_drive_file(drive_link)

            # Eliminar el caso de la base de datos
            connection.execute(
                text("DELETE FROM sentencias WHERE id = :id"),
                {"id": id}
            )

    except Exception as e:
        print(f"Error al eliminar caso: {e}")

    return redirect(url_for('ver_casos'))


@app.route('/chat', methods=['POST'])
def chat():
    genai.configure(api_key="AIzaSyCGw6VPHjs6zIopfdQR6exHZXkKJdlZOCU")
    model = genai.GenerativeModel('gemini-2.0-flash', system_instruction="Eres una IA de un estudio Juridico Toyos y Espin, ademas eres argentino, siempre te responderas en español, y daras las respuestas ordenadas, con parrafos en lo posible")
    try:
        # Obtén los casos de la base de datos
        with engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM sentencias"))
            casos = [dict(row._mapping) for row in result]

        # Construir contexto con los casos
        contexto = f"Tienes acceso a los siguientes casos, si se te pregunta sobre ellos, haras un resumen de toda la informacion (Importante: nunca uses el dato de id) :\n\n {casos} "

        # Obtén el mensaje del usuario
        data = request.get_json()
        mensaje_usuario = data.get('mensaje')

        # Recuperar historial del chat desde la sesión
        if 'historial_chat' not in session:
            session['historial_chat'] = []

        # Agregar mensaje del usuario al historial
        session['historial_chat'].append(f"Usuario: {mensaje_usuario}")

        # Construir historial del chat
        historial_chat = "\n".join(session['historial_chat'])

        # Construir el prompt con memoria del chat
        prompt = f"""
        Eres un asistente legal experto en casos judiciales.
        Importante: solo debes saludar si eres el primer mensaje, despues no (aunque saludes no significa que debes ignorar lo que te mando el usuario, por ejemplo, si te mandan un mensaje diciendo 'Hola, me gustaria saber los casos que hablan sobre...' en ese caso saludaras y le daras la informacion que te piden.
        Tienes acceso a la siguiente información de casos:

        {contexto}

        Conversación previa:
        {historial_chat}

        El usuario te ha preguntado: {mensaje_usuario}
        Importante: nunca uses el dato de id, siempre responderas en español y si se te pide informacion sobre un caso lo daras de manera ordenada y con parrafos en lo posible, respetando reglas gramaticales, aqui tienes un ejemplo:

        El caso Costanzo Emilse Noemi C/ANSES fue resuelto por la Cámara Federal de la Seguridad Social - Sala 1, que analizó un recurso interpuesto por ANSES en contra de la regulación de honorarios y la imposición de costas. La Cámara confirmó que ANSES debía asumir las costas conforme al principio objetivo de la derrota (art. 68 del CPCCN) y jurisprudencia de la CSJN (Rueda, Orlinda c/ ANSES y Morales, Blanca Azucena c/ ANSES). En cuanto a los honorarios, se consideró la complejidad del caso, el mérito profesional, las tareas realizadas en la ejecución y el precedente Finn Carlos Ignacio c/ ANSES, aplicando la Ley 27.423 (arts. 15, 16, 21, 24, 29, 41 y 51), la Acordada CSJN 30/2023 y la Resolución SGA 1497/2024, reduciéndolos a $1.575.300 (30 UMA). El expediente Nº 16712/2011 se encuentra en segunda instancia, con sentencia dictada el 30 de julio de 2024, bajo la jurisdicción de la Cámara Federal de la Seguridad Social - Sala 1, aunque sin mención de los jueces intervinientes. La carátula del expediente es Costanzo Emilse Noemi C/ANSES s/Incidente, y la sentencia permanece sujeta a revisión.
        
        Responde de manera clara y concisa, refiriéndote a los casos específicos cuando sea necesario.
        Si no encuentras información relevante, indica que no tienes datos sobre ese caso.
        """

        # Genera la respuesta con Gemini
        response = model.generate_content(prompt)
        respuesta = response.text.strip()

        # Agregar respuesta al historial de chat
        session['historial_chat'].append(f"Asistente: {respuesta}")

        return jsonify({'respuesta': respuesta})

    except Exception as e:
        print(f"Error en el chat: {e}")
        return jsonify({'error': 'Hubo un error procesando tu solicitud'}), 500


@app.route("/biblioteca")
@login_required
def biblioteca():
    # Configuración de Google Sheets
    SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # En vez de especificar la ruta al archivo JSON, obtenemos el JSON desde la variable de entorno
    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    if credentials_json is None:
        raise Exception("La variable de entorno 'GOOGLE_CREDENTIALS' no está definida.")

    # Convertir la cadena JSON a un diccionario de Python
    credentials_info = json.loads(credentials_json)

    # Crear las credenciales usando la información del service account y los scopes definidos
    creds = Credentials.from_service_account_info(credentials_info, scopes=SCOPE)

    # Usar gspread para acceder a la hoja de Google Sheets
    gc = gspread.authorize(creds)

    # ID de la hoja de cálculo (se extrae del enlace)
    SPREADSHEET_ID = "1N36KM98qxaKh4-fgt1KyUg2zu_SjMNENpPFC0rGjWkA"

    # Abrir la hoja de cálculo utilizando el ID
    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    
    # Obtener todos los registros desde la hoja de cálculo
    data = sheet.get_all_records()

    # Si algunas columnas están vacías, podemos procesar los datos y asegurarnos de que todo se lea bien.
    books = []
    for row in data:
        # Asegurémonos de que las columnas tienen un valor, si no, asignamos un valor predeterminado
        books.append({
            'autor': row.get('Autor (Apellido y Nombre)', 'No disponible'),
            'titulo': row.get('Titulo del libro', 'No disponible'),
            'categoria': row.get('Categoria', 'No disponible'),
            'edicion': row.get('Edición', 'No disponible'),
            'ano': row.get('Año', 'No disponible'),
            'palabras_claves': row.get('Palabras claves de busqueda', 'No disponible'),
            'link': row.get('Link'),

        })

    return render_template("biblioteca/biblioteca.html", books=books)

@app.route('/consultas')
@login_required
def consultas():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM data_clientes"))
        data_clientes = [dict(row._mapping) for row in result]
    return render_template('consultas/consultas.html', data_clientes=data_clientes)

@app.route('/upload_dni', methods=['POST'])
@login_required
def upload_dni():
    # Obtener todos los archivos enviados
    documentos = request.files.getlist('documentos')

    if len(documentos) < 1:
        flash("Debe enviar al menos un archivo (imagen o PDF) del DNI.", "danger")
        return redirect(url_for('consultas'))

    # Procesar cada archivo recibido
    processed_files = []
    for file in documentos:
        processed = process_file(file)
        if not processed:
            flash("Error al procesar alguno de los archivos.", "danger")
            return redirect(url_for('consultas'))
        processed_files.append(processed)

    # Enviar la lista de archivos procesados a la API de Gemini
    extracted_data, error = geminis_api_extract_data(processed_files)

    if error or not extracted_data:
        flash(f"Error al extraer datos del DNI: {error}", "danger")
        return redirect(url_for('consultas'))

    # Guardar los datos extraídos en la base de datos y obtener el ID del cliente insertado
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    INSERT INTO data_clientes (
                        numero_dni, 
                        numero_cuil,
                        numero_celular,
                        nombre,
                        apellido,
                        nombre_completo,
                        nombre_completo_2,
                        sexo,
                        sexo_femenino,
                        sexo_masculino,
                        fecha_de_nacimiento,
                        fecha_de_ingreso,
                        nacionalidad, 
                        direccion,
                        numero_direccion,
                        provincia,
                        departamento,
                        ciudad
                    ) VALUES (
                        :dni_number, 
                        :cuil_number,
                        :phone_number,
                        :name,
                        :surname,
                        :full_name,
                        :full_name_2,
                        :sexo,
                        :sexo_femenino,
                        :sexo_masculino,
                        :date_of_birth,
                        :entry_date,
                        :nationality, 
                        :address,
                        :adress_number,
                        :province,
                        :department,
                        :city
                    )
                """),
                extracted_data
            )
            new_id = result.lastrowid
    except Exception as e:
        return redirect(url_for('consultas'))

    # Redirigir a la pantalla del cliente recién cargado
    return redirect(url_for('ver_cliente', id=new_id))

@app.route('/agregar_cliente', methods=['POST'])
@login_required
def agregar_cliente():
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    INSERT INTO data_clientes (
                        numero_dni, 
                        numero_cuil,
                        numero_celular,
                        nombre,
                        apellido,
                        nombre_completo,
                        nombre_completo_2,
                        sexo,
                        sexo_femenino,
                        sexo_masculino,
                        fecha_de_nacimiento,
                        fecha_de_ingreso,
                        nacionalidad, 
                        direccion,
                        numero_direccion,
                        provincia,
                        departamento,
                        ciudad
                    ) VALUES (
                        NULL, 
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL, 
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL
                    )
                """)
            )
            new_id = result.lastrowid
    except Exception as e:
        return redirect(url_for('consultas'))

    # Redirigir a la pantalla del cliente recién cargado
    return redirect(url_for('ver_cliente', id=new_id))


@app.route('/eliminar_cliente/<int:id>', methods=['POST'])
@login_required
def eliminar_cliente(id):
    try:
        with engine.begin() as connection:
            # Primero verificar que existe el caso y obtener sus datos
            result = connection.execute(
                text("SELECT * FROM data_clientes WHERE id = :id"),
                {"id": id}
            )
            caso = result.mappings().first()
            if not caso:
                return redirect(url_for('consultas'))

            # Eliminar el caso de la base de datos
            connection.execute(
                text("DELETE FROM data_clientes WHERE id = :id"),
                {"id": id}
            )

    except Exception as e:
        print(f"Error al eliminar caso: {e}")
    return redirect(url_for('consultas'))


@app.route('/ver_cliente/<int:id>', methods=['GET', 'POST'])
@login_required
def ver_cliente(id):
    if request.method == 'POST':
        accion = request.form.get('accion')

        # Convertir los datos del formulario en un diccionario
        data = request.form.to_dict()
        # Actualizar los datos del cliente en la base de datos
        update_cliente_in_db(data)

        if accion == 'hacer_formulario':
            # Se obtiene la información actualizada del cliente desde la DB
            with engine.connect() as connection:
                result = connection.execute(
                    text("SELECT * FROM data_clientes WHERE id = :id"),
                    {"id": id}
                )
                data_cliente = result.mappings().first()

            # Construir el diccionario con los datos extraídos de la base
            nombre = data_cliente.get("nombre", "")
            apellido = data_cliente.get("apellido", "")
            datos = {
                "nombre": nombre,
                "apellido": apellido,
                "numero_celular": data_cliente.get("numero_celular", ""),
                "nombre_completo": f"{apellido} {nombre}",
                "nombre_completo_2": f"{nombre} {apellido}",
                "sexo": data_cliente.get("sexo", ""),
                "sexo_femenino": data_cliente.get("sexo_femenino", ""),
                "sexo_masculino": data_cliente.get("sexo_masculino", ""),
                "numero_dni": data_cliente.get("numero_dni", ""),
                "fecha_de_nacimiento_formato": data_cliente.get("fecha_de_nacimiento").strftime('%d/%m/%Y') if data_cliente.get("fecha_de_nacimiento") else "",
                "fecha_de_nacimiento": data_cliente.get("fecha_de_nacimiento").strftime('%d%m%Y') if data_cliente.get("fecha_de_nacimiento") else "",
                "fecha_de_nacimiento_dia": data_cliente.get("fecha_de_nacimiento").strftime('%d') if data_cliente.get("fecha_de_nacimiento") else "",
                "fecha_de_nacimiento_mes": data_cliente.get("fecha_de_nacimiento").strftime('%m') if data_cliente.get("fecha_de_nacimiento") else "",
                "fecha_de_nacimiento_año": data_cliente.get("fecha_de_nacimiento").strftime('%Y') if data_cliente.get("fecha_de_nacimiento") else "",
                "fecha_de_ingreso": data_cliente.get("fecha_de_ingreso").strftime('%d%m%y') if data_cliente.get("fecha_de_ingreso") else "",
                "numero_cuil": data_cliente.get("numero_cuil", ""),
                "cuil_inicio": data_cliente.get("numero_cuil", "")[:2],
                "cuil_fin": data_cliente.get("numero_cuil", "")[-1:],
                "nacionalidad": data_cliente.get("nacionalidad", ""),
                "direccion": data_cliente.get("direccion", ""),
                "numero_direccion": data_cliente.get("numero_direccion", ""),
                "provincia": data_cliente.get("provincia", ""),
                "departamento": data_cliente.get("departamento", ""),
                "ciudad": data_cliente.get("ciudad", ""),
                "donde_firmar": "X",

            }

            # Diccionario para almacenar los archivos generados en memoria (PDFs y Word)
            archivos_generados = {}
            lista_formularios = []
            # Procesar cada formulario PDF (como antes)
            formularios = []
            if request.form.get("2.91_Guarda_Documental"):
                formularios.append("datos/formularios/2.91_Guarda_Documental.pdf")
                lista_formularios.append("2.91 Guarda Documental")
                
            if request.form.get("6.18_Solicitud_Prestaciones_Previsionales"):
                formularios.append("datos/formularios/6.18_Solicitud_Prestaciones_Previsionales.pdf")
                lista_formularios.append("6.18 Solicitud Prestaciones Previsionales")
                
            if request.form.get("6.18_Solicitud_Prestaciones_Previsionales_pension"):
                formularios.append("datos/formularios/6.18_Solicitud_Prestaciones_Previsionales_pension.pdf")
                lista_formularios.append("6.18 Solicitud Prestaciones Previsionales pension")
                
            if request.form.get("Anexo_Baja_Puam"):
                formularios.append("datos/formularios/Anexo_Baja_Puam.pdf")
                lista_formularios.append("Anexo Baja Puam")
                
            if request.form.get("Anexo_I_Ley_27.625"):
                formularios.append("datos/formularios/Anexo_I_Ley_27.625.pdf")
                lista_formularios.append("Anexo I Ley 27.625")
                
            if request.form.get("Anexo_II_DEC_894_01"):
                formularios.append("datos/formularios/Anexo_II_DEC_894_01.pdf")
                lista_formularios.append("Anexo II DEC 894 01")
                
            if request.form.get("Anexo_II_980_05"):
                formularios.append("datos/formularios/Anexo_II_980_05.pdf")
                lista_formularios.append("Anexo II 980 05")
                
            if request.form.get("Anexo_II_Socioeconómico_24.476"):
                formularios.append("datos/formularios/Anexo_II_Socioeconómico_24.476.pdf")
                lista_formularios.append("Anexo II Socioeconómico 24.476")
                
            if request.form.get("Baja_PNC"):
                formularios.append("datos/formularios/Baja_PNC.pdf")
                lista_formularios.append("Baja PNC")
                
            if request.form.get("Carta_Poder_SRT"):
                formularios.append("datos/formularios/Carta_Poder_SRT.pdf")
                lista_formularios.append("Carta Poder SRT")
                
            if request.form.get("DDJJ_de_salud_resol_300"):
                formularios.append("datos/formularios/DDJJ_de_salud_resol_300.pdf")
                lista_formularios.append("DDJJ de salud resol 300")
                
            if request.form.get("DDJJ_Ley_17562_6.9"):
                formularios.append("datos/formularios/DDJJ_Ley_17562_6.9.pdf")
                lista_formularios.append("DDJJ Ley 17562 6.9")
                
            if request.form.get("F_3283_Autorización_ARCA"):
                formularios.append("datos/formularios/F_3283_Autorización_ARCA.pdf")
                lista_formularios.append("F 3283 Autorización ARCA")
                
            if request.form.get("Formulario_Carta_Poder_(CSS)"):
                formularios.append("datos/formularios/Formulario_Carta_Poder_(CSS).pdf")
                lista_formularios.append("Formulario Carta Poder (CSS)")
                
            if request.form.get("Formulario_encuesta_RTI"):
                formularios.append("datos/formularios/Formulario_encuesta_RTI.pdf")
                lista_formularios.append("Formulario encuesta RTI")
                
            if request.form.get("PS_1.75_Carta_Poder_Cap_III_27.705"):
                formularios.append("datos/formularios/PS_1.75_Carta_Poder_Cap_III_27.705.pdf")
                lista_formularios.append("PS 1.75 Carta Poder Cap III 27.705")

            if request.form.get("PS_5.7_Derivacion_aportes_Obra_Social"):
                formularios.append("datos/formularios/PS_5.7_Derivacion_aportes_Obra_Social.pdf")
                lista_formularios.append("PS 5.7 Derivacion aportes Obra Social")

            if request.form.get("PS_5.11_Aceptacion_de_la_Obra_Social"):
                formularios.append("datos/formularios/PS_5.11_Aceptacion_de_la_Obra_Social.pdf")
                lista_formularios.append("PS 5.11 Aceptacion de la Obra Social")

            if request.form.get("PS_6.292_DDJJ_solicitante_SDM"):
                formularios.append("datos/formularios/PS_6.292_DDJJ_solicitante_SDM.pdf")
                lista_formularios.append("PS 6.292 DDJJ solicitante SDM")

            if request.form.get("PS_6.293_DDJJ_Dador_de_trabajo_SDM"):
                formularios.append("datos/formularios/PS_6.293_DDJJ_Dador_de_trabajo_SDM.pdf")
                lista_formularios.append("PS 6.293 DDJJ Dador de trabajo SDM")

            if request.form.get("PS_6.294_DDJJ_renuncia_SDM"):
                formularios.append("datos/formularios/PS_6.294_DDJJ_renuncia_SDM.pdf")
                lista_formularios.append("PS 6.294 DDJJ renuncia SDM")

            if request.form.get("PS_6.2_Certific_de_Servicios"):
                formularios.append("datos/formularios/PS_6.2_Certific_de_Servicios.pdf")
                lista_formularios.append("PS 6.2 Certific de Servicios")

            if request.form.get("PS_6.3_Nivel_de_estudios_RTI"):
                formularios.append("datos/formularios/PS_6.3_Nivel_de_estudios_RTI.pdf")
                lista_formularios.append("PS 6.3 Nivel de estudios RTI")

            if request.form.get("PS_6.4_Carta_Poder"):
                formularios.append("datos/formularios/PS_6.4_Carta_Poder.pdf")
                lista_formularios.append("PS 6.4 Carta Poder")

            if request.form.get("PS_6.8_DDJJ_TESTIMONIAL_ACRED_SERVICIOS"):
                formularios.append("datos/formularios/PS_6.8_DDJJ_TESTIMONIAL_ACRED_SERVICIOS.pdf")
                lista_formularios.append("PS 6.8 DDJJ TESTIMONIAL ACRED SERVICIOS")

            if request.form.get("PS_6.13_DDJJ_Testimonial_dependencia_económica"):
                formularios.append("datos/formularios/PS_6.13_DDJJ_Testimonial_dependencia_económica.pdf")
                lista_formularios.append("PS 6.13 DDJJ Testimonial dependencia económica")

            if request.form.get("PS_6.268_Certific_de_Servicios_(Ampliatoria)"):
                formularios.append("datos/formularios/PS_6.268_Certific_de_Servicios_(Ampliatoria).pdf")
                lista_formularios.append("PS 6.268 Certific de Servicios (Ampliatoria)")

            if request.form.get("PS_6.273_Certific_complementaria_investigadores"):
                formularios.append("datos/formularios/PS_6.273_Certific_complementaria_investigadores.pdf")
                lista_formularios.append("PS 6.273 Certific complementaria investigadores")

            if request.form.get("PS_6.278_Dto_de_cuotas_jubilación"):
                formularios.append("datos/formularios/PS_6.278_Dto_de_cuotas_jubilación.pdf")
                lista_formularios.append("PS 6.278 Dto de cuotas jubilación")

            if request.form.get("PS_6.279_Dto_de_cuotas_pensión"):
                formularios.append("datos/formularios/PS_6.279_Dto_de_cuotas_pensión.pdf")
                lista_formularios.append("PS 6.279 Dto de cuotas pensión")

            if request.form.get("PS_6.284_DDJJ_Fzas_Armadas"):
                formularios.append("datos/formularios/PS_6.284_DDJJ_Fzas_Armadas.pdf")
                lista_formularios.append("PS 6.284 DDJJ Fzas Armadas")

            if request.form.get("PS_6.305_Carta_Poder"):
                formularios.append("datos/formularios/PS_6.305_Carta_Poder.pdf")
                lista_formularios.append("PS 6.305 Carta Poder")

            if request.form.get("Renuncia_condicionada"):
                formularios.append("datos/formularios/Renuncia_condicionada.pdf")
                lista_formularios.append("Renuncia condicionada")

            if request.form.get("Telegrama_revocando_poder"):
                formularios.append("datos/formularios/Telegrama_revocando_poder.pdf")
                lista_formularios.append("Telegrama revocando poder") 

            for idx, formulario in enumerate(formularios):
                reader = PdfReader(formulario)
                writer = PdfWriter()
                writer.clone_reader_document_root(reader)

                # Verifica que el PDF tenga al menos una página
                if len(writer.pages) == 0:
                    flash(f"El archivo {formulario} no tiene páginas o está dañado.", "error")
                    return redirect(url_for('ver_cliente', id=id))

                writer.update_page_form_field_values(writer.pages[0], datos)

                # Obtener nombre del archivo sin extensión y sin ruta
                nombre_formulario = os.path.splitext(os.path.basename(formulario))[0]
                nombre_formulario = secure_filename(nombre_formulario)  # por si tiene caracteres raros
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_pdf_name = f"{nombre_formulario}_{timestamp}.pdf"

                output = BytesIO()
                writer.write(output)
                output.seek(0)
                archivos_generados[output_pdf_name] = output

            # Procesar archivos Word si existen checkboxes marcados
            # Definir una lista de tuplas (nombre_archivo_base, ruta_template)
            word_templates = []
            if request.form.get("Acta_Poder"):
                word_templates.append(("acta_poder", "datos/formularios/Acta_Poder.docx"))
                lista_formularios.append("Acta Poder")

            if request.form.get("(Beneficios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado"):
                word_templates.append(("(Beneficios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado", "datos/formularios/(Beneficios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado.docx"))
                lista_formularios.append("(Beneficios) NUEVO CONVENIO DE HONORARIOS Numerado")

            if request.form.get("(Juicios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado"):
                word_templates.append(("(Juicios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado", "datos/formularios/(Juicios)_NUEVO_CONVENIO_DE_HONORARIOS_Numerado.docx"))
                lista_formularios.append("(Juicios) NUEVO CONVENIO DE HONORARIOS Numerado")

            if request.form.get("CONVENIO_MAGISTRADOS"):
                word_templates.append(("CONVENIO_MAGISTRADOS", "datos/formularios/CONVENIO_MAGISTRADOS.docx"))
                lista_formularios.append("CONVENIO MAGISTRADOS")

            if request.form.get("CONVENIO_DE_GASTOS_ADMINISTRATIVOS_JUDICIALES"):
                word_templates.append(("CONVENIO_DE_GASTOS_ADMINISTRATIVOS_JUDICIALES", "datos/formularios/CONVENIO_DE_GASTOS_ADMINISTRATIVOS_JUDICIALES.docx"))
                lista_formularios.append("CONVENIO DE GASTOS ADMINISTRATIVOS JUDICIALES")
            

            # Procesar cada template Word
            if word_templates:
                from docxtpl import DocxTemplate
                for nombre_base, template_path in word_templates:
                    doc = DocxTemplate(template_path)
                    doc.render(datos)
                    output_word = BytesIO()
                    doc.save(output_word)
                    output_word.seek(0)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_word_name = f"{nombre_base}_{timestamp}.docx"
                    archivos_generados[output_word_name] = output_word

            # 1) Generar el PDF en memoria
            rendered = render_template(
                'consultas/formularios_impresos.html',
                filas=lista_formularios
            )
            pdf_buffer = BytesIO()
            pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
            if pisa_status.err:
                return "Error al crear el PDF", 500
            pdf_buffer.seek(0)

            # 2) Crear el ZIP en memoria y agregar todos los archivos
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # a) Archivos previamente generados
                for filename, file_data in archivos_generados.items():
                    # file_data es un BytesIO; obtenemos sus bytes
                    zip_file.writestr(filename, file_data.getvalue())

                # b) El PDF recién creado
                # Le puedes dar el nombre que quieras dentro del ZIP
                zip_file.writestr('formularios_impresos.pdf', pdf_buffer.getvalue())

            zip_buffer.seek(0)

            # 3) Enviar el ZIP como attachment
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"formularios_{timestamp}.zip"
            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name=zip_filename,
                mimetype='application/zip'
            )


        elif accion == 'guardar_cambios':
            flash("Caso actualizado correctamente", "success")
            return redirect(url_for('ver_cliente', id=id))

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT * FROM data_clientes WHERE id = :id"),
            {"id": id}
        )
        data_cliente = result.mappings().first()

    if not data_cliente:
        flash("Caso no encontrado", "error")
        return redirect(url_for('consultas'))

    return render_template('consultas/ver_cliente.html', data_cliente=data_cliente)

@app.route("/datos_cruzados")
def datos_cruzados():
    SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    if credentials_json is None:
        raise Exception("La variable de entorno 'GOOGLE_CREDENTIALS' no está definida.")

    credentials_info = json.loads(credentials_json)
    creds = Credentials.from_service_account_info(credentials_info, scopes=SCOPE)

    gc = gspread.authorize(creds)

    # ID de la hoja de cálculo que me pasaste
    SPREADSHEET_ID = "167m4jgbXfm8y2Z2csbxEwIdPtBgGc4g_Kp9wfSQPQ8M"

    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

    data = sheet.get_all_records()

    datos = []
    for row in data:
        datos.append({
            'nombre_planilla': row.get('NOMBRE_Planilla', 'No disponible'),
            'n_beneficio_planilla': row.get('N_BENEFICIO_Planilla', 'No disponible'),
            'nombre_aprobadas': row.get('Nombre y Apellido_Aprobadas', 'No disponible'),
            'beneficio_aprobadas': row.get('Beneficio_Aprobadas', 'No disponible'),
            'detalle_aprobadas': row.get('Detalle_Aprobadas', 'No disponible'),
            'mes_aprobadas': row.get('Mes_Aprobadas', 'No disponible'),
            'link': row.get('Link_Aprobadas', 'No disponible'),

        })

    return render_template("datos_cruzados/datos_cruzados.html", datos=datos)

if __name__ == '__main__':
    app.run(debug=True)


def status_401(error):
    return redirect(url_for('login'))


def status_404(error):
    return "<h1>Página no encontrada</h1>", 404

if __name__ == '__main__':
    app.config.from_object(config['development'])
    app.register_error_handler(401, status_401)
    app.register_error_handler(404, status_404)
    app.run()