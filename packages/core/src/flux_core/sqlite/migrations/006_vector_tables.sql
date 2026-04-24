-- Vector embeddings stored as sqlite-vec vec0 virtual tables inside flux.db.
-- Replaces the separate zvec store at /data/zvec/. Dimension baked in at 384
-- to match fastembed's all-MiniLM-L6-v2. Swapping the embedding model
-- requires a new migration that rebuilds these tables.

CREATE VIRTUAL TABLE IF NOT EXISTS vec_transaction_embeddings USING vec0(
    id TEXT PRIMARY KEY,
    embedding float[384],
    user_id TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS vec_memory_embeddings USING vec0(
    id TEXT PRIMARY KEY,
    embedding float[384],
    user_id TEXT
);
