CREATE SCHEMA common;

--------- The object list -----------
CREATE TABLE common.pgc (id serial PRIMARY KEY);

--------- Bibliography -----------
CREATE TABLE common.bib (
  id serial PRIMARY KEY,
  -- bibcode references the ADS database: https://ui.adsabs.harvard.edu/
  bibcode text UNIQUE,
  year smallint NOT NULL,
  author text [] CHECK (
    array_length(author, 1) >= 1
    and author [1] IS NOT NULL
  ),
  title text,
  modification_time timestamp without time zone DEFAULT NOW()
);

-------- Designation ------------
CREATE SCHEMA designation;

CREATE TABLE designation.data (
  pgc integer NOT NULL REFERENCES common.pgc(id) ON DELETE restrict ON UPDATE cascade,
  design text NOT NULL UNIQUE,
  bib integer NOT NULL REFERENCES common.bib(id) ON DELETE restrict ON UPDATE cascade,
  modification_time timestamp without time zone NOT NULL,
  PRIMARY KEY (pgc, design)
);

CREATE INDEX ON designation.data (upper(replace(design, ' ', '')));

CREATE TABLE designation.ambiguity (
  pgc integer NOT NULL REFERENCES common.pgc(id) ON DELETE restrict ON UPDATE cascade,
  design text NOT NULL,
  bib integer NOT NULL REFERENCES common.bib(id) ON DELETE restrict ON UPDATE cascade,
  modification_time timestamp without time zone NOT NULL,
  PRIMARY KEY (pgc, design)
);

CREATE INDEX ON designation.ambiguity (upper(replace(design, ' ', '')));

CREATE VIEW designation.list AS
SELECT
  *
FROM
  designation.data
UNION
SELECT
  *
FROM
  designation.ambiguity;

CREATE VIEW designation.main AS
SELECT
  DISTINCT ON (pgc) d.*
FROM
  designation.data AS d
  LEFT JOIN common.bib AS b ON (d.bib = b.id)
ORDER BY
  pgc,
  CASE
    WHEN d.design ~ '^MESSIER' THEN 1
    WHEN d.design ~ '^NGC' THEN 2
    WHEN d.design ~ '^IC' THEN 3
    WHEN d.design ~ '^DDO' THEN 4
    WHEN d.design ~ '^UGC' THEN 5
    WHEN d.design ~ '^PGC'
    and d.pgc < 1000000 THEN 6
    WHEN b.bibcode IS NOT NULL THEN b.year -1800
    ELSE b.year
  END;

----------- Coordinate catalog ---------------------
CREATE SCHEMA icrs;

CREATE TABLE icrs.data (
  id serial PRIMARY KEY,
  pgc integer NOT NULL REFERENCES common.pgc (id) ON DELETE restrict ON UPDATE cascade,
  ra double precision NOT NULL,
  dec double precision NOT NULL,
  bib integer NOT NULL REFERENCES common.bib (id) ON DELETE restrict ON UPDATE cascade,
  modification_time timestamp without time zone NOT NULL,
  CHECK (
    ra >= 0
    and ra <= 360
    and dec >= -90
    and dec <= 90
  )
);

CREATE INDEX ON icrs.data (ra);

CREATE INDEX ON icrs.data (dec);

CREATE INDEX ON icrs.data (ra, dec);

CREATE TABLE icrs.err (
  id integer NOT NULL REFERENCES icrs.data (id) ON DELETE restrict ON UPDATE cascade,
  ra double precision NOT NULL,
  dec double precision NOT NULL
);

CREATE TABLE icrs.dataseterr (
  bib integer NOT NULL REFERENCES common.bib (id) ON DELETE restrict ON UPDATE cascade,
  ra double precision NOT NULL,
  dec double precision NOT NULL
);

CREATE TABLE icrs.obsoleted (
  bib integer NOT NULL REFERENCES common.bib (id) ON DELETE restrict ON UPDATE cascade,
  renewed integer NOT NULL REFERENCES common.bib (id) ON DELETE restrict ON UPDATE cascade,
  modification_time timestamp without time zone NOT NULL
);

CREATE TABLE icrs.excluded (
  id bigint NOT NULL REFERENCES icrs.data (id) ON DELETE restrict ON UPDATE cascade,
  note text NOT NULL,
  modification_time timestamp without time zone NOT NULL
);

CREATE VIEW icrs.list AS
SELECT
  d.id,
  d.pgc,
  d.ra,
  d.dec,
  COALESCE(err.ra, dserr.ra) AS e_ra,
  COALESCE(err.dec, dserr.dec) AS e_dec,
  b.id AS bib,
  b.bibcode,
  b.year,
  b.author,
  b.title,
  obsol.bib IS NOT NULL
  and excl.id IS NOT NULL AS isok,
  GREATEST(
    d.modification_time,
    b.modification_time,
    excl.modification_time
  ) AS modification_time
FROM
  icrs.data AS d
  LEFT JOIN icrs.err AS err USING (id)
  LEFT JOIN icrs.dataseterr AS dserr USING (bib)
  LEFT JOIN common.bib AS b ON (d.bib = b.id)
  LEFT JOIN icrs.obsoleted AS obsol ON (obsol.bib = d.bib)
  LEFT JOIN icrs.excluded AS excl ON (excl.id = d.id);

CREATE VIEW icrs.mean AS WITH xyz AS (
  SELECT
    pgc,
    cosd(dec) * cosd(ra) AS x,
    cosd(dec) * sind(ra) AS y,
    sind(dec) AS z,
    coalesce(1 /((e_ra * cosd(dec)) ^ 2 + e_dec ^ 2), 1) AS invvar
  FROM
    icrs.list
  WHERE
    isOk
),
mean AS (
  SELECT
    pgc,
    avg(x * invvar) / avg(invvar) AS x,
    avg(y * invvar) / avg(invvar) AS y,
    avg(z * invvar) / avg(invvar) AS z,
    sqrt(1 / sum(invvar)) AS sig
  FROM
    xyz
  GROUP BY
    pgc
)
SELECT
  pgc,
  atan2d(y, x) AS ra,
  atan2d(z, sqrt(x ^ 2 + y ^ 2)) AS dec,
  sig AS e_ra,
  sig AS e_dec
FROM
  mean;