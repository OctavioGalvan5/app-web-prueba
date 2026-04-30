# Guía de Configuración de Flujos n8n para Jurisprudencia

## Resumen
Esta guía te ayudará a importar y configurar los dos flujos n8n necesarios para el sistema de jurisprudencia:
1. **Jurisprudencia_Vectorizer.json** - Vectoriza sentencias y las guarda en `jurisprudencia_vectors`
2. **Jurisprudencia_Chatbot.json** - Chatbot especializado en jurisprudencia con RAG

## Prerrequisitos

### 1. SQL: Crear tabla de vectores
Primero ejecuta este SQL en tu Supabase para crear la tabla separada de vectores:

```sql
-- Crear tabla de vectores para jurisprudencia (SEPARADA del chatbot)
CREATE TABLE IF NOT EXISTS jurisprudencia_vectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sentencia_id BIGINT REFERENCES biblioteca_jurisprudencia(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(3072),  -- text-embedding-3-large
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice HNSW para búsqueda de similitud vectorial
CREATE INDEX IF NOT EXISTS idx_jurisprudencia_vectors_embedding
ON jurisprudencia_vectors
USING hnsw (embedding vector_cosine_ops);

-- Índice para sentencia_id (buscar chunks de una sentencia)
CREATE INDEX IF NOT EXISTS idx_jurisprudencia_vectors_sentencia
ON jurisprudencia_vectors(sentencia_id);

-- Verificar que la tabla existe
SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE tablename = 'jurisprudencia_vectors';

-- Verificar que tiene la columna vector con dimensión correcta
SELECT
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_name = 'jurisprudencia_vectors';
```

### 2. Verificar extensión pgvector
```sql
-- Verificar que pgvector está instalado
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Si no está, instalarlo (en Supabase debería estar por defecto)
CREATE EXTENSION IF NOT EXISTS vector;
```

## Paso 1: Crear Credenciales en n8n

### Credencial de PostgreSQL (Supabase)

1. Ve a **Settings → Credentials** en n8n
2. Click en **Add Credential**
3. Busca **Postgres**
4. Completa los campos:
   - **Name**: `Postgres account` (o el nombre que prefieras)
   - **Host**: Tu host de Supabase (ej: `db.your-project.supabase.co`)
   - **Database**: `postgres`
   - **User**: `postgres`
   - **Password**: Tu contraseña de Supabase
   - **Port**: `5432` (o `6543` para pooler)
   - **SSL**: `allow` o `require` (según tu configuración)
5. Click en **Save**
6. **Copia el ID de la credencial** que aparece en la URL o en la lista

### Credencial de OpenAI

1. En **Settings → Credentials**, click en **Add Credential**
2. Busca **OpenAI**
3. Completa:
   - **Name**: `OpenAi account`
   - **API Key**: Tu clave de OpenAI (empieza con `sk-`)
4. Click en **Save**
5. **Copia el ID de la credencial**

## Paso 2: Importar los Flujos

### Importar Jurisprudencia_Vectorizer.json

1. Ve a **Workflows** en n8n
2. Click en el botón **Import from File**
3. Selecciona `n8n_flows/Jurisprudencia_Vectorizer.json`
4. El flujo se importará como **"Jurisprudencia Vectorizer"**

### Importar Jurisprudencia_Chatbot.json

1. Ve a **Workflows** en n8n
2. Click en **Import from File**
3. Selecciona `n8n_flows/Jurisprudencia_Chatbot.json`
4. El flujo se importará como **"Chatbot Jurisprudencia"**

## Paso 3: Configurar Credenciales en los Flujos

### En Jurisprudencia_Vectorizer

Abre el flujo y actualiza estos nodos:

#### Nodos con PostgreSQL:
- **Delete Old Vectors**
- **Update Status Ready**
- **Delete Vectors**

Para cada uno:
1. Click en el nodo
2. En la sección **Credential to connect with**, click en el dropdown
3. Selecciona la credencial de Postgres que creaste

#### Nodos con OpenAI:
- **Embeddings OpenAI**

1. Click en el nodo
2. Selecciona la credencial de OpenAI

### En Jurisprudencia_Chatbot

Abre el flujo y actualiza estos nodos:

#### Nodos con PostgreSQL:
- **Postgres Chat Memory**
- **PGVector Retriever**

Para cada uno:
1. Click en el nodo
2. Selecciona la credencial de Postgres

#### Nodos con OpenAI:
- **OpenAI Chat Model**
- **Embeddings OpenAI**

Para cada uno:
1. Click en el nodo
2. Selecciona la credencial de OpenAI

## Paso 4: Obtener URLs de Webhooks

### Webhook del Vectorizador

1. Abre el flujo **Jurisprudencia_Vectorizer**
2. Click en el nodo **Webhook Vectorize**
3. En el panel derecho, verás la **Production URL**
4. Copia esta URL (será algo como: `https://tu-n8n.com/webhook/jurisprudencia-vectorize`)
5. Esta URL va en tu `.env` como:
   ```
   N8N_VECTORIZE_WEBHOOK=https://tu-n8n.com/webhook/jurisprudencia-vectorize
   ```

### Webhook del Chatbot

1. Abre el flujo **Chatbot Jurisprudencia**
2. Click en el nodo **Webhook Chat**
3. Copia la **Production URL** (será: `https://tu-n8n.com/webhook/jurisprudencia-chat`)
4. Esta URL se usará en tu frontend para enviar queries al chatbot

### Webhook de Eliminación

1. En el flujo **Jurisprudencia_Vectorizer**
2. Click en el nodo **Webhook Delete**
3. Copia la **Production URL** (será: `https://tu-n8n.com/webhook/jurisprudencia-delete`)
4. Se usa cuando eliminas una sentencia

## Paso 5: Activar los Flujos

1. Abre cada flujo
2. En la esquina superior derecha, cambia el toggle de **Inactive** a **Active**
3. Verifica que no haya errores en ningún nodo (deben tener checkmarks verdes)

## Paso 6: Configurar Variables de Entorno en Flask

Actualiza tu `.env`:

```bash
# URLs de n8n
N8N_VECTORIZE_WEBHOOK=https://tu-n8n.com/webhook/jurisprudencia-vectorize
N8N_DELETE_WEBHOOK=https://tu-n8n.com/webhook/jurisprudencia-delete
N8N_CHAT_WEBHOOK=https://tu-n8n.com/webhook/jurisprudencia-chat

# OpenAI (para análisis en Flask)
OPENAI_API_KEY=sk-tu-clave-aqui

# MinIO
MINIO_ENDPOINT=tu-minio-endpoint:9000
MINIO_ACCESS_KEY=tu-access-key
MINIO_SECRET_KEY=tu-secret-key
MINIO_BUCKET=jurisprudencia
MINIO_SECURE=False

# Supabase/PostgreSQL
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
```

## Paso 7: Probar el Sistema

### Test 1: Vectorización

```bash
# Desde terminal o Postman
curl -X POST https://tu-n8n.com/webhook/jurisprudencia-vectorize \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "1",
    "file_hash": "abc123",
    "minio_url": "http://minio:9000/jurisprudencia/test.pdf",
    "texto": "Esta es una sentencia de prueba sobre seguridad social...",
    "callback_url": "http://tu-flask:5000/api/jurisprudencia/callback/1"
  }'
```

Deberías recibir:
```json
{
  "success": true,
  "message": "Sentencia vectorizada",
  "sentencia_id": "1"
}
```

### Test 2: Chatbot

```bash
curl -X POST https://tu-n8n.com/webhook/jurisprudencia-chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Qué dice la jurisprudencia sobre jubilaciones anticipadas?",
    "user_id": "usuario123"
  }'
```

Deberías recibir:
```json
{
  "success": true,
  "response": "Encontré 3 sentencias relevantes sobre jubilaciones anticipadas...",
  "user_id": "usuario123"
}
```

### Test 3: Eliminar vectores

```bash
curl -X POST https://tu-n8n.com/webhook/jurisprudencia-delete \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "1"
  }'
```

## Verificación en Base de Datos

### Ver vectores creados
```sql
SELECT
    id,
    sentencia_id,
    LEFT(content, 100) as content_preview,
    metadata,
    created_at
FROM jurisprudencia_vectors
ORDER BY created_at DESC
LIMIT 10;
```

### Contar chunks por sentencia
```sql
SELECT
    sentencia_id,
    COUNT(*) as total_chunks
FROM jurisprudencia_vectors
GROUP BY sentencia_id;
```

### Verificar dimensión de embeddings
```sql
SELECT
    id,
    sentencia_id,
    vector_dims(embedding) as dimension
FROM jurisprudencia_vectors
LIMIT 5;
```

## Arquitectura del Flujo

### Flujo de Vectorización
```
Flask Upload → GPT-4 Análisis → MinIO → Save DB (status: pending)
                                               ↓
                                    Webhook n8n Vectorize
                                               ↓
                              Delete Old Vectors (si existen)
                                               ↓
                                    Text Chunker (JS)
                                               ↓
                              OpenAI Embeddings (3072 dims)
                                               ↓
                              Save to jurisprudencia_vectors
                                               ↓
                              Update status → 'ready'
                                               ↓
                                    Callback Flask
```

### Flujo del Chatbot
```
User Query → Webhook Chat → AI Agent (GPT-4o)
                                ↓
                    PGVector Retriever (jurisprudencia_vectors)
                                ↓
                    Similarity Search (top 5 results)
                                ↓
                    AI Agent synthesizes response
                                ↓
                    Return JSON response
```

## Troubleshooting

### Error: "Table jurisprudencia_vectors does not exist"
- Ejecuta el SQL del Paso 1 para crear la tabla

### Error: "Credential not found"
- Verifica que las credenciales estén correctamente asignadas en todos los nodos
- Revisa que las credenciales de Postgres y OpenAI estén guardadas

### Error: "Connection refused" en PostgreSQL
- Verifica que el host y puerto sean correctos
- Asegúrate de estar usando el pooler correcto (puerto 5432 o 6543)
- Revisa los firewall rules en Supabase

### Error: "Embedding dimension mismatch"
- Verifica que la tabla use `vector(3072)` (no 1536)
- Asegúrate de usar `text-embedding-3-large` en el nodo de embeddings

### Webhook no responde
- Verifica que el flujo esté **Activado** (Active)
- Revisa los logs de ejecución en n8n (Executions)
- Asegúrate de usar la **Production URL**, no Test URL

## Monitoreo

### Ver ejecuciones en n8n
1. Ve a **Executions** en el menú lateral
2. Filtra por workflow (Vectorizer o Chatbot)
3. Click en cada ejecución para ver detalles

### Logs útiles
- **Success**: ✅ verde
- **Error**: ❌ rojo
- Click en cada nodo para ver input/output

### Métricas importantes
- Tiempo de vectorización por documento
- Número de chunks generados
- Tiempo de respuesta del chatbot
- Precisión de las búsquedas (feedback manual)

## Diferencias con el Chatbot General

| Aspecto | Chatbot General | Chatbot Jurisprudencia |
|---------|----------------|------------------------|
| Tabla de vectores | `documents_pg` | `jurisprudencia_vectors` |
| Tipo de documentos | PDFs generales | Sentencias judiciales |
| System prompt | General | Experto legal |
| Herramientas | Búsqueda general | `buscar_jurisprudencia` |
| Metadata | Básica | Tribunal, fecha, jueces |
| Webhook | `/webhook/chat` | `/webhook/jurisprudencia-chat` |

## Mantenimiento

### Limpiar vectores huérfanos
```sql
-- Eliminar vectores de sentencias que ya no existen
DELETE FROM jurisprudencia_vectors
WHERE sentencia_id NOT IN (
    SELECT id FROM biblioteca_jurisprudencia
);
```

### Re-vectorizar todas las sentencias
```bash
# Script Python para re-procesar todo
python scripts/re_vectorize_all.py
```

### Backup de vectores
```sql
-- Exportar vectores
COPY jurisprudencia_vectors TO '/tmp/jurisprudencia_vectors_backup.csv' CSV HEADER;
```

## Próximos Pasos

1. ✅ Crear tabla `jurisprudencia_vectors`
2. ✅ Importar flujos n8n
3. ✅ Configurar credenciales
4. ✅ Activar flujos
5. ⏳ Crear interfaz de chat en frontend
6. ⏳ Agregar filtros por tribunal/fecha
7. ⏳ Implementar feedback de resultados
8. ⏳ Optimizar chunks para mejor precisión

## Soporte

Si encuentras problemas:
1. Revisa los logs de n8n (Executions)
2. Verifica las credenciales
3. Comprueba que la tabla existe en PostgreSQL
4. Revisa las URLs de webhooks en `.env`
5. Consulta los logs de Flask para el callback
