from flask import Flask, render_template, request, make_response
from xhtml2pdf import pisa
from io import BytesIO


app = Flask(__name__)

@app.route('/')
def hello_world():
    return render_template('menu.html')

@app.route('/calculadora_percibido')
def Calculadora_Percibido():
    return render_template('prueba.html')

@app.route('/calculadora_uma')
def calculadora_uma():
    return render_template('/calculadora_uma.html')


@app.route('/resultado_uma')
def resultado_calculadora_uma():
    return render_template('resultado_calculadora_uma.html')
@app.route('/generar_pdf', methods=['POST'])
def generar_pdf():
    autos = request.form.get('Autos')
    expediente = request.form.get('Expediente')
    periodo_desde = request.form.get('PeriodoDesde')
    periodo_hasta = request.form.get('PeriodoHasta')
    fecha_de_cierre_de_liquidacion = request.form.get('Fecha_de_Cierre_de_Liquidacion')
    fecha_de_regulacion = request.form.get('Fecha_de_Regulacion')
    fecha_aprobacion_sentencia = request.form.get('Fecha_Aprobacion_Sentencia')
    monto_aprobado = request.form.get('Monto_Aprobado')
    monto_aprobado_actualizado = request.form.get('Monto_Aprobado_Actualizado')


    # Renderiza el HTML a partir de la plantilla
    rendered = render_template('resultado.html', 
                               autos=autos, 
                               expediente=expediente, 
                               periodo_desde=periodo_desde, 
                               periodo_hasta=periodo_hasta, 
                               fecha_de_cierre_de_liquidacion=fecha_de_cierre_de_liquidacion,
                               fecha_de_regulacion=fecha_de_regulacion,
                               fecha_aprobacion_sentencia=fecha_aprobacion_sentencia,
                               monto_aprobado=monto_aprobado,
                               monto_aprobado_actualizado=monto_aprobado_actualizado)

    # Convierte el HTML a PDF usando xhtml2pdf
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
    pdf_buffer.seek(0)
    pdf = pdf_buffer.getvalue()

    # Crea una respuesta HTTP con el contenido del PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=resultado.pdf'

    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
