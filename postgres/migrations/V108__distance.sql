BEGIN;
------------------------------------------------------------------
--------          Distance catalog (level 1)             ---------
------------------------------------------------------------------

DROP SCHEMA IF EXISTS distance CASCADE ;

CREATE SCHEMA distance ;
COMMENT ON SCHEMA distance IS 'Distance catalog' ;


CREATE TYPE distance.class	AS ENUM ('direct' , 'standard candle' , 'standard ruler' , 'standard siren') ;
COMMENT ON TYPE distance.class	IS 'direct = direct distance measurements without assumptions about object nature; standard candle = luminosity based distance indicators; standard ruler = phisical size based distance indicators; standard siren = gravitational waves indicators' ;


-------- Distance measurement method --------------
CREATE TABLE distance.method (
  id	text	PRIMARY KEY
, class	distance.class	NOT NULL	DEFAULT 'standard candle'
, short	text	NOT NULL
, description	text
) ;

COMMENT ON TABLE distance.method	IS 'List of distance determination methods' ;
COMMENT ON COLUMN distance.method.id	IS 'Distance determination method ID' ;
COMMENT ON COLUMN distance.method.class	IS 'Distance indicator class: direct, standard candle, standard ruler, standard siren' ;
COMMENT ON COLUMN distance.method.short	IS 'Short description of the method' ;
COMMENT ON COLUMN distance.method.description	IS 'Distance determination method description' ;


-------- Method calibration --------------
CREATE TABLE distance.calib (
  id	text	PRIMARY KEY
, method	text	NOT NULL	REFERENCES distance.method (id)	ON DELETE restrict	ON UPDATE cascade
, bib	integer	NOT NULL	REFERENCES common.bib (id)	ON DELETE restrict	ON UPDATE cascade
, relation	text	NOT NULL
, description	text
) ;
CREATE INDEX ON distance.calib (method) ;

COMMENT ON TABLE distance.calib	IS 'Distance method calibration' ;
COMMENT ON COLUMN distance.calib.id	IS 'Calibration ID' ;
COMMENT ON COLUMN distance.calib.method	IS 'Distance method ID' ;
COMMENT ON COLUMN distance.calib.relation	IS 'Relation description' ;
COMMENT ON COLUMN distance.calib.bib	IS 'Bibliography ID' ;
COMMENT ON COLUMN distance.calib.description	IS 'Distance calibration description' ;


-------- Distance Dataset -------------------------
CREATE TABLE distance.dataset (
  id	serial	PRIMARY KEY
, calib	text	NOT NULL	REFERENCES distance.calib (id)	ON DELETE restrict	ON UPDATE cascade
, src	integer	REFERENCES rawdata.tables (id)	ON DELETE restrict	ON UPDATE cascade
) ;
CREATE INDEX ON distance.dataset (calib) ;

COMMENT ON TABLE distance.dataset	IS 'Dataset' ;
COMMENT ON COLUMN distance.dataset.id	IS 'Dataset ID' ;
COMMENT ON COLUMN distance.dataset.calib	IS 'Calibration' ;
COMMENT ON COLUMN distance.dataset.src	IS 'Source table' ;


---------- Distance data --------------------------
CREATE TABLE distance.data (
  id	serial	PRIMARY KEY
, pgc	integer	NOT NULL	REFERENCES common.pgc (id)	ON DELETE restrict	ON UPDATE cascade
, modulus	real	NOT NULL	CHECK (modulus>15 and modulus<40)
, e_modulus	real	CHECK (e_modulus>0 and e_modulus<0.5)
, quality	common.quality	NOT NULL	DEFAULT 'ok'
, dataset	integer	NOT NULL	REFERENCES distance.dataset (id)	ON DELETE restrict	ON UPDATE cascade
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
, UNIQUE (pgc,dataset)
) ;


---------- List of excluded measurements ----------
CREATE TABLE distance.excluded (
  id	integer	PRIMARY KEY	REFERENCES distance.data (id)	ON DELETE restrict	ON UPDATE cascade
, bib	integer	NOT NULL	REFERENCES common.bib (id)	ON DELETE restrict	ON UPDATE cascade
, note	text	NOT NULL
, modification_time	timestamp without time zone	NOT NULL	DEFAULT now()
) ;

COMMENT ON TABLE distance.excluded	IS 'List of measurements excluded from consideration' ;
COMMENT ON COLUMN distance.excluded.id	IS 'measurement ID' ;
COMMENT ON COLUMN distance.excluded.bib	IS 'Bibliography reference where given measurement was marked as wrong' ;
COMMENT ON COLUMN distance.excluded.note	IS 'Note on exclusion' ;
COMMENT ON COLUMN distance.excluded.modification_time	IS 'Timestamp when the record was added to the database' ;


---------- List of distance measurements ----------
CREATE VIEW distance.list AS
SELECT
  d.id
, d.pgc
, d.modulus
, d.e_modulus
, d.quality
, d.dataset
, ds.calib
, c.method
, ds.src
, t.bib
, t.datatype
, obsol.bib IS NULL and excl.id IS NULL	AS isok
, greatest( d.modification_time, obsol.modification_time, excl.modification_time )	AS modification_time
FROM
  distance.data AS d
  LEFT JOIN distance.dataset AS ds ON (ds.id=d.dataset)
  LEFT JOIN distance.calib AS c ON (c.id=ds.calib)
  LEFT JOIN rawdata.tables AS t ON (t.id=ds.src)
  LEFT JOIN common.obsoleted AS obsol ON (obsol.bib=t.bib)
  LEFT JOIN distance.excluded AS excl ON (excl.id=d.id)
;

COMMENT ON VIEW distance.list	IS 'Distance measurement catalog' ;
COMMENT ON COLUMN distance.list.id	IS 'Measurement ID' ;
COMMENT ON COLUMN distance.list.pgc	IS 'PGC number of the object' ;
COMMENT ON COLUMN distance.list.modulus	IS 'Distance modulus [mag]' ;
COMMENT ON COLUMN distance.list.e_modulus	IS 'Distance modulus error [mag]' ;
COMMENT ON COLUMN distance.list.quality	IS 'Measurement quality' ;
COMMENT ON COLUMN distance.list.dataset	IS 'Dataset ID' ;
COMMENT ON COLUMN distance.list.calib	IS 'Calibration ID' ;
COMMENT ON COLUMN distance.list.method	IS 'Distance measurement method' ;
COMMENT ON COLUMN distance.list.src	IS 'Data source ID' ;
COMMENT ON COLUMN distance.list.bib	IS 'Bibliography ID' ;
COMMENT ON COLUMN distance.list.datatype	IS 'Data types: regular,reprocessing,preliminary,compilation' ;
COMMENT ON COLUMN distance.list.isok	IS 'True if the measurement is actual and False if it is obsoleted or excluded' ;
COMMENT ON COLUMN distance.list.modification_time	IS 'Timestamp when the record was added to the database' ;



---------- Methods --------------------------------
INSERT INTO distance.method (id,class,short,description) VALUES
  ( 'DEB'   , 'direct' , 'Detached Eclipsing Binary stars' , 'The Detached Eclipsing Binaries (DEB) provide an accurate geometric method for distance determination. The fundamental parameters of the stars (the radii, effective temperatures, masses, and luminosities) can be determined from the light and radial velocity curves of an eclipsing binary. This method is independent of any intermediate calibration steps.' )
, ( 'DSM'   , 'direct' , 'Dense Shell Method' , 'The Dense Shell Method relies on observations of an expanding dense shell in SN IIn and allows one to determine the linear size of such a shell in absolute units, and hence the distance to it, without addressing the cosmological distance ladder.' )
, ( 'EPM'   , 'direct' , 'Expanding Photosphere Method' , 'The Expanding Photosphere Method (EPM) is a geometric distance determination technique based on comparing radial velocities with proper motion of an expanding shell after supernova explosion.' )
, ( 'ESM'   , 'direct' , 'Expanding Shock front Method' , 'The Expanding Shock front Method (ESM) is a geometric distance determination technique based on comparing radial velocities with proper motion of an expanding shell after supernova explosion.' )
, ( 'Maser' , 'direct' , 'Maser emission in an accretion disk' , 'The method is based on study of kinematics of an accretion disk around a supermassive black hole by a radio maser emission. It gives a direct geometric estimate of an absolute distance. Humphreys et al. (2013, ApJ, 775, 13) measured the distance of 7.6 Mpc with 3% uncertainty to the Seyfert II galaxy NGC 4258 using 10 years observations of the H2O maser.' )
, ( 'SEAM'  , 'direct' , 'The Spectral-fitting Expanding Atmosphere Method' , 'The SEAM is similar to the EPM in spirit, but it avoids the use of dilution factors and color temperatures. Velocities are determined accurately by actually fitting synthetic and observed spectra. The radius is still determined by the relationship R = vt (which is an excellent approximation because all SNe quickly reach homologous expansion), and the explosion time is found by demanding self-consistency. The SEAM uses all the spectral information available in the observed spectra simultaneously, which broadens the base of parameter determination.' )

, ( 'Asteroseismic' , 'standard candle' , 'Asteroseismic distance' , 'A method  is based on a relation between the frequency of maximum oscillation power Vmax, the large frequency separation dV, the apparent magnitude V, the metallicity Z, and the distance modulus (m-M)0.' )
, ( 'BBSLF' , 'standard candle' , 'Luminosity Function of Brightest Blue Stars' , NULL )
, ( 'BRSLF' , 'standard candle' , 'Luminosity Function of Brightest Red Supergiants' , NULL )
, ( 'BS'    , 'standard candle' , 'mean absolute magnitude of Brightest Stars' , NULL )
, ( 'BS3B'  , 'standard candle' , 'mean absolute magnitude of three Brightest Blue Stars' , NULL )
, ( 'BS3R'  , 'standard candle' , 'mean absolute magnitude of three Brightest Red Stars' , NULL )

, ( 'BHB'   , 'standard candle' , 'Blue Horizontal Branch stars' , 'This method uses the blue horizontal branch (BHB) stars as standard candles. Carretta et al. (2000, ApJ, 533, 215) give the relation between absolute magnitude and metallicity of HB: MV(HB) = (0.13±0.09)([Fe/H]+1.5) + (0.54±0.07).' )
, ( 'HB'    , 'standard candle' , 'Horizontal Branch stars' , 'This method uses the horizontal branch (HB) stars as standard candles. Carretta et al. (2000, ApJ, 533, 215) give the relation between absolute magnitude and metallicity of HB: MV(HB) = (0.13±0.09)([Fe/H]+1.5) + (0.54±0.07).' )
, ( 'RHB'   , 'standard candle' , 'Red Horizontal Branch stars' , NULL )
, ( 'ZAHB'  , 'standard candle' , 'Zero-Age Horizontal Branch' , NULL )
, ( 'BL'    , 'standard candle' , 'Blue Loop stars' , 'This method is based on a fit of the magnitude of the He-burning Blue Loop stars with theoretical isochrones. Because of the large uncertainties in the theoretical models, this method cannot be considered as a reliable distance indicator.' )
, ( 'CMD'   , 'standard candle' , 'Color Magnitude Diagram' , 'It uses various features of the composite colour-magnitude diagram (CMD) of a galaxy resolved into individual stars to estimate the distance by comparison with template CMD or with theoretical isochrones. For instance, Dolphin (2000, ApJ, 531, 804) develops the software which fits the observed CMD with synthetic data, to estimate in the same time the distance and the star formation history of a galaxy.' )
, ( 'CS'    , 'standard candle' , 'Carbon Stars' , 'The carbon-rich Stars (CS) in the TP-AGB phase form the horizontal red tail on CMD, at about 0.5 mag brighter than the TRGB. Battinelli & Demers (2005, A&A, 442, 159) find the absolute I-band magnitude of CS as a function of the metallicity of the parent galaxy: <MI> = -4.33+0.28[Fe/H].' )
, ( 'Cepheids' , 'standard candle' ,  'period-luminosity relation for Cepheids' , 'This is one of the most important standard candles. The method is based on the period-luminosity (PL) relation for Cepheid variable stars. There are many calibrations of the relation in different pass-bands using the Galactic or Large Magellanic Cloud (LMC) PL relation, for example, the Hubble Space Telescope Key Project On the Extragalactic Distance Scale (Freedman et al., 2001, ApJ, 553, 47), the HIPPARCOS trigonometric parallaxes (Feast & Catchpole, 1997, MNRAS, 286, L1), or the Baade-Wesselink methods (Storm et al., 2011, A&A, 534, A95). It is foreseen that the calibration will be dramatically improved in the coming years thanks to the GAIA astrometric satellite which starts to operate now.' )
, ( 'FGLR'  , 'standard candle' , 'Flux-weighted Gravity-Luminosity Relationship' , 'The Flux-weighted Gravity-Luminosity Relationship (FGLR) is a technique to derive the distance from a spectral analysis of the B and A supergiant stars (Kudritzki et al., 2008, ApJ, 681, 269). It is based on a tight correlation between the absolute bolometric magnitude and the flux-weighted gravity, g/Teff^4.' )
, ( 'GCLF'  , 'standard candle' , 'Globular Cluster Luminosity Function' , 'The old globular cluster luminosity function (GCLF) method uses the peak (or turnover, TO) of the GCLF as a standard candle. For instance, Di Criscienzo et al. (2006, MNRAS, 365, 1357) derive MV,TO=-7.66±0.09 with adopted the LMC distance modulus of 18.50.' )
, ( 'GCR'   , 'standard ruler'  , 'Globular Cluster half-light Radii' , 'The median of the Globular Cluster half-light Radii (GCR) of 2.7±0.3 pc (Jordan et al., 2005, ApJ, 634, 1002) can be used as a standard ruler for distance estimate. The half-light radius of individual GC should be corrected for colour, surface brightness, and host galaxy colour.' )
, ( 'MS'    , 'standard candle' , 'Main Sequence with clear turn-off' , 'This method fits the position of the Main Sequence below the turn-off with a theoretical isochrones or with template CMD. It relates to the CMD distance determination method.' )
, ( 'Miras' , 'standard candle' , 'period-luminosity relation for Miras' , 'Mira Ceti stars are long period variable stars in the asymptotic giant branch phase. Ita & Matsunaga (2011, MNRAS, 412, 2345), among others, derive the period-magnitude relations for Mira-like variables in the LMC using bolometric, near- and mid-infrared magnitudes.' )
, ( 'PNLF'  , 'standard candle' , 'Planetary Nebula Luminosity Function' , 'This method uses the sharp exponential truncation of the planetary nebulae luminosity function (PNLF) as a standard candle. The zero-point, M*=-4.48, is based on the M 31 distance of 710 kpc (Ciardullo et al., 2002, ApJ, 577, 31).' )
, ( 'RC'    , 'standard candle' , 'Red Clump stars' , 'The Red Clump (RC) is populated by core helium-burning stars of intermediate age. Their mean absolute magnitude provides a standard candle for distance determination. Girardi & Salaris (2001, MNRAS, 323, 109) find important non-linear dependences on both the age and the metallicity of the stellar population.' )
, ( 'RRLyrae' , 'standard candle' , 'RR Lyrae variable stars' , 'The method is based on the mean absolute magnitude for RR Lyrae variable stars, which depends on metallicity: MV(HB) = (0.18±0.09)([Fe/H]+1.5) + (0.57±0.07) (Carretta et al. 2000, ApJ, 533, 215).' )
, ( 'RSV'   , 'standard candle' , 'period-luminosity relation for Red Supergiant Variable stars' , 'This method uses the period-luminosity relation for the Red Supergiant Variable (RSV) stars. The calibration of the PL relation by Pierce et al. (2000, MNRAS, 313, 271) adopts the distance modulus of 18.50 mag for LMC. The RSVs as well as the Miras are long period variable stars.' )
, ( 'SBF'   , 'standard candle' , 'Surface Brightness Fluctuations' , 'The Surface Brightness Fluctuations (SBF) method relies on the luminosity fluctuations that arise from the counting statistics of stars contributing the flux in each pixel of an image (Tonry & Schneider 1988, AJ, 96, 807). The absolute fluctuation magnitude depends on the stellar populations and, consequently, on the colour of the galaxy. It can only be applied to old stellar populations.' )
, ( 'SNIa'  , 'standard candle' , 'SN Ia' , 'Because of their extremely high luminosity and regular behaviour the type Ia supernovae (SN Ia) provide a powerful tool for measuring cosmological distances. The method uses the relationship between the light-curve shape and the maximum luminosity of a SN Ia.' )
, ( 'TRGB'  , 'standard candle' , 'Tip of the Red Giant Branch' , 'The Tip of the Red Giant Branch (TRGB) is an excellent distance indicator for nearby galaxies resolved into individual stars. The method, relying on the old stellar population, can be used for galaxies of any morphological types. Thanks to the shallow colour-dependence of the magnitude of the TRGB in the I-band, the method is one of the most precise distance indicators. For example, Rizzi et al. (2007, ApJ, 661, 815) calibrates the zero-point of the TRGB method using HB stars: MIJC = -4.05(±0.02) + 0.22(±0.01)[(V-I)-1.6].' )
, ( 'spec'  , 'standard candle' , 'Spectroscopic classification of individual stars' , NULL )
, ( 'BWM'   , 'standard candle' , 'The Baade-Wesselink method' , NULL )

, ( 'TF'    , 'standard candle' , 'Tully-Fisher relation' , 'The Tully-Fisher (TF) is a standard candle based on empirical relationship between the absolute magnitude of a spiral galaxy and its maximum rotational velocity, estimated by a HI line width The recent calibration I-band TF relation gives MIb,i,k = -21.39-8.81(log Wimx-2.5) (Tully & Courtois 2012, ApJ, 749, 78).' )
, ( 'BTF'   , 'standard candle' , 'Baryonic Tully-Fisher relation' , 'The Baryonic Tully-Fisher (BTF) relation uses relationship between the amplitude of rotation and the baryonic mass of the galaxy. This relation takes into account not only the stellar light from optical data as in the original TF relation, but also the mass of gas in neutral and molecular forms. The BTF relation is comparable to the TF one for giant spiral galaxies, and it represents an improvement for dwarf galaxies with circular velocities below 90 km s-1 (McGaugh et al 2000, ApJ, 533, L99) where the cold gas represents an important and variable dynamical component. The BTF can also be applied to gas rich dwarf elliptical galaxies (De Rijcke et al. 2007, ApJ, 659, 1172).' )
, ( 'FJ'    , 'standard ruler'  , 'Faber-Jackson relation' , 'The Faber-Jackson (FB) relation provides a standard candle for elliptical and early-type galaxies based on the relationship between absolute magnitude and central velocity dispersion.' )
, ( 'FP'    , 'standard ruler'  , 'Fundamental Plane' , 'The Fundamental Plane (FP) is a distance determination method for early-type galaxies based on relation between the absolute magnitude, effective radius, velocity dispersion, and mean surface brightness. log D = logre - 1.24 logσ + 0.82 log<I>e +0.173 (Kelson et al. 2000, ApJ, 529, 768).' )
, ( 'SB-M'  , 'standard candle' , 'Surface Brightness-total Magnitude relation' , 'The Surface Brightness-total Magnitude relation can be considered as rough distance estimate for small mass elliptical galaxies.' )
, ( 'Sersic-M' , 'standard candle' , 'Sersic index-total Magnitude relation' , 'The Sersic index-total Magnitude relation (Sersic-M) can be considered as rough distance estimate for small mass elliptical galaxies.' )
, ( 'Sosie' , 'standard candle' , 'Look-alike galaxies' , 'The method of look alike (sosie in French) is proposed by Paturel (1984, ApJ, 282, 382). It is based on the idea that galaxies with the same morphological type, the same inclination, and the same HI line width must to have the same absolute luminosity according to the TF relation.' )

, ( 'GW'    , 'standard siren' , 'Gravitational Wave' , NULL )
;

COMMIT;