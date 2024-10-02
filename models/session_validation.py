from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user, logout_user
from models.ModelUser import ModelUser

# Decorador para validar el session_token
def validate_session_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            user_in_db = ModelUser.get_by_id(current_user.id)
            if user_in_db.session_token != current_user.session_token:
                # Si el token de sesión no coincide, cerramos la sesión
                logout_user()
                flash('Sesión expirada o iniciada en otro dispositivo', 'warning')
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
