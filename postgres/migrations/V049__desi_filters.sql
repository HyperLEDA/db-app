/* pgmigrate-encoding: utf-8 */

INSERT INTO photometry.systems (id, description, bibcode, svo_id) VALUES
  ( 'MzLS', 'Mayall z-band Legacy Survey', NULL, 'gname=KPNO&gname2=MzLS' )
, ( 'BASS', 'The Beijing-Arizona Sky Survey (BASS)', NULL, 'gname=BOK&gname2=BASS' )
;

INSERT INTO photometry.bands (id, name, photsys, waveref, fwhm, extinction, svo_id) VALUES
  ( 'z_MzLS', 'z', 'MzLS', 9200.33, 1451.21, 0.49143, 'KPNO/MzLS.z' )
, ( 'g_BASS', 'g', 'BASS', 4769.48, 1418.56, 1.19591, 'BOK/BASS.g' )
, ( 'r_BASS', 'r', 'BASS', 6390.20, 1425.21, 0.83898, 'BOK/BASS.r' )
;

INSERT INTO photometry.calib_bands (id, band, magsys ) VALUES
  ( 'g_BASS', 'g_BASS', 'AB' )
, ( 'r_BASS', 'r_BASS', 'AB' )
, ( 'z_MzLS', 'z_MzLS', 'AB' )
;
