/* pgmigrate-encoding: utf-8 */
SELECT meta.setparams('layer2', 'icrs', 'ra', '{"unit": "deg"}');
SELECT meta.setparams('layer2', 'icrs', 'dec', '{"unit": "deg"}');
SELECT meta.setparams('layer2', 'icrs', 'e_ra', '{"unit": "deg"}');
SELECT meta.setparams('layer2', 'icrs', 'e_dec', '{"unit": "deg"}');
