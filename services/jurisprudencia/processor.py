"""
Procesador principal de sentencias judiciales
Orquesta: MinIO + GPT-4 + Supabase + n8n
"""

import hashlib
from sqlalchemy import text
from models.supabase_connection import supabase_engine
from services.minio_client import minio_client
from services.jurisprudencia.gpt4_analyzer import gpt4_analyzer
import os
import requests

def calculate_file_hash(file_obj):
    """Calcula hash SHA256 del archivo"""
    file_obj.seek(0)
    hash_obj = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(4096), b""):
        hash_obj.update(chunk)
    file_obj.seek(0)
    return hash_obj.hexdigest()

def file_exists_in_db(file_hash):
    """Verifica si el hash ya existe en la BD"""
    query = text("SELECT id, caratula FROM biblioteca_jurisprudencia WHERE file_hash = :hash")
    with supabase_engine.connect() as conn:
        result = conn.execute(query, {"hash": file_hash})
        row = result.first()
        if row:
            return True, dict(row._mapping)
        return False, None

def save_to_database(data):
    """Guarda sentencia en Supabase"""
    insert_query = text("""
        INSERT INTO biblioteca_jurisprudencia (
            file_hash, caratula, autos, numero_expediente, fecha_sentencia,
            instancia, organo, juez_vocales, juez_vocales_display,
            voces, voces_display, contenido_sumario, resumen, texto_completo,
            minio_url, minio_bucket, minio_object_name,
            numero_resolucion, normativa, fundamentos, estado_sentencia,
            processing_status
        ) VALUES (
            :file_hash, :caratula, :autos, :numero_expediente, :fecha_sentencia,
            :instancia, :organo, :juez_vocales, :juez_vocales_display,
            :voces, :voces_display, :contenido_sumario, :resumen, :texto_completo,
            :minio_url, :minio_bucket, :minio_object_name,
            :numero_resolucion, :normativa, :fundamentos, :estado_sentencia,
            :processing_status
        )
        RETURNING id
    """)

    try:
        with supabase_engine.begin() as conn:
            result = conn.execute(insert_query, data)
            new_id = result.scalar()
            print(f"✅ Sentencia guardada en BD (ID: {new_id})")
            return new_id
    except Exception as e:
        print(f"❌ Error guardando en BD: {e}")
        raise

def process_sentencia(file_obj, filename):
    """
    Proceso completo de una sentencia:
    1. Calcular hash y verificar duplicados
    2. Analizar con GPT-4 (texto + jueces)
    3. Subir PDF a MinIO
    4. Guardar en Supabase (status: pending)
    5. Llamar webhook n8n para generar embeddings
    6. Retornar ID

    Args:
        file_obj: Archivo PDF
        filename: Nombre del archivo

    Returns:
        dict: {success, id, message, error}
    """
    print(f"\n{'='*60}")
    print(f"📄 Procesando: {filename}")
    print(f"{'='*60}")

    try:
        # PASO 1: Calcular hash
        file_hash = calculate_file_hash(file_obj)
        print(f"🔐 Hash calculado: {file_hash[:16]}...")

        # PASO 2: Verificar duplicados
        exists, existing = file_exists_in_db(file_hash)
        if exists:
            return {
                "success": False,
                "error": f"Esta sentencia ya fue subida: {existing.get('caratula', 'Sin carátula')}",
                "duplicate": True,
                "existing_id": existing.get('id')
            }

        # PASO 3: Analizar con GPT-4
        file_obj.seek(0)
        print("\n🤖 Analizando con GPT-4...")
        analisis = gpt4_analyzer.process_pdf_complete(file_obj)

        if 'error' in analisis:
            return {
                "success": False,
                "error": f"Error en análisis: {analisis['error']}"
            }

        # PASO 4: Subir a MinIO
        file_obj.seek(0)
        print("\n☁️  Subiendo a MinIO...")
        minio_url, object_name = minio_client.upload_pdf(file_obj, file_hash, filename)

        # PASO 5: Preparar datos para BD
        # Convertir fecha
        fecha_str = analisis.get('fecha_sentencia')
        fecha_date = None
        if fecha_str:
            try:
                from datetime import datetime
                fecha_date = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except:
                pass

        # Preparar arrays
        jueces = analisis.get('juez_vocales', [])
        voces = analisis.get('voces', [])

        data = {
            'file_hash': file_hash,
            'caratula': analisis.get('caratula'),
            'autos': analisis.get('autos'),
            'numero_expediente': analisis.get('numero_expediente'),
            'fecha_sentencia': fecha_date,
            'instancia': analisis.get('instancia'),
            'organo': analisis.get('organo'),
            'juez_vocales': jueces,
            'juez_vocales_display': ', '.join(jueces) if jueces else None,
            'voces': voces,
            'voces_display': ', '.join(voces) if voces else None,
            'contenido_sumario': analisis.get('contenido_sumario'),
            'resumen': analisis.get('resumen'),
            'texto_completo': analisis.get('texto_completo'),
            'minio_url': minio_url,
            'minio_bucket': minio_client.bucket,
            'minio_object_name': object_name,
            'numero_resolucion': analisis.get('numero_resolucion'),
            'normativa': analisis.get('normativa'),
            'fundamentos': analisis.get('fundamentos'),
            'estado_sentencia': analisis.get('estado_sentencia'),
            'processing_status': 'pending'  # Se actualizará a 'ready' después de vectorizar
        }

        # PASO 6: Guardar en BD
        print("\n💾 Guardando en Supabase...")
        new_id = save_to_database(data)

        # PASO 7: Llamar webhook n8n para vectorizar (opcional)
        n8n_webhook = os.getenv("N8N_VECTORIZE_ENDPOINT")
        if n8n_webhook:
            try:
                print("\n🔗 Llamando webhook n8n para vectorizar...")
                payload = {
                    "document_id": str(new_id),
                    "file_hash": file_hash,
                    "minio_url": minio_url,
                    "texto": analisis.get('texto_completo', '')[:8000],  # Limitar para n8n
                    "callback_url": f"{os.getenv('FLASK_APP_URL', 'http://localhost:5000')}/api/jurisprudencia/callback/{new_id}"
                }
                response = requests.post(n8n_webhook, json=payload, timeout=10)
                response.raise_for_status()
                print("✅ Webhook n8n llamado correctamente")
            except Exception as e:
                print(f"⚠️  Error llamando webhook n8n: {e}")
                # No es crítico, continuar

        print(f"\n{'='*60}")
        print(f"✅ PROCESAMIENTO COMPLETADO (ID: {new_id})")
        print(f"{'='*60}\n")

        return {
            "success": True,
            "id": new_id,
            "file_hash": file_hash,
            "caratula": analisis.get('caratula'),
            "message": "Sentencia procesada exitosamente"
        }

    except Exception as e:
        print(f"\n❌ ERROR EN PROCESAMIENTO: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    print("Procesador de sentencias inicializado")
