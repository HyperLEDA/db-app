DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'db_private_reader') THEN
        CREATE ROLE db_private_reader;
    END IF;
END
$$;

DO $$
DECLARE
    schema_name text;
BEGIN
    FOR schema_name IN
        SELECT nspname
        FROM pg_namespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema')
          AND nspname NOT LIKE 'pg_temp_%'
          AND nspname NOT LIKE 'pg_toast%'
    LOOP
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO db_private_reader', schema_name);
        EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO db_private_reader', schema_name);
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON TABLES TO db_private_reader',
            schema_name
        );
    END LOOP;
END
$$;
