from flask import Flask, render_template, request, make_response
from xhtml2pdf import pisa
from io import BytesIO
from database import obtener_acordada, obtener_valor_uma
from calculos import calcular_porcentajes, formatear_dinero, transformar_fecha, calcular_porcentajes_ley_21839

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
    monto_aprobado = float(monto_aprobado)  # o float(monto_aprobado) si no necesitas precisión decimal
    monto_aprobado_actualizado = float(monto_aprobado_actualizado)  # o float(monto_actualizado)
    ### CIERRE DE LIQUIDACION ###
    Acordada_fecha_de_cierre_de_liquidacion = obtener_acordada(fecha_de_cierre_de_liquidacion)
    UMA_fecha_de_cierre_de_liquidacion = obtener_valor_uma(fecha_de_cierre_de_liquidacion)
    porcentajesFCL, cantidadFCL, minimoFCL, apoderadoFCL, reduccionFCL,ejecucionFCL, incidenciaFCL = calcular_porcentajes(monto_aprobado, UMA_fecha_de_cierre_de_liquidacion)
    ### APROBACION ###
    Acordada_fecha_aprobacion_sentencia = obtener_acordada(fecha_aprobacion_sentencia)
    UMA_fecha_aprobacion_sentencia = obtener_valor_uma(fecha_aprobacion_sentencia)
    porcentajesAS, cantidadAS, minimoAS, apoderadoAS, reduccionAS,ejecucionAS, incidenciaAS = calcular_porcentajes(monto_aprobado,UMA_fecha_aprobacion_sentencia)
    ### REGULACION ###
    Acordada_fecha_de_regulacion = obtener_acordada(fecha_de_regulacion)
    UMA_fecha_de_regulacion = obtener_valor_uma(fecha_de_regulacion)
    porcentajesR, cantidadR, minimoR, apoderadoR, reduccionR,ejecucionR, incidenciaR = calcular_porcentajes(monto_aprobado, UMA_fecha_de_regulacion)
    ### TASA PASIVA ###
    porcentajesTP, cantidadTP, minimoTP, apoderadoTP, reduccionTP, ejecucionTP, incidenciaTP = calcular_porcentajes(monto_aprobado_actualizado, UMA_fecha_de_regulacion)

    ### ley 21.839 ###
    porcentaje_aplicable, apoderada, sin_excepciones, criterio = calcular_porcentajes_ley_21839(monto_aprobado)     
    porcentaje_aplicableTP, apoderadaTP, sin_excepcionesTP, criterioTP = calcular_porcentajes_ley_21839(monto_aprobado_actualizado)     

    # Renderiza el HTML a partir de la plantilla
    rendered = render_template(
        'resultado_calculadora_uma.html',
        autos=autos,
        expediente=expediente,
        periodo_desde=transformar_fecha(periodo_desde),
        periodo_hasta=transformar_fecha(periodo_hasta),
        #
        fecha_de_cierre_de_liquidacion=transformar_fecha(fecha_de_cierre_de_liquidacion),
        Acordada_fecha_de_cierre_de_liquidacion=Acordada_fecha_de_cierre_de_liquidacion,
        UMA_fecha_de_cierre_de_liquidacion=formatear_dinero(UMA_fecha_de_cierre_de_liquidacion),
        porcentajesFCL=porcentajesFCL,
        cantidadFCL=cantidadFCL,
        minimoFCL=minimoFCL,
        apoderadoFCL=apoderadoFCL,
        reduccionFCL=reduccionFCL,
        ejecucionFCL=ejecucionFCL,
        incidenciaFCL=incidenciaFCL,
        #
        fecha_de_regulacion=transformar_fecha(fecha_de_regulacion),
        Acordada_fecha_de_regulacion=Acordada_fecha_de_regulacion,
        UMA_fecha_de_regulacion=formatear_dinero(UMA_fecha_de_regulacion),
        porcentajesR=porcentajesR,
        cantidadR=cantidadR,
        minimoR=minimoR,
        apoderadoR=apoderadoR,
        reduccionR=reduccionR,
        ejecucionR=ejecucionR,
        incidenciaR=incidenciaR,
        #
        fecha_aprobacion_sentencia=transformar_fecha(fecha_aprobacion_sentencia),
        Acordada_fecha_aprobacion_sentencia=Acordada_fecha_aprobacion_sentencia,
        UMA_fecha_aprobacion_sentencia=formatear_dinero(UMA_fecha_aprobacion_sentencia),
        porcentajesAS=porcentajesAS,
        cantidadAS=cantidadAS,
        minimoAS=minimoAS,
        apoderadoAS=apoderadoAS,
        reduccionAS=reduccionAS,
        ejecucionAS=ejecucionAS,
        incidenciaAS=incidenciaAS,
        #
        porcentajesTP=porcentajesTP,
        cantidadTP=cantidadTP,
        minimoTP=minimoTP,
        apoderadoTP=apoderadoTP,
        reduccionTP=reduccionTP,
        ejecucionTP=ejecucionTP,
        incidenciaTP=incidenciaTP,
        #
        monto_aprobado=formatear_dinero(monto_aprobado),
        monto_aprobado_actualizado=formatear_dinero(monto_aprobado_actualizado),
        #
        porcentaje_aplicable=formatear_dinero(porcentaje_aplicable),
        apoderada=formatear_dinero(apoderada),
        sin_excepciones=formatear_dinero(sin_excepciones),
        criterio=formatear_dinero(criterio),
        porcentaje_aplicableTP=formatear_dinero(porcentaje_aplicableTP),
        apoderadaTP=formatear_dinero(apoderadaTP),
        sin_excepcionesTP=formatear_dinero(sin_excepcionesTP),
        criterioTP=formatear_dinero(criterioTP)
    )

    # Convierte el HTML a PDF usando xhtml2pdf
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
    pdf_buffer.seek(0)
    pdf = pdf_buffer.getvalue()

    # Crea una respuesta HTTP con el contenido del PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=resultado.pdf'  # Cambiado a 'inline'

    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
