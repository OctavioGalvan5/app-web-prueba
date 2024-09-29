from xhtml2pdf import pisa
from io import BytesIO
from models.database import obtener_acordada, obtener_valor_uma
from models.calculos import calcular_porcentajes, formatear_dinero, transformar_fecha, calcular_porcentajes_ley_21839
from flask import render_template

class PDFGenerator:
  def __init__(self, autos, expediente, periodo_desde, periodo_hasta, fecha_de_cierre_de_liquidacion,
               fecha_de_regulacion, fecha_aprobacion_sentencia, monto_aprobado, monto_aprobado_actualizado):
      self.autos = autos
      self.expediente = expediente
      self.periodo_desde = periodo_desde
      self.periodo_hasta = periodo_hasta
      self.fecha_de_cierre_de_liquidacion = fecha_de_cierre_de_liquidacion
      self.fecha_de_regulacion = fecha_de_regulacion
      self.fecha_aprobacion_sentencia = fecha_aprobacion_sentencia
      self.monto_aprobado = float(monto_aprobado)
      self.monto_aprobado_actualizado = float(monto_aprobado_actualizado)

  def obtener_datos(self):
      datos = {}
      datos['Acordada_fecha_de_cierre_de_liquidacion'] = obtener_acordada(self.fecha_de_cierre_de_liquidacion)
      datos['UMA_fecha_de_cierre_de_liquidacion'] = obtener_valor_uma(self.fecha_de_cierre_de_liquidacion)
      datos['porcentajesFCL'], datos['cantidadFCL'], datos['minimoFCL'], datos['apoderadoFCL'], datos['reduccionFCL'], datos['ejecucionFCL'], datos['incidenciaFCL'] = calcular_porcentajes(self.monto_aprobado, datos['UMA_fecha_de_cierre_de_liquidacion'])

      datos['Acordada_fecha_de_regulacion'] = obtener_acordada(self.fecha_de_regulacion)
      datos['UMA_fecha_de_regulacion'] = obtener_valor_uma(self.fecha_de_regulacion)
      datos['porcentajesR'], datos['cantidadR'], datos['minimoR'], datos['apoderadoR'], datos['reduccionR'], datos['ejecucionR'], datos['incidenciaR'] = calcular_porcentajes(self.monto_aprobado, datos['UMA_fecha_de_regulacion'])

      datos['Acordada_fecha_aprobacion_sentencia'] = obtener_acordada(self.fecha_aprobacion_sentencia)
      datos['UMA_fecha_aprobacion_sentencia'] = obtener_valor_uma(self.fecha_aprobacion_sentencia)
      datos['porcentajesAS'], datos['cantidadAS'], datos['minimoAS'], datos['apoderadoAS'], datos['reduccionAS'], datos['ejecucionAS'], datos['incidenciaAS'] = calcular_porcentajes(self.monto_aprobado, datos['UMA_fecha_aprobacion_sentencia'])

      datos['porcentajesTP'], datos['cantidadTP'], datos['minimoTP'], datos['apoderadoTP'], datos['reduccionTP'], datos['ejecucionTP'], datos['incidenciaTP'] = calcular_porcentajes(self.monto_aprobado_actualizado, datos['UMA_fecha_de_regulacion'])

      datos['porcentaje_aplicable'], datos['apoderada'], datos['sin_excepciones'], datos['criterio'] = calcular_porcentajes_ley_21839(self.monto_aprobado)
      datos['porcentaje_aplicableTP'], datos['apoderadaTP'], datos['sin_excepcionesTP'], datos['criterioTP'] = calcular_porcentajes_ley_21839(self.monto_aprobado_actualizado)

      return datos

  def generar_pdf(self):
      datos = self.obtener_datos()

      rendered = render_template(
          'resultado_calculadora_uma.html',
          autos=self.autos,
          expediente=self.expediente,
          periodo_desde=transformar_fecha(self.periodo_desde),
          periodo_hasta=transformar_fecha(self.periodo_hasta),
          fecha_de_cierre_de_liquidacion=transformar_fecha(self.fecha_de_cierre_de_liquidacion),
          Acordada_fecha_de_cierre_de_liquidacion=datos['Acordada_fecha_de_cierre_de_liquidacion'],
          UMA_fecha_de_cierre_de_liquidacion=formatear_dinero(datos['UMA_fecha_de_cierre_de_liquidacion']),
          porcentajesFCL=datos['porcentajesFCL'],
          cantidadFCL=datos['cantidadFCL'],
          minimoFCL=datos['minimoFCL'],
          apoderadoFCL=datos['apoderadoFCL'],
          reduccionFCL=datos['reduccionFCL'],
          ejecucionFCL=datos['ejecucionFCL'],
          incidenciaFCL=datos['incidenciaFCL'],
          fecha_de_regulacion=transformar_fecha(self.fecha_de_regulacion),
          Acordada_fecha_de_regulacion=datos['Acordada_fecha_de_regulacion'],
          UMA_fecha_de_regulacion=formatear_dinero(datos['UMA_fecha_de_regulacion']),
          porcentajesR=datos['porcentajesR'],
          cantidadR=datos['cantidadR'],
          minimoR=datos['minimoR'],
          apoderadoR=datos['apoderadoR'],
          reduccionR=datos['reduccionR'],
          ejecucionR=datos['ejecucionR'],
          incidenciaR=datos['incidenciaR'],
          fecha_aprobacion_sentencia=transformar_fecha(self.fecha_aprobacion_sentencia),
          Acordada_fecha_aprobacion_sentencia=datos['Acordada_fecha_aprobacion_sentencia'],
          UMA_fecha_aprobacion_sentencia=formatear_dinero(datos['UMA_fecha_aprobacion_sentencia']),
          porcentajesAS=datos['porcentajesAS'],
          cantidadAS=datos['cantidadAS'],
          minimoAS=datos['minimoAS'],
          apoderadoAS=datos['apoderadoAS'],
          reduccionAS=datos['reduccionAS'],
          ejecucionAS=datos['ejecucionAS'],
          incidenciaAS=datos['incidenciaAS'],
          porcentajesTP=datos['porcentajesTP'],
          cantidadTP=datos['cantidadTP'],
          minimoTP=datos['minimoTP'],
          apoderadoTP=datos['apoderadoTP'],
          reduccionTP=datos['reduccionTP'],
          ejecucionTP=datos['ejecucionTP'],
          incidenciaTP=datos['incidenciaTP'],
          monto_aprobado=formatear_dinero(self.monto_aprobado),
          monto_aprobado_actualizado=formatear_dinero(self.monto_aprobado_actualizado),
          porcentaje_aplicable=formatear_dinero(datos['porcentaje_aplicable']),
          apoderada=formatear_dinero(datos['apoderada']),
          sin_excepciones=formatear_dinero(datos['sin_excepciones']),
          criterio=formatear_dinero(datos['criterio']),
          porcentaje_aplicableTP=formatear_dinero(datos['porcentaje_aplicableTP']),
          apoderadaTP=formatear_dinero(datos['apoderadaTP']),
          sin_excepcionesTP=formatear_dinero(datos['sin_excepcionesTP']),
          criterioTP=formatear_dinero(datos['criterioTP'])
      )

      pdf_buffer = BytesIO()
      pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
      pdf_buffer.seek(0)
      return pdf_buffer.getvalue()
