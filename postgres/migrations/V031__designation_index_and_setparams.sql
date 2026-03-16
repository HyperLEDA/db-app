CREATE INDEX ON designation.data (design);

CREATE OR REPLACE FUNCTION meta.setparams(
  p_schema text,
  p_table text,
  p_column text,
  p_key text,
  p_value text
)
RETURNS void
AS $$
DECLARE
  tab_oid oid;
  col_ord int;
  current_comment text;
  new_param jsonb;
BEGIN
  tab_oid := (quote_ident(p_schema) || '.' || quote_ident(p_table))::regclass;
  SELECT c.ordinal_position INTO col_ord
  FROM information_schema.columns c
  WHERE c.table_schema = p_schema
    AND c.table_name = p_table
    AND c.column_name = p_column;
  IF col_ord IS NULL THEN
    RAISE EXCEPTION 'column %.%.% does not exist', p_schema, p_table, p_column;
  END IF;

  current_comment := pg_catalog.col_description(tab_oid, col_ord);
  IF current_comment IS NULL THEN
    new_param := '{}'::jsonb;
  ELSIF current_comment ~ '^\s*\{' THEN
    BEGIN
      new_param := current_comment::jsonb;
    EXCEPTION WHEN OTHERS THEN
      new_param := jsonb_build_object('description', current_comment);
    END;
  ELSE
    new_param := jsonb_build_object('description', current_comment);
  END IF;
  new_param := new_param || jsonb_build_object(p_key, p_value);

  EXECUTE format(
    'COMMENT ON COLUMN %I.%I.%I IS %L',
    p_schema, p_table, p_column,
    new_param::text
  );
END;
$$ LANGUAGE plpgsql COST 100 VOLATILE STRICT PARALLEL UNSAFE;

