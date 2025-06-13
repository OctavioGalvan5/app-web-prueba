from babel.numbers import format_currency
from datetime import datetime
from models.database import engine
from sqlalchemy import text

def obtener_porcentajes_fila_anterior(valor_ingresado):
  with engine.connect() as conn:
      result = conn.execute(text("SELECT * FROM porcentaje_uma"))

      fila_anterior = None

      for row in result:
          valor1 = row[1]  # Suponiendo que la columna 1 es valor1
          valor2 = row[2]  # Suponiendo que la columna 2 es valor2

          if valor1 <= valor_ingresado <= valor2:
              return fila_anterior[3] if fila_anterior else None

          fila_anterior = row  # Guarda la fila actual como la "anterior" para la siguiente iteración

  return None

def obtener_porcentajes(valor_ingresado):
  with engine.connect() as conn:
      result = conn.execute(text("SELECT * FROM porcentaje_uma"))

      for row in result:
          valor1 = row[1]  # Asumiendo que la columna 1 es el primer elemento
          valor2 = row[2]  # Asumiendo que la columna 2 es el segundo elemento

          # Verificar si valor_ingresado está entre valor1 y valor2
          if valor1 <= valor_ingresado <= valor2:
              # Devolver el elemento 3 de la fila
              return row[3]  # Asumiendo que la columna 3 es el tercer elemento

  return None  # Si no se encuentra ningún rango que contenga el valor ingresado

def obtener_porcentaje_minimo(valor_ingresado):
  with engine.connect() as conn:
      result = conn.execute(text("SELECT * FROM porcentaje_uma"))

      for row in result:
          valor1 = row[1]  # Asumiendo que la columna 1 es el primer elemento
          valor2 = row[2]  # Asumiendo que la columna 2 es el segundo elemento

          # Verificar si valor_ingresado está entre valor1 y valor2
          if valor1 <= valor_ingresado <= valor2:
              # Devolver el elemento 3 de la fila
              return row[4]  # Asumiendo que la columna 3 es el tercer elemento
  return None  # Si no se encuentra ningún rango que contenga el valor ingresado


def obtener_porcentaje_maximo(valor_ingresado):
  with engine.connect() as conn:
      result = conn.execute(text("SELECT * FROM porcentaje_uma"))

      for row in result:
          valor1 = row[1]  # Asumiendo que la columna 1 es el primer elemento
          valor2 = row[2]  # Asumiendo que la columna 2 es el segundo elemento

          # Verificar si valor_ingresado está entre valor1 y valor2
          if valor1 <= valor_ingresado <= valor2:
              # Devolver el elemento 3 de la fila
              return row[5]  # Asumiendo que la columna 3 es el tercer elemento
  return None  # Si no se encuentra ningún rango que contenga el valor ingresado

def obtener_porcentaje_maximo_fila_anterior(valor_ingresado):
  with engine.connect() as conn:
      result = conn.execute(text("SELECT * FROM porcentaje_uma"))

      fila_anterior = None

      for row in result:
          valor1 = row[1]  # Rango inferior
          valor2 = row[2]  # Rango superior

          if valor1 <= valor_ingresado <= valor2:
              return fila_anterior[5] if fila_anterior else None

          fila_anterior = row  # Guarda la fila actual para la próxima iteración

  return None

def obtener_monto_uma_maximo_fila_anterior(valor_ingresado):
  with engine.connect() as conn:
      result = conn.execute(text("SELECT * FROM porcentaje_uma"))

      fila_anterior = None

      for row in result:
          valor1 = row[1]  # Valor mínimo del rango
          valor2 = row[2]  # Valor máximo del rango (el monto UMA máximo actual)

          if valor1 <= valor_ingresado <= valor2:
              return fila_anterior[2] if fila_anterior else None  # Retorna el UMA máximo de la fila anterior

          fila_anterior = row  # Guarda la fila actual como "anterior" para la próxima vuelta

  return None  # Si no se encuentra un rango, devuelve None
  
def formatear_dinero(cantidad):
    return format_currency(cantidad, 'ARS', locale='es_AR').replace(u'\xa0', u'')

def dividir(monto, valor_uma):
  resultado = float(monto) / float(valor_uma)
  return round(resultado, 2)

def calcular_porcentaje(porcentaje, numero):
  resultado = (porcentaje / 100) * numero
  return round(resultado, 2)

def sumar_porcentaje(porcentaje, numero):
  resultado = numero + (numero * porcentaje / 100)
  return round(resultado, 2)

def restar_porcentaje(porcentaje, numero):
  resultado = numero - (numero * porcentaje / 100)
  return round(resultado, 2)

def calcular_porcentajes(monto_aprobado, valor_uma):
  cantidad_uma = dividir(monto_aprobado, valor_uma)
  valor_divido_2 = dividir(cantidad_uma, 2)
  if valor_divido_2 < 15:
    porcentaje = obtener_porcentaje_maximo(valor_divido_2)
    porcentajes = obtener_porcentajes(valor_divido_2)
    total_uma = calcular_porcentaje(porcentaje, valor_divido_2)
    apoderado = sumar_porcentaje(40,total_uma)
    reduccion_excepciones = restar_porcentaje(10,apoderado)
    porcentaje_anterior = 0
    primera_valor_uma_final = 0
    segunda_valor_uma_final = 0
    
  else:
    porcentajes = obtener_porcentajes(valor_divido_2) #final
    porcentaje_anterior = obtener_porcentajes_fila_anterior(valor_divido_2)
    porcentaje_minimo = obtener_porcentaje_minimo(valor_divido_2)
    porcentaje_maximo = obtener_porcentaje_maximo_fila_anterior(valor_divido_2)
    primer_valor_uma = obtener_monto_uma_maximo_fila_anterior(valor_divido_2)
    primera_valor_uma_final = calcular_porcentaje(porcentaje_maximo,primer_valor_uma)
    segunda_valor_uma = valor_divido_2 - primer_valor_uma
    segunda_valor_uma_final = calcular_porcentaje(porcentaje_minimo, segunda_valor_uma)
    total_uma = round(primera_valor_uma_final + segunda_valor_uma_final, 2)
    apoderado = sumar_porcentaje(40,total_uma) # final
    reduccion_excepciones = restar_porcentaje(10,apoderado) #final
    #ejecucion_art54 = restar_porcentaje(50,reduccion_excepciones) #final
    #incidencia = calcular_porcentaje(25, ejecucion_art54) #final

  return cantidad_uma, valor_divido_2, porcentajes, porcentaje_anterior, primera_valor_uma_final, segunda_valor_uma_final, total_uma, apoderado, reduccion_excepciones

def transformar_fecha(fecha):
  # Convertir la fecha de string a objeto datetime
  fecha_objeto = datetime.strptime(fecha, "%Y-%m-%d")
  # Formatear la fecha al nuevo formato deseado
  fecha_formateada = fecha_objeto.strftime("%d/%m/%Y")
  return fecha_formateada

def transformar_fecha_periodo(fecha):
  # Convertir la fecha de string a objeto datetime
  fecha_objeto = datetime.strptime(fecha, "%Y-%m-%d")
  # Formatear la fecha al nuevo formato deseado
  fecha_formateada = fecha_objeto.strftime("%m/%Y")
  return fecha_formateada

def calcular_porcentajes_ley_21839(monto):
  porcentaje_aplicable= calcular_porcentaje(13,monto)
  apoderada = sumar_porcentaje(30,porcentaje_aplicable)
  sin_excepciones = restar_porcentaje(30,apoderada)
  criterio_jurisprudencial = sin_excepciones/2

  return porcentaje_aplicable, apoderada, sin_excepciones, criterio_jurisprudencial

def convertir_fecha(fecha):
    """
    Convierte una fecha de tipo datetime al formato 'dd/mm/yyyy'.

    :param fecha: Un objeto de tipo datetime.
    :return: Una cadena de texto con la fecha en formato 'dd/mm/yyyy'.
    """
    return fecha.strftime('%d/%m/%Y')

def convertir_fecha_periodo(fecha):
  """
  Convierte una fecha de tipo datetime al formato 'mm/yyyy'.

  :param fecha: Un objeto de tipo datetime.
  :return: Una cadena de texto con la fecha en formato 'mm/yyyy'.
  """
  return fecha.strftime('%m/%Y')