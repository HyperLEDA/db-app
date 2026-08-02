/* pgmigrate-encoding: utf-8 */
SELECT meta.setparams('icrs', 'data', 'ra', '{"description": "Right Ascension (ICRS)", "unit": "deg", "ucd": "pos.eq.ra"}');
SELECT meta.setparams('icrs', 'data', 'dec', '{"description": "Declination (ICRS)", "unit": "deg", "ucd": "pos.eq.dec"}');
SELECT meta.setparams('icrs', 'data', 'e_ra', '{"description": "Right Ascension error", "unit": "deg"}');
SELECT meta.setparams('icrs', 'data', 'e_dec', '{"description": "Declination error", "unit": "deg"}');
SELECT meta.setparams('cz', 'data', 'cz', '{"description": "Heliocentric redshift (cz)", "unit": "m/s"}');
SELECT meta.setparams('cz', 'data', 'e_cz', '{"description": "Redshift measurement error", "unit": "m/s"}');
