from dataclasses import dataclass, field
from datetime import datetime


CHECKPOINTS_DISPONIBLES = [
    ('pbu',                  'PBU — Prestación Básica Universal'),
    ('pc',                   'PC — Prestación Compensatoria'),
    ('movilidad',            'Movilidad de haberes'),
    ('ganancias',            'Impuesto a las Ganancias'),
    ('error_material',       'Error Material'),
    ('reajuste_haberes',     'Reajuste de haberes'),
    ('sumas_no_remunerativas', 'Sumas no remunerativas'),
    ('dictamen_fiscal',      'Dictamen de Fiscalía'),
    ('fecha_otorgamiento',   'Fecha de otorgamiento'),
    ('periodo_aportes',      'Período de aportes'),
    ('inconstitucionalidad', 'Inconstitucionalidad de normas'),
]

CHECKPOINT_IDS = [cp_id for cp_id, _ in CHECKPOINTS_DISPONIBLES]

_MESES = [
    '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]


def _fecha_larga(dt: datetime) -> str:
    return f"{dt.day} de {_MESES[dt.month]} de {dt.year}"


@dataclass
class AnalisisIA:
    """Resultado del análisis de los 3 PDFs por la IA."""
    nombre_caratula: str = ""
    numero_expte: str = ""
    anio_expte: str = ""
    nombre_actora: str = ""
    dni_actora: str = ""
    numero_beneficio: str = ""
    fecha_adquisicion: str = ""
    fecha_alta: str = ""
    fecha_desde_retroactivo: str = ""
    minuta_actor: str = ""
    minuta_anses: str = ""
    resumen_conflicto: str = ""
    checkpoints_detectados: list = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict) -> 'AnalisisIA':
        obj = cls()
        obj.nombre_caratula = data.get('nombre_caratula', '')
        obj.numero_expte = data.get('numero_expte', '')
        obj.anio_expte = data.get('anio_expte', '')
        obj.nombre_actora = data.get('nombre_actora', '')
        obj.dni_actora = data.get('dni_actora', '')
        obj.numero_beneficio = data.get('numero_beneficio', '')
        obj.fecha_adquisicion = data.get('fecha_adquisicion', '')
        obj.fecha_alta = data.get('fecha_alta', '')
        obj.fecha_desde_retroactivo = data.get('fecha_desde_retroactivo', '')
        obj.minuta_actor = data.get('minuta_actor', '')
        obj.minuta_anses = data.get('minuta_anses', '')
        obj.resumen_conflicto = data.get('resumen_conflicto', '')
        detectados = data.get('checkpoints_detectados', [])
        obj.checkpoints_detectados = [cp for cp in detectados if cp in CHECKPOINT_IDS]
        return obj


@dataclass
class DatosSentencia:
    """Datos confirmados por el usuario desde el formulario."""
    nombre_caratula: str = ""
    numero_expte: str = ""
    anio_expte: str = ""
    nombre_actora: str = ""
    dni_actora: str = ""
    numero_beneficio: str = ""
    fecha_adquisicion: str = ""
    fecha_alta: str = ""
    fecha_desde_retroactivo: str = ""
    minuta_actor: str = ""
    minuta_anses: str = ""
    resumen_conflicto: str = ""
    checkpoints_seleccionados: list = field(default_factory=list)

    @classmethod
    def from_form(cls, form_data) -> 'DatosSentencia':
        datos = cls()
        datos.nombre_caratula = form_data.get('nombre_caratula', '')
        datos.numero_expte = form_data.get('numero_expte', '')
        datos.anio_expte = form_data.get('anio_expte', '')
        datos.nombre_actora = form_data.get('nombre_actora', '')
        datos.dni_actora = form_data.get('dni_actora', '')
        datos.numero_beneficio = form_data.get('numero_beneficio', '')
        datos.fecha_adquisicion = form_data.get('fecha_adquisicion', '')
        datos.fecha_alta = form_data.get('fecha_alta', '')
        datos.fecha_desde_retroactivo = form_data.get('fecha_desde_retroactivo', '')
        datos.minuta_actor = form_data.get('minuta_actor', '')
        datos.minuta_anses = form_data.get('minuta_anses', '')
        datos.resumen_conflicto = form_data.get('resumen_conflicto', '')
        datos.checkpoints_seleccionados = [
            cp_id for cp_id in CHECKPOINT_IDS
            if form_data.get(f'checkpoint_{cp_id}', '') == 'on'
        ]
        return datos

    def to_template_context(self) -> dict:
        ctx = {
            'fecha_sentencia': _fecha_larga(datetime.now()),
            'nombre_caratula': self.nombre_caratula,
            'numero_expte': self.numero_expte,
            'anio_expte': self.anio_expte,
            'nombre_actora': self.nombre_actora,
            'dni_actora': self.dni_actora,
            'numero_beneficio': self.numero_beneficio,
            'fecha_adquisicion': self.fecha_adquisicion,
            'fecha_alta': self.fecha_alta,
            'fecha_desde_retroactivo': self.fecha_desde_retroactivo,
            'minuta_actor': self.minuta_actor,
            'minuta_anses': self.minuta_anses,
            'resumen_conflicto': self.resumen_conflicto,
        }
        for cp_id in CHECKPOINT_IDS:
            ctx[f'cp_{cp_id}'] = cp_id in self.checkpoints_seleccionados
        return ctx
