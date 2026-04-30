#!/usr/bin/env python3
"""
Script para probar diferentes URLs de conexión a PostgreSQL
"""

from sqlalchemy import create_engine, text

# Lista de URLs a probar
URLS_TO_TEST = [
    # Opción 1: Puerto 5432 directo sin tenant
    ("Puerto 5432 (sin tenant)", "postgresql://postgres:xkltlovnqwtjmmzr@76.13.233.143:5432/postgres"),

    # Opción 2: Puerto 6543 con tenant
    ("Puerto 6543 con tenant", "postgresql://postgres.your-tenant-id:xkltlovnqwtjmmzr@76.13.233.143:6543/postgres"),

    # Opción 3: IP interna con tenant
    ("IP interna 172.17.0.1:6543", "postgresql://postgres.your-tenant-id:xkltlovnqwtjmmzr@172.17.0.1:6543/postgres"),

    # Opción 4: IP interna sin tenant
    ("IP interna 172.17.0.1:5432", "postgresql://postgres:xkltlovnqwtjmmzr@172.17.0.1:5432/postgres"),
]

def test_url(name, url):
    """Probar una URL de conexión"""
    print(f"\n🔍 Probando: {name}")
    print(f"   URL: {url[:60]}...")

    try:
        engine = create_engine(url, echo=False, pool_pre_ping=False)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"   ✅ ¡CONEXIÓN EXITOSA!")
            print(f"   PostgreSQL: {version[:60]}...")

            # Verificar si existe pgvector
            result = conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
            ))
            has_pgvector = result.scalar()
            if has_pgvector:
                print(f"   ✅ pgvector disponible")
            else:
                print(f"   ⚠️  pgvector NO disponible")

            return url

    except Exception as e:
        error_msg = str(e)
        if "Tenant or user not found" in error_msg:
            print(f"   ❌ Error: Tenant o usuario no encontrado")
        elif "Connection refused" in error_msg:
            print(f"   ❌ Error: Conexión rechazada (puerto cerrado o firewall)")
        elif "timeout" in error_msg.lower():
            print(f"   ❌ Error: Timeout (servidor no responde)")
        else:
            print(f"   ❌ Error: {error_msg[:80]}")
        return None

def main():
    print("=" * 70)
    print("🔌 PRUEBA DE CONEXIONES A POSTGRESQL")
    print("=" * 70)

    successful_url = None

    for name, url in URLS_TO_TEST:
        result = test_url(name, url)
        if result:
            successful_url = result
            break

    print("\n" + "=" * 70)
    if successful_url:
        print("✅ CONEXIÓN ENCONTRADA!")
        print("\nUsa esta URL en tu archivo .env y en setup_database.py:")
        print(f"\nDATABASE_URL={successful_url}")
        print("\nAhora puedes ejecutar: python setup_database.py")
    else:
        print("❌ NO SE PUDO CONECTAR CON NINGUNA OPCIÓN")
        print("\nPosibles soluciones:")
        print("1. Verifica que el puerto 5432 o 6543 esté expuesto en Docker")
        print("2. Verifica el tenant ID correcto (puede que no sea 'your-tenant-id')")
        print("3. Verifica que el firewall del VPS permita conexiones")
        print("4. Si estás en el mismo servidor, usa 172.17.0.1 en lugar de la IP pública")
    print("=" * 70)

if __name__ == "__main__":
    main()
