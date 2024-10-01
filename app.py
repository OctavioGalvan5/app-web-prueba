from flask import Flask, render_template, request, make_response, send_file, redirect, url_for, flash
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
def Calculadora_Percibido():
    return render_template('calculadora_movilidad.html')

@app.route('/calculadora_uma')
def calculadora_uma():
    return render_template('/calculadora_uma.html')


@app.route('/resultado_uma', methods=['POST'])
def generar_pdf_route():
    autos = request.form.get('Autos')
    expediente = request.form.get('Expediente')
    periodo_desde = request.form.get('PeriodoDesde')
    periodo_hasta = request.form.get('PeriodoHasta')
    fecha_de_cierre_de_liquidacion = request.form.get('Fecha_de_Cierre_de_Liquidacion')
    fecha_de_regulacion = request.form.get('Fecha_de_Regulacion')
    fecha_aprobacion_sentencia = request.form.get('Fecha_Aprobacion_Sentencia')
    monto_aprobado = request.form.get('Monto_Aprobado')
    monto_aprobado_actualizado = request.form.get('Monto_Aprobado_Actualizado')

    pdf_generator = PDFGenerator(
        autos, expediente, periodo_desde, periodo_hasta,
        fecha_de_cierre_de_liquidacion, fecha_de_regulacion, 
        fecha_aprobacion_sentencia, monto_aprobado, monto_aprobado_actualizado
    )

    pdf = pdf_generator.generar_pdf()

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
        edad = request.form['edad']
        # Llama a la función para crear el documento Word
        return crear_documento(nombre, edad)

    return render_template('formulario.html')

def crear_documento(nombre, edad):
    # Cargar el archivo .docx de plantilla
    doc = DocxTemplate('datos/plantilla.docx')

    # Crear el contexto con las variables
    contexto = {
        'nombre': nombre,
        'edad': edad,
    }

    # Renderizar el documento con el contexto
    doc.render(contexto)

    # Guardar el documento editado
    doc.save('datos/documento_editado.docx')

    # Devolver el archivo editado al usuario
    return send_file('datos/documento_editado.docx', as_attachment=True)

def status_401(error):
    return redirect(url_for('login'))


def status_404(error):
    return "<h1>Página no encontrada</h1>", 404
    
if __name__ == '__main__':
    app.config.from_object(config['development'])
    app.register_error_handler(401, status_401)
    app.register_error_handler(404, status_404)
    app.run()
