"""
Generador de documentos Word para el módulo de creación de sentencias.

Usa una plantilla docx con condicionales Jinja2 (via docxtpl).
Cada checkpoint seleccionado activa un bloque de párrafos en el documento.

Plantilla esperada: datos/creacion_sentencias/Modelo_Sentencia.docx
Variables en la plantilla:
  - {{ nombre_caratula }}, {{ numero_expte }}, {{ anio_expte }}
  - {{ minuta_actor }}, {{ minuta_anses }}, {{ resumen_conflicto }}
  - {%p if cp_pbu %} ... {%p endif %}   (un bloque por checkpoint)
"""

import os
import tempfile

from docxtpl import DocxTemplate

from blueprints.creacion_sentencias.schemas import DatosSentencia


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLANTILLA_PATH = os.path.join(
    BASE_DIR, '..', '..', 'datos', 'creacion_sentencias',
    'Modelo_Sentencia.docx'
)


def generar_documento(datos: DatosSentencia) -> str:
    """Genera el .docx de sentencia y retorna la ruta al archivo temporal."""
    plantilla = os.path.abspath(PLANTILLA_PATH)
    if not os.path.exists(plantilla):
        raise FileNotFoundError(
            f"Plantilla no encontrada: {plantilla}\n"
            "Colocá 'Modelo_Sentencia.docx' en la carpeta 'datos/creacion_sentencias/'"
        )

    doc = DocxTemplate(plantilla)
    context = datos.to_template_context()
    doc.render(context)

    output = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.docx',
        prefix='sentencia_'
    )
    doc.save(output.name)
    output.close()
    return output.name
