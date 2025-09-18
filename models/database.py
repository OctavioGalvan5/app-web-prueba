from sqlalchemy import create_engine, text
from datetime import datetime
from babel.numbers import format_currency

db_connection_string = (
    "mysql+pymysql://admin:root2025@database-1.cruqq6acemph.us-east-2.rds.amazonaws.com:3306/calculadoras"
    "?charset=utf8mb4"
)

engine = create_engine(
    db_connection_string,
    pool_pre_ping=True,    # evita usar conexiones muertas
    pool_recycle=900,      # recicla antes del timeout del server (ajustá si tu MySQL corta antes)
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    connect_args={
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30,
        "ssl": {"ssl_ca": "/etc/ssl/cert.pem"},
    },
)

def formatear_dinero(cantidad):
    return format_currency(cantidad, 'ARS', locale='es_AR').replace(u'\xa0', u'')




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