BEGIN;

-----------------------------------------------
-------- Distance measurements schema ---------
-----------------------------------------------
CREATE SCHEMA IF NOT EXISTS distance;
COMMENT ON SCHEMA distance IS 'Catalog of the distance measurements';

CREATE TYPE distance.IndicatorType AS ENUM ( 'direct', 'quasi-geometric', 'standard candle', 'standard ruler', 'standard siren', 'luminosity-based scaling relation', 'size-based scaling relation' ) ;

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
, bibcode	Char(19)	REFERENCES common.bib (id) ON DELETE restrict ON UPDATE cascade
, description	json
, UNIQUE (method, bibcode)
);

COMMENT ON TABLE distance.calib	IS 'Calibration of the distance method';
COMMENT ON COLUMN distance.calib.id	IS 'Calibration ID';
COMMENT ON COLUMN distance.calib.method	IS 'Distance method ID';
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


-------------------- Calibrations -------------------------
INSERT INTO distance.calibrations (id, method, bibcode, description) VALUES
  ('Maser',	'Maser',	NULL,	NULL )

, ('DSM:Blinnikov+2012',	'DSM',	'2012JETPL..96..153B',	NULL )
, ('EPM:Dessart+2005',	'EPM',	'2005A&A...439..671D',	'{"description": "Dilution factor from 2005A&A...439..671D"}' )
, ('EPM:Eastman+1996',	'EPM',	'1996ApJ...466..911E',	'{"description": "Dilution factor from 1996ApJ...466..911E"}' )
, ('EPM:Hamuy+2001',	'EPM',	'2001ApJ...558..615H',	'{"description": "Dilution factor from 2001ApJ...558..615H"}' )
, ('SEAM:Baron+2004',	'SEAM',	'2004ApJ...616L..91B',	'{"description": "based on the generalized stellar atmosphere code PHOENIX"}' )

, ('TRGB:Bellazzini+2001',	'TRGB',	'2001ApJ...556..635B',	'{"relation": "Mbol(TRGB)=-0.12*[Fe/H]-3.76, MI(TRGB)=0.14*[Fe/H]^2+0.48*[Fe/H]-3.66"}' )
, ('TRGB:Bellazzini+2004',	'TRGB',	'2004A&A...424..199B',	'{"relation": "MI(TRGB)=-4.05, MJ(TRGB)=-5.20, MH(TRGB)=-5.94, MK(TRGB)=-6.04 for Omega Cen", "anchor":"Omega Cen"}' )
, ('TRGB:Bellazzini+2004B',	'TRGB',	'2004MNRAS.354..708B',	'{"relation": "MI(TRGB)=0.258*[M/H]^2+0.676*[M/H]-3.629, [M/H]=[Fe/H]+log(0.638*10^[alpha/Fe]+0.362)"}' )
, ('TRGB:Bellazzini2008',	'TRGB',	'2008MmSAI..79..440B',	'{"relation": "MI(TRGB)=0.080*(V-I)0^2-0.194*(V-I)0-3.939 is based on TRGB:Bellazzini+2001; MiSDSS(TRGB)=-3.44 +-0.1 for [Fe/H]<=-1.0; MzSDSS(TRGB)=-3.67 +-0.1 for [Fe/H]<=-0.4"}' )
, ('TRGB:Bressan+2012',	'TRGB',	'2012MNRAS.427..127B',	'{"description": "PARSEC: stellar tracks and isochrones with the PAdova and TRieste Stellar Evolution Code"}' )
, ('TRGB:DaCosta+1990',	'TRGB',	'1990AJ....100..162D',	'{"relation": "Mbol(1st)=-0.19*[Fe/H]-3.81, BC_I=0.881-0.243*(V-I)0, [Fe/H]=-15.16+17.0*(V-I)0_{-3}-4.9*((V-I)0_{-3})^2"}' )
, ('TRGB:Dotter+2008',	'TRGB',	'2008ApJS..178...89D',	'{"description": "theoretical isochrones"}' )
, ('TRGB:Ferrarese+2000',	'TRGB',	'2000ApJ...529..745F',	'{"description": "MI(TRGB)=-4.06 +-0.7(random) +-0.13(systematic)"}' )
, ('TRGB:Girardi+2008',	'TRGB',	'2008PASP..120..583G',	'{"description": "Padova isochrones"}' )
, ('TRGB:Gorski+2011',	'TRGB',	'2011AJ....141..194G',	'{"relation": "MJ(TRGB)=-5.67-0.31*[Fe/H], MH(TRGB)=-6.71-0.47*[Fe/H], MK(TRGB)=-6.98-0.58*[Fe/H]"}' )
, ('TRGB:I=-4.00',	'TRGB',	'{"relation": "MI(TRGB)=-4.0 for metal-poor systems"}' )
, ('TRGB:I=-4.03',	'TRGB',	'{"relation": "MI(TRGB)=-4.03 +-0.05", "description": "from the theoretical models of Girardi et al. (2000) and the semi-empirical calibration of Lee et al. (1993)"}' )
, ('TRGB:I=-4.04',	'TRGB',	'{"relation": "MI(TRGB)=-4.04+-0.12 at [Fe/H]=-0.7", "description": "based on Omega Centauri by Bellazzini+2001", "anchor": "Omega Cen"}' )
, ('TRGB:I=-4.05',	'TRGB',	'{"relation": "MI(TRGB)=-4.05 for metal-poor systems',	NULL )
, ('TRGB:Jang+2017',	'TRGB',	'2017ApJ...835...28J',	'{"relation": "M_QT(TRGB)=-4.016+-0.058"}' )
, ('TRGB:Lee+1993',	'TRGB',	'1993ApJ...417..553L',	'{"relation": "Mbol(TRGB)=-0.19*[Fe/H]-3.81, BC_I=0.881*-0.243*(V-I)0, [Fe/H]=-12.64+12.6*(V-I)_{-3.5}-3.3*(V-I)_{-3.5}^2"}' )
, ('TRGB:Madore+2009',	'TRGB',	'2009ApJ...690..389M',	'{"relation": "MI(TRGB)=-4.05+0.20*((V-I)0-1.5)"}' )
, ('TRGB:Marigo+2008',	'TRGB',	'2008A&A...482..883M',	'{"description": "Optical to far-infrared isochrones with improved TP-AGB models."}' )
, ('TRGB:McConnachie+2005',	'TRGB',	'2005MNRAS.356..979M',	'{"relation": "MI(TRGB)= min(-4.04,0.258*[M/H]^2+0.676*[M/H]-3.629)"}' )
, ('TRGB:Rizzi+2007',	'TRGB',	'2007ApJ...661..815R',	'{"relation": "MI(TRGB)=-4.05+0.217*((V-I)0-1.6)"}' )
, ('TRGB:Sand+2014',	'TRGB',	'2014ApJ...793L...7S',	'{"relation": "MrSDSS(TRGB)=-3.01 +-0.01 for Age=12 Gyr and [Fe/H] = from -2.5 to -1.0", "description": "from Dartmouth stellar evolutionary models (Dotter et al. 2008) with a fixed age of 12 Gyr and metallicities ranging from [Fe/H]=-2.5 to -1.0"}' )
, ('TRGB:Wu+2014:F110W',	'TRGB',	'2014AJ....148....7W',	'{"relation": "MF110W(TRGB)=-5.02-1.41*((F110W-F160W)-0.95), F110W-F160W<=0.95; -5.02-2.81*((F110W-F160W)-0.95), F110W-F160W>0.95"}' )
, ('TRGB:Wu+2014:F160W',	'TRGB',	'2014AJ....148....7W',	'{"relation": "MF160W(TRGB)=-5.97-2.41*((F110W-F160W)-0.95), F110W-F160W<=0.95; -5.97-3.81*((F110W-F160W)-0.95), F110W-F160W>0.95"}' )
, ('TRGB:Martinez-Vazquez+2017',	'TRGB',	'2017ApJ...850..137M',	'{"relation": "MF814W(TRGB)=-4.11+0.07*((F475W-F814W)0-2.5)+0.09*((F475W-F814W)0-2.5)^2, sigma=0.02", "description": "the theoretical calibration MF814W(TRGB) as a function of the color (F475W-F814W)0 obtained by fitting the BaSTI predictions (Pietrinferni et al. 2004, 2006)"}' )
, ('TRGB',	'TRGB',	NULL,	'{"description": "Unknown/unspecified calibration relation"}' )

, ('BHB:Deason+2011',	'BHB',	'2011MNRAS.416.2903D',	'{"relation": "Mg(BHB)=0.434-0.169*(g-r)+2.319*(g-r)^2+20.449*(g-r)^3+94.517*(g-r)^4"}' )
, ('BHB:mod(M15)=15.25',	'BHB',	NULL,	'{"anchor": "M15", "modulus": "15.25"}' )
, ('BHB:mod(M15)=15.39',	'BHB',	NULL,	'{"anchor": "M15", "modulus": "15.39"}' )
, ('BHB:mod(M92)=14.65',	'BHB',	NULL,	'{"anchor": "M92", "modulus": "14.65"}' )
, ('HB:Carretta+2000',	'HB',	'2000ApJ...533..215C',	'{"relation": "MV(HB)=0.13*([Fe/H]+1.5)+0.54", "anchor": "LMC", "modulus": "18.54+-0.03+-0.06"}' )
, ('RHB:Chen+2009',	'RHB',	'2009ApJ...702.1336C',	'{"relation": "Mi(RHB)=0.06*[Fe/H]+0.040*t+0.03" "description": "SDSS ugriz photometric system"}' )
, ('ZAHB:Carretta+2000',	'ZAHB',	'2000ApJ...533..215C',	'{"relation": "MV(ZAHB)=0.18*([Fe/H]+1.5)+0.63", "anchor": "LMC", "modulus": "18.54+-0.03+-0.06"}' )
, ('RC:Bilir+2013',	'RC',	'2013NewA...23...88B',	'{"relation": "MV(RC)=0.627(+-0.104)*(B-V)0+0.046(+-0.043)*[Fe/H]+0.262(+-0.111) for 0.42<(B-V)0<1.20 mag, -1.55<[Fe/H]<+0.40 dex and 0.43<MV<1.03 mag", "description": "The distances obtained from trigonometric parallaxes and spectrophotometric analysis."}' )
, ('RC:Udalski2000',	'RC',	'2000ApJ...531L..25U',	'{"relation": "MI=0.13*([Fe/H]+0.25)-0.26, -0.6<[Fe/H]<0.2, sigma=0.12", "description": "based on Hipparcos measurements"}' )
, ('RC:Popowski2000',	'RC',	'2000ApJ...528L...9P',	'{"relation": "MI=-0.36+0.19*([Fe/H]+0.66)"}' )

, ('CMD:Bressan+2012',	'CMD',	'2012MNRAS.427..127B',	NULL,	'{"description": "PARSEC: stellar tracks and isochrones with the PAdova and TRieste Stellar Evolution Code"}' )
, ('CMD:Dotter+2008',	'CMD',	'2008ApJS..178...89D',	NULL,	'{"description": "theoretical isochrones"}' )
, ('CMD:Fadely+2011',	'CMD',	'2011AJ....142...88F',	NULL,	'{"description": "a maximum likelihood fit of CMD using Dartmouth isochrones library (Dotter et al. 2008ApJS..178...89D)", "calibration_basis": "2008ApJS..178...89D"}' )
, ('CMD:Girardi+2004',	'CMD',	'2004A&A...422..205G',	NULL,	'{"description": "theoretical isochrones: SDSS ugriz system"}' )
, ('CMD:mod(M15)=15.39',	'CMD',	NULL,	'{"anchor": "M15", "modulus": "15.39"}' )

, ('Cepheids:Feast+1997',	'Cepheids',	'1997MNRAS.286L...1F',	'{"relation": "<MV>=-2.81*log(P)-1.43, e=0.10", "description": "Hipparcos trigonometrical parallaxes of Galactic Cepheid variables. The slope from LMC was addopted."}' )
, ('Cepheids:Fiorentino+2007',	'Cepheids',	'2007A&A...476..863F',	'{"description": "PL and WPL relations. Theoretical nonlinear convective pulsation models"}' )
, ('Cepheids:Fouque+2003',	'Cepheids',	'2003LNP...635...21F',	'{"relation": "MB=-2.72*(log(P)-1)-?, MV=-3.06*(log(P)-1)-4.049, MI=-3.24*(log(P)-1)-4.790, W=-3.57*(log(P)-1)-5.919, J=-3.53*(log(P)-1)-5.346, H=-3.64*(log(P)-1)-5.666, K=-3.67*(log(P)-1)-5.698", "description": "Galaxy N=32"}' )
, ('Cepheids:Freedman+2001',	'Cepheids',	'2001ApJ...553...47F',	'{"relation": "MV=-2.760*(log(P)-1)-4.218, eV=+-0.16; MI=-2.962*(log(P)-1)-4.904, eI=+-0.11; mu0=muW=muV-R*(muV-muI)=2.45*muI-1.45*muV=W+3.255*(log(P)-1)+5.899, eW=0.08", "description": "it is based on slope from Udalski et al. 1999 and modulus(LMC)=18.50", "anchor": "LMC", "modulus": "18.50"}' )
, ('Cepheids:Freedman+2001:Z',	'Cepheids',	'2001ApJ...553...47F',	'{"relation": "MV=-2.760*(log(P)-1)-4.218, eV=+-0.16; MI=-2.962*(log(P)-1)-4.904, eI=+-0.11; mu0=muW=muV-R*(muV-muI)=2.45*muI-1.45*muV=W+3.255*(log(P)-1)+5.899, eW=0.08; mu0Z=muV-R*(muV-muI)+dmuZ, dmuZ=gammaVI*([O/H]-[O/H]LMC), gammaVI=-0.2 +-0.2 mag dex^-1"}' )
, ('Cepheids:Gieren+1998',	'Cepheids',	'1998ApJ...496...17G',	'{"relation": "MV=-3.037*(log(P)-1)-4.058, e=0.209; MIc=-3.329*(log(P)-1)-4.764, e=0.194; MJ(Carter)=-3.436*(log(P)-1)-5.185, e=0.173; MH(Carter)=-3.562*(log(P)-1)-5.580, e=0.175; MK(Carter)=-3.598*(log(P)-1)-5.664, e=0.173", "description": Galaxy. The infrared Barnes-Evans surface brightness technique is used to derive the radii and distances of 34 Galactic Cepheid variables."}' )
, ('Cepheids:Kanbur+2003',	'Cepheids',	'2003A&A...411..361K',	'{"relation": "MI=-2.965*log(P)-1.889, e=0.145; MV=-2.746*log(P)-1.401", "description": "634, modulus(LMC)=18.50", "anchor": "LMC", "modulus": "18.50"}' )
, ('Cepheids:Kanbur+2003:PLmax',	'Cepheids',	'2003A&A...411..361K',	'{"relation": "MI=-2.958*log(P)-2.129, e=0.171; MV=-2.744*log(P)-1.817, e=0.261", description": "PL(Max) relation. N=634, modulus(LMC)=18.50", "anchor": "LMC", "modulus": "18.50"}' )
, ('Cepheids:Kanbur+2003:Z',	'Cepheids',	'2003A&A...411..361K',	'{"relation": "dmuZ=gammaVI*([O/H]ref-[O/H]gal); gammaVI=-0.2+-0.2; [O/H](LMC)=8.50; [O/H](Galaxy)=8.87", "description": "Metallicity correction to relation Cepheids:Kanbur+2003"}' )
, ('Cepheids:Lanoix+1999',	'Cepheids',	'1999MNRAS.308..969L',	'{"relation": "<MV>=-2.77*log(P)-1.44 (+-0.05), <MIc>=-3.05*log(P)-1.81 (+-0.09)", "description": "Hipparcos trigonometrical parallaxes of Galactic Cepheid variables. The slope from LMC was addopted."}' )
, ('Cepheids:Madore+1991',	'Cepheids',	'1991PASP..103..933M',	'{"relation": "MB=-2.43*(log(P)-1)-3.50, eB=0.36; MV=-2.76*(log(P)-1)-4.16, eV=0.27; MRc=-2.94*(log(P)-1)-4.52, eRc=0.22; MIc=-3.06*(log(P)-1)-4.87, eIc=0.18", "description": "32 LMC Cepheids"}' )
, ('Cepheids:Saha+2006',	'Cepheids',	'2006ApJS..165..108S',	'{"relation": "mu0=RV/(RV-RI)*muI-RI/(RV-RI)*muV=2.52*muI-1.52*muV; dmuZ=1.67*(log(P)-0.933)*([O/H]-A), A=8.60 for Galaxy, A=8.34 for LMC", "description": "metallicity corrected distances using calibration of Sandage et al. 2004"}' )
, ('Cepheids:Sandage+2004:Galaxy',	'Cepheids',	'2004A&A...424...43S',	'{"relation": "MB=-2.692*log(P)-0.575, e=0.25; MV=-3.087*log(P)-0.914, e=0.23;  MI=-3.348*log(P)-1.429, e=0.23", "description": "Galaxy, NB=69, NV=69, NI=68"}' )
, ('Cepheids:Sandage+2004:LMC',	'Cepheids',	'2004A&A...424...43S',	'{"relation": "log(P)<1 : MB=-2.683*log(P)-0.995, MV=-2.963*log(P)-1.335, MI=-3.099*log(P)-1.846; log(P)>1 : MB=-2.151*log(P)-1.404, MV=-2.567*log(P)-1.634, MI=-2.822*log(P)-2.084", "anchor": "LMC", "modulus": "18.54"}' )
, ('Cepheids:Tammann+2002',	'Cepheids',	'2002Ap&SS.280..165T',	'{"relation": "MB=-2.42*log(P)-1.24, MV=-2.86*log(P)-1.46, MI=-3.03*log(P)-1.96 if P<10 days; MB=-1.89*log(P)-1.71, MV=-2.48*log(P)-1.81, MI=-2.82*log(P)-2.15 if P>10 days", "anchor": "LMC", "modulus": "18.56"}' )
, ('Cepheids:Tammann+2002:LMC=18.50',	'Cepheids',	'2002Ap&SS.280..165T',	'{"relation": "MB=-2.42*log(P)-1.18, MV=-2.86*log(P)-1.40, MI=-3.03*log(P)-1.90 if P<10 days; MB=-1.89*log(P)-1.65, MV=-2.48*log(P)-1.75, MI=-2.82*log(P)-2.09 if P>10 days", "description": "corrected to modulus(LMC)=18.50", "anchor": "LMC", "modulus": "18.50"}' )
, ('Cepheids:Tammann+2003',	'Cepheids',	'2003A&A...404..423T',	'{"relation": "MB=-2.757*log(P)-0.472, e=0.27; MV=-3.141*log(P)-0.826, e=0.24; MI=-3.408*log(P)-1.325, e=0.23", "description": "Galaxy. N=53"}' )
, ('Cepheids:Udalski+1999',	'Cepheids',	'1999AcA....49..201U',	'{"relation": "MI=-2.962*log(P)+16.558-18.22, eI=0.109; MV=-2.760*log(P)+17.042-18.22, eV=0.159", "description": "658 in I, 649 in V, LMC Cepheids modulus(LMC)=18.22", "anchor": "LMC", "modulus": "18.22"}' )
, ('Cepheids:Udalski+1999:LMC=18.50',	'Cepheids',	'1999AcA....49..201U',	'{"relation": "MI=-2.962*log(P)-1.942, eI=0.109; MV=-2.760*log(P)-1.458, eV=0.159", "description": "corrected to modulus(LMC)=18.50", "anchor": "LMC", "modulus": "18.50"}' )
, ('Cepheids:Willick+2001',	'Cepheids',	'2001ApJ...548..564W',	'{"relation": "MB=-3.569-2.308*(log(P)-1), MV=-4.219-2.760*(log(P)-1), MI=-4.906-2.963*(log(P)-1)", "description": "realtion is based on the OGLE LMC Cepheid PL relation and modulus(LMC)=18.50", "anchor": "LMC", "modulus": "18.50"}' )
, ('Cepheids',	'Cepheids',	NULL,	'{"description": "Unknown/unspecified calibration relation"}' )

, ('RRLyrae:Bernard+2009',	'RRLyrae',	'2009ApJ...699.1742B',	'{"relation": "MV(RR)=0.866+0.214*[Fe/H]", "anchor": "LMC", "modulus": "18.515", "[Fe/H]": "-1.5"}' )
, ('RRLyrae:Borissova+2009',	'RRLyrae',	'2009A&A...502..505B',	'{"relation": "MK*(RR)=2.11*log(P)+0.05*[Fe/H]-1.05"}' )
, ('RRLyrae:Caceres+2008',	'RRLyrae',	'2008ApJS..179..242C',	NULL )
, ('RRLyrae:Caputo+2000',	'RRLyrae',	'2000MNRAS.316..819C',	'{"relation": "MV(FOBE)=-0.178-2.255*log10(P(FOBE))+0.151*log10(Z)", "description": "FOBE=first-overtone blue edge"}' )
, ('RRLyrae:Carretta+2000',	'RRLyrae',	'2000ApJ...533..215C',	'{"relation": "MV(RR)=0.18*([Fe/H]+1.5)+0.57", "anchor": "LMC", "modulus": "18.54+-0.03+-0.06"}' )
, ('RRLyrae:Catelan+2004',	'RRLyrae',	'2004ApJS..154..633C',	'{"relation": "MI=0.471-1.132*logP+0.205*logZ; MV=2.288+0.882*logZ+0.108*logZ^2; MJ=-0.141-1.773*logP+0.190*logZ; MH=-0.551-2.313*logP+0.178*logZ; MK=-0.597-2.353*logP+0.175*logZ", "description": "Average relations in UBVRIJHK"}' )
, ('RRLyrae:Chaboyer1999',	'RRLyrae',	'1999ASSL..237..111C',	'{"relation": "MV(RR)=0.23*([Fe/H]+1.6)+0.56"}' )
, ('RRLyrae:Clementini+2003',	'RRLyrae',	'2003AJ....125.1309C',	'{"relation": "visual absorption corrected <V0(RR)>=0.214*([Fe/H]+1.5)+19.064", "anchor": "LMC", "modulus": "18.515+-0.085"}' )
, ('RRLyrae:Lee+1990',	'RRLyrae',	'1990ApJ...350..155L',	'{"relation": "MV(RR)=0.17*[Fe/H]+0.82"}' )
, ('RRLyrae:MV=0.68',	'RRLyrae',	NULL,	'{"relation": "MV=0.68+-0.15 at [Fe/H]=-1.5", "description": "the absolute magnitude derived from the Baade-Wesselink method"}' )
, ('RRLyrae:MV=0.76',	'RRLyrae',	NULL,	'{"relation": "MV=0.76+-0.13 at [Fe/H]=-1.5", "description": "the absolute magnitude derived from the Hipparcos-based statistical parallaxes"}' )
, ('RRLyrae:Marconi+2015',	'RRLyrae',	'2015ApJ...808...50M',	'{"description": "nonlinear, time-dependent convective hydrodynamical models of RR Lyrae stars computed assuming a constant helium-to-metal enrichment ratio and a broad range in metal abundances (Z=0.0001-0.02)"}' )
, ('RRLyrae:Martinez-Vazquez+2017:LMR:C03',	'RRLyrae',	'2017ApJ...850..137M',	'{"relation": "<MV>=0.866+0.214*[Fe/H]", "description": "from Clementini et al. 2003AJ....125.1309C"}' )
, ('RRLyrae:Martinez-Vazquez+2017:LMR:B03',	'RRLyrae',	'2017ApJ...850..137M',	'{"relation": "<MV>=0.768+0.177*[Fe/H]", "description": "from Bono et al. 2003MNRAS.344.1097B"}' )
, ('RRLyrae:Martinez-Vazquez+2017:PWR',	'RRLyrae',	'2017ApJ...850..137M',	'{"relation": "W(I,B-I)=-0.97-2.40*logP+0.11*[Fe/H], W(I,B-I)=I-0.78*(B-I), sigma=0.04", "description": "Period-Wesenheit Relations"}' )

, ('Asteroseismic:Wu+2014:Classic',	'Asteroseismic',	'2014ApJ...786...10W',	'{"relation": "6*log(Vmax) + 15*log(Teff) = 12*log(dV) + 1.2*(4.75-V-BC) + 1.2*(m-M)0 + 1.2*AV"}' )
, ('Asteroseismic:Wu+2014:Z',	'Asteroseismic',	'2014ApJ...786...10W',	'{"relation": "9.482*log(Vmax) = 15.549*log(dV) - 1.2*(V+BC) + 0.737*log(Z) + 1.2(m-M)0 + 1.2*AV + 5.968"}' )

, ('FGLR:Kudritzki+2008',	'FGLR',	'2008ApJ...681..269K',	'{"relation": "Mbol=a*(log(gF)-1.5)+b; a=3.41+-0.16, b=-8.02+-0.04", "description": "sigma=0.32 over 8 galaxies"}' )
, ('FGLR:Kudritzki+2012',	'FGLR',	'2012ApJ...747...15K',	'{"relation": "Mbol=a*(log(gF)-1.5)+b; a=4.53, b=-7.88", "description": "based on LMC (m-M)0=18.50 reffers to unpublished article Urbaneja 2012 in preparation", "anchor": "LMC", "modulus": "18.50"}' )

, ('SNIa:Folatelli+2010',	'SNIa',	'2010AJ....139..120F',	'{"relation": "muX=mX-MX(0)-bX*(dm15(B)-1.1)-R^{YZ}X*E(Y-Z) for ugriBVYJH bands", "description": "Average distance modulus from fits (Table 9)"}' )
, ('SNIa:Guy+2005',	'SNIa',	'2005A&A...443..781G',	'{"description": "SALT: a spectral adaptive light curve template for type Ia supernovae"}' )
, ('SNIa:Guy+2007',	'SNIa',	'2007A&A...466...11G',	'{"description": "SALT2: using distant supernovae to improve the use of type Ia supernovae as distance indicators"}' )
, ('SNIa:Jha+2007',	'SNIa',	'2007ApJ...659..122J',	'{"description": "Multicolor Light-Curve Shapes: MLCS2k2"}' )
, ('SNIa:Jha+2007:RV=1.7',	'SNIa',	'2007ApJ...659..122J',	'{"description": "Multicolor Light-Curve Shapes: MLCS2k2 (RV=1.7)"}' )
, ('SNIa:Jha+2007:RV=3.1',	'SNIa',	'2007ApJ...659..122J',	'{"description": "Multicolor Light-Curve Shapes: MLCS2k2 (RV=3.1)"}' )
, ('SNIa:Mandel+2009',	'SNIa',	'2009ApJ...704..629M',	'{"description": "BayeSN - Markov Chain Monte Carlo (MCMC) algorithm"}' )
, ('SNIa:Mandel+2011',	'SNIa',	'2011ApJ...731..120M',	'{"description": "Improoved BayeSN Markov Chain Monte Carlo (MCMC) code"}' )
, ('SNIa:Prieto+2006',	'SNIa',	'2006ApJ...647..501P',	'{"H0": "72"}' )
, ('SNIa:Reindl+2005',	'SNIa',	'2005ApJ...624..532R',	'{"relation": "MB00=0.612*(dm15-1.1)+0.692*((B-V)+0.024)-19.57, sig=0.15; MV00=0.612*(dm15-1.1)-0.308*((B-V)+0.024)-19.55, sig=0.15; MI00=0.439*(dm15-1.1)+0.827*((B-V)+0.024)-19.29, sig=0.14", "H0": "60"}' )
, ('SNIa:Wood-Vasey+2008',	'SNIa',	'2008ApJ...689..377W',	'{"relation": "MH=-18.07+-0.03 sig=0.16; MJ=-18.27+-0.07 sig=0.29; MK=-18.30+-0.11 sig=0.29"}' )

, ('SBF:Blakeslee+2009',	'SBF',	'2009ApJ...694..556B',	'{"relation": "Mz=-2.04+1.41*x+2.60*x^2+3.72*x^3, where x=(g475-z850)-1.3, z850=F850LP(HST), g475=F475W(HST)", "description": :"zero point is bases on the Cepheid distance scale (Freedman et al. 2001; Macri et al. 2006)"}' )
, ('SBF:Blakeslee+2010',	'SBF',	'2010ApJ...724..657B',	'{"relation": "M814=(-1.168 +-0.013+-0.092) + (1.83 +-0.20)*[(g475-I814)-1.2]  if 1.06<(g475-I814)<1.32, where g475=F475W_AB, I814=F814W_AB", "description": "Recalibration of Blakeslee+2009 for F814W fileter"}' )
, ('SBF:Jensen+2003',	'SBF',	'2003ApJ...583..712J',	'{"relation": "MF160W=-4.86+5.1*((V-I)0-1.16) for 1.05<(V-I)0<1.24"}' )
, ('SBF:Mei+2005',	'SBF',	'2005ApJ...625..121M',	'{"relation": "M850=-2.06+0.9*((g475-z850)0-1.3) if 1.0<=(g475-z850)0<=1.3, M850=-2.06+2.0*((g475-z850)0-1.3) if 1.3<(g475-z850)0<=1.6; z850=F850LP(HST), g475=F475W(HST)", "description": "Virgo distance mu=31.09+-0.03 mag is based on Freedman et al. 2001 Cepheid PL metallicity corrected relation", "anchor": "Virgo", "modulus": "31.09+-0.03"}' )
, ('SBF:Mieske+2003',	'SBF',	'2003A&A...410..445M',	'{"relation": "MI=-1.74+4.5*((V-I)-1.15) if (V-I)>=1.0, MI=-2.07+2.25*((V-I)-1.15) if (V-I)<1.0", "description": "bases on Tonry et al. 2001 relation for (V-I)>=1.0"}' )
, ('SBF:Tonry+2000',	'SBF',	'2000ApJ...530..625T',	'{"relation": "MI=-1.74+4.5*((V-I)0-1.15)", "description": "calibrated using the HST Key Project Cepheid distances 2000ApJ...529..745F"}' )
, ('SBF',	'SBF',	NULL,	'{"description": "Unknown/unspecified calibration relation"}' )

, ('GW:direct',	'GW',	NULL,	'{"description": "Analysis of the gravitational-wave data produces estimates for the parameters of the source, under the assumption that general relativity is the correct model of gravity"}' )

, ('PNLF:Ciardullo+1989',	'PNLF',	'1989ApJ...339...53C',	'{"relation": "M*=-4.48; N(M)~exp(0.307*M)*(1-exp(3*(M*-M)))", "anchor": "M31", "distance": "710", "unit": "kpc", "E(B-V)": "0.11"}' )
, ('PNLF:Ciardullo+2002',	'PNLF',	'2002ApJ...577...31C',	'{"relation": "M*=-4.47 for 12+log(O/H)>=8.5; M*Z=M*+0.928*[O/H]^2+0.225*[O/H]+0.014, where Sun has 12+log(O/H)=8.87"}' )
, ('PNLF:Feldmeier+1996',	'PNLF',	'1996ApJ...461L..25F',	'{"relation": "M*=-4.54", "anchor": "M31", "distance": "770", "unit": "kpc", "E(B-V)": "0.08"}' )
, ('PNLF:Mendez+1997',	'PNLF',	'1997A&A...321..898M',	'{"description": "Simulations of PNLF"}' )
, ('PNLF',	'PNLF',	NULL,	'{"description": "Unknown/unspecified calibration relation"}' )

, ('Sosie:Terry+2002',	'Sosie',	'2002A&A...393...57T',	'{"description": "21 calibrators with two-independent calibrations of Cepheid PL relations (2002A&A...389...19P, 2002A&A...383..398P)"}' )
, ('TF:Gavazzi+1999',	'TF',	'1999MNRAS.304..595G',	'{"relation": "MH=-2.6-7.85*log(Wc)", "description": "Virgo cluster A D=16 Mpc (modulus0=31.02), modulus(Coma)-modulus(Virgo cl.A)=3.71 => modulus(Coma)=34.73, <V(Coma)>CMB=7185 km/s => H0=81.35; Virgo infall=220 km/s", "anchor": "Virgo Cluster A", "distance": "16", "unit": "Mpc", "modulus": "31.02"}' )
, ('TF:Karachentsev+2002',	'TF',	'2002A&A...396..431K',	'{"relation": "slopes: B=-4.90, I=-6.37, J20=-8.73, Jexp=-8.20, Jfe=-7.74, H20=-9.02, Hext=-8.71, Hfe=-7.95, K20=-9.34, Kest=-9.02, Kfe=-8.38", "H0": "75", "description": "2MASS TF relation for edge-on galaxies"}' )
, ('TF:Sorce+2014:MC[3.6]',	'TF',	'2014MNRAS.444..527S',	'{"relation": "MC[3.6]=-(20.31+/-0.07)-(9.10+/-0.21)*(logWi-2.5), sigma=0.45", "description": "MC[3.6]=color corrected [3.6] absolute magnitude", "H0": "75.2+/-3.3"}' )
, ('TF:Sorce+2014:M[3.6]',	'TF',	'2014MNRAS.444..527S',	'{"relation": "M[3.6]=-(20.31+/-0.09)-(9.77+/-0.19)*(logWi-2.5), sigma=0.54", "description": "M[3.6]=[3.6] absolute magnitude", "H0": "75.2+/-3.3"}' )
, ('TF:Tully+2008',	'TF',	'2008ApJ...676..184T',	'{"relation": "MB^{b,i,k}=-19.99-7.27*(W^i-2.5); MR^{b,i,k}=-21.00-7.65*(W^i-2.5); MI^{b,i,k}=-21.43-8.11*(W^i-2.5); MH^{b,i,k}=-22.17-9.55*(W^i-2.5);", "description": "Calibration of Tully&Pierce(2000) is shifted slightly to be consistent in zero point with the HST Cepheid Key Project results."}' )

, ('FP:Gavazzi+1999',	'FP',	'1999MNRAS.304..595G',	'{"relation": "log(Re)=-8.354+1.52*log(sigma)+0.32*mue; err=0.45", "H0": "81.35"}' )
, ('FP:Hjorth+1997',	'FP',	'1997ApJ...482...68H',	'{"relation": "log(DA)=-log(Re)+a*log(sigma)+b*log(<I>e)+c*log(Mg2)+d, (a,b,c,d)=(1.24,-0.82,0,2.194) for the classic FP & (1.128,-0.78,-0.4,2.447) for the Mg2 FP", "description": "Using Leo I, FP:Jorgensen+1996 (1996MNRAS.280..167J) FP exponents, Mg2-log(sigma) relation"}' )
, ('FP:Jorgensen+1996',	'FP',	'1996MNRAS.280..167J',	'{"relation": "log(Re)=1.24*log(sigma)-0.82*log(<Ie>)+cnt"}' )
, ('FP:Mutabazi+2014',	'FP',	'2014MNRAS.439.3666M',	'{"relation": "log(DA)=1.465*log(Sig)+0.326*mue -5.902 -log(re); sigma=0.08 in log(Sig)", "H0": "70.5", "Omega_M": "0.27", "Omega_L": "0.73", "anchor": "Coma", "zCMB": "0.0240"}' )

, ('BS3B:Karachentsev+1994',	'BS3B',	'1994A&A...286..718K',	'{"relation": "<MB(3B)>=0.35*MBT-2.50, e=0.30; <MB(3B)>=-0.51*(<B(3B)>-BT)-4.14, e=0.45; modulus=1.51*<B(3B)>-0.51*BT+4.14", "calibration_basis": "Cepheids"}' )
, ('BS:Makarova+1998',	'BS',	'1998A&AS..133..181M',	'{"relation": "modulus0(R1)=1.10*V(R1)-0.10*BT+7.00-0.76*AB, (B-V)=1.6", "calibration_basis": "1994A&A...286..718K"}' )
;

ROLLBACK ;
-- COMMIT ;
