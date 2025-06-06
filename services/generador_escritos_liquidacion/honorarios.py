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
               fecha_de_regulacion, fecha_aprobacion_sentencia, total_liquidacion, Total_Segunda_Liquidacion, Total_Primera_Liquidacion_IPC, Total_Segunda_Liquidacion_IPC, Segunda_Liquidacion_Si, IPC_Liquidacion_Si):
      self.autos = autos
      self.expediente = expediente
      self.periodo_desde = periodo_desde
      self.periodo_hasta = periodo_hasta
      self.fecha_de_cierre_de_liquidacion = fecha_de_cierre_de_liquidacion
      self.Segunda_Liquidacion_Si = Segunda_Liquidacion_Si
      self.IPC_Liquidacion_Si = IPC_Liquidacion_Si
      self.fecha_de_regulacion = fecha_de_regulacion
      self.fecha_aprobacion_sentencia = fecha_aprobacion_sentencia
      self.total_liquidacion = float(total_liquidacion)
      if Segunda_Liquidacion_Si:
        self.Total_Segunda_Liquidacion = float(Total_Segunda_Liquidacion)
      if IPC_Liquidacion_Si:
        self.Total_Primera_Liquidacion_IPC = float(Total_Primera_Liquidacion_IPC)
      if Segunda_Liquidacion_Si and IPC_Liquidacion_Si:
        self.Total_Segunda_Liquidacion_IPC = float(Total_Segunda_Liquidacion_IPC)

  def obtener_datos(self):
      datos = {}
      datos['Acordada_fecha_de_cierre_de_liquidacion'] = obtener_acordada(self.fecha_de_cierre_de_liquidacion)
      datos['UMA_fecha_de_cierre_de_liquidacion'] = obtener_valor_uma(self.fecha_de_cierre_de_liquidacion)
      datos['porcentajesFCL'], datos['cantidadFCL'], datos['minimoFCL'], datos['apoderadoFCL'], datos['reduccionFCL'], datos['ejecucionFCL'], datos['incidenciaFCL'] = calcular_porcentajes(self.total_liquidacion, datos['UMA_fecha_de_cierre_de_liquidacion'])

      if self.IPC_Liquidacion_Si:
          datos['Acordada_fecha_de_regulacion'] = obtener_acordada(self.fecha_de_regulacion)
          datos['UMA_fecha_de_regulacion'] = obtener_valor_uma(self.fecha_de_regulacion)
          datos['porcentajesR'], datos['cantidadR'], datos['minimoR'], datos['apoderadoR'], datos['reduccionR'], datos['ejecucionR'], datos['incidenciaR'] = calcular_porcentajes(self.Total_Primera_Liquidacion_IPC, datos['UMA_fecha_de_regulacion'])

      if self.Segunda_Liquidacion_Si:
          datos['Acordada_fecha_aprobacion_sentencia'] = obtener_acordada(self.fecha_aprobacion_sentencia)
          datos['UMA_fecha_aprobacion_sentencia'] = obtener_valor_uma(self.fecha_aprobacion_sentencia)
          datos['porcentajesAS'], datos['cantidadAS'], datos['minimoAS'], datos['apoderadoAS'], datos['reduccionAS'], datos['ejecucionAS'], datos['incidenciaAS'] = calcular_porcentajes(self.Total_Segunda_Liquidacion, datos['UMA_fecha_aprobacion_sentencia'])

      if self.IPC_Liquidacion_Si and self.Segunda_Liquidacion_Si:
          datos['porcentajesTP'], datos['cantidadTP'], datos['minimoTP'], datos['apoderadoTP'], datos['reduccionTP'], datos['ejecucionTP'], datos['incidenciaTP'] = calcular_porcentajes(self.Total_Segunda_Liquidacion_IPC, datos['UMA_fecha_de_regulacion'])

      #datos['porcentaje_aplicable'], datos['apoderada'], datos['sin_excepciones'], datos['criterio'] = calcular_porcentajes_ley_21839(self.monto_aprobado)
      #datos['porcentaje_aplicableTP'], datos['apoderadaTP'], datos['sin_excepcionesTP'], datos['criterioTP'] = calcular_porcentajes_ley_21839(self.monto_aprobado_actualizado)

      return datos

  def generar_pdf(self):
      datos = self.obtener_datos()

      context = {
          'autos': self.autos,
          'expediente': self.expediente,
          'IPC_Liquidacion_Si': self.IPC_Liquidacion_Si,
          'Segunda_Liquidacion_Si': self.Segunda_Liquidacion_Si,
          'periodo_desde': transformar_fecha(self.periodo_desde),
          'periodo_hasta': transformar_fecha(self.periodo_hasta),
          'fecha_de_cierre_de_liquidacion': transformar_fecha(self.fecha_de_cierre_de_liquidacion),
          'Acordada_fecha_de_cierre_de_liquidacion': datos['Acordada_fecha_de_cierre_de_liquidacion'],
          'UMA_fecha_de_cierre_de_liquidacion': formatear_dinero(datos['UMA_fecha_de_cierre_de_liquidacion']),
          'porcentajesFCL': datos['porcentajesFCL'],
          'cantidadFCL': datos['cantidadFCL'],
          'minimoFCL': datos['minimoFCL'],
          'apoderadoFCL': datos['apoderadoFCL'],
          'reduccionFCL': datos['reduccionFCL'],
          'ejecucionFCL': datos['ejecucionFCL'],
          'incidenciaFCL': datos['incidenciaFCL'],
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

      if self.IPC_Liquidacion_Si:
          context.update({
              'fecha_de_regulacion': transformar_fecha(self.fecha_de_regulacion),
              'Acordada_fecha_de_regulacion': datos['Acordada_fecha_de_regulacion'],
              'UMA_fecha_de_regulacion': formatear_dinero(datos['UMA_fecha_de_regulacion']),
              'porcentajesR': datos['porcentajesR'],
              'cantidadR': datos['cantidadR'],
              'minimoR': datos['minimoR'],
              'apoderadoR': datos['apoderadoR'],
              'reduccionR': datos['reduccionR'],
              'ejecucionR': datos['ejecucionR'],
              'incidenciaR': datos['incidenciaR'],
          })

      if self.Segunda_Liquidacion_Si:
          context.update({
              'fecha_aprobacion_sentencia': transformar_fecha(self.fecha_aprobacion_sentencia),
              'Acordada_fecha_aprobacion_sentencia': datos['Acordada_fecha_aprobacion_sentencia'],
              'UMA_fecha_aprobacion_sentencia': formatear_dinero(datos['UMA_fecha_aprobacion_sentencia']),
              'porcentajesAS': datos['porcentajesAS'],
              'cantidadAS': datos['cantidadAS'],
              'minimoAS': datos['minimoAS'],
              'apoderadoAS': datos['apoderadoAS'],
              'reduccionAS': datos['reduccionAS'],
              'ejecucionAS': datos['ejecucionAS'],
              'incidenciaAS': datos['incidenciaAS'],
          })

      if self.Segunda_Liquidacion_Si and self.IPC_Liquidacion_Si:
          context.update({
              'porcentajesTP': datos['porcentajesTP'],
              'cantidadTP': datos['cantidadTP'],
              'minimoTP': datos['minimoTP'],
              'apoderadoTP': datos['apoderadoTP'],
              'reduccionTP': datos['reduccionTP'],
              'ejecucionTP': datos['ejecucionTP'],
              'incidenciaTP': datos['incidenciaTP'],
          })

      rendered = render_template('calculadora_uma/resultado_calculadora_uma.html', **context)

      pdf_buffer = BytesIO()
      pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
      pdf_buffer.seek(0)
      return pdf_buffer.getvalue()
