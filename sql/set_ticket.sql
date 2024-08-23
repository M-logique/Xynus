INSERT INTO tickets (
    "guild_id", 
    "owner_id", 
    "channel_id", 
    "user_ids", 
    "is_open", 
    "is_valid", 
    "panel_id", 
    "original_name"
)
VALUES (
    $1, 
    $2,
    $3, 
    $4, 
    $5, 
    $6, 
    $7, 
    $8
)
ON CONFLICT (channel_id) DO UPDATE
SET "guild_id" = EXCLUDED."guild_id",
    "user_ids" = EXCLUDED."user_ids",
    "is_open" = EXCLUDED."is_open",
    "is_valid" = EXCLUDED."is_valid",
    "panel_id" = EXCLUDED."panel_id",
    "original_name" = EXCLUDED."original_name";