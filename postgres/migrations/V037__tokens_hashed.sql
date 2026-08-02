DROP TRIGGER IF EXISTS tr_disable_other_tokens ON common.tokens;

TRUNCATE common.tokens;

ALTER TABLE common.tokens DROP CONSTRAINT tokens_pkey;
ALTER TABLE common.tokens DROP COLUMN token;

ALTER TABLE common.tokens ADD COLUMN token_hash bytea NOT NULL PRIMARY KEY;

CREATE OR REPLACE FUNCTION common.disable_other_tokens() RETURNS trigger
  LANGUAGE plpgsql
AS
$$
  BEGIN
  UPDATE common.tokens
  SET active = false
  WHERE user_id = NEW.user_id
  AND token_hash != NEW.token_hash;
  RETURN NEW;
  END
$$;

CREATE TRIGGER tr_disable_other_tokens
  AFTER INSERT ON common.tokens
  FOR EACH ROW
EXECUTE FUNCTION common.disable_other_tokens();
