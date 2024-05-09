/* pgmigrate-encoding: utf-8 */

BEGIN;

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
COMMENT ON COLUMN common.magsys.id IS 'Magnitude system ID' ;
COMMENT ON COLUMN common.magsys.description IS 'Description of the magnitude system' ;

INSERT INTO common.magsys VALUES
  ( 'Vega', 'The Vega magnitude system uses the Vega as the standard star with an apparent magnitude of zero, regardeless of the wavelength filter. The spectrum of Vega used to define this system is a composite spectrum of empirical and synthetic spectra (Bohlin & Gilliland, 2004AJ....127.3508B). m(Vega) = -2.5*log10(F/FVega), where F is flux of an object, and FVega is the calibrated spectrum of Vega.' )
, ( 'AB', 'The AB magnitude system uses flat reference spectrum in frequency space. The conversion is chosen such that the V-magnitude corresponds roughly to that in the Johnson system. The monochromatic AB magnitude is defined as m(AB) = 8.9 -2.5*log10(Fv[Jy]) = -48.6 -2.5*log10(Fv[erg s^−1 cm^−2 Hz^−1]), where Fv is the spectral flux density.' )
, ( 'ST', 'The ST magnitude system uses flat reference spectrum in wavelength space. The conversion is chosen such that the V-magnitude corresponds roughly to that in the Johnson system. The monochromatic ST magnitude is defined as m(ST) = -21.1 -2.5*log10(Flambda[erg s^−1 cm^−2 Angstrom^−1]), where Flambda is the spectral flux density.' )
;


CREATE TABLE common.photsys (
  id	text	PRIMARY KEY
, description	text	NOT NULL
, svo_query	text	UNIQUE
) ;

COMMENT ON TABLE common.photsys IS 'Photometric system' ;
COMMENT ON COLUMN common.photsys.id IS 'Photometric system ID' ;
COMMENT ON COLUMN common.photsys.description IS 'Description of the photometric system' ;
COMMENT ON COLUMN common.photsys.svo_query IS '{"description" : "Query to the Spanish Virtual Observatory", "url" : "http://svo2.cab.inta-csic.es/theory/fps/index.php", "ucd" : "meta.query"}' ;

INSERT INTO common.photsys VALUES
  ( 'Johnson' , 'Johnson UBVRIJHKL photometric system' , 'gname=Generic&gname2=Johnson_UBVRIJHKL' )
, ( 'Cousins' , 'Cousins (Rc,Ic) photometric system' , 'gname=Generic&gname2=Cousins' )

, ( 'Tycho-2' , 'Tycho photometric system' , 'gname=TYCHO' )
, ( 'Hipparcos' , 'Hipparcos photometric system' , 'gname=Hipparcos' )
, ( 'Gaia3' , 'Gaia mission, eDR3 release photometric system' , 'gname=GAIA&gname2=GAIA3' )

, ( 'ACS_WFC' , 'Hubble Space Telescope (HST), Advanced Camera for Surveys (ACS), Wide Field Channel photometric system' , 'gname=HST&gname2=ACS_WFC' )
, ( 'WFPC2_WF' , 'Hubble Space Telescope (HST), Wide-Field Planetary Camera 2 (WFPC2), Wide Field photometric system' , 'gname=HST&gname2=WFPC2-WF' )
, ( 'WFPC3_IR' , 'Hubble Space Telescope (HST), Wide-Field Planetary Camera 3 (WFPC3), IR channel photometric system' , 'gname=HST&gname2=WFC3_IR' )

, ( 'NIRCam' , 'James Webb Space Telescope (JWST), Near Infrared Camera (NIRCam) photometric system' , 'gname=JWST&gname2=NIRCam' )

, ( 'SDSS' , 'Sloan Digital Sky Survey photometric system' , 'gname=SLOAN&gname2=SDSS' )
, ( 'PS1' , 'Panoramic Survey Telescope and Rapid Response System (Pan-STARRS), PS1 photometric system' , 'gname=PAN-STARRS' )
, ( 'DES' , 'Dark Energy Camera (DECam) photometric system (at the prime focus of the Blanco 4-m telescope)' , 'gname=CTIO&gname2=DECam' )
, ( 'HSC' , 'Hyper Suprime-Cam (HSC) photometric system (at the prime focus of Subaru Telescope)' , 'Subaru&gname2=HSC' )
, ( '2MASS' , 'Two Micron All Sky Survey (2MASS) photometric system' , 'gname=2MASS' )
, ( 'DENIS' , 'Deep Near Infrared Survey of the Southern Sky (DENIS) photometric system' , 'gname=DENIS' )

, ( 'GALEX' , 'Galaxy Evolution Explorer (GALEX) photometric system' , 'gname=GALEX' )
, ( 'IRAS' , 'Infrared Astronomical Satellite (IRAS) photometric system' , 'gname=IRAS' )
, ( 'WISE' , 'Wide-field Infrared Survey Explorer (WISE) photometric system' , 'gname=WISE' )
;


CREATE TABLE common.filter (
  id	text	PRIMARY KEY
, name	text	NOT NULL
, photsys	text	NOT NULL	REFERENCES common.photsys (id) ON DELETE restrict ON UPDATE cascade
, wavemean	real	NOT NULL
, fwhm	real	NOT NULL
, description	text	NOT NULL
, bib	integer	REFERENCES common.bib (id) ON DELETE restrict ON UPDATE cascade
, svo_id	text	UNIQUE
) ;
CREATE INDEX ON common.filter (wavemean) ;
CREATE INDEX ON common.filter (name) ;
CREATE INDEX ON common.filter (photsys) ;

COMMENT ON TABLE common.filter IS 'List of filters' ;
COMMENT ON COLUMN common.filter.id IS 'Filter ID' ;
COMMENT ON COLUMN common.filter.name IS 'Common filter designation' ;
COMMENT ON COLUMN common.filter.photsys IS 'Photometric system' ;
COMMENT ON COLUMN common.filter.wavemean IS 'The Mean wavelength of the filter transmission: λmean = int( λ*T(λ) dλ ) / int( T(λ) dλ )' ;
COMMENT ON COLUMN common.filter.fwhm IS 'The Full Width Half Maximum of the filter transmission' ;
COMMENT ON COLUMN common.filter.description IS 'Description of the filter' ;
COMMENT ON COLUMN common.filter.bib IS 'Bibliography reference' ;
COMMENT ON COLUMN common.filter.svo_id IS '{"description" : "The Spanish Virtual Observatory filter ID", "url" : "http://svo2.cab.inta-csic.es/theory/fps/index.php?id=", "ucd" : "meta.ref.ivoid"}' ;


CREATE TABLE common.calibpassband (
  id	serial	PRIMARY KEY
, filter	text	NOT NULL	REFERENCES common.filter (id) ON DELETE restrict ON UPDATE cascade
, magsys	text	NOT NULL	REFERENCES common.magsys (id) ON DELETE restrict ON UPDATE cascade
, UNIQUE (filter,magsys)
) ;

COMMENT ON TABLE common.calibpassband IS 'Calibrated passbands' ;
COMMENT ON COLUMN common.calibpassband.id IS 'Calibrated passband ID' ;
COMMENT ON COLUMN common.calibpassband.filter IS 'Filter ID' ;
COMMENT ON COLUMN common.calibpassband.magsys IS 'Magnitude system ID' ;

COMMIT;