"""
Generador de documentos Word para el módulo de escritos de liquidación.

Usa una única plantilla docx con condicionales internos (Jinja2 via docxtpl),
eliminando la necesidad de múltiples plantillas.
"""

import os
import tempfile

from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm

from blueprints.escritos_liquidacion.schemas import DatosEscrito
from blueprints.escritos_liquidacion.service import generar_cuadro_uma_imagen


# Ruta a la plantilla docx
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLANTILLA_PATH = os.path.join(
    BASE_DIR, '..', '..', 'datos', 'escritos_liquidacion',
    'Modelo_Escrito_liquidacion.docx'
)


def generar_documento(datos: DatosEscrito) -> str:
    """Genera el documento Word final a partir de los datos del formulario.

    Args:
        datos: DatosEscrito con todos los campos del formulario.

    Returns:
        Ruta al archivo .docx generado (temporal).
    """
    plantilla = os.path.abspath(PLANTILLA_PATH)
    if not os.path.exists(plantilla):
        raise FileNotFoundError(f"No se encontró la plantilla: {plantilla}")

    doc = DocxTemplate(plantilla)
    context = datos.to_template_context()

    # Generar cuadro de honorarios UMA como imagen
    imagen_uma_path = None
    try:
        imagen_uma_path = generar_cuadro_uma_imagen(datos)
        if imagen_uma_path and os.path.exists(imagen_uma_path):
            context['cuadro_honorarios'] = InlineImage(
                doc, imagen_uma_path, width=Mm(160)
            )
        else:
            context['cuadro_honorarios'] = ""
    except Exception as e:
        print(f"Error generando cuadro UMA: {e}")
        context['cuadro_honorarios'] = ""

    # Renderizar documento
    doc.render(context)

    # Guardar en archivo temporal
    output = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.docx',
        prefix='escrito_liquidacion_'
    )
    doc.save(output.name)
    output.close()

    # Limpiar imagen temporal
    if imagen_uma_path:
        try:
            os.remove(imagen_uma_path)
        except OSError:
            pass

    return output.name
