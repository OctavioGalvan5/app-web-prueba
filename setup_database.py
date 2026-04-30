#!/usr/bin/env python3
"""
Script de configuración de base de datos para Sistema de Jurisprudencia
Crea la tabla biblioteca_jurisprudencia con soporte para RAG (pgvector)
"""

from sqlalchemy import create_engine, text
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de conexión
# Intenta primero conectarte al contenedor directo (sin pooler)
# Esto evita el problema del tenant

# OPCIÓN 1: Conexión directa al contenedor PostgreSQL (puerto interno)
# Si estás ejecutando desde dentro de Docker, usa la IP interna
POSTGRES_URL = "postgresql://postgres:xkltlovnqwtjmmzr@76.13.233.143:5432/postgres"

# OPCIÓN 2: Si estás fuera de Docker, usa la IP pública con el puerto directo
# Descomenta esta línea si la OPCIÓN 1 falla
# POSTGRES_URL = "postgresql://postgres:xkltlovnqwtjmmzr@76.13.233.143:5432/postgres"

# OPCIÓN 3: Con tenant a través del pooler (solo si las anteriores fallan)
# POSTGRES_URL = "postgresql://postgres.your-tenant-id:xkltlovnqwtjmmzr@76.13.233.143:6543/postgres"

def create_connection():
    """Crear conexión a PostgreSQL"""
    try:
        engine = create_engine(POSTGRES_URL, echo=False)
        return engine
    except Exception as e:
        print(f"❌ Error creando conexión: {e}")
        sys.exit(1)

def test_connection(engine):
    """Probar conexión a PostgreSQL"""
    print("🔍 Probando conexión a PostgreSQL...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Conectado exitosamente!")
            print(f"   PostgreSQL: {version[:80]}...")

            result = conn.execute(text("SELECT current_database()"))
            db = result.scalar()
            print(f"📊 Base de datos: {db}\n")
            return True
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def install_pgvector(engine):
    """Instalar extensión pgvector"""
    print("📦 Instalando extensión pgvector...")
    try:
        with engine.begin() as conn:
            # Verificar si ya está instalada
            result = conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            ))
            exists = result.scalar()

            if exists:
                print("   ℹ️  pgvector ya está instalada")
                return True

            # Instalar
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("   ✅ pgvector instalada correctamente")
            return True

    except Exception as e:
        print(f"   ❌ Error instalando pgvector: {e}")
        print("\n   SOLUCIÓN:")
        print("   1. Conectate al contenedor: docker exec -it <container_name> bash")
        print("   2. Instala pgvector: apt-get update && apt-get install -y postgresql-15-pgvector")
        print("   3. O usa la imagen: pgvector/pgvector:pg15")
        return False

def create_table(engine):
    """Crear tabla biblioteca_jurisprudencia"""
    print("\n📋 Creando tabla biblioteca_jurisprudencia...")

    sql = """
    -- ============================================
    -- TABLA PRINCIPAL
    -- ============================================
    CREATE TABLE IF NOT EXISTS biblioteca_jurisprudencia (
        -- Control
        id BIGSERIAL PRIMARY KEY,
        file_hash VARCHAR(64) UNIQUE NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),

        -- Identificación del Caso
        caratula TEXT,
        autos TEXT,
        numero_expediente VARCHAR(100),
        fecha_sentencia DATE,

        -- Tribunal
        instancia VARCHAR(100),
        organo VARCHAR(200),

        -- Jueces/Vocales (son parte de voces)
        juez_vocales TEXT[],
        juez_vocales_display TEXT,

        -- Voces (Jueces + Palabras Clave)
        voces TEXT[],
        voces_display TEXT,

        -- Contenido
        contenido_sumario TEXT,
        resumen TEXT,
        texto_completo TEXT,

        -- MinIO
        minio_url TEXT,
        minio_bucket VARCHAR(100) DEFAULT 'jurisprudencia',
        minio_object_name VARCHAR(255),

        -- Embeddings para RAG
        embedding vector(3072),

        -- Metadatos
        numero_resolucion VARCHAR(100),
        normativa TEXT,
        fundamentos TEXT,
        estado_sentencia VARCHAR(50),

        -- Estado de procesamiento
        processing_status VARCHAR(20) DEFAULT 'pending' -- pending, processing, ready, error
    );
    """

    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
            print("   ✅ Tabla creada exitosamente")
            return True
    except Exception as e:
        print(f"   ❌ Error creando tabla: {e}")
        return False

def create_indexes(engine):
    """Crear índices para optimizar búsquedas"""
    print("\n🔍 Creando índices...")

    indexes = [
        # Índices básicos
        ("idx_fecha_sentencia", "CREATE INDEX IF NOT EXISTS idx_fecha_sentencia ON biblioteca_jurisprudencia(fecha_sentencia DESC)"),
        ("idx_instancia", "CREATE INDEX IF NOT EXISTS idx_instancia ON biblioteca_jurisprudencia(instancia)"),
        ("idx_organo", "CREATE INDEX IF NOT EXISTS idx_organo ON biblioteca_jurisprudencia(organo)"),
        ("idx_file_hash", "CREATE INDEX IF NOT EXISTS idx_file_hash ON biblioteca_jurisprudencia(file_hash)"),
        ("idx_processing_status", "CREATE INDEX IF NOT EXISTS idx_processing_status ON biblioteca_jurisprudencia(processing_status)"),

        # Índices GIN para arrays
        ("idx_juez_vocales_gin", "CREATE INDEX IF NOT EXISTS idx_juez_vocales_gin ON biblioteca_jurisprudencia USING gin(juez_vocales)"),
        ("idx_voces_gin", "CREATE INDEX IF NOT EXISTS idx_voces_gin ON biblioteca_jurisprudencia USING gin(voces)"),

        # Full-text search en español
        ("idx_fulltext_es", """
            CREATE INDEX IF NOT EXISTS idx_fulltext_es ON biblioteca_jurisprudencia
            USING gin(to_tsvector('spanish',
                coalesce(caratula, '') || ' ' ||
                coalesce(autos, '') || ' ' ||
                coalesce(contenido_sumario, '') || ' ' ||
                coalesce(resumen, '')
            ))
        """),

        # Índice compuesto
        ("idx_instancia_fecha", "CREATE INDEX IF NOT EXISTS idx_instancia_fecha ON biblioteca_jurisprudencia(instancia, fecha_sentencia DESC)")
    ]

    created = 0
    for index_name, sql in indexes:
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
                print(f"   ✅ {index_name}")
                created += 1
        except Exception as e:
            print(f"   ⚠️  {index_name}: {str(e)[:60]}...")

    print(f"\n   📊 {created}/{len(indexes)} índices creados")
    return True

def create_search_function(engine):
    """Crear función de búsqueda RAG"""
    print("\n🔎 Creando función de búsqueda RAG...")

    sql = """
    CREATE OR REPLACE FUNCTION search_jurisprudencia(
        query_embedding vector(3072),
        match_threshold float DEFAULT 0.3,
        match_count int DEFAULT 20,
        filter_juez text DEFAULT NULL,
        filter_voces text[] DEFAULT NULL,
        filter_instancia text DEFAULT NULL,
        filter_organo text DEFAULT NULL,
        filter_fecha_desde date DEFAULT NULL,
        filter_fecha_hasta date DEFAULT NULL
    )
    RETURNS TABLE (
        id bigint,
        caratula text,
        autos text,
        numero_expediente varchar,
        fecha_sentencia date,
        instancia varchar,
        organo varchar,
        juez_vocales_display text,
        voces_display text,
        contenido_sumario text,
        resumen text,
        minio_url text,
        similarity float
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RETURN QUERY
        SELECT
            bj.id,
            bj.caratula,
            bj.autos,
            bj.numero_expediente,
            bj.fecha_sentencia,
            bj.instancia,
            bj.organo,
            bj.juez_vocales_display,
            bj.voces_display,
            bj.contenido_sumario,
            bj.resumen,
            bj.minio_url,
            1 - (bj.embedding <=> query_embedding) AS similarity
        FROM biblioteca_jurisprudencia bj
        WHERE
            bj.processing_status = 'ready'
            AND bj.embedding IS NOT NULL
            AND (1 - (bj.embedding <=> query_embedding)) > match_threshold
            AND (filter_juez IS NULL OR filter_juez = ANY(bj.juez_vocales))
            AND (filter_voces IS NULL OR bj.voces && filter_voces)
            AND (filter_instancia IS NULL OR bj.instancia = filter_instancia)
            AND (filter_organo IS NULL OR bj.organo ILIKE '%' || filter_organo || '%')
            AND (filter_fecha_desde IS NULL OR bj.fecha_sentencia >= filter_fecha_desde)
            AND (filter_fecha_hasta IS NULL OR bj.fecha_sentencia <= filter_fecha_hasta)
        ORDER BY similarity DESC
        LIMIT match_count;
    END;
    $$;
    """

    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
            print("   ✅ Función search_jurisprudencia creada")
            return True
    except Exception as e:
        print(f"   ❌ Error creando función: {e}")
        return False

def create_trigger(engine):
    """Crear trigger para updated_at"""
    print("\n⚡ Creando trigger para updated_at...")

    sql = """
    -- Función del trigger
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    -- Drop trigger si existe
    DROP TRIGGER IF EXISTS update_biblioteca_jurisprudencia_updated_at ON biblioteca_jurisprudencia;

    -- Crear trigger
    CREATE TRIGGER update_biblioteca_jurisprudencia_updated_at
    BEFORE UPDATE ON biblioteca_jurisprudencia
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """

    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
            print("   ✅ Trigger creado exitosamente")
            return True
    except Exception as e:
        print(f"   ❌ Error creando trigger: {e}")
        return False

def verify_installation(engine):
    """Verificar que todo se instaló correctamente"""
    print("\n✅ VERIFICACIÓN FINAL")
    print("=" * 50)

    checks = []

    try:
        with engine.connect() as conn:
            # 1. Verificar extensión
            result = conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            ))
            has_vector = result.scalar()
            checks.append(("Extensión pgvector", has_vector))

            # 2. Verificar tabla
            result = conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'biblioteca_jurisprudencia')"
            ))
            has_table = result.scalar()
            checks.append(("Tabla biblioteca_jurisprudencia", has_table))

            if has_table:
                # 3. Contar columnas
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'biblioteca_jurisprudencia'"
                ))
                col_count = result.scalar()
                checks.append((f"Columnas en tabla ({col_count})", col_count > 20))

                # 4. Verificar columna embedding
                result = conn.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'biblioteca_jurisprudencia' AND column_name = 'embedding')"
                ))
                has_embedding = result.scalar()
                checks.append(("Columna embedding", has_embedding))

                # 5. Contar índices
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'biblioteca_jurisprudencia'"
                ))
                index_count = result.scalar()
                checks.append((f"Índices ({index_count})", index_count >= 5))

                # 6. Verificar función
                result = conn.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'search_jurisprudencia')"
                ))
                has_function = result.scalar()
                checks.append(("Función search_jurisprudencia", has_function))

                # 7. Contar registros
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM biblioteca_jurisprudencia"
                ))
                record_count = result.scalar()
                checks.append((f"Registros actuales", True))
                print(f"\n📄 Registros en tabla: {record_count}")

            # Imprimir resultados
            print()
            all_ok = True
            for check_name, status in checks:
                icon = "✅" if status else "❌"
                print(f"{icon} {check_name}")
                if not status:
                    all_ok = False

            return all_ok

    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return False

def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 CONFIGURACIÓN DE BASE DE DATOS - JURISPRUDENCIA")
    print("=" * 60)
    print()

    # 1. Crear conexión
    engine = create_connection()

    # 2. Probar conexión
    if not test_connection(engine):
        print("\n❌ No se pudo conectar a PostgreSQL")
        sys.exit(1)

    # 3. Instalar pgvector
    if not install_pgvector(engine):
        print("\n⚠️  ADVERTENCIA: pgvector no está instalada")
        print("   El sistema funcionará pero sin búsqueda semántica (RAG)")
        response = input("\n¿Continuar de todas formas? (s/n): ")
        if response.lower() != 's':
            sys.exit(1)

    # 4. Crear tabla
    if not create_table(engine):
        print("\n❌ Error crítico creando tabla")
        sys.exit(1)

    # 5. Crear índices
    create_indexes(engine)

    # 6. Crear función de búsqueda
    create_search_function(engine)

    # 7. Crear trigger
    create_trigger(engine)

    # 8. Verificar
    print()
    success = verify_installation(engine)

    print("\n" + "=" * 60)
    if success:
        print("✅ ¡INSTALACIÓN COMPLETADA EXITOSAMENTE!")
        print("\nPróximos pasos:")
        print("1. Configura el archivo .env con DATABASE_URL")
        print("2. Configura MinIO para almacenar PDFs")
        print("3. Configura n8n para procesamiento con IA")
        print("4. ¡Empieza a subir sentencias!")
    else:
        print("⚠️  INSTALACIÓN COMPLETADA CON ADVERTENCIAS")
        print("Revisa los errores anteriores")
    print("=" * 60)

if __name__ == "__main__":
    main()
