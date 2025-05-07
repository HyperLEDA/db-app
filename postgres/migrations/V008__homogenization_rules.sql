CREATE SCHEMA IF NOT EXISTS layer0;
COMMENT ON SCHEMA layer0 IS 'Tables that serve as management tables for rawdata tables' ;

CREATE TABLE layer0.homogenization_rules (
    id SERIAL PRIMARY KEY,
    catalog text NOT NULL,
    parameter text NOT NULL,
    key text,
    filters jsonb NOT NULL,
    priority int,
    enrichment jsonb
);

CREATE TABLE layer0.homogenization_params (
    catalog text NOT NULL,
    key text NOT NULL,
    params jsonb NOT NULL,
    PRIMARY KEY (catalog, key)
);
