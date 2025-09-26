CREATE SCHEMA IF NOT EXISTS nature;

CREATE TYPE nature.status AS ENUM(
  '*',
  '*S',
  'ISM',
  'G',
  'MG',
  'O',
  'X'
);

CREATE TABLE nature.data (
    object_id text PRIMARY KEY REFERENCES rawdata.objects (id),
    nature nature.status NOT NULL,
    modification_time timestamp without time zone NOT NULL DEFAULT NOW(),
);

CREATE TABLE layer2.nature (
    pgc integer PRIMARY KEY,
    nature nature.status NOT NULL
);
