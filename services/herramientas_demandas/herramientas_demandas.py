import plotly.graph_objects as go
import io
import base64
from services.calculos import formatear_dinero, transformar_fecha
from flask import render_template, send_file
from werkzeug.wrappers import response
from config import config
from xhtml2pdf import pisa
from io import BytesIO
from datetime import datetime

def crear_graficos(datos, etiquetas, titulo):
  etiquetas = etiquetas
  valores = datos
  titulo = titulo
  resultados = list(map(formatear_dinero, valores))

  # Crear el gráfico de barras
  fig = go.Figure(data=go.Bar(
      x=etiquetas, 
      y=valores, 
      marker_color=['#7671FA','#00c4ff', '#E5EAF3', '#07244C', '#178DAD', '#7E7F9C', '#9e73a3', '#3cd7c4', '#83007f','#bb73b3'],
      text=resultados, textposition='auto',
      textfont=dict(size=14)
  ))

  # Agregar la línea horizontal en el nivel de la primera columna
  valor_primera_columna = valores[0]
  fig.add_shape(
      type="line",
      x0=-0.5,  # Colocar la línea al inicio del gráfico
      x1=len(etiquetas) - 0.5,  # Colocar la línea hasta el final del gráfico
      y0=valor_primera_columna,
      y1=valor_primera_columna,
      line=dict(color="red", width=3, dash="solid")
  )

  # Actualizar el diseño del gráfico con título
  fig.update_layout(
      title=dict(
          text=titulo,  # Título del gráfico
          font=dict(size=20),  # Tamaño del título
          x=0,  # Alinea el título a la izquierda
          xanchor='left'  # Ancla el título a la izquierda
      ),
      xaxis_title='Categorías',  # Título del eje X
      yaxis_title='Monto ($)',  # Título del eje Y
      plot_bgcolor='rgba(0, 0, 0, 0)',
      paper_bgcolor='rgba(0, 0, 0, 0)',
      margin=dict(l=40, r=40, t=60, b=40),
      width=800, height=600,
      xaxis=dict(title_font=dict(size=14), tickfont=dict(size=10)),
      yaxis=dict(title_font=dict(size=14), tickfont=dict(size=12))
  )

  # Guardar el gráfico como imagen en un buffer
  img_bytes = fig.to_image(format="png")  # Usar Kaleido para generar la imagen

  # Codificar la imagen en base64
  grafico_base64 = base64.b64encode(img_bytes).decode('utf-8')

  return grafico_base64

class HerramientasDemanda:
  def __init__(self, 
               datos_del_actor, expediente, cuil_expediente, beneficio, 
               num_beneficio,comparacion_reparacion_historica, fecha_comparacion_repa, PBU_repa, PC_repa, 
               PAP_repa, REPA_repa, OTROS_repa, 
               PBU_reclamado, PC_reclamado, PAP_reclamado, 
               REPA_reclamado, OTROS_reclamado,
               comparacion_repa_movilizado, comparacion_repa_movilizado_No,
               PBU_repa_movilizado, PC_repa_movilizado, 
               PAP_repa_movilizado, REPA_repa_movilizado, 
               OTROS_repa_movilizado, diccionario_sumas):
    
      self.datos_del_actor = datos_del_actor
      self.expediente = expediente
      self.cuil_expediente = cuil_expediente
      self.beneficio = beneficio
      self.num_beneficio = num_beneficio

      self.comparacion_reparacion_historica = comparacion_reparacion_historica
      self.fecha_comparacion_repa = fecha_comparacion_repa
    
      self.PBU_repa = PBU_repa
      self.PC_repa = PC_repa
      self.PAP_repa = PAP_repa
      self.REPA_repa = REPA_repa
      self.OTROS_repa = OTROS_repa

      self.PBU_reclamado = PBU_reclamado
      self.PC_reclamado = PC_reclamado
      self.PAP_reclamado = PAP_reclamado
      self.REPA_reclamado = REPA_reclamado
      self.OTROS_reclamado = OTROS_reclamado

      self.comparacion_repa_movilizado = comparacion_repa_movilizado
      self.comparacion_repa_movilizado_No = comparacion_repa_movilizado_No

      self.PBU_repa_movilizado = PBU_repa_movilizado
      self.PC_repa_movilizado = PC_repa_movilizado
      self.PAP_repa_movilizado = PAP_repa_movilizado
      self.REPA_repa_movilizado = REPA_repa_movilizado
      self.OTROS_repa_movilizado = OTROS_repa_movilizado

      self.diccionario_sumas = diccionario_sumas

  def obtener_datos_repa(self):
    diccionario = {
      'total_haber_con_repa': (self.PBU_repa + self.PC_repa + self.PAP_repa + self.REPA_repa + self.OTROS_repa),
      'total_haber_reclamado': (self.PBU_reclamado + self.PC_reclamado + self.PAP_reclamado+ self.REPA_reclamado + self.OTROS_reclamado),
      'total_haber_con_repa_movilizado': (self.PBU_repa_movilizado + self.PC_repa_movilizado + self.PAP_repa_movilizado + self.REPA_repa_movilizado + self.OTROS_repa_movilizado),
    }

    # Agregar diferencias al diccionario después de calcular los totales
    diccionario['dif_reclamado_repa'] = (diccionario['total_haber_reclamado'] - diccionario['total_haber_con_repa'])
    diccionario['incidencia_reclamado_repa'] = str(round(diccionario['dif_reclamado_repa'] / diccionario['total_haber_con_repa'] * 100,2)) + "%"
    diccionario['quita_confis_reclamado_repa'] = str(round(diccionario['dif_reclamado_repa'] / diccionario['total_haber_reclamado'] * 100,2)) + "%"

    
    diccionario['dif_repa_movilizado_repa'] = (diccionario['total_haber_con_repa_movilizado'] - diccionario['total_haber_con_repa'])
    if diccionario['total_haber_con_repa_movilizado'] != 0:
      diccionario['incidencia_repa_movilizado_repa'] = str(round(diccionario['dif_repa_movilizado_repa'] / diccionario['total_haber_con_repa'] * 100,2)) + "%"
      diccionario['quita_confis_repa_movilizado_repa'] = str(round(diccionario['dif_repa_movilizado_repa'] / diccionario['total_haber_con_repa_movilizado'] * 100,2)) + "%"

    datos = [diccionario['total_haber_con_repa'], diccionario['total_haber_reclamado']]
    etiquetas = ['Haber Percibido con Reparacion Historica', 'Haber Reclamado']
    if self.comparacion_repa_movilizado:
      datos.append(diccionario['total_haber_con_repa_movilizado'])
      etiquetas.append('Haber con Reparacion Historica Movilizada')

    grafico_repa = crear_graficos(datos,etiquetas, "Diferencia de Haber con Reparacion Historica")

    diccionario['total_haber_con_repa'] = formatear_dinero(diccionario['total_haber_con_repa'])
    diccionario['total_haber_reclamado'] = formatear_dinero(diccionario['total_haber_reclamado'])
    diccionario['total_haber_con_repa_movilizado'] = formatear_dinero(diccionario['total_haber_con_repa_movilizado'])

    diccionario['dif_reclamado_repa'] = formatear_dinero(diccionario['dif_reclamado_repa'])
    diccionario['dif_repa_movilizado_repa'] = formatear_dinero(diccionario['dif_repa_movilizado_repa'])
    

    
    return diccionario, grafico_repa

  def generar_pdf(self):
    diccionario_repa, grafico_repa = self.obtener_datos_repa()

    rendered = render_template(
      'herramientas_demanda/resultado_herramientas_demanda.html',
      datos_del_actor = self.datos_del_actor,
      expediente = self.expediente,
      cuil_expediente = self.cuil_expediente,
      beneficio = self.beneficio,
      num_beneficio = self.num_beneficio,
      comparacion_reparacion_historica = self.comparacion_reparacion_historica,
      fecha_comparacion_repa = self.fecha_comparacion_repa,
      PBU_repa = formatear_dinero(self.PBU_repa),
      PC_repa = formatear_dinero(self.PC_repa),
      PAP_repa = formatear_dinero(self.PAP_repa),
      REPA_repa = formatear_dinero(self.REPA_repa),
      OTROS_repa = formatear_dinero(self.OTROS_repa),
      PBU_reclamado = formatear_dinero(self.PBU_reclamado),
      PC_reclamado = formatear_dinero(self.PC_reclamado),
      PAP_reclamado = formatear_dinero(self.PAP_reclamado),
      REPA_reclamado = formatear_dinero(self.REPA_reclamado),
      OTROS_reclamado = formatear_dinero(self.OTROS_reclamado),
      comparacion_repa_movilizado = self.comparacion_repa_movilizado,
      PBU_repa_movilizado = formatear_dinero(self.PBU_repa_movilizado),
      PC_repa_movilizado = formatear_dinero(self.PC_repa_movilizado),
      PAP_repa_movilizado = formatear_dinero(self.PAP_repa_movilizado),
      REPA_repa_movilizado = formatear_dinero(self.REPA_repa_movilizado),
      OTROS_repa_movilizado = formatear_dinero(self.OTROS_repa_movilizado),
      diccionario_repa = diccionario_repa,
      grafico_repa = grafico_repa,
      diccionario_sumas = self.diccionario_sumas,
    )

    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)

    if pisa_status.err:
        # Manejar el error en caso de que la creación del PDF falle
        return "Error al crear el PDF", 500

    pdf_buffer.seek(0)

    # Enviar el PDF como respuesta
    return send_file(pdf_buffer, as_attachment=True, download_name='resultado.pdf', mimetype='application/pdf')

