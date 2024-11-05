from sqlalchemy import create_engine, text
from datetime import datetime
from babel.numbers import format_currency

# Configuración de la conexión a la base de datos
db_connection_string = "mysql+pymysql://admin:root2024@database-2.cp6ssaigs94q.us-east-2.rds.amazonaws.com:3306/calculadoras"

engine = create_engine(
    db_connection_string,
    connect_args={
        "ssl": {
            "ssl_ca": "/etc/ssl/cert.pem"
        }
    })

def formatear_dinero(cantidad):
    return format_currency(cantidad, 'ARS', locale='es_AR').replace(u'\xa0', u'')

def buscar_fechas(fecha_inicio,fecha_fin, monto):
    # Convertir la fecha ingresada a un objeto datetime.date en formato 'dd/mm/yyyy'
    fecha_ingresada_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

    # Lista para almacenar las tuplas de montos
    lista_filas = []
    lista_montos = []

    with engine.connect() as conn:
        # Buscar la fila con la fecha más cercana menor a la ingresada
        result = conn.execute(text("SELECT * FROM indices_calculadora_de_movilidad WHERE fechas <= :fecha ORDER BY fechas DESC LIMIT 1"), {"fecha": fecha_ingresada_dt})

        fila_menor = result.fetchone()  # Obtener la fila con la fecha más cercana menor

        if fila_menor:
            # Calcular los montos multiplicados por la fila menor
            monto_columna2 = fila_menor[2] * monto
            monto_columna3 = fila_menor[3] * monto
            monto_columna4 = fila_menor[4] * monto
            monto_columna5 = fila_menor[5] * monto
            monto_columna6 = fila_menor[6] * monto
            monto_columna7 = fila_menor[7] * monto
            monto_columna8 = fila_menor[8] * monto
            monto_columna9 = fila_menor[9] * monto
            monto_columna10 = fila_menor[10] * monto
            monto_columna11 = fila_menor[11] * monto
            monto_columna12 = fila_menor[12] * monto


            # Agregar la primera tupla a la lista
            lista_filas.append((convertir_fecha_periodo(fila_menor[1]),
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
            lista_montos.append((monto_columna2,monto_columna3,monto_columna4,monto_columna5,monto_columna6,monto_columna7, monto_columna8, monto_columna9, monto_columna10, monto_columna11,monto_columna12))
        else:
            print("No se encontró una fecha menor a la ingresada.")
            return []

        # Buscar todas las filas con fechas mayores a la ingresada
        result_mayores = conn.execute(text("SELECT * FROM indices_calculadora_de_movilidad WHERE fechas > :fecha ORDER BY fechas ASC"), {"fecha": fecha_ingresada_dt})

        filas_mayores = result_mayores.fetchall()  # Obtener todas las filas con fechas mayores

        if filas_mayores:
            # Iterar sobre cada fila mayor y multiplicar los valores correspondientes
            for fila_idx, fila in enumerate(filas_mayores):
                if fila[0] == 33:
                    monto_columna2 = monto_columna2 * fila[2] + 1500
                else:
                    monto_columna2 = monto_columna2 * fila[2]

                monto_columna3 = monto_columna3 * fila[3]
                monto_columna4 *= fila[4]
                monto_columna5 *= fila[5]
                monto_columna6 *= fila[6]
                monto_columna7 *= fila[7]
                monto_columna8 *= fila[8]
                monto_columna9 *= fila[9]
                monto_columna10 *= fila[10]
                monto_columna11 *= fila[11]
                monto_columna12 *= fila[12]

                # Agregar la tupla a la lista
                lista_filas.append((convertir_fecha_periodo(fila[1]),
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
                lista_montos.append((monto_columna2,monto_columna3,monto_columna4,monto_columna5,monto_columna6,monto_columna7,monto_columna8, monto_columna9, monto_columna10, monto_columna11, monto_columna12))

                # Comparar si el año y el mes son los mismos
                if fila[1].year == fecha_fin_dt.year and fila[1].month == fecha_fin_dt.month:
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