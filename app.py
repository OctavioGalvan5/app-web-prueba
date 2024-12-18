import os
import tempfile
from docx import Document
from docx.shared import Inches
from datetime import datetime, timedelta
from flask import Flask, render_template, request, make_response, send_file, redirect, url_for, flash, session
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
#Models
from models.ModelUser import ModelUser
#Services
from services.generador_demandas.demanda import Formulario
from services.calculadora_uma.generador_pdf import PDFGenerator
from services.calculadora_uma.generador_docx import Documento
from services.calculadora_movilidad.calculadora import CalculadorMovilidad
from services.calculos import formatear_dinero, transformar_fecha
from services.generador_regulacion.generador_regulacion import Regulacion
from services.generador_escritos_liquidacion.generador_escritos_liquidacion import Escrito_liquidacion
from services.calculadora_tope_maximo.generador_pdf import Comparativa
from services.movilizador_de_haber.movilizador_de_haber import calculo_retroactivo
from services.planilla_docente.planilla_docente import Planilla_Docente
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
@login_required
def resultado_calculado_movilidad():
        if current_user.credito <= 0:
            flash("No tienes suficientes créditos para realizar esta operación.")
            return redirect(url_for('prueba'))
        current_user.credito -= 1
        ModelUser.update_credito(current_user.id, current_user.credito)  # Actualiza el crédito en la base de datos

        # Vuelve a cargar la información del usuario para reflejar el cambio en current_user
        login_user(ModelUser.get_by_id(current_user.id))  # Esto actualizará la información del usuario en Flask-Login
        # Recibir los datos necesarios del formulario
        datos_del_actor =  request.form['datos_del_actor']
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

        comparacion_mov_sentencia_si = request.form.get('comparacion_mov_sentencia_si', False)
        comparacion_mov_sentencia_no = request.form.get('comparacion_mov_sentencia_no', False)

        calculo = CalculadorMovilidad(datos_del_actor, expediente,cuil_expediente, beneficio,num_beneficio, fecha_inicio, fecha_fin,fecha_adquisicion_del_derecho,monto, ipc, ripte, uma, movilidad_sentencia, Ley_27426_rezago,caliva_mas_anses, Caliva_Marquez_con_27551_con_3_rezago,Caliva_Marquez_con_27551_con_6_rezago,Alanis_Mas_Anses,Alanis_con_27551_con_3_meses_rezago, comparacion_mov_sentencia_si, comparacion_mov_sentencia_no)

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
    primera_fecha = request.form.get("primera_fecha")
    segunda_fecha = request.form.get("segunda_fecha")

    pdf_generator = Comparativa(
        autos, expediente, primera_fecha, segunda_fecha
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

    monto = Decimal(request.form['monto'])
    movilidad_1 = request.form.get('movilidad_1')
    movilidad_2 = request.form.get('movilidad_2')
    movilidad_3 = request.form.get('movilidad_3')
    movilidad_4 = request.form.get('movilidad_4')
    movilidad_5 = request.form.get('movilidad_5')



    tupla=((primer_fecha_fin,movilidad_2),(segunda_fecha_fin,movilidad_3),(tercer_fecha_fin,movilidad_4), (cuarta_fecha_fin,movilidad_5))

    
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
    datos['Total_Segunda_Liquidacion'] = request.form.get('Total_Segunda_Liquidacion')

    # Liquidación IPC
    datos['IPC_Liquidacion_Si'] = request.form.get('IPC_Liquidacion_Si', False) == 'on'
    datos['IPC_Liquidacion_No'] = request.form.get('IPC_Liquidacion_No', False) == 'on'
    datos['Movilidad_Primera_Liquidacion_IPC'] = request.form.get('Movilidad_Primera_Liquidacion_IPC')
    datos['Haber_de_Alta_Primera_Liquidacion_IPC'] = request.form.get('Haber_de_Alta_Primera_Liquidacion_IPC') or "25252"
    datos['Capital_Primera_Liquidacion_IPC'] = request.form.get('Capital_Primera_Liquidacion_IPC')
    datos['Intereses_Primera_Liquidacion_IPC'] = request.form.get('Intereses_Primera_Liquidacion_IPC')
    datos['Total_Primera_Liquidacion_IPC'] = request.form.get('Total_Primera_Liquidacion_IPC')

    # Segunda liquidación IPC
    datos['Movilidad_Segunda_Liquidacion_IPC'] = request.form.get('Movilidad_Segunda_Liquidacion_IPC')
    datos['Haber_de_Alta_Segunda_Liquidacion_IPC'] = request.form.get('Haber_de_Alta_Segunda_Liquidacion_IPC') or "250250"
    datos['Capital_Segunda_Liquidacion_IPC'] = request.form.get('Capital_Segunda_Liquidacion_IPC')
    datos['Intereses_Segunda_Liquidacion_IPC'] = request.form.get('Intereses_Segunda_Liquidacion_IPC')
    datos['Total_Segunda_Liquidacion_IPC'] = request.form.get('Total_Segunda_Liquidacion_IPC')

    datos['Diferencias'] = ""
    datos['Porcentaje'] = ""
    datos['Diferencias_2'] = ""
    datos['Porcentaje_2'] = ""

    datos['Daños_Si'] = request.form.get('Daños_Si', False) == 'on'
    datos['Sancionatorios_Si'] = request.form.get('Sancionatorios_Si', False) == 'on'
    
    escrito = Escrito_liquidacion(datos)
    resultado = escrito.crear_documento()
    
    return resultado

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