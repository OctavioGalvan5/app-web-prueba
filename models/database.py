from sqlalchemy import create_engine, text
from datetime import datetime

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

ejemplo = obtener_porcentaje_minimo(444.49)
print(ejemplo)