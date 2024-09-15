from sqlalchemy import create_engine, text

# Actualiza con el nombre de la base de datos correcto
db_connection_string = "mysql+pymysql://admin:root2024@database-2.cp6ssaigs94q.us-east-2.rds.amazonaws.com:3306/calculadoras"

engine = create_engine(
  db_connection_string,
  connect_args={
    "ssl": {
      "ssl_ca": "/etc/ssl/cert.pem"
    }
  })

with engine.connect() as conn:
    # Usa text para envolver la consulta SQL
    result = conn.execute(text("SELECT * FROM valor_uma"))
    print(result.fetchall())

