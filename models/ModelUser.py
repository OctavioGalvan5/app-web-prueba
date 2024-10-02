import uuid
from sqlalchemy import text
from models.database import engine
from .entities.User import User

class ModelUser():

    @classmethod
    def login(cls, user):
        try:
            with engine.connect() as conn:
                sql = text("SELECT id, username, password, fullname, session_token FROM users WHERE username = :username")
                result = conn.execute(sql, {'username': user.username})
                row = result.fetchone()
                if row is not None:
                    user = User(row[0], row[1], User.check_password(row[2], user.password), row[3], row[4])
                    if user.password:  # Si la contraseña es correcta
                        # Generar un nuevo token de sesión
                        new_session_token = str(uuid.uuid4())
                        user.session_token = new_session_token
                        # Actualizar el token de sesión en la base de datos
                        update_sql = text("UPDATE users SET session_token = :session_token WHERE id = :id")
                        conn.execute(update_sql, {'session_token': new_session_token, 'id': user.id})
                        return user
                return None
        except Exception as ex:
            raise Exception(ex)

    @classmethod
    def get_by_id(cls, id):
        try:
            with engine.connect() as conn:
                sql = text("SELECT id, username, fullname, session_token FROM users WHERE id = :id")
                result = conn.execute(sql, {'id': id})
                row = result.fetchone()
                if row is not None:
                    return User(row[0], row[1], None, row[2], row[3])
                else:
                    return None
        except Exception as ex:
            raise Exception(ex)

