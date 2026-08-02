CREATE VIEW layer2.photometry_total AS
SELECT
  r.pgc
, pt.band
, cb.magsys
, pt.method
, b.waveref AS wavelength
, pt.mag
, pt.e_mag
FROM photometry.total AS pt
  JOIN layer0.records AS r ON pt.record_id = r.id
  JOIN photometry.calib_bands AS cb ON pt.band = cb.id
  JOIN photometry.bands AS b ON cb.band = b.id
WHERE r.pgc IS NOT NULL;
