from sqlalchemy import create_engine, MetaData, Table, select, extract
from datetime import datetime
import plotly.graph_objects as go
import io
import base64
from services.calculos import formatear_dinero
from models.database import engine
from flask import render_template, send_file
from werkzeug.wrappers import response
from config import config
from xhtml2pdf import pisa
from io import BytesIO



def convertir_fecha_periodo(fecha):
    # Convertir la fecha si es una cadena
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d')  # Ajusta el formato a como esté tu fecha
    return fecha.strftime('%m/%Y')


def reajuste_movilidad(fecha_inicial, columna, monto, fecha_final, tupla_reajuste):
    with engine.connect() as connection:
        # Cargar la tabla desde la base de datos
        metadata = MetaData()
        tabla = Table('indices_calculadora_de_movilidad', metadata, autoload_with=engine)

        # Inicializar variables y convertir fechas a tipo date si son datetime
        fecha_actual = fecha_inicial.date() if isinstance(fecha_inicial, datetime) else fecha_inicial
        fecha_final = fecha_final.date() if isinstance(fecha_final, datetime) else fecha_final
        resultados = []
        columna_actual = columna

        # Iterar hasta alcanzar la fecha final
        while fecha_actual <= fecha_final:
            # Seleccionar el valor de la columna para el año y mes actuales
            consulta = select(tabla.c[columna_actual]).where(
                extract('year', tabla.c.fechas) == fecha_actual.year,
                extract('month', tabla.c.fechas) == fecha_actual.month
            )
            resultado = connection.execute(consulta).fetchone()

            # Si no hay datos, salir del bucle
            if not resultado:
                break

            # Multiplicar el monto por el valor de la columna y actualizar el monto acumulado
            valor = resultado[0]
            if valor is not None:
                monto *= valor  # Actualiza el monto acumulado multiplicando por el índice actual

            # Verificar si la fecha es 2020-03-01 y agregar 1500 al monto si coincide
            if fecha_actual == datetime(2020, 3, 1).date() and columna_actual == 'ANSES':
                monto += 1500

            # Almacenar la fecha y el monto en resultados
            resultados.append((convertir_fecha_periodo(fecha_actual), formatear_dinero(monto)))

            # Verificar si el mes y año de fecha_actual coinciden con alguna fecha en la tupla para cambiar de columna
            for ajuste in tupla_reajuste:
                if ajuste[0] is not None and fecha_actual.year == ajuste[0].year and fecha_actual.month == ajuste[0].month:
                    columna_actual = ajuste[1]  # Cambiar a la columna de ajuste
                    break

            # Incrementar fecha_actual a la siguiente fecha en la tabla
            fecha_actual = siguiente_fecha(connection, tabla, fecha_actual)

            # Si no se encuentra una siguiente fecha, termina el bucle
            if fecha_actual is None:
                break

        for fecha, monto_final in resultados:
            print(f"Fecha: {fecha}, Monto: {monto_final}")
        return resultados


# Función para obtener la siguiente fecha en la tabla
def siguiente_fecha(connection, tabla, fecha_actual):
    consulta = select(tabla.c.fechas).where(tabla.c.fechas > fecha_actual).order_by(tabla.c.fechas.asc()).limit(1)
    resultado = connection.execute(consulta).fetchone()
    return resultado[0] if resultado else None

def procesar_tuplas(tuplas, movilidad_1):

    diccionario = {
        'ANSES': 'Aumentos Generales de la ANSeS por movilidad',
        'Caliva_mas_Anses': 'Aumentos fallo Marquez, Raimundo por Ley 27551',
        'Alanis_Mas_Anses': 'Aumentos fallo Alanis, Daniel Ley 27551 35,55% para el año 2020',
        'IPC': 'IPC',


    }
    resultado = diccionario[movilidad_1]

    for elemento in tuplas:
        # Verifica si el primer elemento no es nulo
        if elemento[0] is not None:
            # Obtiene el string del segundo elemento
            clave = elemento[1]
            fecha = elemento[0]
            if clave in diccionario:
                if resultado != "":
                    resultado += " hasta el " + fecha.strftime('%d/%m/%Y') + " y desde ahi " + diccionario[clave] 


    return resultado.strip()  # Elimina espacios al final

#reajuste_movilidad(
   # datetime(2018, 1, 25),   # Fecha inicial
    #'Alanis_Mas_Anses',      # Columna
    #15000,                   # Monto
    #datetime(2024, 8, 9),    # Fecha final
   # [(datetime(2019, 1, 18), 'ANSES'), (datetime(2020, 2, 25), 'Alanis_Mas_Anses')]  # Tupla de ajustes como lista de tuplas
#)


# python services/movilizador_de_haber/movilizador_de_haber.py

class calculo_retroactivo:
    def __init__(self, datos_del_actor, expediente, cuil_expediente, beneficio, 
         num_beneficio, fecha_inicio, fecha_fin, 
         fecha_adquisicion_del_derecho, monto, movilidad_1, tupla):

        self.datos_del_actor = datos_del_actor
        self.expediente = expediente
        self.cuil_expediente = cuil_expediente
        self.beneficio = beneficio
        self.num_beneficio = num_beneficio
        self.fecha_inicio = fecha_inicio #fecha inicial
        self.fecha_fin = fecha_fin # fecha final
        self.fecha_adquisicion_del_derecho = fecha_adquisicion_del_derecho
        self.monto = monto # monto
        self.movilidad_1 = movilidad_1 #columna
        self.tupla = tupla #tupla
        self.resultado = procesar_tuplas(self.tupla, self.movilidad_1)

    def generar_pdf(self):
        filas = reajuste_movilidad(self.fecha_inicio, self.movilidad_1, self.monto, self.fecha_fin,self.tupla)
        rendered = render_template(
            'movilizador_de_haber/resultado.html',
            filas=filas, 
            monto = formatear_dinero(self.monto),
            datos_del_actor = self.datos_del_actor,
            expediente = self.expediente,
            cuil_expediente = self.cuil_expediente,
            beneficio = self.beneficio,
            num_beneficio = self.num_beneficio,
            fecha_inicio = convertir_fecha_periodo(self.fecha_inicio),
            fecha_fin = convertir_fecha_periodo(self.fecha_fin),
            fecha_adquisicion_del_derecho = self.fecha_adquisicion_del_derecho,
            movilidad = self.resultado
        )
        # Crear el PDF en memoria
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(rendered, dest=pdf_buffer)

        if pisa_status.err:
            # Manejar el error en caso de que la creación del PDF falle
            return "Error al crear el PDF", 500

        pdf_buffer.seek(0)

        # Enviar el PDF como respuesta
        return send_file(pdf_buffer, as_attachment=True, download_name='resultado.pdf', mimetype='application/pdf')