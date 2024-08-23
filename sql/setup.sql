CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    owner_id BIGINT NOT NULL,
    channel_id BIGINT UNIQUE NOT NULL,
    user_ids INTEGER[] NOT NULL,
    is_open BOOLEAN NOT NULL,
    is_valid BOOLEAN NOT NULL,
    panel_id TEXT NOT NULL,
    original_name TEXT NOT NULL
);