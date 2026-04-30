#!/usr/bin/env python3
"""
Script para conectar a tu PostgreSQL de Dokploy
"""

from sqlalchemy import create_engine, text

# De la imagen veo que tu External Host es:
# postgresql://postgres:xkltlovnqwtjmmzr@76.13.233.143:5432/postgres

# Pero dice "Tenant or user not found", esto significa que usa Supavisor pooler
# Necesitamos usar el Internal Host desde dentro del mismo network de Docker

URLS_TO_TEST = [
    # Opción 1: Usando el nombre del contenedor (si corres desde Flask dentro de Docker)
    ("Contenedor interno", "postgresql://postgres:xkltlovnqwtjmmzr@estudio-toyos-y-espin-database-estudio-ohvquk:5432/postgres"),

    # Opción 2: IP externa directa (lo que mostraste)
    ("IP externa puerto 5432", "postgresql://postgres:xkltlovnqwtjmmzr@76.13.233.143:5432/postgres"),
]

def test_url(name, url):
    """Probar una URL de conexión"""
    print(f"\n🔍 Probando: {name}")
    print(f"   URL: {url[:80]}...")

    try:
        engine = create_engine(url, echo=False, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"   ✅ ¡CONEXIÓN EXITOSA!")
            print(f"   PostgreSQL: {version[:60]}...")

            # Verificar base de datos
            result = conn.execute(text("SELECT current_database()"))
            db = result.scalar()
            print(f"   📊 Base de datos: {db}")

            # Verificar si pgvector está disponible
            result = conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
            ))
            has_pgvector = result.scalar()
            if has_pgvector:
                print(f"   ✅ pgvector disponible para instalar")

                # Verificar si ya está instalada
                result = conn.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                ))
                is_installed = result.scalar()
                if is_installed:
                    print(f"   ✅ pgvector YA ESTÁ INSTALADA")
                else:
                    print(f"   ℹ️  pgvector disponible pero no instalada aún")
            else:
                print(f"   ⚠️  pgvector NO está disponible (necesita instalarse en el contenedor)")

            return url

    except Exception as e:
        error_msg = str(e)
        if "Tenant or user not found" in error_msg:
            print(f"   ❌ Error: Este PostgreSQL usa Supavisor, necesitas el nombre del tenant")
        elif "Connection refused" in error_msg:
            print(f"   ❌ Error: Conexión rechazada")
        elif "timeout" in error_msg.lower():
            print(f"   ❌ Error: Timeout")
        elif "Name or service not known" in error_msg:
            print(f"   ❌ Error: Nombre de host no encontrado (solo funciona dentro de Docker)")
        else:
            print(f"   ❌ Error: {error_msg[:100]}")
        return None

def main():
    print("=" * 80)
    print("🔌 PRUEBA DE CONEXIÓN - PostgreSQL Dokploy")
    print("=" * 80)

    successful_url = None

    for name, url in URLS_TO_TEST:
        result = test_url(name, url)
        if result:
            successful_url = result
            break

    print("\n" + "=" * 80)
    if successful_url:
        print("✅ ¡CONEXIÓN EXITOSA!")
        print("\nGuarda esta URL en tu .env:")
        print(f"\nDATABASE_URL={successful_url}")

        # Guardar en archivo
        with open('.env.database', 'w') as f:
            f.write(f"DATABASE_URL={successful_url}\n")
        print("\n✅ Guardado en .env.database")

        print("\nAhora ejecuta: python setup_database.py")
    else:
        print("❌ NO SE PUDO CONECTAR")
        print("\nProbablemente necesitas ejecutar este script DESDE DENTRO de Docker")
        print("o configurar el acceso externo correctamente en Dokploy.")
    print("=" * 80)

if __name__ == "__main__":
    main()
