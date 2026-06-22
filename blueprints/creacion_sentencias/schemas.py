from dataclasses import dataclass, field


CHECKPOINTS_DISPONIBLES = [
    ('pbu',                'PBU — Prestación Básica Universal'),
    ('pap',                'PAP — Prestación Adicional por Permanencia'),
    ('pc',                 'PC — Prestación Compensatoria'),
    ('movilidad',          'Movilidad de haberes'),
    ('ganancias',          'Impuesto a las Ganancias'),
    ('error_material',     'Error Material'),
    ('reajuste_haberes',   'Reajuste de haberes'),
    ('fecha_otorgamiento', 'Fecha de otorgamiento'),
    ('periodo_aportes',    'Período de aportes'),
    ('inconstitucionalidad', 'Inconstitucionalidad de normas'),
]

CHECKPOINT_IDS = [cp_id for cp_id, _ in CHECKPOINTS_DISPONIBLES]


@dataclass
class AnalisisIA:
    """Resultado del análisis de los 3 PDFs por la IA."""
    nombre_caratula: str = ""
    numero_expte: str = ""
    anio_expte: str = ""
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
        datos.minuta_actor = form_data.get('minuta_actor', '')
        datos.minuta_anses = form_data.get('minuta_anses', '')
        datos.resumen_conflicto = form_data.get('resumen_conflicto', '')
        datos.checkpoints_seleccionados = [
            cp_id for cp_id in CHECKPOINT_IDS
            if form_data.get(f'checkpoint_{cp_id}', '') == 'on'
        ]
        return datos

    def to_template_context(self) -> dict:
        """Genera el dict de variables para docxtpl.

        Cada checkpoint genera una variable booleana 'cp_<id>' en el docx.
        """
        ctx = {
            'nombre_caratula': self.nombre_caratula,
            'numero_expte': self.numero_expte,
            'anio_expte': self.anio_expte,
            'minuta_actor': self.minuta_actor,
            'minuta_anses': self.minuta_anses,
            'resumen_conflicto': self.resumen_conflicto,
        }
        for cp_id in CHECKPOINT_IDS:
            ctx[f'cp_{cp_id}'] = cp_id in self.checkpoints_seleccionados
        return ctx
