# 📚 Sistema de Biblioteca Jurisprudencia

## ✅ ¿Qué se ha creado?

### **Archivos nuevos:**

1. **`models/supabase_connection.py`** - Conexión a Supabase PostgreSQL
2. **`services/minio_client.py`** - Cliente para almacenar PDFs en MinIO
3. **`services/jurisprudencia/gpt4_analyzer.py`** - Análisis de sentencias con GPT-4 y GPT-4 Vision
4. **`services/jurisprudencia/processor.py`** - Procesador principal (orquesta todo)
5. **`routes_jurisprudencia.py`** - Rutas Flask listas para copiar

### **Base de datos:**
- ✅ Tabla `biblioteca_jurisprudencia` creada en Supabase
- ✅ 11 índices para búsqueda optimizada
- ✅ Función `search_jurisprudencia()` para RAG
- ✅ Triggers automáticos

---

## 🚀 Pasos para activar el sistema

### **PASO 1: Instalar dependencias**

```bash
pip install psycopg2-binary pgvector minio openai requests
```

O instala todo:

```bash
pip install -r requirements.txt
```

### **PASO 2: Configurar .env**

Agrega estas variables a tu archivo `.env`:

```bash
# SUPABASE / POSTGRESQL
DATABASE_URL=postgresql://postgres.your-tenant-id:0usai6cmqoz6exuxh1vzo16n7ncc6jbq@172.17.0.1:6543/postgres

# OPENAI (para GPT-4)
OPENAI_API_KEY=sk-proj-TU_KEY_AQUI

# MINIO (Storage de PDFs)
MINIO_ENDPOINT=76.13.233.143:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=jurisprudencia
MINIO_USE_SSL=false

# N8N (opcional, para vectorización)
N8N_WEBHOOK_URL=https://n8n.estudiotye.com/webhook
N8N_VECTORIZE_ENDPOINT=${N8N_WEBHOOK_URL}/jurisprudencia-vectorize

# FLASK APP URL
FLASK_APP_URL=https://app.estudiotye.com
```

### **PASO 3: Configurar MinIO**

Debes tener MinIO corriendo. Si no lo tienes:

#### Opción A: Docker en Dokploy

Crea un nuevo servicio Docker con esta imagen:

```yaml
image: minio/minio:latest
command: server /data --console-address ":9001"
ports:
  - "9000:9000"
  - "9001:9001"
environment:
  MINIO_ROOT_USER: minioadmin
  MINIO_ROOT_PASSWORD: minioadmin
```

#### Opción B: Probar conexión

```bash
python services/minio_client.py
```

### **PASO 4: Agregar rutas a app.py**

Abre `app.py` y agrega al inicio (después de los otros imports):

```python
# Imports para Jurisprudencia
from services.jurisprudencia.processor import process_sentencia
from models.supabase_connection import supabase_engine
```

Luego copia **TODO el contenido** de `routes_jurisprudencia.py` y pégalo en tu `app.py` (antes del `if __name__ == "__main__"`).

### **PASO 5: Crear carpeta de templates**

Crea esta estructura:

```
templates/
  jurisprudencia/
    listado.html       (lo crearemos después)
    detalle.html       (lo crearemos después)
    editar.html        (lo crearemos después)
```

Por ahora, puedes usar templates simples o los templates existentes de `base_datos_casos` como base.

### **PASO 6: Probar conexiones**

```bash
# Probar Supabase
python models/supabase_connection.py

# Probar MinIO
python services/minio_client.py
```

---

## 📖 ¿Cómo funciona?

### **Flujo completo al subir una sentencia:**

```
1. Usuario sube PDF
   ↓
2. Se calcula hash SHA256 (prevenir duplicados)
   ↓
3. GPT-4 Vision extrae jueces de última página
   ↓
4. GPT-4 analiza el texto completo y extrae:
   - Carátula, autos, expediente
   - Fecha, instancia, órgano
   - Jueces/vocales
   - Palabras clave (voces)
   - Resumen, normativa, fundamentos
   ↓
5. PDF se sube a MinIO
   ↓
6. Datos se guardan en Supabase (status: pending)
   ↓
7. (Opcional) n8n genera embeddings para RAG
   ↓
8. Status cambia a "ready"
```

### **Búsqueda por voces:**

Puedes buscar por **cualquier juez** o **cualquier palabra clave**:

```sql
-- Buscar sentencias del Dr. Pérez
SELECT * FROM biblioteca_jurisprudencia
WHERE 'Dr. Pérez' = ANY(juez_vocales);

-- Buscar por palabra clave "movilidad"
SELECT * FROM biblioteca_jurisprudencia
WHERE 'movilidad' = ANY(voces);

-- Buscar por múltiples palabras
SELECT * FROM biblioteca_jurisprudencia
WHERE voces && ARRAY['movilidad', 'PBU', 'tope'];
```

---

## 🔗 Endpoints disponibles

Una vez agregues las rutas a `app.py`:

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/jurisprudencia` | GET | Listado de sentencias |
| `/jurisprudencia/upload` | POST | Subir nueva sentencia |
| `/jurisprudencia/<id>` | GET | Ver detalle |
| `/jurisprudencia/<id>/edit` | GET/POST | Editar sentencia |
| `/jurisprudencia/<id>/delete` | POST | Eliminar sentencia |
| `/api/jurisprudencia/callback/<id>` | PUT | Callback de n8n |

---

## 🎯 Próximos pasos (TODO)

### **1. Crear templates HTML**

Necesitas crear los templates en `templates/jurisprudencia/`:
- `listado.html` - Lista de sentencias (tabla con filtros)
- `detalle.html` - Vista completa de una sentencia
- `editar.html` - Formulario de edición

Puedes basarte en los templates existentes de `base_datos_casos`.

### **2. Implementar búsqueda RAG**

Falta implementar la búsqueda semántica con embeddings. Esto requiere:
- Generar embeddings con OpenAI
- Usar la función `search_jurisprudencia()` de PostgreSQL
- Crear interfaz de búsqueda con filtros

### **3. Adaptar flujo n8n**

Si quieres vectorización automática, necesitas:
- Crear flujo n8n similar al `RAG Vectorizer - MinIO (3).json`
- Configurar webhook que reciba los datos
- Generar embeddings con OpenAI
- Actualizar status a "ready"

---

## 🧪 Pruebas

### **Probar análisis de PDF:**

```python
from services.jurisprudencia.gpt4_analyzer import gpt4_analyzer

# Abrir PDF
with open('sentencia.pdf', 'rb') as f:
    resultado = gpt4_analyzer.process_pdf_complete(f)
    print(resultado)
```

### **Probar procesamiento completo:**

```python
from services.jurisprudencia.processor import process_sentencia

# Subir sentencia
with open('sentencia.pdf', 'rb') as f:
    from werkzeug.datastructures import FileStorage
    file = FileStorage(f, filename='sentencia.pdf')
    resultado = process_sentencia(file, 'sentencia.pdf')
    print(resultado)
```

---

## ❓ Preguntas frecuentes

**P: ¿Necesito MinIO obligatoriamente?**
R: Sí, es donde se almacenan los PDFs. Pero puedes usar Google Drive temporalmente si prefieres.

**P: ¿Cuánto cuesta usar GPT-4?**
R: Aprox $0.01-0.03 por sentencia (depende del tamaño del PDF).

**P: ¿Puedo cambiar a Gemini en lugar de GPT-4?**
R: Sí, solo modifica `gpt4_analyzer.py` para usar Gemini.

**P: ¿Cómo busco por múltiples voces?**
R: Usa el operador `&&` en PostgreSQL para buscar por cualquiera de las voces.

---

## 📞 Soporte

Si tienes dudas o errores, revisa:
1. Logs de Flask
2. Logs de Supabase (SQL Editor)
3. Logs de MinIO
4. Verifica que el `.env` esté bien configurado

---

**¡Sistema listo para usar!** 🎉

Solo falta:
1. Agregar las rutas a `app.py`
2. Crear los templates HTML
3. Configurar MinIO

¿Necesitas ayuda con algo específico?
