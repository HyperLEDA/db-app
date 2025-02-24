/* pgmigrate-encoding: utf-8 */
CREATE SCHEMA IF NOT EXISTS layer2;

CREATE TABLE layer2.last_update (dt timestamp NOT NULL);

INSERT INTO layer2.last_update (dt) VALUES (to_timestamp(0));

CREATE TABLE layer2.designation(
    pgc integer PRIMARY KEY,
    design text NOT NULL
);

CREATE TABLE layer2.icrs (
    pgc integer PRIMARY KEY,
    ra double precision NOT NULL,
    e_ra real NOT NULL,
    dec double precision NOT NULL,
    e_dec real NOT NULL
);

CREATE TABLE layer2.cz (
    pgc integer PRIMARY KEY,
    cz double precision NOT NULL,
    e_cz real NOT NULL
);