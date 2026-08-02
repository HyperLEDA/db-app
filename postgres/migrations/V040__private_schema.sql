CREATE SCHEMA IF NOT EXISTS private;
COMMENT ON SCHEMA private IS 'Auth and other non-public tables, not exposed to users';

DROP TRIGGER IF EXISTS tr_disable_other_tokens ON common.tokens;
DROP FUNCTION IF EXISTS common.disable_other_tokens();

ALTER TABLE common.tokens SET SCHEMA private;
ALTER TABLE common.users SET SCHEMA private;
ALTER TYPE common.user_role SET SCHEMA private;

CREATE OR REPLACE FUNCTION private.disable_other_tokens() RETURNS trigger
  LANGUAGE plpgsql
AS
$$
  BEGIN
  UPDATE private.tokens
  SET active = false
  WHERE user_id = NEW.user_id
  AND token_hash != NEW.token_hash;
  RETURN NEW;
  END
$$;

CREATE TRIGGER tr_disable_other_tokens
  AFTER INSERT ON private.tokens
  FOR EACH ROW
EXECUTE FUNCTION private.disable_other_tokens();
