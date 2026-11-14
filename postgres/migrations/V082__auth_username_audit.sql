ALTER TABLE private.action_log ADD COLUMN username text;
UPDATE private.action_log AS al
SET username = u.login
FROM private.users AS u
WHERE al.user_id = u.id;
UPDATE private.action_log SET username = 'unknown' WHERE username IS NULL;
ALTER TABLE private.action_log ALTER COLUMN username SET NOT NULL;
ALTER TABLE private.action_log DROP COLUMN user_id;

ALTER TABLE private.runs ADD COLUMN username text;
UPDATE private.runs AS r
SET username = u.login
FROM private.users AS u
WHERE r.user_id = u.id;
UPDATE private.runs SET username = 'unknown' WHERE username IS NULL;
ALTER TABLE private.runs ALTER COLUMN username SET NOT NULL;
ALTER TABLE private.runs DROP COLUMN user_id;

DROP TABLE private.tokens;
DROP TABLE private.users;
DROP TYPE private.user_role;
