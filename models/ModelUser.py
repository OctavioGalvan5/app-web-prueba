from sqlalchemy import text
from models.database import engine
from .entities.User import User

class ModelUser():

    @classmethod
    def login(cls, user):
        try:
            with engine.connect() as conn:
                sql = text("SELECT id, username, password, fullname, credito FROM users WHERE username = :username")
                result = conn.execute(sql, {'username': user.username})
                row = result.fetchone()
                if row is not None:
                    user = User(row[0], row[1], User.check_password(row[2], user.password), row[3], row[4])  # Incluyendo el credito
                    return user
                else:
                    return None
        except Exception as ex:
            raise Exception(ex)


    @classmethod
    def get_by_id(cls, id):
        try:
            with engine.connect() as conn:
                sql = text("SELECT id, username, fullname, credito FROM users WHERE id = :id")
                result = conn.execute(sql, {'id': id})
                row = result.fetchone()
                if row is not None:
                    return User(row[0], row[1], None, row[2], row[3])  # Incluyendo el credito
                else:
                    return None
        except Exception as ex:
            raise Exception(ex)

            
    @classmethod
    def update_credito(cls, user_id, nuevo_credito):
        try:
            with engine.connect() as conn:
                sql = text("UPDATE users SET credito = :credito WHERE id = :id")
                conn.execute(sql, {'credito': nuevo_credito, 'id': user_id})
                conn.commit()  # Asegúrate de que se realicen las transacciones
        except Exception as ex:
            raise Exception(ex)