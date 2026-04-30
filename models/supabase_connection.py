"""
Conexión a Supabase PostgreSQL para Biblioteca Jurisprudencia
"""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv

load_dotenv()

# URL de conexión a Supabase
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL no está definida en .env")

# Engine de SQLAlchemy
supabase_engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False
)

def test_supabase_connection():
    """Probar conexión a Supabase"""
    try:
        with supabase_engine.connect() as conn:
            # Verificar conexión
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Conectado a Supabase PostgreSQL")
            print(f"   Version: {version[:80]}...")

            # Verificar base de datos
            result = conn.execute(text("SELECT current_database()"))
            db = result.scalar()
            print(f"📊 Base de datos: {db}")

            # Verificar pgvector
            result = conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            ))
            has_vector = result.scalar()
            if has_vector:
                print("✅ Extensión pgvector instalada")
            else:
                print("❌ pgvector NO instalada")
                return False

            # Verificar tabla
            result = conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE tablename = 'biblioteca_jurisprudencia')"
            ))
            has_table = result.scalar()
            if has_table:
                print("✅ Tabla biblioteca_jurisprudencia existe")

                # Contar registros
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM biblioteca_jurisprudencia"
                ))
                count = result.scalar()
                print(f"📄 Registros actuales: {count}")
            else:
                print("❌ Tabla biblioteca_jurisprudencia NO existe")
                print("   Ejecuta el SQL en Supabase SQL Editor")
                return False

            return True

    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testeando conexión a Supabase...\n")
    success = test_supabase_connection()
    if success:
        print("\n✅ Todo configurado correctamente!")
    else:
        print("\n❌ Hay problemas. Revisa la configuración.")
