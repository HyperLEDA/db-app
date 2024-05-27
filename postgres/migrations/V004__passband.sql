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

INSERT INTO common.filter VALUES
 ('UV2000',NULL,NULL,150,NULL,'Ultraviolet between 100 and 200 nm',NULL,NULL)
,('Opt',NULL,NULL,NULL,NULL,'Optical part of the spectrum',NULL,NULL)
,('OptB',NULL,NULL,450,NULL,'Optical band between 400 and 500 nm',NULL,NULL)
,('OptV',NULL,NULL,550,NULL,'Optical band between 500 and 600 nm',NULL,NULL)
,('OptR',NULL,NULL,680,NULL,'Optical band between 600 and 750 nm',NULL,NULL)
,('FUV_GALEX','GALEX FUV','GALEX',154.582,23.393,'GALEX far-ultraviolet FUV','https://ui.adsabs.harvard.edu/abs/2007ApJS..173..185G','GALEX.FUV')
,('NUV_GALEX','GALEX NUV','GALEX',234.49,79.519,'GALEX near-ultraviolet NUV','https://ui.adsabs.harvard.edu/abs/2007ApJS..173..185G','GALEX.FUV')
,('UVM2_UVOT','UVOT UVM2','UVOT',227.271,52.713,'UVOT UVM2 filter effective area','https://heasarc.gsfc.nasa.gov/docs/heasarc/caldb/swift/docs/uvot/','UVOT.UVM2')
,('U','Johnson U','Johnson',353.105,68.373,'U band','https://ui.adsabs.harvard.edu/abs/1953ApJ...117..313J','Johnson.U')
,('B','Johnson B','Johnson',443.054,97.643,'B band','https://ui.adsabs.harvard.edu/abs/1953ApJ...117..313J','Johnson.B')
,('V','Johnson V','Johnson',553.716,87.667,'V band','https://ui.adsabs.harvard.edu/abs/1976AJ.....81..228C','Johnson.V')
,('R','Johnson R','Johnson',693.952,209.333,'R band','https://ui.adsabs.harvard.edu/abs/1965CoLPL...3...73J','Johnson.R')
,('I','Johnson I','Johnson',878.066,220.545,'I band','https://ui.adsabs.harvard.edu/abs/1965CoLPL...3...73J','Johnson.I')
,('J','Johnson J','Johnson',1248.781,370.767,'J band','https://ui.adsabs.harvard.edu/abs/1965CoLPL...3...73J','Johnson.J')
,('u_SDSS','ugriz u','SDSS',357.218,56.58,'SDSS u full transmission','https://ui.adsabs.harvard.edu/abs/1998AJ....116.3040G','SDSS.u')
,('g_SDSS','ugriz g','SDSS',475.082,117.563,'SDSS g full transmission','https://ui.adsabs.harvard.edu/abs/1998AJ....116.3040G','SDSS.g')
,('r_SDSS','ugriz r','SDSS',620.429,113.056,'SDSS r full transmission','https://ui.adsabs.harvard.edu/abs/1998AJ....116.3040G','SDSS.r')
,('i_SDSS','ugriz i','SDSS',751.927,125.33,'SDSS i full transmission','https://ui.adsabs.harvard.edu/abs/1998AJ....116.3040G','SDSS.i')
,('z_SDSS','ugriz z','SDSS',899.226,99.85,'SDSS z full transmission','https://ui.adsabs.harvard.edu/abs/1998AJ....116.3040G','SDSS.z')
,('C',NULL,NULL,391,110,'C','https://ui.adsabs.harvard.edu/abs/1976AJ.....81..228C',NULL)
,('Y',NULL,NULL,1020,120,'Y',NULL,NULL)
,('K',NULL,NULL,2200,590,'K','https://ui.adsabs.harvard.edu/abs/1965CoLPL...3...73J',NULL)
,('Ks',NULL,NULL,2150,300,'K short',NULL,NULL)
,('H_Aar',NULL,'Aaronson',NULL,NULL,'H band 1.6mu',NULL,NULL)
,('S850',NULL,NULL,850000,NULL,'S850',NULL,NULL)
,('21cm',NULL,NULL,NULL,NULL,'21 cm HI line 1420 Mhz','https://ui.adsabs.harvard.edu/abs/1991rc3..book.....D',NULL)
,('S1.4GHz',NULL,NULL,NULL,NULL,'S1.4GHz',NULL,NULL)
,('S408MHz',NULL,NULL,NULL,NULL,'S408MHz',NULL,NULL)
,('u_CFHT','MegaCam u','MegaCam',369.262,45.642,'MegaCam 3rd generation u filter installed in 2015',NULL,'MegaCam.u')
,('g_CFHT','MegaCam g','MegaCam',482.401,153.224,'MegaCam 3rd generation g filter installed in 2015',NULL,'MegaCam.g')
,('r_CFHT','MegaCam r','MegaCam',642.546,147.766,'MegaCam 3rd generation r filter installed in 2015',NULL,'MegaCam.r')
,('i_CFHT','MegaCam i','MegaCam',772.106,153.812,'MegaCam 3rd generation i filter installed in 2015',NULL,'MegaCam.i')
,('z_CFHT','MegaCam z','MegaCam',900.478,77.401,'MegaCam 3rd generation z filter installed in 2015',NULL,'MegaCam.z')
,('Ks_CFHT','Wircam Ks','Wircam',2149.746,327.046,'Wircam Ks',NULL,'Wircam.Ks')
,('pg',NULL,NULL,NULL,NULL,'Photographic magnitude Holmberg',NULL,NULL)
,('pv',NULL,NULL,NULL,NULL,'Photovisual magnitude Holmberg',NULL,NULL)
,('F475W','ACS_WFC F475W','ACS-WFC',480.231,139.886,'F475W filter for HST ACS_WFC',NULL,'ACS_WFC.F475W')
,('F606W','ACS_WFC F606W','ACS-WFC',603.573,225.34,'F606W filter for HST ACS_WFC',NULL,'ACS_WFC.F606W')
,('F625W','ACS_WFC F625W','ACS-WFC',635.246,138.928,'F625W filter for HST ACS_WFC',NULL,'ACS_WFC.F625W')
,('F775W','ACS_WFC F775W','ACS-WFC',773.077,151.731,'F775W filter for HST ACS_WFC',NULL,'ACS_WFC.F775W')
,('F814W','ACS_WFC F814W','ACS-WFC',812.921,209.815,'F814W filter for HST ACS_WFC',NULL,'ACS_WFC.F814W')
,('F850LP','ACS_WFC F850LP','ACS-WFC',908.026,127.35,'F850LP filter for HST ACS_WFC',NULL,'ACS_WFC.F850LP')
,('F814W_PC','WFPC2-PC F814W','WFPC2-PC',808.047,165.652,'F814W filter for HST WFPC2 planetary camera detector 1',NULL,'WFPC2-PC.F814W')
,('F814W_WF','WFPC2-WF F814W','WFPC2-WF',808.663,167.613,'F814W filter for HST WFPC2 wide field camera detector 4',NULL,'WFPC2-WF.F814W')
,('B_J',NULL,NULL,456.8,123.1,'Photographic B_J SuperCOSMOS from ADPS','https://ui.adsabs.harvard.edu/abs/1980PASP...92..746C',NULL)
,('Rg',NULL,NULL,658.5,72.9,'Gunn-Oke R-band magnitude from the POSS II from ADPS','https://ui.adsabs.harvard.edu/abs/1980PASP...92..746C',NULL)
,('r_T&G',NULL,NULL,651.3,85.5,'r-band Thuan & Gunn 1976 magnitude from ADPS','https://ui.adsabs.harvard.edu/abs/1980PASP...92..746C',NULL)
,('R_F',NULL,NULL,669.3,46.2,'Photographic R_F from ADPS','https://ui.adsabs.harvard.edu/abs/1980PASP...92..746C',NULL)
,('H',NULL,NULL,1650,270,'H band Bessell & Brett, 1988 from ADPS',NULL,NULL)
,("K'",NULL,NULL,2110,320,"K' band Tokunaga et al. 2002 from ADPS",NULL,NULL)
,('B_Bessell','Bessell B','Bessell',441.308,94.762,'Bessell B generic filter','https://ui.adsabs.harvard.edu/abs/1990PASP..102.1181B','Bessell.B')
,('I_Bessell','Bessell I','Bessell',805.988,154.311,'Bessell I generic filter','https://ui.adsabs.harvard.edu/abs/1990PASP..102.1181B','Bessell.I')
,('g_PS1','PS1 g','PAN-STARRS',490.012,114.866,'PS1 g filter','https://ui.adsabs.harvard.edu/abs/2012ApJ...750...99T','PS1.g')
,('r_PS1','PS1 r','PAN-STARRS',624.127,139.773,'PS1 r filter','https://ui.adsabs.harvard.edu/abs/2012ApJ...750...99T','PS1.r')
,('i_PS1','PS1 i','PAN-STARRS',756.376,129.239,'PS1 i filter','https://ui.adsabs.harvard.edu/abs/2012ApJ...750...99T','PS1.i')
,('R_Cousins','Cousins R','Cousins',646.944,151.649,'Cousins R generic filter','https://ui.adsabs.harvard.edu/abs/1976MmRAS..81...25C','Cousins.R')
,('I_Cousins','Cousins I','Cousins',788.559,109.368,'Cousins I generic filter','https://ui.adsabs.harvard.edu/abs/1976MmRAS..81...25C','Cousins.I')
,('T1',NULL,NULL,633,80,'T1','https://ui.adsabs.harvard.edu/abs/1976AJ.....81..228C',NULL)
,('i_BATC',NULL,NULL,665.59,49.1,'9: i-band of the Beijing-Arizona-Taiwan-Connecticut Sky Survey','https://ui.adsabs.harvard.edu/abs/2000PASP..112..691Y',NULL)
,('Halpha',NULL,NULL,656.28,NULL,'H-alpha line','https://ui.adsabs.harvard.edu/abs/2013AJ....145..101K',NULL)
,('I_DENIS','DENIS I','DENIS',793.037,131.111,'DENIS I',NULL,'DENIS.I')
,('J_DENIS','DENIS J','DENIS',1235.743,199.111,'DENIS J',NULL,'DENIS.J')
,('Ks_DENIS','DENIS Ks','DENIS',2162.634,330.194,'DENIS Ks',NULL,'DENIS.Ks')
,('I_Mathewson','Mathewson I','Mathewson',NULL,NULL,'I band for Mathewson system',NULL,NULL)
,('J_2MASS','2MASS J','2MASS',1241.051,214.914,'2MASS J','https://ui.adsabs.harvard.edu/abs/2003AJ....126.1090C','2MASS.J')
,('H_2MASS','2MASS H','2MASS',1651.366,260.965,'2MASS H','https://ui.adsabs.harvard.edu/abs/2003AJ....126.1090C','2MASS.H')
,('Ks_2MASS','2MASS Ks','2MASS',2165.631,278.455,'2MASS Ks','https://ui.adsabs.harvard.edu/abs/2003AJ....126.1090C','2MASS.Ks')
,('Y_UKIDSS','UKIDSS J','UKIDSS',1032.794,102.681,'UKIDSS Y',NULL,'UKIDSS.Y')
,('H_UKIDSS','UKIDSS H','UKIDSS',1642.288,295.217,'UKIDSS H',NULL,'UKIDSS.H')
,('K_UKIDSS','UKIDSS K','UKIDSS',2213.199,351.137,'UKIDSS K',NULL,'UKIDSS.K')
,('W1','W1','WISE',3400.255,635.793,'WISE W1 filter','https://ui.adsabs.harvard.edu/abs/2010AJ....140.1868W','WISE.W1')
,('W2','W2','WISE',4652.008,1107.319,'WISE W2 filter','https://ui.adsabs.harvard.edu/abs/2010AJ....140.1868W','WISE.W2')
,('W3','W3','WISE',12807.578,6275.804,'WISE W3 filter','https://ui.adsabs.harvard.edu/abs/2010AJ....140.1868W','WISE.W3')
,('W4','W4','WISE',22375.303,4739.734,'WISE W4 filter','https://ui.adsabs.harvard.edu/abs/2010AJ....140.1868W','WISE.W4')
,('I1_IRAC','IRAC3.6','IRAC',3557.259,743.171,'Spitzer IRAC 3.6um','https://ui.adsabs.harvard.edu/abs/2004ApJS..154...10F','IRAC.I1')
,('I2_IRAC','IRAC4.5','IRAC',4504.928,1009.682,'Spitzer IRAC 4.5um','https://ui.adsabs.harvard.edu/abs/2004ApJS..154...10F','IRAC.I2')
,('12mu_IRAS','IRAS 12mu','IRAS',11598.03,6930.643,'IRAS 12 μm,https://ui.adsabs.harvard.edu/abs/1984ApJ...278L...1N','IRAS.12mu')
,('25mu_IRAS','IRAS 25mu','IRAS',23877.516,11254.287,'IRAS 25 μm','https://ui.adsabs.harvard.edu/abs/1984ApJ...278L...1N','IRAS.25mu')
,('60mu_IRAS','IRAS 60mu','IRAS',61484.959,32760.504,'IRAS 60 μm','https://ui.adsabs.harvard.edu/abs/1984ApJ...278L...1N','IRAS.60mu')
,('100mu_IRAS','IRAS 100mu','IRAS',101948.641,32224.987,'IRAS 100 μm','https://ui.adsabs.harvard.edu/abs/1984ApJ...278L...1N','IRAS.100mu')
;

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
