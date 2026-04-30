"""
Rutas Flask para el sistema de Biblioteca Jurisprudencia

INSTRUCCIONES:
Copia estas rutas y pégalas en tu app.py

Asegúrate de tener estos imports al inicio de app.py:
from services.jurisprudencia.processor import process_sentencia
from models.supabase_connection import supabase_engine
from sqlalchemy import text
"""

# ============================================
# RUTA: Ver listado de sentencias
# ============================================
@app.route('/jurisprudencia')
@login_required
def jurisprudencia():
    """Muestra el listado de sentencias"""
    try:
        with supabase_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    id, caratula, autos, numero_expediente, fecha_sentencia,
                    instancia, organo, juez_vocales_display, voces_display,
                    contenido_sumario, minio_url, processing_status,
                    created_at
                FROM biblioteca_jurisprudencia
                ORDER BY created_at DESC
            """))
            sentencias = [dict(row._mapping) for row in result]

        return render_template('jurisprudencia/listado.html', sentencias=sentencias)

    except Exception as e:
        flash(f"Error cargando sentencias: {str(e)}", "error")
        return redirect(url_for('index'))


# ============================================
# RUTA: Subir nueva sentencia
# ============================================
@app.route('/jurisprudencia/upload', methods=['POST'])
@login_required
def upload_sentencia():
    """Procesa y sube una nueva sentencia"""
    if 'archivo' not in request.files:
        flash("No se envió ningún archivo", "error")
        return redirect(url_for('jurisprudencia'))

    archivo = request.files['archivo']

    if archivo.filename == '':
        flash("Nombre de archivo vacío", "error")
        return redirect(url_for('jurisprudencia'))

    if not archivo.filename.lower().endswith('.pdf'):
        flash("Solo se permiten archivos PDF", "error")
        return redirect(url_for('jurisprudencia'))

    # Procesar sentencia
    result = process_sentencia(archivo, archivo.filename)

    if result['success']:
        flash(f"✅ {result['message']}: {result.get('caratula', 'Sin carátula')}", "success")
        return redirect(url_for('ver_sentencia', id=result['id']))
    else:
        if result.get('duplicate'):
            flash(f"⚠️ {result['error']}", "warning")
            if result.get('existing_id'):
                return redirect(url_for('ver_sentencia', id=result['existing_id']))
        else:
            flash(f"❌ {result.get('error', 'Error desconocido')}", "error")

        return redirect(url_for('jurisprudencia'))


# ============================================
# RUTA: Ver detalle de sentencia
# ============================================
@app.route('/jurisprudencia/<int:id>')
@login_required
def ver_sentencia(id):
    """Muestra el detalle completo de una sentencia"""
    try:
        with supabase_engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM biblioteca_jurisprudencia WHERE id = :id"),
                {"id": id}
            )
            sentencia = result.mappings().first()

        if not sentencia:
            flash("Sentencia no encontrada", "error")
            return redirect(url_for('jurisprudencia'))

        return render_template('jurisprudencia/detalle.html', sentencia=dict(sentencia))

    except Exception as e:
        flash(f"Error cargando sentencia: {str(e)}", "error")
        return redirect(url_for('jurisprudencia'))


# ============================================
# RUTA: Editar sentencia
# ============================================
@app.route('/jurisprudencia/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def editar_sentencia(id):
    """Edita los datos de una sentencia"""
    if request.method == 'POST':
        try:
            # Preparar datos del formulario
            data = {
                'id': id,
                'caratula': request.form.get('caratula'),
                'autos': request.form.get('autos'),
                'numero_expediente': request.form.get('numero_expediente'),
                'fecha_sentencia': request.form.get('fecha_sentencia') or None,
                'instancia': request.form.get('instancia'),
                'organo': request.form.get('organo'),
                'contenido_sumario': request.form.get('contenido_sumario'),
                'resumen': request.form.get('resumen'),
                'numero_resolucion': request.form.get('numero_resolucion'),
                'normativa': request.form.get('normativa'),
                'fundamentos': request.form.get('fundamentos'),
                'estado_sentencia': request.form.get('estado_sentencia')
            }

            # Actualizar en BD
            update_query = text("""
                UPDATE biblioteca_jurisprudencia SET
                    caratula = :caratula,
                    autos = :autos,
                    numero_expediente = :numero_expediente,
                    fecha_sentencia = :fecha_sentencia,
                    instancia = :instancia,
                    organo = :organo,
                    contenido_sumario = :contenido_sumario,
                    resumen = :resumen,
                    numero_resolucion = :numero_resolucion,
                    normativa = :normativa,
                    fundamentos = :fundamentos,
                    estado_sentencia = :estado_sentencia
                WHERE id = :id
            """)

            with supabase_engine.begin() as conn:
                conn.execute(update_query, data)

            flash("✅ Sentencia actualizada correctamente", "success")
            return redirect(url_for('ver_sentencia', id=id))

        except Exception as e:
            flash(f"❌ Error actualizando: {str(e)}", "error")
            return redirect(url_for('editar_sentencia', id=id))

    # GET: Mostrar formulario
    try:
        with supabase_engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM biblioteca_jurisprudencia WHERE id = :id"),
                {"id": id}
            )
            sentencia = result.mappings().first()

        if not sentencia:
            flash("Sentencia no encontrada", "error")
            return redirect(url_for('jurisprudencia'))

        return render_template('jurisprudencia/editar.html', sentencia=dict(sentencia))

    except Exception as e:
        flash(f"Error cargando sentencia: {str(e)}", "error")
        return redirect(url_for('jurisprudencia'))


# ============================================
# RUTA: Eliminar sentencia
# ============================================
@app.route('/jurisprudencia/<int:id>/delete', methods=['POST'])
@login_required
def eliminar_sentencia(id):
    """Elimina una sentencia (BD + MinIO)"""
    try:
        # Obtener datos antes de eliminar
        with supabase_engine.connect() as conn:
            result = conn.execute(
                text("SELECT minio_object_name FROM biblioteca_jurisprudencia WHERE id = :id"),
                {"id": id}
            )
            row = result.first()

        if not row:
            flash("Sentencia no encontrada", "error")
            return redirect(url_for('jurisprudencia'))

        minio_object_name = row[0]

        # Eliminar de MinIO
        if minio_object_name:
            from services.minio_client import minio_client
            minio_client.delete_pdf(minio_object_name)

        # Eliminar de BD
        with supabase_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM biblioteca_jurisprudencia WHERE id = :id"),
                {"id": id}
            )

        flash("✅ Sentencia eliminada correctamente", "success")

    except Exception as e:
        flash(f"❌ Error eliminando sentencia: {str(e)}", "error")

    return redirect(url_for('jurisprudencia'))


# ============================================
# RUTA: Callback de n8n (para actualizar status)
# ============================================
@app.route('/api/jurisprudencia/callback/<int:id>', methods=['PUT'])
def jurisprudencia_callback(id):
    """
    Callback que llama n8n cuando termina de generar embeddings
    Actualiza el processing_status a 'ready'
    """
    try:
        data = request.json
        status = data.get('status', 'ready')

        with supabase_engine.begin() as conn:
            conn.execute(
                text("UPDATE biblioteca_jurisprudencia SET processing_status = :status WHERE id = :id"),
                {"status": status, "id": id}
            )

        print(f"📄 Sentencia {id} actualizada a status: {status}")
        return jsonify({"success": True})

    except Exception as e:
        print(f"❌ Error en callback: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# RUTA: Búsqueda RAG (próximamente)
# ============================================
@app.route('/jurisprudencia/buscar', methods=['POST'])
@login_required
def buscar_jurisprudencia():
    """Búsqueda semántica con RAG - TODO: Implementar"""
    query = request.form.get('query', '')

    # TODO: Implementar búsqueda RAG con embeddings
    flash("Búsqueda RAG en desarrollo", "info")
    return redirect(url_for('jurisprudencia'))
