DROP TRIGGER IF EXISTS tr_disable_other_tokens ON private.tokens;
DROP FUNCTION IF EXISTS private.disable_other_tokens();

CREATE OR REPLACE FUNCTION private.disable_excess_tokens() RETURNS trigger
  LANGUAGE plpgsql
AS
$$
  BEGIN
  UPDATE private.tokens
  SET active = false
  WHERE user_id = NEW.user_id
    AND active = true
    AND token_hash NOT IN (
      SELECT token_hash
      FROM private.tokens
      WHERE user_id = NEW.user_id
        AND active = true
      ORDER BY expiry_time DESC
      LIMIT 3
    );
  RETURN NEW;
  END
$$;

CREATE TRIGGER tr_disable_excess_tokens
  AFTER INSERT ON private.tokens
  FOR EACH ROW
EXECUTE FUNCTION private.disable_excess_tokens();
