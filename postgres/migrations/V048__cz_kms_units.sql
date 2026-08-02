/* pgmigrate-encoding: utf-8 */

UPDATE cz.data
SET cz = cz / 1000,
    e_cz = e_cz / 1000;

UPDATE layer2.cz
SET cz = cz / 1000,
    e_cz = e_cz / 1000;

SELECT meta.setparams('cz', 'data', 'cz', '{"description": "Heliocentric redshift (cz)", "unit": "km/s"}');
SELECT meta.setparams('cz', 'data', 'e_cz', '{"description": "Redshift measurement error", "unit": "km/s"}');

SELECT meta.setparams('layer2', 'cz', 'cz', '{"description": "Heliocentric redshift (cz)", "unit": "km/s"}');
SELECT meta.setparams('layer2', 'cz', 'e_cz', '{"description": "Redshift measurement error", "unit": "km/s"}');
