BEGIN;

-----------------------------------------------
-------- Distance measurements schema ---------
-----------------------------------------------
CREATE SCHEMA IF NOT EXISTS distance;
COMMENT ON SCHEMA distance IS 'Catalog of the distance measurements';

CREATE TYPE distance.IndicatorType AS ENUM ( 'direct', 'candle', 'ruler', 'siren' ) ;

COMMENT ON TYPE distance.IndicatorType IS '{
"description": "Classification of the standards used for the distance measurement",
"values": {
  "direct": "Direct distance measurements without assumptions about object nature",
  "quasi-geometric": "Geometric measurements based on additional model assumptions, i.e. atmosphere/radiative transfer models",
  "standard candle": "Luminosity based distance indicators (standard candle)",
  "standard ruler": "Phisical size based distance indicators (standard ruler)",
  "standard siren": "Gravitational waves indicators (standard siren)",
  "luminosity-based scaling relation": "Secondary distance indicators linking luminosity to galaxy properties",
  "size-based scaling relation": "Secondary distance indicators linking size to galaxy properties"
  }
}';


------------ Methods --------------
CREATE TABLE distance.methods (
  id	Text	PRIMARY KEY
, indicator	distance.IndicatorType	NOT NULL	DEFAULT 'standard candle'
, short	Text	NOT NULL
, description	Text	NOT NULL
) ;

COMMENT ON TABLE distance.methods	IS 'Distance determination methods' ;
COMMENT ON COLUMN distance.methods.id	IS 'Method ID' ;
COMMENT ON COLUMN distance.methods.indicator	IS 'Distance indicator type (direct, standard candle, standard ruler, standard siren)' ;
COMMENT ON COLUMN distance.methods.short	IS 'Short description of the method';
COMMENT ON COLUMN distance.methods.description	IS 'Method description' ;


---------- Calibration -----------
CREATE TABLE distance.calibrations (
  id	Text	PRIMARY KEY
, method	Text	NOT NULL	REFERENCES distance.methods (id) ON DELETE restrict ON UPDATE cascade
, bibcode	Char(19)	NOT NULL	REFERENCES common.bib (id) ON DELETE restrict ON UPDATE cascade
, relation	Text	NOT NULL
, description	Text	NOT NULL
, UNIQUE (method, bibcode)
);

COMMENT ON TABLE distance.calib	IS 'Calibration of the distance method';
COMMENT ON COLUMN distance.calib.id	IS 'Calibration ID';
COMMENT ON COLUMN distance.calib.method	IS 'Distance method ID';
COMMENT ON COLUMN distance.calib.relation	IS 'Relation description';
COMMENT ON COLUMN distance.calib.bibcode	IS 'ADS bibcode';
COMMENT ON COLUMN distance.calib.description	IS 'Distance calibration description';


------- Distance catalog -------
CREATE TABLE distance.data (
  record_id	Text	NOT NULL	REFERENCES layer0.records(id) ON UPDATE cascade ON DELETE restrict
, modulus	Real	NOT NULL
, em_modulus	Real
, ep_modulus	Real
, quality	common.QualityType	NOT NULL	DEFAULT 'regular'
, calib_id	Text	NOT NULL	REFERENCES distance.calibrations(id) ON UPDATE cascade ON DELETE restrict
, PRIMARY KEY (record_id, calib_id)
, CHECK ( (em_modulus IS NULL and ep_modulus IS NULL) or (em_modulus IS NOT NULL and ep_modulus IS NOT NULL) )
) ;
CREATE INDEX ON distance.data (record_id) ;
CREATE INDEX ON distance.data (calib_id) ;

COMMENT ON TABLE distance.data	IS 'Redshift independent distance catalog' ;
COMMENT ON COLUMN distance.data.record_id	IS 'Record ID';
COMMENT ON COLUMN distance.data.modulus	IS '{"description": "Distance modulus", "unit": "mag", "ucd": "phot.mag.distMod"}' ;
COMMENT ON COLUMN distance.data.em_modulus	IS '{"description": "Statustucal plus uncertainty of the distance modulus", "unit": "mag", "ucd": "stat.error;phot.mag.distMod"}' ;
COMMENT ON COLUMN distance.data.ep_modulus	IS '{"description": "Statustucal minus uncertainty of the distance modulus", "unit": "mag", "ucd": "stat.error;phot.mag.distMod"}' ;
COMMENT ON COLUMN distance.data.calib_id	IS 'ID of the calibration of the distance method' ;


---------- Methods --------------------------------
INSERT INTO distance.methods (id, indicator, short, description) VALUES
  ( 'parallax',	'direct',	'Trigonometric parallax',	NULL )
, ( 'DEB',	'direct',	'Detached Eclipsing Binary stars',	'The Detached Eclipsing Binaries (DEB) provide an accurate geometric method for distance determination. The fundamental parameters of the stars (the radii, effective temperatures, masses, and luminosities) can be determined from the light and radial velocity curves of an eclipsing binary. This method is independent of any intermediate calibration steps.' )
, ( 'Maser',	'direct',	'Maser emission in an accretion disk',	'The method is based on study of kinematics of an accretion disk around a supermassive black hole by a radio maser emission. It gives a direct geometric estimate of an absolute distance. Humphreys et al. (2013, ApJ, 775, 13) measured the distance of 7.6 Mpc with 3% uncertainty to the Seyfert II galaxy NGC 4258 using 10 years observations of the H2O maser.' )

, ( 'BWM',	'quasi-geometric',	'The Baade-Wesselink method',	NULL )
, ( 'DSM',	'quasi-geometric',	'Dense Shell Method',	'The Dense Shell Method relies on observations of an expanding dense shell in SN IIn and allows one to determine the linear size of such a shell in absolute units, and hence the distance to it, without addressing the cosmological distance ladder.' )
, ( 'EPM',	'quasi-geometric',	'Expanding Photosphere Method',	'The Expanding Photosphere Method (EPM) is a geometric distance determination technique based on comparing radial velocities with proper motion of an expanding shell after supernova explosion.' )
, ( 'ESM',	'quasi-geometric',	'Expanding Shock front Method',	'The Expanding Shock front Method (ESM) is a geometric distance determination technique based on comparing radial velocities with proper motion of an expanding shell after supernova explosion.' )
, ( 'SEAM',	'quasi-geometric',	'The Spectral-fitting Expanding Atmosphere Method',	'The SEAM is similar to the EPM in spirit, but it avoids the use of dilution factors and color temperatures. Velocities are determined accurately by actually fitting synthetic and observed spectra. The radius is still determined by the relationship R = vt (which is an excellent approximation because all SNe quickly reach homologous expansion), and the explosion time is found by demanding self-consistency. The SEAM uses all the spectral information available in the observed spectra simultaneously, which broadens the base of parameter determination.' )

, ( 'CMD',	'standard candle',	'Color Magnitude Diagram',	'It uses various features of the composite colour-magnitude diagram (CMD) of a galaxy resolved into individual stars to estimate the distance by comparison with template CMD or with theoretical isochrones. For instance, Dolphin (2000, ApJ, 531, 804) develops the software which fits the observed CMD with synthetic data, to estimate in the same time the distance and the star formation history of a galaxy.' )
, ( 'BL',	'standard candle',	'Blue Loop stars',	'This method is based on a fit of the magnitude of the He-burning Blue Loop stars with theoretical isochrones. Because of the large uncertainties in the theoretical models, this method cannot be considered as a reliable distance indicator.' )
, ( 'CS',	'standard candle',	'Carbon Stars',	'The carbon-rich Stars (CS) in the TP-AGB phase form the horizontal red tail on CMD, at about 0.5 mag brighter than the TRGB. Battinelli & Demers (2005, A&A, 442, 159) find the absolute I-band magnitude of CS as a function of the metallicity of the parent galaxy: <MI> = -4.33+0.28[Fe/H].' )
, ( 'MS',	'standard candle',	'Main Sequence with clear turn-off',	'This method fits the position of the Main Sequence below the turn-off with a theoretical isochrones or with template CMD. It relates to the CMD distance determination method.' )
, ( 'HB',	'standard candle',	'Horizontal Branch stars',	'This method uses the horizontal branch (HB) stars as standard candles. Carretta et al. (2000, ApJ, 533, 215) give the relation between absolute magnitude and metallicity of HB: MV(HB) = (0.13±0.09)([Fe/H]+1.5) + (0.54±0.07).' )
, ( 'BHB',	'standard candle',	'Blue Horizontal Branch stars',	'This method uses the blue horizontal branch (BHB) stars as standard candles. Carretta et al. (2000, ApJ, 533, 215) give the relation between absolute magnitude and metallicity of HB: MV(HB) = (0.13±0.09)([Fe/H]+1.5) + (0.54±0.07).' )
, ( 'RHB',	'standard candle',	'Red Horizontal Branch stars',	NULL )
, ( 'ZAHB',	'standard candle',	'Zero-Age Horizontal Branch',	NULL )
, ( 'RC',	'standard candle',	'Red Clump stars',	'The Red Clump (RC) is populated by core helium-burning stars of intermediate age. Their mean absolute magnitude provides a standard candle for distance determination. Girardi & Salaris (2001, MNRAS, 323, 109) find important non-linear dependences on both the age and the metallicity of the stellar population.' )
, ( 'TRGB',	'standard candle',	'Tip of the Red Giant Branch',	'The Tip of the Red Giant Branch (TRGB) is an excellent distance indicator for nearby galaxies resolved into individual stars. The method, relying on the old stellar population, can be used for galaxies of any morphological types. Thanks to the shallow colour-dependence of the magnitude of the TRGB in the I-band, the method is one of the most precise distance indicators. For example, Rizzi et al. (2007, ApJ, 661, 815) calibrates the zero-point of the TRGB method using HB stars: MIJC = -4.05(±0.02) + 0.22(±0.01)[(V-I)-1.6].' )

, ( 'SBF',	'standard candle',	'Surface Brightness Fluctuations',	'The Surface Brightness Fluctuations (SBF) method relies on the luminosity fluctuations that arise from the counting statistics of stars contributing the flux in each pixel of an image (Tonry & Schneider 1988, AJ, 96, 807). The absolute fluctuation magnitude depends on the stellar populations and, consequently, on the colour of the galaxy. It can only be applied to old stellar populations.' )

, ( 'Cepheids',	'standard candle',	'period-luminosity relation for Cepheids',	'This is one of the most important standard candles. The method is based on the period-luminosity (PL) relation for Cepheid variable stars. There are many calibrations of the relation in different pass-bands using the Galactic or Large Magellanic Cloud (LMC) PL relation, for example, the Hubble Space Telescope Key Project On the Extragalactic Distance Scale (Freedman et al., 2001, ApJ, 553, 47), the HIPPARCOS trigonometric parallaxes (Feast & Catchpole, 1997, MNRAS, 286, L1), or the Baade-Wesselink methods (Storm et al., 2011, A&A, 534, A95). It is foreseen that the calibration will be dramatically improved in the coming years thanks to the GAIA astrometric satellite which starts to operate now.' )
, ( 'RRLyrae',	'standard candle',	'RR Lyrae variable stars',	'The method is based on the mean absolute magnitude for RR Lyrae variable stars, which depends on metallicity: MV(HB) = (0.18±0.09)([Fe/H]+1.5) + (0.57±0.07) (Carretta et al. 2000, ApJ, 533, 215).' )
, ( 'Miras',	'standard candle',	'period-luminosity relation for Miras',	'Mira Ceti stars are long period variable stars in the asymptotic giant branch phase. Ita & Matsunaga (2011, MNRAS, 412, 2345), among others, derive the period-magnitude relations for Mira-like variables in the LMC using bolometric, near- and mid-infrared magnitudes.' )
, ( 'RSV',	'standard candle',	'period-luminosity relation for Red Supergiant Variable stars',	'This method uses the period-luminosity relation for the Red Supergiant Variable (RSV) stars. The calibration of the PL relation by Pierce et al. (2000, MNRAS, 313, 271) adopts the distance modulus of 18.50 mag for LMC. The RSVs as well as the Miras are long period variable stars.' )
, ( 'Asteroseismic',	'standard candle',	'Asteroseismic distance',	'A method  is based on a relation between the frequency of maximum oscillation power Vmax, the large frequency separation dV, the apparent magnitude V, the metallicity Z, and the distance modulus (m-M)0.' )

, ( 'spec',	'standard candle',	'Spectroscopic classification of individual stars',	NULL )
, ( 'FGLR',	'standard candle',	'Flux-weighted Gravity-Luminosity Relationship',	'The Flux-weighted Gravity-Luminosity Relationship (FGLR) is a technique to derive the distance from a spectral analysis of the B and A supergiant stars (Kudritzki et al., 2008, ApJ, 681, 269). It is based on a tight correlation between the absolute bolometric magnitude and the flux-weighted gravity, g/Teff^4.' )

, ( 'GCLF',	'standard candle',	'Globular Cluster Luminosity Function',	'The old globular cluster luminosity function (GCLF) method uses the peak (or turnover, TO) of the GCLF as a standard candle. For instance, Di Criscienzo et al. (2006, MNRAS, 365, 1357) derive MV,TO=-7.66±0.09 with adopted the LMC distance modulus of 18.50.' )
, ( 'PNLF',	'standard candle',	'Planetary Nebula Luminosity Function',	'This method uses the sharp exponential truncation of the planetary nebulae luminosity function (PNLF) as a standard candle. The zero-point, M*=-4.48, is based on the M 31 distance of 710 kpc (Ciardullo et al., 2002, ApJ, 577, 31).' )

, ( 'SNIa',	'standard candle',	'SN Ia',	'Because of their extremely high luminosity and regular behaviour the type Ia supernovae (SN Ia) provide a powerful tool for measuring cosmological distances. The method uses the relationship between the light-curve shape and the maximum luminosity of a SN Ia.' )

, ( 'TF',	'luminosity-based scaling relation',	'Tully-Fisher relation',	'The Tully-Fisher (TF) is a standard candle based on empirical relationship between the absolute magnitude of a spiral galaxy and its maximum rotational velocity, estimated by a HI line width The recent calibration I-band TF relation gives MIb,i,k = -21.39-8.81(log Wimx-2.5) (Tully & Courtois 2012, ApJ, 749, 78).' )
, ( 'BTF',	'luminosity-based scaling relation',	'Baryonic Tully-Fisher relation',	'The Baryonic Tully-Fisher (BTF) relation uses relationship between the amplitude of rotation and the baryonic mass of the galaxy. This relation takes into account not only the stellar light from optical data as in the original TF relation, but also the mass of gas in neutral and molecular forms. The BTF relation is comparable to the TF one for giant spiral galaxies, and it represents an improvement for dwarf galaxies with circular velocities below 90 km s-1 (McGaugh et al 2000, ApJ, 533, L99) where the cold gas represents an important and variable dynamical component. The BTF can also be applied to gas rich dwarf elliptical galaxies (De Rijcke et al. 2007, ApJ, 659, 1172).' )
, ( 'Sosie',	'luminosity-based scaling relation',	'Look-alike galaxies',	'The method of look alike (sosie in French) is proposed by Paturel (1984, ApJ, 282, 382). It is based on the idea that galaxies with the same morphological type, the same inclination, and the same HI line width must to have the same absolute luminosity according to the TF relation.' )
, ( 'FJ',	'luminosity-based scaling relation',	'Faber-Jackson relation',	'The Faber-Jackson (FB) relation provides a standard candle for elliptical and early-type galaxies based on the relationship between absolute magnitude and central velocity dispersion.' )
, ( 'SB-M',	'luminosity-based scaling relation',	'Surface Brightness-total Magnitude relation',	'The Surface Brightness-total Magnitude relation can be considered as rough distance estimate for small mass elliptical galaxies.' )
, ( 'Sersic-M',	'luminosity-based scaling relation',	'Sersic index-total Magnitude relation',	'The Sersic index-total Magnitude relation (Sersic-M) can be considered as rough distance estimate for small mass elliptical galaxies.' )

, ( 'BS',	'luminosity-based scaling relation',	'Mean absolute magnitude of Brightest Stars',	NULL )
, ( 'BS3B',	'luminosity-based scaling relation',	'Mean absolute magnitude of three Brightest Blue Stars',	NULL )
, ( 'BS3R',	'luminosity-based scaling relation',	'Mean absolute magnitude of three Brightest Red Stars',	NULL )
, ( 'BBSLF',	'luminosity-based scaling relation',	'Luminosity Function of Brightest Blue Stars',	NULL )
, ( 'BRSLF',	'luminosity-based scaling relation',	'Luminosity Function of Brightest Red Supergiants',	NULL )

, ( 'GCR',	'standard ruler',	'Globular Cluster half-light Radii',	'The median of the Globular Cluster half-light Radii (GCR) of 2.7±0.3 pc (Jordan et al., 2005, ApJ, 634, 1002) can be used as a standard ruler for distance estimate. The half-light radius of individual GC should be corrected for colour, surface brightness, and host galaxy colour.' )

, ( 'FP',	'size-based scaling relation',	'Fundamental Plane',	'The Fundamental Plane (FP) is a distance determination method for early-type galaxies based on relation between the absolute magnitude, effective radius, velocity dispersion, and mean surface brightness. log D = logre - 1.24 logσ + 0.82 log<I>e +0.173 (Kelson et al. 2000, ApJ, 529, 768).' )

, ( 'GW',	'standard siren',	'Gravitational Wave',	NULL )
;

COMMIT ;
