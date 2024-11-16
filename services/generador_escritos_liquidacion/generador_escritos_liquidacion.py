from flask import send_file
from docxtpl import DocxTemplate
from services.calculadora_uma.generador_pdf import obtener_acordada, obtener_valor_uma
from services.calculos import formatear_dinero
import re

def calcular_diferencia_y_porcentaje(monto, monto_ipc):
  # Calcular la diferencia
  diferencia = monto_ipc - monto

  # Calcular el porcentaje de la diferencia con respecto a monto_ipc
  if monto_ipc != 0:  # Para evitar división por cero
      porcentaje = round((diferencia / monto_ipc) * 100, 2)
  else:
      porcentaje = 0  # Si monto_ipc es cero, el porcentaje es 0

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
    texto_con_simbolo = re.sub(r'(\d+\.\d{3},\d{2})', r'$\1', texto_sin_pesos)

    return texto_con_simbolo

def transformar_a_float(monto_str):
    # Reemplazar los separadores de miles (.) y convertir la coma (,) a un punto (.)
    monto_str = monto_str.replace('.', '').replace(',', '.')
    return float(monto_str)


class Escrito_liquidacion:
  def __init__(self, datos):
      self.datos = datos

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

      self.datos['Haber_de_Alta'] = transformar_a_float(self.datos['Haber_de_Alta'])
      self.datos['Haber_de_Alta_Segunda_Liquidacion'] = transformar_a_float(self.datos['Haber_de_Alta_Segunda_Liquidacion'])
      self.datos['Haber_de_Alta_Primera_Liquidacion_IPC'] = transformar_a_float(self.datos['Haber_de_Alta_Primera_Liquidacion_IPC'])
      self.datos['Haber_de_Alta_Segunda_Liquidacion_IPC'] = transformar_a_float(self.datos['Haber_de_Alta_Segunda_Liquidacion_IPC'])

      self.datos['Diferencias'], self.datos['Porcentaje']= calcular_diferencia_y_porcentaje(self.datos['Haber_de_Alta'],self.datos['Haber_de_Alta_Primera_Liquidacion_IPC'])
      self.datos['Diferencias_2'], self.datos['Porcentaje_2'] = calcular_diferencia_y_porcentaje(self.datos['Haber_de_Alta_Segunda_Liquidacion'],self.datos['Haber_de_Alta_Segunda_Liquidacion_IPC'])

  def crear_documento(self):
        plantilla_path = "datos/regulacion/plantilla_regulacion.docx"
        output_path = "datos/regulacion/regulacion_final.docx"
        doc = DocxTemplate(plantilla_path)

        # Renderizar el documento con los datos
        doc.render(self.datos)

      # Guardar el documento renderizado
        doc.save(output_path)

      # Enviar el archivo para su descarga
        return send_file(output_path, as_attachment=True)

      