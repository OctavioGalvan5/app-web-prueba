from sqlalchemy import create_engine, text
from datetime import datetime
from babel.numbers import format_currency

# Configuración de la conexión a la base de datos
db_connection_string = "mysql+pymysql://admin:root2025@database-1.cly8coaeo7ek.us-east-2.rds.amazonaws.com:3306/calculadoras"

engine = create_engine(
    db_connection_string,
    connect_args={
        "ssl": {
            "ssl_ca": "/etc/ssl/cert.pem"
        }
    })

def formatear_dinero(cantidad):
    return format_currency(cantidad, 'ARS', locale='es_AR').replace(u'\xa0', u'')

def buscar_fechas(fecha_inicio, fecha_fin, monto):
    # Convertir las fechas ingresadas a objetos datetime.date en formato 'yyyy-mm-dd'
    fecha_ingresada_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

    lista_filas = []
    lista_montos = []

    with engine.connect() as conn:
        # Buscar la fila con la fecha más cercana menor a la ingresada
        result = conn.execute(
            text("SELECT * FROM indices_calculadora_de_movilidad WHERE fechas <= :fecha ORDER BY fechas DESC LIMIT 1"),
            {"fecha": fecha_ingresada_dt}
        )

        fila_menor = result.fetchone()  # Obtener la fila con la fecha más cercana menor

        if fila_menor:
            columnas = result.keys()  # Obtener los nombres de las columnas
            fila_dict = dict(zip(columnas, fila_menor))  # Convertir la fila a diccionario

            # Acceder a las columnas por nombre y calcular los montos
            monto_columna2 = fila_dict['ANSES'] * monto
            monto_columna3 = fila_dict['IPC'] * monto
            monto_columna4 = fila_dict['RIPTE'] * monto
            monto_columna5 = fila_dict['UMA'] * monto
            monto_columna6 = fila_dict['Mov_de_Sentencia'] * monto
            monto_columna7 = fila_dict['ley_27426_sin_rezago'] * monto
            monto_columna8 = fila_dict['Caliva_Marquez_con_27551_con_3_rezago'] * monto
            monto_columna9 = fila_dict['Caliva_mas_Anses'] * monto
            monto_columna10 = fila_dict['Caliva_Marquez_con_27551_con_6_rezago'] * monto
            monto_columna11 = fila_dict['Alanis_Mas_Anses'] * monto
            monto_columna12 = fila_dict['Alanis_con_27551_con_3_meses_rezago'] * monto

            # Agregar la primera tupla a la lista
            lista_filas.append((
                convertir_fecha_periodo(fila_dict['fechas']),
                formatear_dinero(monto_columna2),
                formatear_dinero(monto_columna3),
                formatear_dinero(monto_columna4),
                formatear_dinero(monto_columna5),
                formatear_dinero(monto_columna6),
                formatear_dinero(monto_columna7),
                formatear_dinero(monto_columna8),
                formatear_dinero(monto_columna9),
                formatear_dinero(monto_columna10),
                formatear_dinero(monto_columna11),
                formatear_dinero(monto_columna12)
            ))
            lista_montos.append((monto_columna2, monto_columna3, monto_columna4, monto_columna5, monto_columna6, monto_columna7,
                                 monto_columna8, monto_columna9, monto_columna10, monto_columna11, monto_columna12))
        else:
            print("No se encontró una fecha menor a la ingresada.")
            return []

        # Buscar todas las filas con fechas mayores a la ingresada
        result_mayores = conn.execute(
            text("SELECT * FROM indices_calculadora_de_movilidad WHERE fechas > :fecha ORDER BY fechas ASC"),
            {"fecha": fecha_ingresada_dt}
        )

        filas_mayores = result_mayores.fetchall()

        if filas_mayores:
            for fila in filas_mayores:
                fila_dict = dict(zip(result_mayores.keys(), fila))  # Convertir la fila a diccionario

                if fila_dict['id'] == 33:
                    monto_columna2 = monto_columna2 * fila_dict['ANSES'] + 1500
                else:
                    monto_columna2 = monto_columna2 * fila_dict['ANSES']

                monto_columna3 *= fila_dict['IPC']
                monto_columna4 *= fila_dict['RIPTE']
                monto_columna5 *= fila_dict['UMA']
                monto_columna6 *= fila_dict['Mov_de_Sentencia']
                monto_columna7 *= fila_dict['ley_27426_sin_rezago']
                monto_columna8 *= fila_dict['Caliva_Marquez_con_27551_con_3_rezago']
                monto_columna9 *= fila_dict['Caliva_mas_Anses']
                monto_columna10 *= fila_dict['Caliva_Marquez_con_27551_con_6_rezago']
                monto_columna11 *= fila_dict['Alanis_Mas_Anses']
                monto_columna12 *= fila_dict['Alanis_con_27551_con_3_meses_rezago']

                lista_filas.append((
                    convertir_fecha_periodo(fila_dict['fechas']),
                    formatear_dinero(monto_columna2),
                    formatear_dinero(monto_columna3),
                    formatear_dinero(monto_columna4),
                    formatear_dinero(monto_columna5),
                    formatear_dinero(monto_columna6),
                    formatear_dinero(monto_columna7),
                    formatear_dinero(monto_columna8),
                    formatear_dinero(monto_columna9),
                    formatear_dinero(monto_columna10),
                    formatear_dinero(monto_columna11),
                    formatear_dinero(monto_columna12)
                ))
                lista_montos.append((monto_columna2, monto_columna3, monto_columna4, monto_columna5, monto_columna6, monto_columna7,
                                     monto_columna8, monto_columna9, monto_columna10, monto_columna11, monto_columna12))

                if fila_dict['fechas'].year == fecha_fin_dt.year and fila_dict['fechas'].month == fecha_fin_dt.month:
                    break
        else:
            print("No se encontraron filas con fechas mayores a la ingresada.")
            return []

    return lista_filas, lista_montos



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