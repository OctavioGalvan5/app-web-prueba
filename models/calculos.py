from models.database import obtener_porcentajes, obtener_porcentaje_minimo
from babel.numbers import format_currency
from datetime import datetime


def formatear_dinero(cantidad):
    return format_currency(cantidad, 'ARS', locale='es_AR').replace(u'\xa0', u'')
  
def dividir(monto, valor_uma):
  resultado = monto / float(valor_uma)
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
  cantidad_uma = dividir(monto_aprobado, valor_uma) # 
  porcentajes = obtener_porcentajes(cantidad_uma) #final
  porcentaje_minimo = obtener_porcentaje_minimo(cantidad_uma)
  minimo_en_uma = calcular_porcentaje(porcentaje_minimo, cantidad_uma) # final
  apoderado = sumar_porcentaje(40,minimo_en_uma) # final
  reduccion_excepciones = restar_porcentaje(10,apoderado) #final
  ejecucion_art54 = restar_porcentaje(50,reduccion_excepciones) #final
  incidencia = calcular_porcentaje(25, ejecucion_art54) #final

  return porcentajes, cantidad_uma, minimo_en_uma, apoderado, reduccion_excepciones,ejecucion_art54, incidencia

def transformar_fecha(fecha):
  # Convertir la fecha de string a objeto datetime
  fecha_objeto = datetime.strptime(fecha, "%Y-%m-%d")
  # Formatear la fecha al nuevo formato deseado
  fecha_formateada = fecha_objeto.strftime("%d/%m/%Y")
  return fecha_formateada
                                      
def calcular_porcentajes_ley_21839(monto):
  porcentaje_aplicable= calcular_porcentaje(13,monto)
  apoderada = sumar_porcentaje(30,porcentaje_aplicable)
  sin_excepciones = restar_porcentaje(30,apoderada)
  criterio_jurisprudencial = sin_excepciones/2

  return porcentaje_aplicable, apoderada, sin_excepciones, criterio_jurisprudencial
  