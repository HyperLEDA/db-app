/* pgmigrate-encoding: utf-8 */

INSERT INTO layer2.last_update (dt, catalog) VALUES (to_timestamp(0), 'icrs');
INSERT INTO layer2.last_update (dt, catalog) VALUES (to_timestamp(0), 'redshift');
INSERT INTO layer2.last_update (dt, catalog) VALUES (to_timestamp(0), 'designation');
DELETE FROM layer2.last_update WHERE catalog = 'all';
