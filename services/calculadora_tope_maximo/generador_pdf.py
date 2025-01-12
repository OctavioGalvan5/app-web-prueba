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
            fila_dict = dict(zip(result.keys(), row))  # Convertir la fila en un diccionario
            fecha_fila = fila_dict['fecha']  # Asumiendo que la columna de la fecha se llama 'fecha'

            if fecha_fila <= fecha_ingresada_dt:
                # Comparar para encontrar la fecha más cercana
                if fecha_cercana is None or fecha_fila > fecha_cercana:
                    fecha_cercana = fecha_fila
                    fila_cercana = fila_dict

        if fila_cercana:
            # Extraer los valores usando los nombres de las columnas
            caliva_anses = fila_cercana['Caliva_Anses']
            anses = fila_cercana['anses']
            badaro = fila_cercana['badaro']
            badaro_cm = fila_cercana['badaro c+m']
            ocheintados_rem_max = fila_cercana['82% rem.max']
            rem_max = fila_cercana['remuneracion maxima']
            rem_max_imponible_cm_extendido_27551 = fila_cercana['rem max imponible c+m extendido 27551']
            martinez = fila_cercana['martinez']


            return caliva_anses, anses, badaro, badaro_cm, ocheintados_rem_max, rem_max, rem_max_imponible_cm_extendido_27551, martinez
        else:
            return None


def crear_grafico_tope_haber_maximo(datos, nombre_grafico, etiquetas):
    etiquetas = etiquetas
    valores = datos

    # Verificar si la lista de valores está vacía
    if not valores:
        return "No hay datos suficientes para generar el gráfico."

    resultados = list(map(formatear_dinero, valores))

    # Encontrar el valor menor de los valores
    valor_minimo = min(valores)

    # Crear el gráfico
    fig = go.Figure(data=go.Bar(
        x=etiquetas, 
        y=valores, 
        marker_color=['#38225b', '#18488a', '#006faf', '#0096c6', '#7E7F9C', '#00bccb', '#00e0c4'],
        text=resultados, textposition='auto',
        textfont=dict(size=14)
    ))

    # Agregar línea roja horizontal al nivel del valor mínimo
    fig.add_shape(
        type='line',
        x0=-0.5,  # Extiende la línea desde antes de la primera barra
        x1=len(etiquetas) - 0.5,  # Hasta después de la última barra
        y0=valor_minimo,  # Altura del valor mínimo
        y1=valor_minimo,
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
  def __init__(self, autos, expediente, periodo_hasta, haber_reclamado, caliva_mas_anses,badaro_mas_anses, badaro_mas_caliva, remuneracion_maxima, ochentaidos_remuneracion_maxima, rem_max_caliva_27551, martinez_mas_anses):
      self.autos = autos
      self.expediente = expediente
      self.periodo_hasta = periodo_hasta
      self.haber_reclamado = haber_reclamado
      self.caliva_mas_anses = caliva_mas_anses
      self.badaro_mas_anses = badaro_mas_anses
      self.badaro_mas_caliva = badaro_mas_caliva
      self.remuneracion_maxima = remuneracion_maxima
      self.ochenintados_remuneracion_maxima = ochentaidos_remuneracion_maxima
      self.rem_max_caliva_27551 = rem_max_caliva_27551
      self.martinez_mas_anses = martinez_mas_anses
      
  def obtener_datos(self):

      caliva_anses, anses_2, badaro_2, badaro_cm_2, ocheintados_rem_max_2, rem_max_2,rem_max_imponible_cm_extendido_27551_2, martinez_2 = obtener_monto(self.periodo_hasta)
      
      datos = {}
      
      datos['autos'] = self.autos
      datos['expediente'] = self.expediente
      datos['periodo_hasta'] = self.periodo_hasta
      datos['haber_reclamado'] = self.haber_reclamado

      datos['caliva_anses'] = caliva_anses
      datos['anses_2'] = anses_2
      datos['badaro_2'] = badaro_2
      datos['badaro_cm_2'] = badaro_cm_2
      datos['ocheintados_rem_max_2'] = ocheintados_rem_max_2
      datos['rem_max_2'] = rem_max_2
      datos['rem_max_imponible_cm_extendido_27551_2'] = rem_max_imponible_cm_extendido_27551_2
      datos['martinez_2'] = martinez_2


      datos['dif_caliva_anses']  = str(round((caliva_anses / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_caliva_anses']  = formatear_dinero(caliva_anses - anses_2)

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

      datos['dif_martinez_anses']  = str(round((martinez_2 / anses_2 - 1) * 100 , 2)) + "%"
      datos['dif_monto_martinez_anses']  = formatear_dinero(martinez_2 - anses_2)

      datos['dif_haber_reclamado_anses'] = formatear_dinero(Decimal(self.haber_reclamado) - anses_2)
      datos['dif_haber_reclamado_anses_graf'] = (Decimal(self.haber_reclamado) - anses_2)
      datos['porc_haber_reclamado_anses'] = str(round((Decimal(self.haber_reclamado) / anses_2 - 1) * 100, 2)) + "%"

      datos['dif_haber_reclamado_Caliva'] = formatear_dinero(Decimal(self.haber_reclamado) - caliva_anses)
      datos['dif_haber_reclamado_Caliva_graf'] = (Decimal(self.haber_reclamado) - caliva_anses)
      datos['porc_haber_reclamado_Caliva'] = str(round((Decimal(self.haber_reclamado) / caliva_anses - 1) * 100, 2)) + "%"
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

      datos['dif_haber_reclamado_martinez_2'] = formatear_dinero(Decimal(self.haber_reclamado) - martinez_2)
      datos['dif_haber_reclamado_martinez_2_graf'] = (Decimal(self.haber_reclamado) - martinez_2)
      datos['porc_haber_reclamado_martinez_2'] = str(round((Decimal(self.haber_reclamado) / martinez_2 - 1) * 100, 2)) + "%"



      return datos

  def generar_pdf(self):
      datos = self.obtener_datos()
      datos_grafico = []
      etiquetas = []
      datos_grafico.append(datos['anses_2'])
      etiquetas.append('Tope Anses')
      if self.caliva_mas_anses:
          datos_grafico.append(datos['caliva_anses'])
          etiquetas.append('Tope Caliva Marquez mas Anses')
      if self.badaro_mas_anses:
          datos_grafico.append(datos['badaro_2'])
          etiquetas.append('Tope Badaro mas Anses')
      if self.badaro_mas_caliva:
          datos_grafico.append(datos['badaro_cm_2'])
          etiquetas.append('Tope Badaro mas Caliva Marquez')
      if self.ochenintados_remuneracion_maxima:
          datos_grafico.append(datos['ocheintados_rem_max_2'])
          etiquetas.append('82% de la Rem Max')
      if self.remuneracion_maxima:
          datos_grafico.append(datos['rem_max_2'])
          etiquetas.append('Rem. Maxima')
      if self.rem_max_caliva_27551:
          datos_grafico.append(datos['rem_max_imponible_cm_extendido_27551_2'])
          etiquetas.append('Rem Max Imponible C+M extendido 27551')
      if self.martinez_mas_anses:
          datos_grafico.append(datos['martinez_2'])
          etiquetas.append('Martinez mas Anses')
      

      
      datos_grafico_2 = []
      etiquetas_2 = []
      datos_grafico_2.append(datos['dif_haber_reclamado_anses_graf'])
      etiquetas_2.append('Tope Anses')
      if self.caliva_mas_anses:
          datos_grafico_2.append(datos['dif_haber_reclamado_Caliva_graf'])
          etiquetas_2.append('Tope Caliva Marquez mas Anses')
      if self.badaro_mas_anses:
            datos_grafico_2.append(datos['dif_haber_reclamado_Badaro_graf'])
            etiquetas_2.append('Tope Badaro mas Anses')
      if self.badaro_mas_caliva:
             datos_grafico_2.append(datos['dif_haber_reclamado_Badaro_CM_graf'])
             etiquetas_2.append('Tope Badaro mas Caliva Marquez')
      if self.ochenintados_remuneracion_maxima:
            datos_grafico_2.append(datos['dif_haber_reclamado_ocheintados_rem_max_2_graf'])
            etiquetas_2.append('82% de la Rem Max')
      if self.remuneracion_maxima:
           datos_grafico_2.append(datos['dif_haber_reclamado_rem_max_2_graf'])
           etiquetas_2.append('Rem. Maxima')
      if self.rem_max_caliva_27551:
              datos_grafico_2.append(datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2_graf'])
              etiquetas_2.append('Rem Max Imponible C+M extendido 27551')
      if self.martinez_mas_anses:
            datos_grafico_2.append(datos['dif_haber_reclamado_martinez_2_graf'])
            etiquetas_2.append('Martinez mas Anses')

      
      grafico = crear_grafico_tope_haber_maximo(datos_grafico, "Diferencia en $ entre Topes", etiquetas)
      grafico_2 = crear_grafico_tope_haber_maximo(datos_grafico_2, "Diferencias en $ aplicando los Topes", etiquetas_2)

      rendered = render_template(
          'calculadora_tope_maximo/resultado.html',
          autos=self.autos,
          expediente=self.expediente,
          periodo_hasta=transformar_fecha(self.periodo_hasta),
          haber_reclamado = formatear_dinero(self.haber_reclamado),
          caliva_mas_anses = self.caliva_mas_anses,  
          badaro_mas_anses = self.badaro_mas_anses,  
          badaro_mas_caliva = self.badaro_mas_caliva,  
          remuneracion_maxima = self.remuneracion_maxima,  
          ochentaidos_remuneracion_maxima = self.ochenintados_remuneracion_maxima,  
          rem_max_caliva_27551 = self.rem_max_caliva_27551,  
          martinez_mas_anses = self.martinez_mas_anses,  
          
          caliva_anses=formatear_dinero(datos['caliva_anses']),
          anses_2=formatear_dinero(datos['anses_2']),
          badaro_2=formatear_dinero(datos['badaro_2']),
          badaro_cm_2=formatear_dinero(datos['badaro_cm_2']),
          ocheintados_rem_max_2=formatear_dinero(datos['ocheintados_rem_max_2']),
          rem_max_2=formatear_dinero(datos['rem_max_2']),
          rem_max_imponible_cm_extendido_27551_2=formatear_dinero(datos['rem_max_imponible_cm_extendido_27551_2']),
          martinez_2=formatear_dinero(datos['martinez_2']),


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

          dif_martinez_anses=datos['dif_martinez_anses'],
          dif_monto_martinez_anses=datos['dif_monto_martinez_anses'],
          
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

          dif_haber_reclamado_martinez_2= datos['dif_haber_reclamado_martinez_2'],
          porc_haber_reclamado_martinez_2 = datos['porc_haber_reclamado_martinez_2'],
          
          dif_haber_reclamado_anses_graf = datos['dif_haber_reclamado_anses_graf'],
          dif_haber_reclamado_Caliva_graf = datos['dif_haber_reclamado_Caliva_graf'],
          dif_haber_reclamado_Badaro_graf = datos['dif_haber_reclamado_Badaro_graf'],
          dif_haber_reclamado_Badaro_CM_graf = datos['dif_haber_reclamado_Badaro_CM_graf'],
          dif_haber_reclamado_ocheintados_rem_max_2_graf = datos['dif_haber_reclamado_ocheintados_rem_max_2_graf'],
          dif_haber_reclamado_rem_max_2_graf = datos['dif_haber_reclamado_rem_max_2_graf'],
          dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2_graf = datos['dif_haber_reclamado_rem_max_imponible_cm_extendido_27551_2_graf'],
          dif_haber_reclamado_martinez_2_graf = datos['dif_haber_reclamado_martinez_2_graf'],
          
          grafico = grafico,
          grafico_2 = grafico_2
         
      )

      pdf_buffer = BytesIO()
      pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)
      pdf_buffer.seek(0)
      return pdf_buffer.getvalue()
