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