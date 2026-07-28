/* pgmigrate-encoding: utf-8 */

DO $$
DECLARE
    schema_name text;
BEGIN
    FOR schema_name IN
        SELECT nspname
        FROM pg_namespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'private')
          AND nspname NOT LIKE 'pg_temp_%'
          AND nspname NOT LIKE 'pg_toast%'
    LOOP
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO db_reader', schema_name);
        EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO db_reader', schema_name);
        EXECUTE format('GRANT SELECT ON ALL SEQUENCES IN SCHEMA %I TO db_reader', schema_name);
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON TABLES TO db_reader',
            schema_name
        );
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON SEQUENCES TO db_reader',
            schema_name
        );

        EXECUTE format('GRANT USAGE ON SCHEMA %I TO db_writer', schema_name);
        EXECUTE format(
            'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO db_writer',
            schema_name
        );
        EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO db_writer', schema_name);
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO db_writer',
            schema_name
        );
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO db_writer',
            schema_name
        );
    END LOOP;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hyperleda_reader') THEN
        CREATE ROLE hyperleda_reader LOGIN PASSWORD 'password';
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hyperleda_writer') THEN
        CREATE ROLE hyperleda_writer LOGIN PASSWORD 'password';
    END IF;
END
$$;

GRANT db_reader TO hyperleda_reader;
GRANT db_writer TO hyperleda_writer;

ALTER SYSTEM SET log_statement = 'mod';
SELECT pg_reload_conf();
