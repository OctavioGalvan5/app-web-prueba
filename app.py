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
        nombre = request.form['nombre']
        dni = request.form['DNI']
        fecha_adquisicion_derecho= request.form['fecha_adquisicion_derecho']
        garcia_vidal = 'garciaVidal' in request.form  # Si está marcado
        domicilio = request.form['domicilio']
        localidad = request.form['localidad']
        fecha_reajuste = request.form['fechaReajuste']
        expediente_reajuste = request.form['expedienteReajuste']

        # Llama a la función para crear el documento Word
        return crear_documento(nombre, dni, fecha_adquisicion_derecho, garcia_vidal, domicilio, localidad, fecha_reajuste, expediente_reajuste)

    return render_template('formulario_demanda.html')

def crear_documento(nombre, dni, fecha_adquisicion_derecho, garcia_vidal, domicilio, localidad, fecha_reajuste, expediente_reajuste):
    # Convertir fecha_adquisicion_derecho a un objeto de fecha
    fecha_adquisicion_derecho = datetime.strptime(fecha_adquisicion_derecho, '%Y-%m-%d')  # Asegúrate de que el formato coincida con el de tu entrada

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
        'fecha_adquisicion_derecho': fecha_adquisicion_derecho,  # Usar objeto de fecha directamente
        'garcia_vidal': garcia_vidal,
        'domicilio': domicilio,
        'localidad': localidad,
        'fecha_reajuste': fecha_reajuste,
        'expediente_reajuste': expediente_reajuste,
    }

    # Renderizar el documento con el contexto
    doc.render(contexto)

    # Guardar el documento editado
    doc.save('datos/documento_editado.docx')

    # Devolver el archivo editado al usuario
    return send_file('datos/documento_editado.docx', as_attachment=True)

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
