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
from decimal import Decimal

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

    # Agregar línea roja horizontal al nivel del valor de "Anses"
    fig.add_shape(
        type='line',
        x0=-0.5,  # Extiende la línea desde antes de la primera barra
        x1=len(etiquetas) - 0.5,  # Hasta después de la última barra
        y0=valores[0],  # Altura del valor de "Anses"
        y1=valores[0],
        line=dict(color='red', width=3, dash='dash')
    )

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

def crear_grafico_tope_haber_maximo_2(datos, nombre_grafico):
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

    # Agregar línea roja horizontal al nivel del valor de "Anses"
    fig.add_shape(
        type='line',
        x0=-0.5,  # Extiende la línea desde antes de la primera barra
        x1=len(etiquetas) - 0.5,  # Hasta después de la última barra
        y0=valores[6],  # Altura del valor de "Anses"
        y1=valores[6],
        line=dict(color='red', width=3, dash='dash')
    )

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
  def __init__(self, autos, expediente, periodo_hasta, haber_reclamado):
      self.autos = autos
      self.expediente = expediente
      self.periodo_hasta = periodo_hasta
      self.haber_reclamado = haber_reclamado

  def obtener_datos(self):

      caliva_ext_27551_2, anses_2, badaro_2, badaro_cm_2, ocheintados_rem_max_2, rem_max_2,rem_max_imponible_cm_extendido_27551_2 = obtener_monto(self.periodo_hasta)
      
      datos = {}
      
      datos['autos'] = self.autos
      datos['expediente'] = self.expediente
      datos['periodo_hasta'] = self.periodo_hasta
      datos['haber_reclamado'] = self.haber_reclamado

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

      datos['dif_haber_reclamado_anses'] = formatear_dinero(Decimal(self.haber_reclamado) - anses_2)
      datos['dif_haber_reclamado_anses_graf'] = (Decimal(self.haber_reclamado) - anses_2)
      datos['porc_haber_reclamado_anses'] = str(round((Decimal(self.haber_reclamado) / anses_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_Caliva'] = formatear_dinero(Decimal(self.haber_reclamado) - caliva_ext_27551_2)
      datos['dif_haber_reclamado_Caliva_graf'] = (Decimal(self.haber_reclamado) - caliva_ext_27551_2)
      datos['porc_haber_reclamado_Caliva'] = str(round((Decimal(self.haber_reclamado) / caliva_ext_27551_2 - 1) * 100, 2)) + "%"
      datos['dif_haber_reclamado_Badaro'] = formatear_dinero(Decimal(self.haber_reclamado) - badaro_2)
      datos['dif_haber_reclamado_Badaro_graf'] = (Decimal(self.haber_reclamado) - badaro_2)
      datos['porc_haber_reclamado_Badaro'] = str(round((Decimal(self.haber_reclamado) / badaro_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_Badaro_CM'] = formatear_dinero(Decimal(self.haber_reclamado) - badaro_cm_2)
      datos['dif_haber_reclamado_Badaro_CM_graf'] = (Decimal(self.haber_reclamado) - badaro_cm_2)
      datos['porc_haber_reclamado_Badaro_CM'] = str(round((Decimal(self.haber_reclamado) / badaro_cm_2 - 1) * 100, 2)) + "%"
      datos['dif_haber_reclamado_ocheintados_rem_max_2'] = formatear_dinero(Decimal(self.haber_reclamado) - ocheintados_rem_max_2)
      datos['dif_haber_reclamado_ocheintados_rem_max_2_graf'] = (Decimal(self.haber_reclamado) - ocheintados_rem_max_2)
      datos['porc_haber_reclamado_ocheintados_rem_max_2'] = str(round((Decimal(self.haber_reclamado) / ocheintados_rem_max_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_rem_max_2'] = formatear_dinero(Decimal(self.haber_reclamado) - rem_max_2)
      datos['dif_haber_reclamado_rem_max_2_graf'] = (Decimal(self.haber_reclamado) - rem_max_2)
      datos['porc_haber_reclamado_rem_max_2'] = str(round((Decimal(self.haber_reclamado) / rem_max_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2'] = formatear_dinero(Decimal(self.haber_reclamado) - rem_max_imponible_cm_extendido_27551_2)
      datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2_graf'] = (Decimal(self.haber_reclamado) - rem_max_imponible_cm_extendido_27551_2)
      datos['porc_haber_reclamado_rem_max_imponible_cm_extendido_27551_2'] = str(round((Decimal(self.haber_reclamado) / rem_max_imponible_cm_extendido_27551_2 - 1) * 100, 2)) + "%"


      return datos

  def generar_pdf(self):
      datos = self.obtener_datos()
      datos_grafico = [datos['anses_2'],datos['caliva_ext_27551_2'],datos['badaro_2'],datos['badaro_cm_2'],datos['ocheintados_rem_max_2'], datos['rem_max_2'],datos['rem_max_imponible_cm_extendido_27551_2'] ]
      datos_grafico_2 = [datos['dif_haber_reclamado_anses_graf'],datos['dif_haber_reclamado_Caliva_graf'],datos['dif_haber_reclamado_Badaro_graf'],datos['dif_haber_reclamado_Badaro_CM_graf'],datos['dif_haber_reclamado_ocheintados_rem_max_2_graf'], datos['dif_haber_reclamado_rem_max_2_graf'],datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2_graf'] ]
      grafico = crear_grafico_tope_haber_maximo(datos_grafico, "")
      grafico_2 = crear_grafico_tope_haber_maximo_2(datos_grafico_2, "")

      rendered = render_template(
          'calculadora_tope_maximo/resultado.html',
          autos=self.autos,
          expediente=self.expediente,
          periodo_hasta=transformar_fecha(self.periodo_hasta),
          haber_reclamado = formatear_dinero(self.haber_reclamado),

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
          dif_haber_reclamado_anses = datos['dif_haber_reclamado_anses'],
          porc_haber_reclamado_anses = datos['porc_haber_reclamado_anses'],
          
          dif_haber_reclamado_Caliva = datos['dif_haber_reclamado_Caliva'],
          porc_haber_reclamado_Caliva = datos['porc_haber_reclamado_Caliva'],

          dif_haber_reclamado_Badaro = datos['dif_haber_reclamado_Badaro'],
          porc_haber_reclamado_Badaro = datos['porc_haber_reclamado_Badaro'],

          dif_haber_reclamado_Badaro_CM = datos['dif_haber_reclamado_Badaro_CM'],
          porc_haber_reclamado_Badaro_CM = datos['porc_haber_reclamado_Badaro_CM'],

          dif_haber_reclamado_ocheintados_rem_max_2= datos['dif_haber_reclamado_ocheintados_rem_max_2'],
          porc_haber_reclamado_ocheintados_rem_max_2 = datos['porc_haber_reclamado_ocheintados_rem_max_2'],

          dif_haber_reclamado_rem_max_2= datos['dif_haber_reclamado_rem_max_2'],
          porc_haber_reclamado_rem_max_2 = datos['porc_haber_reclamado_rem_max_2'],

          dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2 = datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2'],
          porc_haber_reclamado_rem_max_imponible_cm_extendido_27551_2= datos['porc_haber_reclamado_rem_max_imponible_cm_extendido_27551_2'],
          grafico = grafico,
          grafico_2 = grafico_2
         
      )

      pdf_buffer = BytesIO()
      pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
      pdf_buffer.seek(0)
      return pdf_buffer.getvalue()
