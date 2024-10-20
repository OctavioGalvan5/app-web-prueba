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

def obtener_acordada(fecha_ingresada):
    # Convertir la fecha ingresada por el usuario a un objeto datetime.date
    fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%Y-%m-%d').date()

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM valor_uma"))

        # Variables para almacenar la fila más cercana
        fila_cercana = None
        fecha_cercana = None

        for row in result:
            fecha_fila = row[1]  # Asumiendo que la segunda columna es la fecha
            if fecha_fila <= fecha_ingresada_dt:
                # Comparar para encontrar la fecha más cercana
                if fecha_cercana is None or fecha_fila > fecha_cercana:
                    fecha_cercana = fecha_fila
                    fila_cercana = row

        if fila_cercana:
            # Extraer el elemento 4
            acordada = fila_cercana[3]
            return acordada
        else:
            return None

def obtener_valor_uma(fecha_ingresada):
    fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%Y-%m-%d').date()

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM valor_uma"))

        # Variables para almacenar la fila más cercana
        fila_cercana = None
        fecha_cercana = None

        for row in result:
            fecha_fila = row[1]  # Asumiendo que la segunda columna es la fecha
            if fecha_fila <= fecha_ingresada_dt:
                # Comparar para encontrar la fecha más cercana
                if fecha_cercana is None or fecha_fila > fecha_cercana:
                    fecha_cercana = fecha_fila
                    fila_cercana = row

        if fila_cercana:
            # Extraer el elemento 5
            acordada = fila_cercana[4]
            return acordada
        else:
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

def formatear_dinero(cantidad):
    return format_currency(cantidad, 'ARS', locale='es_AR').replace(u'\xa0', u'')

def buscar_fechas(fecha_ingresada, monto):
    # Convertir la fecha ingresada a un objeto datetime.date en formato 'dd/mm/yyyy'
    fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%d/%m/%Y').date()

    with engine.connect() as conn:
        # Buscar la fila con la fecha más cercana menor a la ingresada
        result = conn.execute(text("SELECT * FROM indices_calculadora_de_movilidad WHERE fechas <= :fecha ORDER BY fechas DESC LIMIT 1"), {"fecha": fecha_ingresada_dt})

        fila_menor = result.fetchone()  # Obtener la fila con la fecha más cercana menor

        if fila_menor:
            print("La fila más cercana a la fecha ingresada (menor) es:")

            # Calcular los montos multiplicados por la fila menor
            monto_columna2 = fila_menor[2] * monto
            monto_columna3 = fila_menor[3] * monto
            monto_columna4 = fila_menor[4] * monto
            monto_columna5 = fila_menor[5] * monto
            monto_columna6 = fila_menor[6] * monto
            monto_columna7 = fila_menor[7] * monto

            print(f"Monto columna 2: {formatear_dinero(monto_columna2)}")
            print(f"Indice Anses: {fila_menor[2]}")
            print(f"Monto columna 3: {formatear_dinero(monto_columna3)}")
            print(f"Indice IPC: {fila_menor[3]}")
            print(f"Monto columna 4: {formatear_dinero(monto_columna4)}")
            print(f"Indice RIPTE: {fila_menor[4]}")
            print(f"Monto columna 5: {formatear_dinero(monto_columna5)}")
            print(f"Indice UMA: {fila_menor[5]}")
            print(f"Monto columna 6: {formatear_dinero(monto_columna6)}")
            print(f"Indice Movilidad de sentencia: {fila_menor[6]}")
            print(f"Monto columna 7: {formatear_dinero(monto_columna7)}")
            print(f"Indice Ley con rezago: {fila_menor[7]}")
        else:
            print("No se encontró una fecha menor a la ingresada.")
            return

        print("\nMultiplicando montos con filas con fechas mayores a la ingresada:")

        # Buscar todas las filas con fechas mayores a la ingresada
        result_mayores = conn.execute(text("SELECT * FROM indices_calculadora_de_movilidad WHERE fechas > :fecha ORDER BY fechas ASC"), {"fecha": fecha_ingresada_dt})

        filas_mayores = result_mayores.fetchall()  # Obtener todas las filas con fechas mayores

        if filas_mayores:
            # Iterar sobre cada fila mayor y multiplicar los valores correspondientes
            for fila_idx, fila in enumerate(filas_mayores):
                print(f"\nFila {fila_idx + 1}:")

                print(fila[1])
                # Multiplicar monto_columna2 por el valor de la columna 2 en la fila actual
                if fila[0] == 33:
                    monto_columna2 = monto_columna2 * fila[2] + 1500
                else:
                    monto_columna2 = monto_columna2 * fila[2]
                print(f"Multiplicando Columna 2: {formatear_dinero(monto_columna2)}")
                print(f"Indice Anses: {fila[2]}")

                # Multiplicar monto_columna3 por el valor de la columna 3 en la fila actual
                monto_columna3 = monto_columna3 * fila[3]
                print(f"Multiplicando Columna 3: {formatear_dinero(monto_columna3)}")
                print(f"Indice IPC: {fila[3]}")

                # Multiplicar monto_columna4 por el valor de la columna 4 en la fila actual
                monto_columna4 *= fila[4]
                print(f"Multiplicando Columna 4: {formatear_dinero(monto_columna4)}")
                print(f"Indice RIPTE: {fila[4]}")

                # Multiplicar monto_columna5 por el valor de la columna 5 en la fila actual
                monto_columna5 *= fila[5]
                print(f"Multiplicando Columna 5: {formatear_dinero(monto_columna5)}")
                print(f"Indice UMA: {fila[5]}")

                # Multiplicar monto_columna6 por el valor de la columna 6 en la fila actual
                monto_columna6 *= fila[6]
                print(f"Multiplicando Columna 6: {formatear_dinero(monto_columna6)}")
                print(f"Indice Movilidad de sentencia: {fila[6]}")

                # Multiplicar monto_columna7 por el valor de la columna 7 en la fila actual
                monto_columna7 *= fila[7]
                print(f"Multiplicando Columna 7: {formatear_dinero(monto_columna7)}")
                print(f"Indice Ley con rezago: {fila[7]}")

        else:
            print("No se encontraron filas con fechas mayores a la ingresada.")

# Ejemplo de uso
buscar_fechas("25/07/2017", 16049.62)