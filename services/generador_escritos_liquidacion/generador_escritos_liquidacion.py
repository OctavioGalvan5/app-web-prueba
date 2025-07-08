from flask import send_file
from docxtpl import DocxTemplate
from datetime import datetime
from services.calculadora_uma.generador_pdf import obtener_acordada, obtener_valor_uma
from services.calculadora_tope_maximo.generador_pdf import obtener_monto
from services.generador_escritos_liquidacion.honorarios import PDFGenerator
from services.calculos import formatear_dinero
import re
import plotly.graph_objects as go
import base64
from docx.shared import Inches
import tempfile
from babel.numbers import format_currency
from decimal import Decimal

import fitz  # PyMuPDF
from PIL import Image

def cortar_dos_tercios_superiores(pdf_bytes, output_image_path):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)  # Primera página

    rect = page.rect
    tres_cuartos_alto = rect.height * (3 / 4)

    # Definimos el rectángulo desde el tope hasta los 3/4 de altura
    clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + tres_cuartos_alto)

    # Renderizar solo esa parte
    pix = page.get_pixmap(clip=clip, dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img.save(output_image_path)
    doc.close()
    return output_image_path

def replace_pic(doc, marker, img_path):
    """Reemplaza un marcador en un documento Word por una imagen."""
    for paragraph in doc.paragraphs:
        if marker in paragraph.text:
            run = paragraph.runs[0]
            run.clear()
            run.add_picture(img_path, width=Inches(5))  # Ajusta el tamaño
            break
            
def crear_graficos(datos, etiquetas):
    """Crea un gráfico de barras y lo guarda como imagen temporal."""
    valores = datos
    resultados = list(map(formatear_dinero, valores))

    # Crear el gráfico de barras
    fig = go.Figure(data=go.Bar(
        x=etiquetas, 
        y=valores, 
        marker_color=['#6BAED6', '#74C476'],  # Colores personalizados
        text=resultados, textposition='auto',
        textfont=dict(size=14, color='black', family='Verdana')
    ))

    # Agregar la línea horizontal en el nivel de la primera columna
    valor_primera_columna = valores[0]
    fig.add_shape(
        type="line",
        x0=-0.5, 
        x1=len(etiquetas) - 0.5, 
        y0=valor_primera_columna,
        y1=valor_primera_columna,
        line=dict(color="red", width=3, dash="solid")
    )

    # Configurar diseño
    fig.update_layout(
        title=dict(text="Comparacion de Haberes", font=dict(size=24, color="#333")),
        xaxis_title="Movilidad",
        yaxis_title="Monto",
        plot_bgcolor='whitesmoke',
        paper_bgcolor='#f8f8f8',
        margin=dict(l=40, r=40, t=60, b=40),
        font=dict(family="Arial", size=16, color="#333"),
        width=800, height=600
    )

    # Líneas de cuadrícula suaves
    fig.update_xaxes(showgrid=True, gridcolor='lightgrey', gridwidth=0.5)
    fig.update_yaxes(showgrid=True, gridcolor='lightgrey', gridwidth=0.5)

    # Guardar el gráfico como archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.write_image(temp_file.name)  # Usar Kaleido para guardar la imagen

    return temp_file.name

def calcular_diferencia_y_porcentaje(monto, monto_ipc):
  # Calcular la diferencia
  diferencia = round(monto_ipc - monto, 2)
  # Calcular el porcentaje de la diferencia con respecto a monto_ipc
  if monto_ipc != 0:  # Para evitar división por cero
      porcentaje = round((diferencia / monto_ipc) * 100, 2)
  else:
      porcentaje = 0  # Si monto_ipc es cero, el porcentaje es 0
  diferencia = str(diferencia)
  diferencia = formatear_dinero(diferencia)
  return diferencia, porcentaje

def transformar_fecha(fecha_iso):
  """
  Transforma una fecha en formato YYYY-MM-DD a DD/MM/YYYY.

  :param fecha_iso: Cadena con la fecha en formato YYYY-MM-DD
  :return: Cadena con la fecha en formato DD/MM/YYYY
  """
  try:
      partes = fecha_iso.split("-")  # Dividir la fecha en partes
      return f"{partes[2]}/{partes[1]}/{partes[0]}"  # Reorganizar al formato DD/MM/YYYY
  except IndexError:
      raise ValueError("El formato de la fecha no es válido. Se espera YYYY-MM-DD.")
    
def modificar_montos(texto):
    # Eliminar la palabra "Pesos"
    texto_sin_pesos = texto.replace(" Pesos", "")

    # Reemplazar los montos por el formato con "$"
    texto_con_simbolo = re.sub(r'(\d{1,3}(?:\.\d{3})?,\d{2})', r'$\1', texto_sin_pesos)

    return texto_con_simbolo

def transformar_a_float(monto_str):
    # Reemplazar los separadores de miles (.) y convertir la coma (,) a un punto (.)
    monto_str = monto_str.replace('.', '').replace(',', '.')
    return float(monto_str)

def procesar_tuplas(tuplas):
    if tuplas[1][0] is not "":
        resultado = "Se descontaron pagos de "
        bandera = 1
    else:
        resultado = "Se desconto pago de "
        bandera = 0
    for elemento in tuplas:
        # Verifica si el primer elemento no es nulo
        if elemento[0] is not "":
            fecha = datetime.strptime(elemento[1], '%Y-%m-%d')
            if bandera == 1:
                resultado += "$" + elemento[0] + " en el periodo " + fecha.strftime('%d/%m/%Y') + " ,"
            else:
                resultado += "$" + elemento[0] + " en el periodo " + fecha.strftime('%d/%m/%Y') + "."


    return resultado.strip()  # Elimina espacios al final
class Escrito_liquidacion:
  def __init__(self, datos):
      self.datos = datos
      # UMA
      liquidaciones = [
        ]
      self.Fecha_de_cierre_de_intereses = self.datos['Fecha_de_cierre_de_intereses']
      self.datos['Valor_UMA'] = obtener_valor_uma(self.datos['Fecha_de_cierre_de_intereses'])
      self.datos['total_liquidacion'] = transformar_a_float(self.datos['total_liquidacion'])
      self.total_liquidacion = self.datos['total_liquidacion']
      self.datos['total_liquidacion_en_UMA'] = round(float(self.datos['total_liquidacion']) / float(self.datos['Valor_UMA']),2)
      self.datos['total_liquidacion'] = formatear_dinero(self.datos['total_liquidacion'])
      liquidaciones.append({"monto": self.datos['total_liquidacion'], "monto_en_uma": self.datos['total_liquidacion_en_UMA'], "numero_liquidacion":"1ra"})

      
      if self.datos['Total_Segunda_Liquidacion'] != "0":
          self.datos['Total_Segunda_Liquidacion'] = transformar_a_float(self.datos['Total_Segunda_Liquidacion'])
      self.Total_Segunda_Liquidacion = self.datos['Total_Segunda_Liquidacion']
      if self.datos['Total_Segunda_Liquidacion'] != "0":
          self.datos['Total_Segunda_Liquidacion_en_UMA'] = round(float(self.datos['Total_Segunda_Liquidacion']) / float(self.datos['Valor_UMA']),2)
          self.datos['Total_Segunda_Liquidacion'] = formatear_dinero(self.datos['Total_Segunda_Liquidacion'])
          liquidaciones.append({"monto": self.datos['Total_Segunda_Liquidacion'], "monto_en_uma": self.datos['Total_Segunda_Liquidacion_en_UMA'], "numero_liquidacion":"2da"})

      

      if self.datos['Total_Primera_Liquidacion_IPC'] != "0":
          self.datos['Total_Primera_Liquidacion_IPC'] = transformar_a_float(self.datos['Total_Primera_Liquidacion_IPC'])
      self.Total_Primera_Liquidacion_IPC = self.datos['Total_Primera_Liquidacion_IPC']
      if self.datos['Total_Primera_Liquidacion_IPC'] != "0":
          self.datos['Total_Primera_Liquidacion_IPC_en_UMA'] = round(float(self.datos['Total_Primera_Liquidacion_IPC']) / float(self.datos['Valor_UMA']),2)
          self.datos['Total_Primera_Liquidacion_IPC'] = formatear_dinero(self.datos['Total_Primera_Liquidacion_IPC'])
          liquidaciones.append({"monto": self.datos['Total_Primera_Liquidacion_IPC'], "monto_en_uma": self.datos['Total_Primera_Liquidacion_IPC_en_UMA'], "numero_liquidacion":"3ra"})

      

      if self.datos['Total_Segunda_Liquidacion_IPC'] != "0":
          self.datos['Total_Segunda_Liquidacion_IPC'] = transformar_a_float(self.datos['Total_Segunda_Liquidacion_IPC'])
      self.Total_Segunda_Liquidacion_IPC = self.datos['Total_Segunda_Liquidacion_IPC']
      if self.datos['Total_Segunda_Liquidacion_IPC'] != "0":
          self.datos['Total_Segunda_Liquidacion_IPC_en_UMA'] = round(float(self.datos['Total_Segunda_Liquidacion_IPC']) / float(self.datos['Valor_UMA']),2)
          self.datos['Total_Segunda_Liquidacion_IPC'] = formatear_dinero(self.datos['Total_Segunda_Liquidacion_IPC'])
          liquidaciones.append({"monto": self.datos['Total_Segunda_Liquidacion_IPC'], "monto_en_uma": self.datos['Total_Segunda_Liquidacion_IPC_en_UMA'], "numero_liquidacion":"4ta"})

      
      self.datos['Valor_UMA'] = formatear_dinero(self.datos['Valor_UMA'])
      self.datos["liquidaciones"] = liquidaciones
      
      
      self.datos['Percibido'] = modificar_montos(self.datos['Percibido'])
      self.datos['Reclamado'] = modificar_montos(self.datos['Reclamado'])

      self.datos['Movilidad'] = modificar_montos(self.datos['Movilidad'])
      self.datos['Movilidad_Segunda_Liquidacion'] = modificar_montos(self.datos['Movilidad_Segunda_Liquidacion'])
      self.datos['Movilidad_Primera_Liquidacion_IPC'] = modificar_montos(self.datos['Movilidad_Primera_Liquidacion_IPC'])
      self.datos['Movilidad_Segunda_Liquidacion_IPC'] = modificar_montos(self.datos['Movilidad_Segunda_Liquidacion_IPC'])

      self.datos['Fecha_Sentencia_Primera'] = transformar_fecha(self.datos['Fecha_Sentencia_Primera'])
      self.datos['Sentencia_de_Segunda'] = transformar_fecha(self.datos['Sentencia_de_Segunda'])
      
      self.datos['Fecha_Inicial_de_Pago'] = transformar_fecha(self.datos['Fecha_Inicial_de_Pago'])
      self.datos['Fecha_de_cierre_de_liquidación'] = transformar_fecha(self.datos['Fecha_de_cierre_de_liquidación'])
      self.datos['fecha_aprobacion_planilla'] = transformar_fecha(self.datos['fecha_aprobacion_planilla'])
      
      self.datos['fecha_fallecimiento'] = transformar_fecha(self.datos['fecha_fallecimiento'])
      self.datos['Error_Material_primer_fecha'] = transformar_fecha(self.datos['Error_Material_primer_fecha'])
      self.datos['Error_Material_ultima_fecha'] = transformar_fecha(self.datos['Error_Material_ultima_fecha'])
      self.datos['primer_fecha_RH'] = transformar_fecha(self.datos['primer_fecha_RH'])
      self.datos['ultima_fecha_RH'] = transformar_fecha(self.datos['ultima_fecha_RH'])
      self.datos['primer_fecha_AC'] = transformar_fecha(self.datos['primer_fecha_AC'])
      self.datos['ultima_fecha_AC'] = transformar_fecha(self.datos['ultima_fecha_AC'])
      
      self.datos['fecha_descuento_1'] = transformar_fecha(self.datos['fecha_descuento_1'])
      self.datos['fecha_descuento_2'] = transformar_fecha(self.datos['fecha_descuento_2'])
      self.datos['fecha_descuento_3'] = transformar_fecha(self.datos['fecha_descuento_3'])
      self.datos['fecha_descuento_4'] = transformar_fecha(self.datos['fecha_descuento_4'])
      self. datos['parrafo_descuentos'] = procesar_tuplas(datos['tupla_descuentos'])

      

      self.datos['Haber_de_Alta'] = transformar_a_float(self.datos['Haber_de_Alta'])
      etiquetas = ['Haber con 27609', 'Haber con IPC']
      self.datos['Haber_de_Alta_Segunda_Liquidacion'] = transformar_a_float(self.datos['Haber_de_Alta_Segunda_Liquidacion'])
      self.datos['Haber_de_Alta_Primera_Liquidacion_IPC'] = transformar_a_float(self.datos['Haber_de_Alta_Primera_Liquidacion_IPC'])
      self.datos['Haber_de_Alta_Segunda_Liquidacion_IPC'] = transformar_a_float(self.datos['Haber_de_Alta_Segunda_Liquidacion_IPC'])
      datos_primer_grafico= [self.datos['Haber_de_Alta'], self.datos['Haber_de_Alta_Primera_Liquidacion_IPC']]
      datos_segundo_grafico= [self.datos['Haber_de_Alta_Segunda_Liquidacion'], self.datos['Haber_de_Alta_Segunda_Liquidacion_IPC']]

      self.datos['grafico_1'] = crear_graficos(datos_primer_grafico, etiquetas)
      self.datos['grafico_2'] = crear_graficos(datos_segundo_grafico, etiquetas)

      self.datos['Diferencias'], self.datos['Porcentaje']= calcular_diferencia_y_porcentaje(self.datos['Haber_de_Alta'],self.datos['Haber_de_Alta_Primera_Liquidacion_IPC'])
      self.datos['Diferencias_2'], self.datos['Porcentaje_2'] = calcular_diferencia_y_porcentaje(self.datos['Haber_de_Alta_Segunda_Liquidacion'],self.datos['Haber_de_Alta_Segunda_Liquidacion_IPC'])

      self.datos['Haber_de_Alta'] = formatear_dinero(str(self.datos['Haber_de_Alta']))
      self.datos['Haber_de_Alta_Segunda_Liquidacion'] = formatear_dinero(str(self.datos['Haber_de_Alta_Segunda_Liquidacion']))
      self.datos['Haber_de_Alta_Primera_Liquidacion_IPC'] = formatear_dinero(str(self.datos['Haber_de_Alta_Primera_Liquidacion_IPC']))
      self.datos['Haber_de_Alta_Segunda_Liquidacion_IPC'] = formatear_dinero(str(self.datos['Haber_de_Alta_Segunda_Liquidacion_IPC']))

      if self.datos['Tope_Si']:
          caliva_anses, anses, badaro, badaro_cm, ocheintados_rem_max, rem_max,rem_max_imponible_cm_extendido_27551, martinez, anses_palavecino, caliva_palavecino, badaro_cm_palavecino, RM_Badaro_FP_CM_P_Anses, Alanis_colina = obtener_monto(self.datos['Fecha_de_cierre_de_intereses'])
          self.datos['dif_haber_reclamado_anses'] = formatear_dinero(Decimal(self.datos['haber_tope_maximo']) - anses)
          self.datos['porc_haber_reclamado_anses'] = str(round((Decimal(self.datos['haber_tope_maximo']) / anses - 1) * 100, 2)) + "%"
          self.datos['dif_ocheintados_rem_max_anses']  = str(round((ocheintados_rem_max / anses - 1) * 100 , 2)) + "%"
          self.datos['tope_anses'] = formatear_dinero(anses_2)
          self.datos['tope_ocheintados_rem_max'] = formatear_dinero(ocheintados_rem_max)
      self.datos['Fecha_de_cierre_de_intereses'] = transformar_fecha(self.datos['Fecha_de_cierre_de_intereses'])


  def crear_documento(self):

        pdf_generator = PDFGenerator(
          "", "", "2020-01-01", "2020-01-01",
          self.Fecha_de_cierre_de_intereses, self.total_liquidacion, 
          self.Total_Segunda_Liquidacion, self.Total_Primera_Liquidacion_IPC, self.Total_Segunda_Liquidacion_IPC, self.datos["Segunda_Liquidacion_Si"], self.datos["IPC_Liquidacion_Si"]
        )
        pdf = pdf_generator.generar_pdf()

        imagen_path = cortar_dos_tercios_superiores(
            pdf, 'datos/escritos_liquidacion/temp_liquidacion.png'
        )

      
        plantilla_path = 'datos/escritos_liquidacion/plantilla_liquidacion_1ra_vez.docx'
        if self.datos['tipo_escrito'] == 'liquidacion_1ra_vez':
            plantilla_path = "datos/escritos_liquidacion/plantilla_liquidacion_1ra_vez.docx"
        if self.datos['tipo_escrito']=='liquidacion_1ra_vez_inconstitucionalidad':
            plantilla_path = "datos/escritos_liquidacion/plantilla_liquidacion_1ra_vez_inco.docx"
        if self.datos['tipo_escrito']=='descuento_pago':
            plantilla_path = "datos/escritos_liquidacion/plantilla_liquidacion_descuento.docx"
        if self.datos['tipo_escrito']=='descuento_pago_inconstitucionalidad':
            plantilla_path = "datos/escritos_liquidacion/plantilla_liquidacion_descuento_inco.docx"
        if self.datos['tipo_escrito']=='ampliacion':
            plantilla_path = "datos/escritos_liquidacion/plantilla_liquidacion_ampliacion.docx"
        output_path = "datos/escritos_liquidacion/liquidacion_final.docx"
        doc = DocxTemplate(plantilla_path)

        # Renderizar el documento con los datos
        doc.render(self.datos)
      # Reemplazar el marcador con la imagen del gráfico
        replace_pic(doc, 'Comparacion_1', self.datos['grafico_1'])
        replace_pic(doc, 'Comparacion_2', self.datos['grafico_2'])
        replace_pic(doc, 'Cuadro_Uma', imagen_path)


      # Guardar el documento renderizado
        doc.save(output_path)

      # Enviar el archivo para su descarga
        return send_file(output_path, as_attachment=True)

      