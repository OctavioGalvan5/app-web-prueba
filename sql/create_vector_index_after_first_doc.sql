-- ============================================================
-- EJECUTAR DESPUÉS DE CARGAR LA PRIMERA SENTENCIA
-- ============================================================

-- Este SQL crea el índice vectorial IVFFlat que optimiza las búsquedas
-- IMPORTANTE: Necesita al menos 1 documento vectorizado para funcionar correctamente

-- Crear índice vectorial IVFFlat (soporta 3072 dimensiones)
CREATE INDEX IF NOT EXISTS idx_jurisprudencia_vectors_embedding
ON jurisprudencia_vectors
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Verificar que se creó correctamente
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'jurisprudencia_vectors';

-- Ver estadísticas del índice
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'jurisprudencia_vectors';

-- Contar vectores almacenados
SELECT
    COUNT(*) as total_vectores,
    COUNT(DISTINCT sentencia_id) as total_sentencias
FROM jurisprudencia_vectors;
