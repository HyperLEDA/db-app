BEGIN;
-----------------------------------------------
--------- Bandpass description ----------------

CREATE TABLE common.magsys (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE common.magsys IS 'Magnitude systems' ;
COMMENT ON COLUMN common.magsys.id IS 'ID of the magnitude system' ;
COMMENT ON COLUMN common.magsys.description IS 'Description of the magnitude system' ;

INSERT INTO common.magsys VALUES
  ( 'Vega', 'The Vega magnitude system uses the Vega as the standard star with an apparent magnitude of zero, regardeless of the wavelength filter. The spectrum of Vega used to define this system is a composite spectrum of empirical and synthetic spectra (Bohlin & Gilliland, 2004AJ....127.3508B). m(Vega) = -2.5*log10(F/FVega), where F is flux of an object, and FVega is the calibrated spectrum of Vega.' )
, ( 'AB', 'The AB magnitude system uses flat reference spectrum in frequency space. The conversion is chosen such that the V-magnitude corresponds roughly to that in the Johnson system. The monochromatic AB magnitude is defined as m(AB) = 8.9 -2.5*log10(Fv[Jy]) = -48.6 -2.5*log10(Fv[erg s^−1 cm^−2 Hz^−1]), where Fv is the spectral flux density.' )
, ( 'ST', 'The ST magnitude system uses flat reference spectrum in wavelength space. The conversion is chosen such that the V-magnitude corresponds roughly to that in the Johnson system. The monochromatic ST magnitude is defined as m(ST) = -21.1 -2.5*log10(Flambda[erg s^−1 cm^−2 Angstrom^−1]), where Flambda is the spectral flux density.' )
;


CREATE TABLE common.passband (
  id	serial	PRIMARY KEY
, band	text	NOT NULL	UNIQUE
, wavemean	real	NOT NULL
, fwhm	real	NOT NULL
, description	text	NOT NULL
, bib	integer	REFERENCES	common.bib (id) ON DELETE restrict ON UPDATE cascade
, svoid	text	UNIQUE
) ;
CREATE INDEX ON common.passband (wavemean) ;

COMMENT ON TABLE common.passband IS 'List of passbands' ;
COMMENT ON COLUMN common.passband.id IS 'internal ID of the filter' ;
COMMENT ON COLUMN common.passband.band IS 'The filter name' ;
COMMENT ON COLUMN common.passband.wavemean IS 'The Mean wavelength of the filter transmission: Lmean = int( L*T(L) dL ) / int( T(L)dL )' ;
COMMENT ON COLUMN common.passband.fwhm IS 'The Full Width Half Maximum of the filter transmission' ;
COMMENT ON COLUMN common.passband.description IS 'Description of the filter' ;
COMMENT ON COLUMN common.passband.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN common.passband.svoid IS 'Spanish Virtual Observatory filter ID' ;


COMMIT;