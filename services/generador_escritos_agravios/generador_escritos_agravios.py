from flask import send_file
from docxtpl import DocxTemplate
from datetime import datetime
from services.calculadora_uma.generador_pdf import obtener_acordada, obtener_valor_uma
from services.calculadora_tope_maximo.generador_pdf import obtener_monto
from services.calculos import formatear_dinero
import re
import plotly.graph_objects as go
import base64
from docx.shared import Inches
import tempfile
from babel.numbers import format_currency
from decimal import Decimal


class Escrito_agravios:
  def __init__(self, datos):
      self.datos = datos


  def crear_documento_agravios(self):
        plantilla_path = 'datos/escritos_agravios/escritos_agravios.docx'
        output_path = "datos/escritos_agravios/escritos_agravios_final.docx"
        doc = DocxTemplate(plantilla_path)

        # Renderizar el documento con los datos
        doc.render(self.datos)


      # Guardar el documento renderizado
        doc.save(output_path)

      # Enviar el archivo para su descarga
        return send_file(output_path, as_attachment=True)
