from flask import Flask, render_template, request, make_response, send_file
from docxtpl import DocxTemplate
from models.generador_pdf import PDFGenerator

app = Flask(__name__)

@app.route('/')
def Index():
    return render_template('menu.html')

@app.route('/calculadora_percibido')
def Calculadora_Percibido():
    return render_template('prueba.html')

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
def index():
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
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
