from xhtml2pdf import pisa
from io import BytesIO
from models.database import engine
from services.calculos import calcular_porcentajes, formatear_dinero, transformar_fecha, calcular_porcentajes_ley_21839
from flask import render_template
from datetime import datetime
from sqlalchemy import text


def obtener_acordada(fecha_ingresada):
    # Convertir la fecha ingresada por el usuario a un objeto datetime.date
    fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%Y-%m-%d').date()

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM valor_uma"))

        # Variables para almacenar la fila más cercana
        fila_cercana = None
        fecha_cercana = None

        for row in result:
            fecha_fila = row[1]  # Asumiendo que la segunda columna es la fecha
            if fecha_fila <= fecha_ingresada_dt:
                # Comparar para encontrar la fecha más cercana
                if fecha_cercana is None or fecha_fila > fecha_cercana:
                    fecha_cercana = fecha_fila
                    fila_cercana = row

        if fila_cercana:
            # Extraer el elemento 4
            acordada = fila_cercana[3]
            return acordada
        else:
            return None

def obtener_valor_uma(fecha_ingresada):
    fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%Y-%m-%d').date()

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM valor_uma"))

        # Variables para almacenar la fila más cercana
        fila_cercana = None
        fecha_cercana = None

        for row in result:
            fecha_fila = row[1]  # Asumiendo que la segunda columna es la fecha
            if fecha_fila <= fecha_ingresada_dt:
                # Comparar para encontrar la fecha más cercana
                if fecha_cercana is None or fecha_fila > fecha_cercana:
                    fecha_cercana = fecha_fila
                    fila_cercana = row

        if fila_cercana:
            # Extraer el elemento 5
            acordada = fila_cercana[4]
            return acordada
        else:
            return None


class PDFGenerator:
  def __init__(self, autos, expediente, periodo_desde, periodo_hasta, fecha_de_cierre_de_liquidacion,
               fecha_de_regulacion, fecha_aprobacion_sentencia, monto_aprobado, monto_aprobado_actualizado, incluirAprobacion,
              incluirRegulacion, incluirMontoActualizado):
      self.autos = autos
      self.expediente = expediente
      self.periodo_desde = periodo_desde
      self.periodo_hasta = periodo_hasta
      self.fecha_de_cierre_de_liquidacion = fecha_de_cierre_de_liquidacion
      self.incluirRegulacion = incluirRegulacion
      self.incluirAprobacion = incluirAprobacion
      self.incluirMontoActualizado = incluirMontoActualizado
      self.fecha_de_regulacion = fecha_de_regulacion
      self.fecha_aprobacion_sentencia = fecha_aprobacion_sentencia
      self.monto_aprobado = float(monto_aprobado)
      if incluirMontoActualizado:
        self.monto_aprobado_actualizado = float(monto_aprobado_actualizado)
      else:
        self.monto_aprobado_actualizado = 0

  def obtener_datos(self):
      datos = {}
      datos['Acordada_fecha_de_cierre_de_liquidacion'] = obtener_acordada(self.fecha_de_cierre_de_liquidacion)
      datos['UMA_fecha_de_cierre_de_liquidacion'] = obtener_valor_uma(self.fecha_de_cierre_de_liquidacion)
      datos['cantidad_FCL'], datos['valor_dividido_FCL'], datos['porcentajes_FCL'], datos['porcentaje_anterior_FCL'], datos['porcentaje_maximo_FCL'], datos['primera_valor_uma_FCL'], datos['primera_valor_uma_final_FCL'], datos['segundo_valor_uma_FCL'], datos['porcentaje_minimo_FCL'], datos['segunda_valor_uma_final_FCL'], datos['total_uma_FCL'], datos['apoderado_FCL'], datos['reduccion_excepciones_FCL'] = calcular_porcentajes(self.monto_aprobado, datos['UMA_fecha_de_cierre_de_liquidacion'])

      if self.incluirRegulacion:
          datos['Acordada_fecha_de_regulacion'] = obtener_acordada(self.fecha_de_regulacion)
          datos['UMA_fecha_de_regulacion'] = obtener_valor_uma(self.fecha_de_regulacion)
          datos['cantidad_R'], datos['valor_dividido_R'], datos['porcentajes_R'], datos['porcentaje_anterior_R'], datos['porcentaje_maximo_R'], datos['primera_valor_uma_R'],datos['primera_valor_uma_final_R'], datos['segundo_valor_uma_R'], datos['porcentaje_minimo_R'],  datos['segunda_valor_uma_final_R'], datos['total_uma_R'], datos['apoderado_R'], datos['reduccion_excepciones_R'] = calcular_porcentajes(self.monto_aprobado, datos['UMA_fecha_de_regulacion'])

      if self.incluirAprobacion:
          datos['Acordada_fecha_aprobacion_sentencia'] = obtener_acordada(self.fecha_aprobacion_sentencia)
          datos['UMA_fecha_aprobacion_sentencia'] = obtener_valor_uma(self.fecha_aprobacion_sentencia)
          datos['cantidad_AS'], datos['valor_dividido_AS'],  datos['porcentajes_AS'], datos['porcentaje_anterior_AS'], datos['porcentaje_maximo_AS'], datos['primera_valor_uma_AS'], datos['primera_valor_uma_final_AS'], datos['segundo_valor_uma_AS'], datos['porcentaje_minimo_AS'], datos['segunda_valor_uma_final_AS'], datos['total_uma_AS'], datos['apoderado_AS'], datos['reduccion_excepciones_AS'] = calcular_porcentajes(self.monto_aprobado, datos['UMA_fecha_aprobacion_sentencia'])

      if self.incluirMontoActualizado:
          datos['cantidad_TP'], datos['valor_dividido_TP'], datos['porcentajes_TP'], datos['porcentaje_anterior_TP'], datos['porcentaje_maximo_TP'], datos['primera_valor_uma_TP'], datos['primera_valor_uma_final_TP'], datos['segundo_valor_uma_TP'], datos['porcentaje_minimo_TP'],datos['segunda_valor_uma_final_TP'], datos['total_uma_TP'], datos['apoderado_TP'], datos['reduccion_excepciones_TP'] = calcular_porcentajes(self.monto_aprobado_actualizado, datos['UMA_fecha_de_regulacion'])


      datos['porcentaje_aplicable'], datos['apoderada'], datos['sin_excepciones'], datos['criterio'] = calcular_porcentajes_ley_21839(self.monto_aprobado)
      datos['porcentaje_aplicableTP'], datos['apoderadaTP'], datos['sin_excepcionesTP'], datos['criterioTP'] = calcular_porcentajes_ley_21839(self.monto_aprobado_actualizado)

      return datos

  def generar_pdf(self):
      datos = self.obtener_datos()

      context = {
          'autos': self.autos,
          'expediente': self.expediente,
          'incluirRegulacion': self.incluirRegulacion,
          'incluirAprobacion': self.incluirAprobacion,
          'incluirMontoActualizado': self.incluirMontoActualizado,
          'periodo_desde': transformar_fecha(self.periodo_desde),
          'periodo_hasta': transformar_fecha(self.periodo_hasta),
          'fecha_de_cierre_de_liquidacion': transformar_fecha(self.fecha_de_cierre_de_liquidacion),
          'Acordada_fecha_de_cierre_de_liquidacion': datos['Acordada_fecha_de_cierre_de_liquidacion'],
          'UMA_fecha_de_cierre_de_liquidacion': formatear_dinero(datos['UMA_fecha_de_cierre_de_liquidacion']),
          'porcentajes_FCL': datos['porcentajes_FCL'],
          'cantidad_FCL': datos['cantidad_FCL'],
          'valor_dividido_FCL' : datos['valor_dividido_FCL'],
          'porcentaje_anterior_FCL': datos['porcentaje_anterior_FCL'],
          'porcentaje_maximo_FCL': datos['porcentaje_maximo_FCL'],
          'primera_valor_uma_FCL': datos['primera_valor_uma_FCL'],
          'primera_valor_uma_final_FCL': datos['primera_valor_uma_final_FCL'],
          'segundo_valor_uma_FCL': datos['segundo_valor_uma_FCL'],
          'porcentaje_minimo_FCL': datos['porcentaje_minimo_FCL'],
          'segunda_valor_uma_final_FCL': datos['segunda_valor_uma_final_FCL'],
          'total_uma_FCL': datos['total_uma_FCL'],
          'apoderado_FCL': datos['apoderado_FCL'],
          'reduccion_excepciones_FCL': datos['reduccion_excepciones_FCL'],
          'monto_aprobado': formatear_dinero(self.monto_aprobado),
          'monto_aprobado_actualizado': formatear_dinero(self.monto_aprobado_actualizado),
          'porcentaje_aplicable': formatear_dinero(datos['porcentaje_aplicable']),
          'apoderada': formatear_dinero(datos['apoderada']),
          'sin_excepciones': formatear_dinero(datos['sin_excepciones']),
          'criterio': formatear_dinero(datos['criterio']),
          'porcentaje_aplicableTP': formatear_dinero(datos['porcentaje_aplicableTP']),
          'apoderadaTP': formatear_dinero(datos['apoderadaTP']),
          'sin_excepcionesTP': formatear_dinero(datos['sin_excepcionesTP']),
          'criterioTP': formatear_dinero(datos['criterioTP']),
      }

      if self.incluirRegulacion:
          context.update({
              'fecha_de_regulacion': transformar_fecha(self.fecha_de_regulacion),
              'Acordada_fecha_de_regulacion': datos['Acordada_fecha_de_regulacion'],
              'UMA_fecha_de_regulacion': formatear_dinero(datos['UMA_fecha_de_regulacion']),
              'porcentajes_R': datos['porcentajes_R'],
              'cantidad_R': datos['cantidad_R'],
              'valor_dividido_R' : datos['valor_dividido_R'],
              'porcentaje_anterior_R': datos['porcentaje_anterior_R'],
              'primera_valor_uma_R': datos['primera_valor_uma_R'],
              'porcentaje_maximo_R': datos['porcentaje_maximo_R'],
              'primera_valor_uma_final_R': datos['primera_valor_uma_final_R'],
              'segundo_valor_uma_R': datos['segundo_valor_uma_R'],
              'porcentaje_minimo_R': datos['porcentaje_minimo_R'],
              'segunda_valor_uma_final_R': datos['segunda_valor_uma_final_R'],
              'total_uma_R': datos['total_uma_R'],
              'apoderado_R': datos['apoderado_R'],
              'reduccion_excepciones_R': datos['reduccion_excepciones_R'],
          })

      if self.incluirAprobacion:
          context.update({
              'fecha_aprobacion_sentencia': transformar_fecha(self.fecha_aprobacion_sentencia),
              'Acordada_fecha_aprobacion_sentencia': datos['Acordada_fecha_aprobacion_sentencia'],
              'UMA_fecha_aprobacion_sentencia': formatear_dinero(datos['UMA_fecha_aprobacion_sentencia']),
              'porcentajes_AS': datos['porcentajes_AS'],
              'cantidad_AS': datos['cantidad_AS'],
              'valor_dividido_AS' : datos['valor_dividido_AS'],
              'porcentaje_anterior_AS': datos['porcentaje_anterior_AS'],
              'porcentaje_maximo_AS': datos['porcentaje_maximo_AS'],
              'primera_valor_uma_AS': datos['primera_valor_uma_AS'],
              'primera_valor_uma_final_AS': datos['primera_valor_uma_final_AS'],
              'segundo_valor_uma_AS': datos['segundo_valor_uma_AS'],
              'porcentaje_minimo_AS': datos['porcentaje_minimo_AS'],
              'segunda_valor_uma_final_AS': datos['segunda_valor_uma_final_AS'],
              'total_uma_AS': datos['total_uma_AS'],
              'apoderado_AS': datos['apoderado_AS'],
              'reduccion_excepciones_AS': datos['reduccion_excepciones_AS'],
          })

      if self.incluirMontoActualizado:
          context.update({
              'porcentajes_TP': datos['porcentajes_TP'],
              'cantidad_TP': datos['cantidad_TP'],
              'valor_dividido_TP' : datos['valor_dividido_TP'],
              'porcentaje_anterior_TP': datos['porcentaje_anterior_TP'],
              'porcentaje_maximo_TP': datos['porcentaje_maximo_TP'],
              'primera_valor_uma_TP': datos['primera_valor_uma_TP'],
              'primera_valor_uma_final_TP': datos['primera_valor_uma_final_TP'],
              'porcentaje_minimo_TP': datos['porcentaje_minimo_TP'],
              'segundo_valor_uma_TP': datos['segundo_valor_uma_TP'],
              'segunda_valor_uma_final_TP': datos['segunda_valor_uma_final_TP'],
              'total_uma_TP': datos['total_uma_TP'],
              'apoderado_TP': datos['apoderado_TP'],
              'reduccion_excepciones_TP': datos['reduccion_excepciones_TP'],
          })

      rendered = render_template('calculadora_uma/resultado_calculadora_uma.html', **context)

      pdf_buffer = BytesIO()
      pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
      pdf_buffer.seek(0)
      return pdf_buffer.getvalue()
