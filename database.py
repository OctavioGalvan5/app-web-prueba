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

def obtener_elementos(fecha_ingresada):
    # Convertir la fecha ingresada por el usuario a un objeto datetime.date
    fecha_ingresada_dt = datetime.strptime(fecha_ingresada, '%d/%m/%Y').date()

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
            # Extraer los elementos 4 y 5 de la fila encontrada
            elemento_4 = fila_cercana[3]
            elemento_5 = fila_cercana[4]
            return elemento_4, elemento_5
        else:
            return None, None

# Ejemplo de uso
fecha_usuario = '25/01/2024'
elemento_4, elemento_5 = obtener_elementos(fecha_usuario)
print(f'Elemento 4: {elemento_4}, Elemento 5: {elemento_5}')

