INSERT INTO kv_table ("key", "value")
VALUES ($1, $2)
ON CONFLICT ("key") DO UPDATE
SET "value" = EXCLUDED."value";