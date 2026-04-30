from flask import Blueprint

escritos_liquidacion_bp = Blueprint(
    'escritos_liquidacion',
    __name__,
)

from . import routes  # noqa: E402, F401 — registra las rutas del blueprint
