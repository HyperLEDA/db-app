/* pgmigrate-encoding: utf-8 */

DROP VIEW IF EXISTS meta.column_info;
DROP VIEW IF EXISTS meta.table_info;
DROP VIEW IF EXISTS meta.schema_info;

CREATE VIEW meta.column_info AS
SELECT
  n.nspname::text AS schema_name,
  c.relname::text AS table_name,
  a.attname::text AS column_name,
  CASE
    WHEN d.description IS JSON THEN d.description::json
    ELSE json_build_object('description', d.description)
  END AS param
FROM pg_catalog.pg_namespace n
JOIN pg_catalog.pg_class c
  ON c.relnamespace = n.oid
 AND c.relkind IN ('r', 'v', 'm', 'f', 'p')
JOIN pg_catalog.pg_attribute a
  ON a.attrelid = c.oid
 AND a.attnum > 0
 AND NOT a.attisdropped
LEFT JOIN pg_catalog.pg_description d
  ON d.objoid = c.oid
 AND d.objsubid = a.attnum
 AND d.classoid = 'pg_catalog.pg_class'::regclass
WHERE n.nspname <> 'pg_catalog'
  AND n.nspname <> 'information_schema'
  AND n.nspname !~ 'pg_toast'
;

CREATE VIEW meta.table_info AS
SELECT
  n.nspname::text AS schema_name,
  c.relname::text AS table_name,
  CASE
    WHEN d.description IS JSON THEN d.description::json
    ELSE json_build_object('description', d.description)
  END AS param
FROM pg_catalog.pg_namespace n
JOIN pg_catalog.pg_class c
  ON c.relnamespace = n.oid
 AND c.relkind IN ('r', 'v', 'm', 'f', 'p')
LEFT JOIN pg_catalog.pg_description d
  ON d.objoid = c.oid
 AND d.objsubid = 0
 AND d.classoid = 'pg_catalog.pg_class'::regclass
WHERE n.nspname <> 'pg_catalog'
  AND n.nspname <> 'information_schema'
  AND n.nspname !~ 'pg_toast'
;

CREATE VIEW meta.schema_info AS
SELECT
  n.nspname::text AS schema_name,
  CASE
    WHEN d.description IS JSON THEN d.description::json
    ELSE json_build_object('description', d.description)
  END AS param
FROM pg_catalog.pg_namespace n
LEFT JOIN pg_catalog.pg_description d
  ON d.objoid = n.oid
 AND d.objsubid = 0
 AND d.classoid = 'pg_catalog.pg_namespace'::regclass
WHERE n.nspname <> 'pg_catalog'
  AND n.nspname <> 'information_schema'
  AND n.nspname !~ 'pg_toast'
;
