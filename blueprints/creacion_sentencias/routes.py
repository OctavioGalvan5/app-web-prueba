"""
Rutas HTTP para el módulo de creación de sentencias.

Flujo:
  GET  /creador_sentencias           → página de upload de 3 PDFs
  POST /creador_sentencias           → analiza con IA, muestra formulario pre-rellenado
  POST /creador_sentencias/resultado → genera y descarga el .docx
"""

import os
from flask import render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required

from blueprints.creacion_sentencias import creacion_sentencias_bp
from blueprints.creacion_sentencias.schemas import DatosSentencia, CHECKPOINTS_DISPONIBLES, AnalisisIA
from blueprints.creacion_sentencias.service import analizar_documentos_sentencia
from blueprints.creacion_sentencias.document_generator import generar_documento


@creacion_sentencias_bp.route('/creador_sentencias', methods=['GET', 'POST'])
def creador_sentencias():
    if request.method == 'POST':
        archivo_demanda = request.files.get('pdf_demanda')
        archivo_contestacion = request.files.get('pdf_contestacion')
        archivo_fiscalia = request.files.get('pdf_fiscalia')

        if not archivo_demanda or not archivo_demanda.filename:
            flash("Debés subir la demanda (PDF).", "warning")
            return redirect(url_for('creacion_sentencias.creador_sentencias'))

        if not archivo_contestacion or not archivo_contestacion.filename:
            flash("Debés subir la contestación de ANSES (PDF).", "warning")
            return redirect(url_for('creacion_sentencias.creador_sentencias'))

        try:
            analisis = analizar_documentos_sentencia(
                archivo_demanda, archivo_contestacion, archivo_fiscalia
            )
        except Exception as e:
            print(f"[Sentencias] Error analizando documentos: {e}")
            import traceback
            traceback.print_exc()
            flash(f"Error al procesar los documentos: {str(e)}", "danger")
            analisis = AnalisisIA()

        return render_template(
            'creacion_sentencias/formulario.html',
            analisis=analisis,
            checkpoints=CHECKPOINTS_DISPONIBLES,
        )

    return render_template('creacion_sentencias/index.html')


@creacion_sentencias_bp.route('/creador_sentencias/resultado', methods=['POST'])
@login_required
def resultado_sentencia():
    try:
        datos = DatosSentencia.from_form(request.form)
        archivo_path = generar_documento(datos)

        nombre_archivo = f"Sentencia_{datos.nombre_caratula or 'documento'}.docx"

        response = send_file(
            archivo_path,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

        @response.call_on_close
        def cleanup():
            try:
                os.remove(archivo_path)
            except OSError:
                pass

        return response

    except Exception as e:
        print(f"[Sentencias] Error generando documento: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error al generar la sentencia: {str(e)}", "danger")
        return redirect(url_for('creacion_sentencias.creador_sentencias'))
