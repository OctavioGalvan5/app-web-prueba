"""
Rutas HTTP para el módulo de escritos de liquidación.

Usa las mismas URLs que el sistema anterior para mantener compatibilidad
con links existentes en nav y home.
"""

import os
from flask import render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required

from blueprints.escritos_liquidacion import escritos_liquidacion_bp
from blueprints.escritos_liquidacion.schemas import DatosEscrito
from blueprints.escritos_liquidacion.service import procesar_pdfs
from blueprints.escritos_liquidacion.document_generator import generar_documento


@escritos_liquidacion_bp.route('/generador_escrito_liquidacion', methods=['GET', 'POST'])
def generador_escrito_liquidacion():
    """Página de entrada: upload de PDF o formulario manual.

    GET  → muestra la página de upload (index.html)
    POST → si hay PDF: lo procesa con IA y muestra formulario pre-rellenado
           si no hay PDF: muestra formulario vacío
    """
    if request.method == 'POST':
        archivos = [f for f in request.files.getlist('pdf') if f and f.filename != '']

        if archivos:
            # Procesar PDFs con IA
            try:
                datos = procesar_pdfs(archivos)
            except Exception as e:
                print(f"Error procesando PDFs: {e}")
                flash(f"Error al procesar el PDF: {str(e)}", "danger")
                datos = DatosEscrito()
        else:
            # POST sin archivo → formulario vacío
            datos = DatosEscrito()

        return render_template('escritos_liquidacion/formulario.html', datos=datos)

    # GET → página de upload
    return render_template('escritos_liquidacion/index.html')


@escritos_liquidacion_bp.route('/resultado_escrito_liquidacion', methods=['POST'])
@login_required
def resultado_escrito_liquidacion():
    """Genera el documento Word final y lo envía para descarga."""
    try:
        datos = DatosEscrito.from_form(request.form)
        archivo_path = generar_documento(datos)

        nombre_archivo = f"Escrito_Liquidacion_{datos.nombre_caratula or 'documento'}.docx"

        response = send_file(
            archivo_path,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

        # Limpiar archivo temporal después de enviarlo
        @response.call_on_close
        def cleanup():
            try:
                os.remove(archivo_path)
            except OSError:
                pass

        return response

    except Exception as e:
        print(f"Error generando documento: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error al generar el documento: {str(e)}", "danger")
        return redirect(url_for('escritos_liquidacion.generador_escrito_liquidacion'))
