ALTER TABLE photometry.data RENAME TO total;

CREATE TABLE photometry.isophotal (
  record_id text NOT NULL REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, band text NOT NULL REFERENCES photometry.calib_bands (id) ON UPDATE cascade ON DELETE restrict
, isophote real NOT NULL CHECK (isophote > -1 AND isophote < 30)
, mag real NOT NULL CHECK (mag > -5 AND mag < 40)
, e_mag real CHECK (e_mag > 0 AND e_mag < 20)
, PRIMARY KEY (record_id, band, isophote)
);
CREATE INDEX ON photometry.isophotal (record_id);
CREATE INDEX ON photometry.isophotal (band);
CREATE INDEX ON photometry.isophotal (isophote);

SELECT meta.setparams('photometry', 'isophotal', '{"description": "Catalog of the isophotal photometry"}');
SELECT meta.setparams('photometry', 'isophotal', 'record_id', 'description', 'Record ID');
SELECT meta.setparams('photometry', 'isophotal', 'band', 'description', 'Calibrated passband ID');
SELECT meta.setparams('photometry', 'isophotal', 'band', 'ucd', 'instr.filter');
SELECT meta.setparams('photometry', 'isophotal', 'isophote', 'description', 'Isophote level');
SELECT meta.setparams('photometry', 'isophotal', 'isophote', 'unit', 'mag/arcmin2');
SELECT meta.setparams('photometry', 'isophotal', 'isophote', 'ucd', 'phot.mag.sb');
SELECT meta.setparams('photometry', 'isophotal', 'mag', 'description', 'Magnitude inside given isophote');
SELECT meta.setparams('photometry', 'isophotal', 'mag', 'unit', 'mag');
SELECT meta.setparams('photometry', 'isophotal', 'mag', 'ucd', 'phot.mag');
SELECT meta.setparams('photometry', 'isophotal', 'e_mag', 'description', 'Error of the isophotal magnitude');
SELECT meta.setparams('photometry', 'isophotal', 'e_mag', 'unit', 'mag');
SELECT meta.setparams('photometry', 'isophotal', 'e_mag', 'ucd', 'stat.error;phot.mag');
