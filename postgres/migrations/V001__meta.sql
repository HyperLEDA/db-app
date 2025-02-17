/* pgmigrate-encoding: utf-8 */

CREATE SCHEMA IF NOT EXISTS meta ;
COMMENT ON SCHEMA meta IS 'Some views and functions for convenient metadata management' ;

CREATE OR REPLACE VIEW meta.column_info AS
WITH
  s1 AS (
  SELECT
    table_schema	AS schema_name
  , table_name
  , column_name
  , pg_catalog.col_description(concat(table_schema, '."', table_name, '"')::regclass::oid, ordinal_position)::text	AS str_comment
  FROM 
    information_schema.columns
  WHERE
        table_schema <> 'pg_catalog'
    and table_schema <> 'information_schema'
    and table_schema !~ 'pg_toast'
  )
SELECT
  schema_name
, table_name
, column_name
, CASE WHEN str_comment IS JSON
    THEN str_comment::json
    ELSE json_build_object('description', str_comment )
  END	AS param
FROM s1
;

COMMENT ON VIEW meta.column_info IS 'Column Metadata' ;
COMMENT ON COLUMN meta.column_info.schema_name IS 'Schema name' ;
COMMENT ON COLUMN meta.column_info.table_name IS 'Table name' ;
COMMENT ON COLUMN meta.column_info.column_name IS 'Column name' ;
COMMENT ON COLUMN meta.column_info.param IS 'Metadata in JSON format' ;

CREATE OR REPLACE VIEW meta.table_info AS
WITH
  s1 AS (
  SELECT
    table_schema	AS schema_name
  , table_name
  , pg_catalog.obj_description(concat(table_schema, '."', table_name, '"')::regclass, 'pg_class')::text	AS str_comment
  FROM 
    information_schema.tables
  WHERE
        table_schema <> 'pg_catalog'
    and table_schema <> 'information_schema'
    and table_schema !~ 'pg_toast'
  )
SELECT
  schema_name
, table_name
, CASE WHEN str_comment IS JSON
    THEN str_comment::json
    ELSE json_build_object('description', str_comment )
  END	AS param
FROM s1
;

COMMENT ON VIEW meta.table_info IS 'Table Metadata' ;
COMMENT ON COLUMN meta.table_info.schema_name IS 'Schema name' ;
COMMENT ON COLUMN meta.table_info.table_name IS 'Table name' ;
COMMENT ON COLUMN meta.table_info.param IS 'Metadata in JSON format' ;

CREATE OR REPLACE VIEW meta.schema_info AS
WITH
  s1 AS (
  SELECT
    schema_name
  , pg_catalog.obj_description(schema_name::regnamespace, 'pg_namespace')::text	AS str_comment
  FROM 
    information_schema.schemata
  WHERE
        schema_name <> 'pg_catalog'
    and schema_name <> 'information_schema'
    and schema_name !~ 'pg_toast'
  )
SELECT
  schema_name
, CASE WHEN str_comment IS JSON
    THEN str_comment::json
    ELSE json_build_object('description', str_comment )
  END	AS param
FROM s1
;

COMMENT ON VIEW meta.schema_info IS 'Schema Metadata' ;
COMMENT ON COLUMN meta.schema_info.schema_name IS 'Schema name' ;
COMMENT ON COLUMN meta.schema_info.param IS 'Metadata in JSON format' ;

CREATE OR REPLACE FUNCTION 
  meta.setparams( schema_name text, table_name text, column_name text, param json )
RETURNS void
AS $$
  DECLARE
    str_comment text := param::text ;
  BEGIN
    EXECUTE concat('COMMENT ON COLUMN ', schema_name, '.', table_name, '.', column_name, ' IS ''', str_comment, '''');
  END ;
$$  LANGUAGE plpgsql COST 100 VOLATILE STRICT PARALLEL UNSAFE
;

CREATE OR REPLACE FUNCTION 
  meta.setparams( schema_name text, table_name text, param json )
RETURNS void
AS $$
  DECLARE
    str_comment text := param::text ;
    TabType char ;
  BEGIN
    SELECT c.relkind INTO TabType 
    FROM
      pg_catalog.pg_class AS c
      LEFT JOIN pg_catalog.pg_namespace AS n ON (n.oid = c.relnamespace)
    WHERE
          n.nspname=schema_name
      and c.relname=table_name
    ;

    CASE WHEN TabType='r' THEN EXECUTE concat('COMMENT ON TABLE ', schema_name, '.', table_name, ' IS ''', str_comment, '''');
         WHEN TabType='v' THEN EXECUTE concat('COMMENT ON VIEW ', schema_name, '.', table_name, ' IS ''', str_comment, '''');
         WHEN TabType='m' THEN EXECUTE concat('COMMENT ON MATERIALIZED VIEW ', schema_name, '.', table_name, ' IS ''', str_comment, '''');
    ELSE
    END CASE;
  END ;
$$  LANGUAGE plpgsql COST 100 VOLATILE STRICT PARALLEL UNSAFE
;

CREATE OR REPLACE FUNCTION 
  meta.setparams( schema_name text, param json )
RETURNS void
AS $$
  DECLARE
    str_comment text := param::text ;
  BEGIN
    EXECUTE format( 'COMMENT ON SCHEMA %I IS %L', schema_name, str_comment ) ;
  END ;
$$  LANGUAGE plpgsql COST 100 VOLATILE STRICT PARALLEL UNSAFE
;
