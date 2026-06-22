from flask import Blueprint

creacion_sentencias_bp = Blueprint(
    'creacion_sentencias',
    __name__,
)

from . import routes  # noqa: E402, F401
