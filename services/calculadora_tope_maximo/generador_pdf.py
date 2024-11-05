from xhtml2pdf import pisa
from io import BytesIO
from models.database import engine
from services.calculos import formatear_dinero, transformar_fecha
from flask import render_template
from datetime import datetime
from sqlalchemy import text
import plotly.graph_objects as go
import io
import base64

def obtener_monto(fecha_ingresada):
  # Convertir la fecha ingresada por el usuario a un objeto datetime.date
  fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%Y-%m-%d').date()

  with engine.connect() as conn:
      result = conn.execute(text("SELECT * FROM topes_maximo"))

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
          caliva_ext_27551 = fila_cercana[2]
          anses = fila_cercana[3]
          badaro = fila_cercana[4]
          badaro_cm = fila_cercana[5]
          ocheintados_rem_max = fila_cercana[6]
          rem_max = fila_cercana [7]
          rem_max_imponible_cm_extendido_27551 = fila_cercana[8]
          
          return caliva_ext_27551, anses, badaro, badaro_cm, ocheintados_rem_max, rem_max,rem_max_imponible_cm_extendido_27551
      else:
          return None
def crear_grafico_tope_haber_maximo(datos, nombre_grafico):
    etiquetas = ['Anses', 'Caliva Marquez', 'Badaro', 'Badaro C+M', '82% de la Rem Max', 'Rem Max', 'Rem Max Imponible C+M']
    valores = datos
    resultados = list(map(formatear_dinero, valores))
    # Crear el gráfico
    fig = go.Figure(data=go.Bar(
        x=etiquetas, 
        y=valores, 
         marker_color=['#38225b', '#18488a', '#006faf', '#0096c6', '#7E7F9C', '#00bccb', '#00e0c4'],
        text=resultados, textposition='auto',
        textfont=dict(size=14)

    ))

    # Actualizar el diseño del gráfico
    fig.update_layout(
        title=nombre_grafico, 
        xaxis_title='', 
        yaxis_title='',
        plot_bgcolor='rgba(0, 0, 0, 0)',  # Fondo del área de trazado transparente
        paper_bgcolor='rgba(0, 0, 0, 0)',  # Fondo del gráfico transparente
        margin=dict(l=40, r=40, t=40, b=40),
        width=800, height=400,
        xaxis=dict(title_font=dict(size=14), tickfont=dict(size=12)),
        yaxis=dict(title_font=dict(size=14), tickfont=dict(size=12))
    )

    # Guardar el gráfico como imagen en un buffer
    img_bytes = fig.to_image(format="png")  # Usar Kaleido para generar la imagen

    # Codificar la imagen en base64
    grafico_base64 = base64.b64encode(img_bytes).decode('utf-8')

    return grafico_base64
class Comparativa:
  def __init__(self, autos, expediente, periodo_desde, periodo_hasta):
      self.autos = autos
      self.expediente = expediente
      self.periodo_desde = periodo_desde
      self.periodo_hasta = periodo_hasta

  def obtener_datos(self):
      caliva_ext_27551_1, anses_1, badaro_1, badaro_cm_1, ocheintados_rem_max_1, rem_max_1,rem_max_imponible_cm_extendido_27551_1 = obtener_monto(self.periodo_desde)

      caliva_ext_27551_2, anses_2, badaro_2, badaro_cm_2, ocheintados_rem_max_2, rem_max_2,rem_max_imponible_cm_extendido_27551_2 = obtener_monto(self.periodo_hasta)
      
      datos = {}
      
      datos['autos'] = self.autos
      datos['expediente'] = self.expediente
      datos['periodo_desde'] = self.periodo_desde
      datos['periodo_hasta'] = self.periodo_hasta

      datos['caliva_ext_27551_1'] = caliva_ext_27551_1
      datos['anses_1'] = anses_1
      datos['badaro_1'] = badaro_1
      datos['badaro_cm_1'] = badaro_cm_1
      datos['ocheintados_rem_max_1'] = ocheintados_rem_max_1
      datos['rem_max_1'] = rem_max_1
      datos['rem_max_imponible_cm_extendido_27551_1'] = rem_max_imponible_cm_extendido_27551_1

      datos['caliva_ext_27551_2'] = caliva_ext_27551_2
      datos['anses_2'] = anses_2
      datos['badaro_2'] = badaro_2
      datos['badaro_cm_2'] = badaro_cm_2
      datos['ocheintados_rem_max_2'] = ocheintados_rem_max_2
      datos['rem_max_2'] = rem_max_2
      datos['rem_max_imponible_cm_extendido_27551_2'] = rem_max_imponible_cm_extendido_27551_2

      datos['dif_caliva_anses']  = str(round((caliva_ext_27551_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_caliva_anses']  = formatear_dinero(caliva_ext_27551_2 - anses_2)

      datos['dif_badaro_anses']  = str(round((badaro_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_badaro_anses']  = formatear_dinero(badaro_2 - anses_2)

      datos['dif_badaro_cm_anses']  = str(round((badaro_cm_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_badaro_cm_anses']  = formatear_dinero(badaro_cm_2 - anses_2)
      
      datos['dif_ocheintados_rem_max_anses']  = str(round((ocheintados_rem_max_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_ocheintados_rem_max_anses']  = formatear_dinero(ocheintados_rem_max_2 - anses_2)

      datos['dif_rem_max_anses']  = str(round((rem_max_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_rem_max_anses']  = formatear_dinero(rem_max_2 - anses_2)

      datos['dif_rem_max_imponible_cm_extendido_27551_anses']  = str(round((rem_max_imponible_cm_extendido_27551_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_rem_max_imponible_cm_extendido_27551_anses']  = formatear_dinero(rem_max_imponible_cm_extendido_27551_2 - anses_2)


      return datos

  def generar_pdf(self):
      datos = self.obtener_datos()
      datos_grafico = [datos['anses_2'],datos['caliva_ext_27551_2'],datos['badaro_2'],datos['badaro_cm_2'],datos['ocheintados_rem_max_2'], datos['rem_max_2'],datos['rem_max_imponible_cm_extendido_27551_2'] ]
      grafico = crear_grafico_tope_haber_maximo(datos_grafico, "")
      rendered = render_template(
          'calculadora_tope_maximo/resultado.html',
          autos=self.autos,
          expediente=self.expediente,
          periodo_desde=transformar_fecha(self.periodo_desde),
          periodo_hasta=transformar_fecha(self.periodo_hasta),
          
          caliva_ext_27551_1= formatear_dinero(datos['caliva_ext_27551_1']),
          anses_1=formatear_dinero(datos['anses_1']),
          badaro_1=formatear_dinero(datos['badaro_1']),
          badaro_cm_1=formatear_dinero(datos['badaro_cm_1']),
          ocheintados_rem_max_1=formatear_dinero(datos['ocheintados_rem_max_1']),
          rem_max_1=formatear_dinero(datos['rem_max_1']),
          rem_max_imponible_cm_extendido_27551_1=formatear_dinero(datos['rem_max_imponible_cm_extendido_27551_1']),

          calivas_ext_27551_2=formatear_dinero(datos['caliva_ext_27551_2']),
          anses_2=formatear_dinero(datos['anses_2']),
          badaro_2=formatear_dinero(datos['badaro_2']),
          badaro_cm_2=formatear_dinero(datos['badaro_cm_2']),
          ocheintados_rem_max_2=formatear_dinero(datos['ocheintados_rem_max_2']),
          rem_max_2=formatear_dinero(datos['rem_max_2']),
          rem_max_imponible_cm_extendido_27551_2=formatear_dinero(datos['rem_max_imponible_cm_extendido_27551_2']),

          dif_caliva_anses=datos['dif_caliva_anses'],
          dif_monto_caliva_anses=datos['dif_monto_caliva_anses'] ,
          
          dif_badaro_anses=datos['dif_badaro_anses'],
          dif_monto_badaro_anses=datos['dif_monto_badaro_anses'],
          
          dif_badaro_cm_anses=datos['dif_badaro_cm_anses'],
          dif_monto_badaro_cm_anses=datos['dif_monto_badaro_cm_anses'],
          
          dif_ocheintados_rem_max_anses=datos['dif_ocheintados_rem_max_anses'],
          dif_monto_ocheintados_rem_max_anses=datos['dif_monto_ocheintados_rem_max_anses'],
          
          dif_rem_max_anses=datos['dif_rem_max_anses'],
          dif_monto_rem_max_anses=datos['dif_monto_rem_max_anses'],
          
          dif_rem_max_imponible_cm_extendido_27551_anses= datos['dif_rem_max_imponible_cm_extendido_27551_anses'],
          dif_monto_rem_max_imponible_cm_extendido_27551_anses= datos['dif_monto_rem_max_imponible_cm_extendido_27551_anses'],
          grafico = grafico
         
      )

      pdf_buffer = BytesIO()
      pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
      pdf_buffer.seek(0)
      return pdf_buffer.getvalue()
