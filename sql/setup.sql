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

CREATE TABLE IF NOT EXISTS mappings(
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    guild_id BIGINT,
    trigger TEXT NOT NULL,
    command TEXT NOT NULL,
    created_at BIGINT NOT NULL
);


DO $$
BEGIN
    -- Adding some CONSTRAINT (if not exists)

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_user_trigger'
    ) THEN
        ALTER TABLE mappings
        ADD CONSTRAINT unique_user_trigger UNIQUE (user_id, trigger);
    END IF;

    
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_guild_trigger'
    ) THEN
        ALTER TABLE mappings
        ADD CONSTRAINT unique_guild_trigger UNIQUE (guild_id, trigger);
    END IF;

    
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'guild_user_not_null'
    ) THEN
        ALTER TABLE mappings
        ADD CONSTRAINT guild_user_not_null CHECK (guild_id IS NOT NULL OR user_id IS NOT NULL);
    END IF;
END $$;
