# Configuración de MinIO para Jurisprudencia

## ¿Qué es MinIO?

MinIO es un servidor de almacenamiento de objetos compatible con S3 (como AWS S3, pero self-hosted). Lo usamos para guardar los PDFs de las sentencias en tu VPS.

## Instalación en Dokploy

### Opción 1: Usando Docker Compose en Dokploy

1. **Crear servicio MinIO en Dokploy**:
   - Ve a tu proyecto en Dokploy
   - Click en **"Add Service"** → **"Docker Compose"**
   - Pega este docker-compose:

```yaml
version: '3.8'

services:
  minio:
    image: minio/minio:latest
    container_name: minio-jurisprudencia
    restart: unless-stopped
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console Web
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: tu-password-seguro-aqui-123
    volumes:
      - minio-data:/data
    command: server /data --console-address ":9001"
    networks:
      - app-network

volumes:
  minio-data:
    driver: local

networks:
  app-network:
    external: true
```

2. **Configurar variables**:
   - Cambia `tu-password-seguro-aqui-123` por una contraseña fuerte
   - Deploy el servicio

### Opción 2: Instalación Manual con Docker

```bash
# En tu VPS
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD=tu-password-seguro \
  -v /opt/minio/data:/data \
  minio/minio server /data --console-address ":9001"
```

## Configuración Inicial

### 1. Acceder a la Consola Web

1. Abre en el navegador: `http://tu-vps-ip:9001`
2. Login con:
   - **Username**: `admin`
   - **Password**: La que configuraste

### 2. Crear Bucket para Jurisprudencia

1. En el menú izquierdo, click en **"Buckets"**
2. Click en **"Create Bucket"**
3. Nombre: `jurisprudencia`
4. Click en **"Create"**

### 3. Crear Access Keys (para Flask)

1. En el menú izquierdo, click en **"Access Keys"**
2. Click en **"Create access key"**
3. Guarda el **Access Key** y **Secret Key** (los necesitarás en Flask)
   - Ejemplo:
     - Access Key: `minioadmin123`
     - Secret Key: `minioadmin456secret`

### 4. Configurar Política del Bucket (opcional - solo si querés acceso público)

Si querés que los PDFs sean accesibles públicamente (NO recomendado para sentencias privadas):

1. Ve a **Buckets** → `jurisprudencia` → **Manage**
2. Tab **"Access Policy"**
3. Selecciona **"Public"** (o dejalo privado)

## Configuración en Flask

### Variables de Entorno (.env)

Agrega estas líneas a tu archivo `.env`:

```bash
# MinIO Configuration
MINIO_ENDPOINT=tu-vps-ip:9000
MINIO_ACCESS_KEY=minioadmin123
MINIO_SECRET_KEY=minioadmin456secret
MINIO_BUCKET=jurisprudencia
MINIO_SECURE=False  # True si usás HTTPS

# Si MinIO está en el mismo servidor (localhost)
# MINIO_ENDPOINT=localhost:9000

# Si usás Dokploy con red interna
# MINIO_ENDPOINT=minio-jurisprudencia:9000
```

### Ejemplo Completo del .env

```bash
# PostgreSQL/Supabase
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres

# OpenAI
OPENAI_API_KEY=sk-tu-clave-aqui

# MinIO
MINIO_ENDPOINT=76.13.233.143:9000
MINIO_ACCESS_KEY=minioadmin123
MINIO_SECRET_KEY=minioadmin456secret
MINIO_BUCKET=jurisprudencia
MINIO_SECURE=False

# n8n Webhooks
N8N_VECTORIZE_WEBHOOK=https://tu-n8n.com/webhook/jurisprudencia-vectorize
N8N_DELETE_WEBHOOK=https://tu-n8n.com/webhook/jurisprudencia-delete
N8N_CHAT_WEBHOOK=https://tu-n8n.com/webhook/jurisprudencia-chat
```

## Verificar que Funciona

### Test desde Python

Crea un archivo `test_minio.py`:

```python
from minio import Minio
import os
from dotenv import load_dotenv

load_dotenv()

# Conectar a MinIO
client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=os.getenv("MINIO_SECURE", "False") == "True"
)

# Verificar que el bucket existe
bucket_name = os.getenv("MINIO_BUCKET")

if client.bucket_exists(bucket_name):
    print(f"✅ Bucket '{bucket_name}' existe!")
else:
    print(f"❌ Bucket '{bucket_name}' NO existe. Creando...")
    client.make_bucket(bucket_name)
    print(f"✅ Bucket '{bucket_name}' creado!")

# Listar objetos (debería estar vacío al principio)
objects = client.list_objects(bucket_name)
print(f"\n📁 Objetos en '{bucket_name}':")
for obj in objects:
    print(f"  - {obj.object_name}")
```

Ejecuta:

```bash
python test_minio.py
```

Deberías ver:
```
✅ Bucket 'jurisprudencia' existe!
📁 Objetos en 'jurisprudencia':
```

## Estructura de Almacenamiento

Los PDFs se guardan con esta estructura:

```
jurisprudencia/
├── AB/
│   ├── CD/
│   │   └── ABCD1234567890.pdf
│   │   └── ABCD9876543210.pdf
├── 12/
│   ├── 34/
│   │   └── 1234ABCDEF5678.pdf
```

- **AB/CD/**: Primeros 4 caracteres del hash (para evitar tener miles de archivos en un solo directorio)
- **ABCD1234567890.pdf**: Hash completo del archivo (SHA256)

## Acceso a los Archivos

### URL de Acceso

Los archivos se acceden mediante:

```
http://tu-vps-ip:9000/jurisprudencia/AB/CD/ABCD1234567890.pdf
```

O si usás pre-signed URLs (URLs temporales):

```python
# En services/minio_client.py ya está implementado
url = minio_client.get_presigned_url(object_name)
# Genera: http://minio:9000/jurisprudencia/AB/CD/ABCD1234.pdf?X-Amz-...
```

## Troubleshooting

### Error: "Connection refused"

**Causa**: No podés conectar a MinIO

**Solución**:
```bash
# Verificar que MinIO está corriendo
docker ps | grep minio

# Ver logs
docker logs minio

# Verificar puertos
netstat -tlnp | grep 9000
```

### Error: "Access Denied"

**Causa**: Credenciales incorrectas

**Solución**:
- Verifica que `MINIO_ACCESS_KEY` y `MINIO_SECRET_KEY` coincidan con los de MinIO
- Recrea las Access Keys en la consola web

### Error: "Bucket does not exist"

**Causa**: El bucket `jurisprudencia` no fue creado

**Solución**:
```bash
# Ejecuta test_minio.py para crearlo automáticamente
python test_minio.py
```

O créalo manualmente en la consola web.

## Seguridad

### 🔒 Recomendaciones:

1. **No uses puertos públicos directamente**: Usa un reverse proxy (Nginx/Traefik) con HTTPS
2. **Usa contraseñas fuertes** para `MINIO_ROOT_PASSWORD`
3. **Mantén las Access Keys secretas** (no las subas a Git)
4. **Usa HTTPS** en producción:
   ```bash
   MINIO_SECURE=True
   MINIO_ENDPOINT=minio.tu-dominio.com:443
   ```

### Configurar HTTPS con Traefik (en Dokploy)

Si Dokploy usa Traefik, agrega estas labels al servicio MinIO:

```yaml
services:
  minio:
    # ... configuración anterior ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.minio-api.rule=Host(`minio-api.tu-dominio.com`)"
      - "traefik.http.routers.minio-api.service=minio-api"
      - "traefik.http.services.minio-api.loadbalancer.server.port=9000"
      - "traefik.http.routers.minio-console.rule=Host(`minio.tu-dominio.com`)"
      - "traefik.http.routers.minio-console.service=minio-console"
      - "traefik.http.services.minio-console.loadbalancer.server.port=9001"
```

## Monitoreo

### Ver espacio usado

En la consola web (http://tu-vps-ip:9001):
- **Dashboard** → **Buckets** → `jurisprudencia` → **Summary**
- Verás: tamaño total, cantidad de objetos, etc.

### Listar archivos desde CLI

```bash
# Instalar mc (MinIO Client)
docker run --rm -it \
  --entrypoint=/bin/sh \
  minio/mc

# Configurar alias
mc alias set myminio http://tu-vps-ip:9000 admin tu-password

# Listar archivos
mc ls myminio/jurisprudencia
```

## Backup

### Exportar todos los PDFs

```bash
# Desde el VPS
docker exec minio \
  mc mirror /data/jurisprudencia /backup/jurisprudencia-$(date +%Y%m%d)
```

### Importar PDFs

```bash
# Subir un directorio completo
mc mirror ./pdfs-locales myminio/jurisprudencia
```

## Integración con Flask

El código ya está listo en `services/minio_client.py`. Solo necesitás configurar las variables de entorno.

### Flujo Completo:

1. **Usuario sube PDF** → Flask recibe archivo
2. **Flask calcula hash** → SHA256 del contenido
3. **Flask sube a MinIO** → `jurisprudencia/AB/CD/ABCD123.pdf`
4. **Flask guarda metadata** → En PostgreSQL con URL de MinIO
5. **n8n vectoriza** → Descarga desde MinIO y procesa

## Resumen de Configuración

| Aspecto | Valor |
|---------|-------|
| Puerto API | 9000 |
| Puerto Console | 9001 |
| Bucket | `jurisprudencia` |
| Endpoint | `tu-vps-ip:9000` |
| Secure | `False` (sin HTTPS) |
| Usuario Root | `admin` |
| Password Root | (tu password) |

¿Dudas sobre la configuración de MinIO?
