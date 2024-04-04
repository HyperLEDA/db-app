BEGIN;

-----------------------------------------------
--------- Observation Data Types --------------

CREATE TABLE common.datatype (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE common.datatype IS 'The types of the published data' ;
COMMENT ON COLUMN common.datatype.id IS 'ID of the data type' ;
COMMENT ON COLUMN common.datatype.description IS 'Description of the data type' ;

INSERT INTO common.datatype VALUES 
  ( 'reguliar'     , 'Reguliar measurements' )
, ( 'reprocessing' , 'Reprocessing of observations' )
, ( 'preliminary'  , 'Preliminary results' )
, ( 'compilation'  , 'Compilation of data from literature' )
;


-----------------------------------------------
--------- Data Quality ------------------------

CREATE TABLE common.quality (
  id	smallint	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE common.quality IS 'Data quality' ;
COMMENT ON COLUMN common.quality.id IS 'ID of the data quality' ;
COMMENT ON COLUMN common.quality.description IS 'Description of the data quality' ;

INSERT INTO common.datatype VALUES 
  ( 0 , 'Reguliar measurements' )
, ( 1 , 'Low signal to noise' )
, ( 2 , 'Suspected measurement' )
, ( 3 , 'Lower limit' )
, ( 4 , 'Upper limit' )
, ( 5 , 'Wrong measurement' )
;



-----------------------------------------------
--------- Spectral regions --------------------

CREATE TABLE common.specregion (
  id	text	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE common.specregion IS 'The types of electromagnetic radiation' ;
COMMENT ON COLUMN common.specregion.id IS 'ID of the spectral region' ;
COMMENT ON COLUMN common.specregion.description IS 'Description of the spectral region' ;

INSERT INTO common.specregion VALUES 
  ( 'gamma' , 'Gamma rays part of the spectrum' )
, ( 'Xray'  , 'X-ray part of the spectrum' )
, ( 'UV'    , 'Ultraviolet part of the spectrum' )
, ( 'opt'   , 'Optical part of the spectrum' )
, ( 'IR'    , 'Infrared part part of the spectrum' )
, ( 'mm'    , 'Millimetric/submillimetric part part of the spectrum' )
, ( 'radio' , 'Radio part part of the spectrum' )
;


-----------------------------------------------
--------- FoV dimentions ----------------------

CREATE TABLE common.fovdim (
  id	smallint	PRIMARY KEY
, description	text	NOT NULL
) ;

COMMENT ON TABLE common.fovdim IS 'The dimentions of the spectral field of view' ;
COMMENT ON COLUMN common.fovdim.id IS 'Number of dimentions' ;
COMMENT ON COLUMN common.fovdim.description IS 'Description of the FoV dimentions' ;

INSERT INTO common.fovdim VALUES 
  ( 0, 'Fiber spectroscopy (single dish in case of the radio observations)' )
, ( 1, 'Long-slit spectroscopy' )
, ( 2, 'Integral field (panoramic) spectroscopy (radiointerferometry)' )
;


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