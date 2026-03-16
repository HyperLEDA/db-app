ALTER TABLE photometry.data
  DROP CONSTRAINT data_e_mag_check;

ALTER TABLE photometry.data
  ADD CONSTRAINT data_e_mag_check CHECK (e_mag > 0 AND e_mag < 20);

ALTER TABLE photometry.data
  DROP CONSTRAINT data_mag_check;

ALTER TABLE photometry.data
  ADD CONSTRAINT data_mag_check CHECK (mag > -5 AND mag < 40);
