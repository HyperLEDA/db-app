/* pgmigrate-encoding: utf-8 */
BEGIN;

CREATE TABLE layer2.velocity (
  pgc integer NOT NULL REFERENCES common.pgc(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  apex text NOT NULL,
  v double precision NOT NULL,
  e_v real NOT NULL,
  PRIMARY KEY (pgc, apex)
);

SELECT meta.setparams('layer2', 'velocity', '{"description": "Velocity with respect to configured apexes"}'::json);
SELECT meta.setparams('layer2', 'velocity', 'pgc', '{"description": "PGC identifier"}'::json);
SELECT meta.setparams('layer2', 'velocity', 'apex', '{"description": "Apex reference frame"}'::json);
SELECT meta.setparams('layer2', 'velocity', 'v', '{"description": "Velocity with respect to the apex", "unit": "km/s"}'::json);
SELECT meta.setparams('layer2', 'velocity', 'e_v', '{"description": "Uncertainty of the velocity with respect to the apex", "unit": "km/s"}'::json);

COMMIT;
