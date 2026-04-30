import pandas as pd
import openpyxl
from flask import render_template,send_file
import base64
from xhtml2pdf import pisa
from io import BytesIO
from services.calculos import formatear_dinero


def pesos(lista):
  for i in range(len(lista)):
      lista[i] = formatear_dinero(lista[i])
  return lista
    
class Planilla_Docente:
  def __init__(self,datos):
    self.datos = datos

  def extraer_montos(self,file):
    df = pd.read_excel(self.datos[file])

    # Determinar el número de columnas no vacías
    num_columns = df.shape[1]
    for col in range(1, num_columns):  # Ignorar la primera columna (índice 0)
        if df.iloc[:, col].isnull().all():  # Verificar si toda la columna está vacía
            num_columns = col
            break

    # Contar el número de filas no vacías en la primera columna
    num_rows = df.iloc[:, 0].notnull().sum()

    # Calcular los totales para cada fila desde la columna 1 hasta la última columna válida
    totals = []
    for i in range(num_rows):  # Iterar según el número de filas no vacías
        total = df.iloc[i, 1:num_columns].sum()  # Desde la columna 1 hasta `num_columns`
        totals.append((total))
    return totals

  def crear_documento(self, file):
    df = pd.read_excel(self.datos[file])
    fechas = pd.to_datetime(df.iloc[:, 0], errors='coerce')  # Convertir a datetime (maneja errores)
    fechas = fechas.dt.strftime('%d/%m/%Y').tolist()  # Formatear y convertir a lista
    Percibido = self.extraer_montos('planilla_percibidos')
    Cargo_1 = self.extraer_montos('planilla_Cargo_1')
    Total_Reclamado = self.extraer_montos('planilla_Cargo_1')
    tamaño = len(Total_Reclamado)
    if self.datos['Cargo_2_Si']:
      Cargo_2 = self.extraer_montos('planilla_Cargo_2')
      for i in range (tamaño):
        Total_Reclamado[i] = Total_Reclamado[i] + Cargo_2[i]
    else:
        Cargo_2 = Cargo_1.copy()
    if self.datos['Cargo_3_Si']:
      Cargo_3 = self.extraer_montos('planilla_Cargo_3')
      for i in range (tamaño):
        Total_Reclamado[i] = Total_Reclamado[i] + Cargo_3[i]
    else:
        Cargo_3 = Cargo_1.copy()
    Total_Reclamado_Actualizado = Total_Reclamado.copy()
    for i in range (tamaño):
      Total_Reclamado_Actualizado[i] = Total_Reclamado_Actualizado[i] * 0.82

    filas = list(zip(fechas, pesos(Percibido), pesos(Cargo_1), pesos(Cargo_2), pesos(Cargo_3), pesos(Total_Reclamado), pesos(Total_Reclamado_Actualizado)))
    rendered = render_template(
        "planilla_docente/resultado.html",filas=filas, datos = self.datos)
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)

    if pisa_status.err:
        # Manejar el error en caso de que la creación del PDF falle
        return "Error al crear el PDF", 500

    pdf_buffer.seek(0)

    # Enviar el PDF como respuesta
    return send_file(pdf_buffer, as_attachment=True, download_name='resultado.pdf', mimetype='application/pdf')