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
    command TEXT NOT NULL
);

-- ALTER TABLE mappings IF NOT EXISTS
-- ADD CONSTRAINT unique_user_trigger UNIQUE (user_id, trigger);

-- ALTER TABLE mappings IF NOT EXISTS
-- ADD CONSTRAINT unique_guild_trigger UNIQUE (guild_id, trigger);

-- ALTER TABLE mappings IF NOT EXISTS
-- ADD CONSTRAINT guild_user_not_null CHECK (guild_id IS NOT NULL OR user_id IS NOT NULL);

DO $$
BEGIN
    -- Add unique_user_trigger constraint if it does not exist
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_user_trigger'
    ) THEN
        ALTER TABLE mappings
        ADD CONSTRAINT unique_user_trigger UNIQUE (user_id, trigger);
    END IF;

    -- Add unique_guild_trigger constraint if it does not exist
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_guild_trigger'
    ) THEN
        ALTER TABLE mappings
        ADD CONSTRAINT unique_guild_trigger UNIQUE (guild_id, trigger);
    END IF;

    -- Add guild_user_not_null constraint if it does not exist
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'guild_user_not_null'
    ) THEN
        ALTER TABLE mappings
        ADD CONSTRAINT guild_user_not_null CHECK (guild_id IS NOT NULL OR user_id IS NOT NULL);
    END IF;
END $$;
