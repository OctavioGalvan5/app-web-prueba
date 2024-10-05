import os
import tempfile
from docx import Document
from docx.shared import Inches
from datetime import datetime, timedelta
from flask import Flask, render_template, request, make_response, send_file, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from docxtpl import DocxTemplate
from config import config
#Models
from models.generador_pdf import PDFGenerator
from models.ModelUser import ModelUser

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
        # Obtener los datos del formulario

        # Casillas de verificación
        opcion_error_material = 'opcion_error_material' in request.form
        opcion_sumas_remunerativas = 'opcion_sumas_remunerativas' in request.form
        opcion_reajuste_pbu = 'opcion_reajuste_pbu' in request.form
        opcion_tasa_complementacion = 'opcion_tasa_complementacion' in request.form
        opcion_integralidad_haber_actualizacion_remuneraciones = 'opcion_integralidad_haber_actualizacion_remuneraciones' in                    request.form
        opcion_movilidad_tope_haber_maximo = 'opcion_movilidad_tope_haber_maximo' in request.form
        opcion_inaplicabilidad_tope_art_14_res_06_09 = 'opcion_inaplicabilidad_tope_art_14_res_06_09' in request.form
        opcion_movilidad_haber_jubilatorio = 'opcion_movilidad_haber_jubilatorio' in request.form
        opcion_inaplicabilidad_impuesto_ganancias = 'opcion_inaplicabilidad_impuesto_ganancias' in request.form
        opcion_inaplicabilidad_tope_ley_24241 = 'opcion_inaplicabilidad_tope_ley_24241' in request.form
        opcion_inco_articulo_3_ley_27426_y_4_ley_27609 = 'opcion_inco_articulo_3_ley_27426_y_4_ley_27609' in request.form
        opcion_inco_articulo_3_ley_27426 = 'opcion_inco_articulo_3_ley_27426' in request.form

        # Datos del cliente
        genero = request.form.get('genero')
        nombre = request.form.get('nombre')
        dni = request.form.get('DNI')
        fecha_adquisicion_derecho = request.form.get('fecha_adquisicion_derecho')
        garcia_vidal = 'garciaVidal' in request.form
        domicilio = request.form.get('domicilio')
        localidad = request.form.get('localidad')

        # Beneficio
        fecha_reajuste = request.form.get('fechaReajuste')
        expediente_reajuste = request.form.get('expedienteReajuste')
        beneficio = request.form.get('Beneficio')
        fecha_inicio_remuneraciones = request.form.get('fecha_inicio_remuneraciones')
        fecha_fin_remuneraciones = request.form.get('fecha_fin_remuneraciones')
        fecha_cese = request.form.get('fechaCese')
        # ver
        ultima_remuneracion_actividad = request.form.get('Ultima_Remuneracion_Actividad')
        fecha_ultima_remuneracion_actividad = request.form.get('fecha_Ultima_Remuneracion_Actividad')
        ultima_remuneracion_actualizada_anses = request.form.get('Ultima_remuneracion_actualizada_Anses')
        # ver
        fecha_alta_primer_haber = request.form.get('fecha_alta_primer_haber')
        monto_primer_haber = request.form.get('Monto_primer_haber')
        taza_de_reemplazo = request.form.get('Taza_de_reemplazo')

        # Servicios
        servicios_autonomos = 'Servicios_Autonomos' in request.form
        servicios_dependencia = 'Servicios_Dependencia' in request.form

        # Datos de Servicios Autónomos (si aplica)
        autonomo_input1 = request.form.get('errorInput1') if servicios_autonomos else None
        autonomo_input2 = request.form.get('errorInput2') if servicios_autonomos else None

        # Datos de Servicios en Dependencia (si aplica)
        cargo_desempleado = request.form.get('cargo_desempleado') if servicios_dependencia else None
        empleador = request.form.get('empleador') if servicios_dependencia else None

        # Otros datos adicionales
        ultimo_haber = request.form.get('Ultimo_haber')
        fecha_ultimo_haber = request.form.get('fecha_Ultimo_haber')
        fecha_reclamo = request.form.get('fecha_reclamo')
        # Manejo de la imagen
        #imagen = request.files['imageUpload']  # Obtiene la imagen del formulario

        # Crear un archivo temporal para la imagen
        #with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            #temp_file.write(imagen.read())
            #temp_file_path = temp_file.name  # Guarda la ruta del archivo temporal
            #temp_file_path es la variable que debo ingresar a crear_documento

        # Llama a la función para crear el documento Word
        response = crear_documento(nombre, dni, fecha_adquisicion_derecho, garcia_vidal, domicilio, localidad, fecha_reajuste, expediente_reajuste)

        # Eliminar el archivo temporal después de usarlo
        #try:
            #os.remove(temp_file_path)
        #except FileNotFoundError:
            #print(f"El archivo {temp_file_path} no se encontró y no pudo ser eliminado.")

        return response

    return render_template('formulario_demanda.html')


def crear_documento(nombre, dni, fecha_adquisicion_derecho, garcia_vidal, domicilio, localidad, fecha_reajuste, expediente_reajuste):
    # Convertir fecha_adquisicion_derecho a un objeto de fecha
    fecha_adquisicion_derecho = datetime.strptime(fecha_adquisicion_derecho, '%Y-%m-%d')

    # Inicializar fecha_escrito con la fecha de adquisición
    fecha_escrito = fecha_adquisicion_derecho

    # Restar un año si garcia_vidal es True
    if garcia_vidal:
        fecha_escrito = fecha_escrito - timedelta(days=365)  # Restar un año

    # Seleccionar plantilla según la fecha_escrito
    if fecha_escrito < datetime(2018, 3, 1):
        plantilla = 'datos/MODELO ANT 03.2018. COMPLETO..docx'
    elif datetime(2018, 3, 1) <= fecha_escrito < datetime(2021, 1, 1):
        plantilla = 'datos/plantillaB.docx'
    else:
        plantilla = 'datos/plantillaC.docx'

    # Cargar el archivo .docx de la plantilla seleccionada
    doc = DocxTemplate(plantilla)

    # Crear el contexto con las variables
    contexto = {
        'nombre': nombre,
        'dni': dni,
        'fecha_adquisicion_derecho': fecha_adquisicion_derecho,
        'garcia_vidal': garcia_vidal,
        'domicilio': domicilio,
        'localidad': localidad,
        'fecha_reajuste': fecha_reajuste,
        'expediente_reajuste': expediente_reajuste,
    }

    # Renderizar el documento con el contexto
    doc.render(contexto)

    # Guardar el documento editado temporalmente
    temp_doc_path = 'datos/documento_temporal.docx'
    doc.save(temp_doc_path)  # Guarda temporalmente antes de agregar la imagen

    # Abrir el documento para agregar la imagen
    doc = Document(temp_doc_path)

    # Encontrar el marcador 'Imagen_aqui' en los párrafos y reemplazarlo por la imagen
    #for paragraph in doc.paragraphs:
        #if 'Imagen_aqui' in paragraph.text:
            # Reemplazar el texto del marcador por un espacio vacío
           # paragraph.text = paragraph.text.replace('Imagen_aqui', '')
            # Insertar la imagen justo después del párrafo donde se encontraba 'Imagen_aqui'
            #run = paragraph.add_run()  # Crear un nuevo run en el párrafo
            #run.add_picture(ruta_imagen, width=Inches(5))  # Cambiar el tamaño de la imagen según sea necesario
           # break

    # Guardar el documento final editado
    final_path = 'datos/documento_editado.docx'
    doc.save(final_path)

    # Devolver el archivo editado al usuario
    return send_file(final_path, as_attachment=True)

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
