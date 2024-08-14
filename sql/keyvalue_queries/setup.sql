CREATE TABLE IF NOT EXISTS kv_table (
    key TEXT UNIQUE,
    value JSONB
);