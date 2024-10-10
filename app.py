import os
import tempfile
from docx import Document
from docx.shared import Inches
from datetime import datetime, timedelta
from flask import Flask, render_template, request, make_response, send_file, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from docxtpl import DocxTemplate
from werkzeug.wrappers import response
from config import config
#Models
from models.demanda import Formulario
from models.generador_pdf import PDFGenerator
from models.ModelUser import ModelUser
from models.demanda import Formulario

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
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User(0, request.form['username'], request.form['password'])
        logged_user = ModelUser.login(user)
        if logged_user is not None and logged_user.password:  # Verifica que la contraseña sea correcta
            login_user(logged_user)
            return redirect(url_for('home'))
        else:
            flash("Usuario o contraseña incorrectos")
            return render_template('auth/login.html')
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

@app.route('/calculadora_movilidad')
@login_required
def Calculadora_Percibido():
    return render_template('calculadora_movilidad.html')

@app.route('/calculadora_uma')
@login_required
def calculadora_uma():
    return render_template('/calculadora_uma.html')

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

    # Generar el PDF
    pdf_generator = PDFGenerator(
        autos, expediente, periodo_desde, periodo_hasta,
        fecha_de_cierre_de_liquidacion, fecha_de_regulacion, 
        fecha_aprobacion_sentencia, monto_aprobado, monto_aprobado_actualizado
    )

    pdf = pdf_generator.generar_pdf()

    # Devolver el PDF al navegador
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=resultado.pdf'
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

            # Manejo de la imagen
            'imagenes': []  # Lista para almacenar las rutas de las imágenes subidas
        }
        }
        #NECESITO ALMACENAR TODAS LAS RUTAS EN UN VECTOR, LUEGO USANDO UN METODO CREARE ARCHIVOS TEMPORALES Y USANDO OTRA FUNCION LOS INSERTARE EN EL WORD
        
        # Llama a la función para crear el documento Word
        demanda = Formulario(datos_formulario)
        response = demanda.procesar_imagenes()

        return response

    return render_template('formulario_demanda.html')




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