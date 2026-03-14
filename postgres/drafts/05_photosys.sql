BEGIN;

CREATE SCHEMA IF NOT EXISTS photometry ;
COMMENT ON SCHEMA photometry IS 'Catalog of the photometry';

-----------------------------------------------
--------- Spectral regions --------------------

-- CREATE TYPE common.SpectralRegion AS ENUM ( 'Gamma', 'X','UV','Opt','IR','Radio') ;

-- COMMENT ON TYPE common.SpectralRegion	IS '{
-- "Gamma" : "Gamma rays source",
-- "X" : "X-ray source",
-- "UV" : "Ultraviolet source",
-- "Opt" : "Optical source",
-- "IR" : "Infrared source",
-- "Radio" : "Radio source"
-- }' ;


-----------------------------------------------
---------  Magnitude System Type --------------

CREATE TYPE photometry.MagSysType	AS ENUM ( 'Vega', 'AB', 'ST' ) ;

COMMENT ON TYPE photometry.MagSysType	IS '{
"Vega" : "The Vega magnitude system uses the Vega as the standard star with an apparent magnitude of zero, regardless of the wavelength filter. The spectrum of Vega used to define this system is a composite spectrum of empirical and synthetic spectra (Bohlin & Gilliland, 2004AJ....127.3508B). m(Vega) = -2.5*log10(F/FVega), where F is flux of an object, and FVega is the calibrated spectrum of Vega.",
"AB" : "The AB magnitude system uses flat reference spectrum in frequency space. The conversion is chosen such that the V-magnitude corresponds roughly to that in the Johnson system. The monochromatic AB magnitude is defined as m(AB) = 8.9 -2.5*log10(Fv[Jy]) = -48.6 -2.5*log10(Fv[erg s^−1 cm^−2 Hz^−1]), where Fv is the spectral flux density.",
"ST" : "The ST magnitude system uses flat reference spectrum in wavelength space. The conversion is chosen such that the V-magnitude corresponds roughly to that in the Johnson system. The monochromatic ST magnitude is defined as m(ST) = -21.1 -2.5*log10(Flambda[erg s^−1 cm^−2 Angstrom^−1]), where Flambda is the spectral flux density."
}' ;


-----------------------------------------------
--------- Photometric systems -----------------

CREATE TABLE photometry.systems (
  id	Text	PRIMARY KEY
, description	Text	NOT NULL
, bibcode	Char(19)	UNIQUE
, svo_id	Text	UNIQUE
) ;

COMMENT ON TABLE photometry.systems	IS 'Photometric system' ;
COMMENT ON COLUMN photometry.systems.id	IS 'Photometric system ID' ;
COMMENT ON COLUMN photometry.systems.description	IS 'Description of the photometric system' ;
COMMENT ON COLUMN photometry.systems.bibcode	IS '{"description" : "ADS bibcode", "url" : "https://ui.adsabs.harvard.edu/abs/", "ucd" : "meta.ref.url"}' ;
COMMENT ON COLUMN photometry.systems.svo_id	IS '{"description" : "Query to the Spanish Virtual Observatory", "url" : "http://svo2.cab.inta-csic.es/theory/fps/index.php?", "ucd" : "meta.ref.url"}' ;

INSERT INTO photometry.systems VALUES
  ( 'UBVRIJHKL' , 'Johnson UBVRIJHKL photometric system' , '1965CoLPL...3...73J', 'gname=Generic&gname2=Johnson_UBVRIJHKL' )
, ( 'Cousins' , 'Cousins (Rc,Ic) photometric system' , '1976MmRAS..81...25C', 'gname=Generic&gname2=Cousins' )
, ( 'Bessell' , 'Bessell photometric system' , '1990PASP..102.1181B', 'gname=Generic&gname2=Bessell' )

, ( 'Gaia3' , 'Gaia mission, eDR3 release photometric system' , NULL, 'gname=GAIA&gname2=GAIA3' )

, ( 'ACS_WFC' , 'Hubble Space Telescope (HST), Advanced Camera for Surveys (ACS), Wide Field Channel photometric system' , NULL, 'gname=HST&gname2=ACS_WFC' )
, ( 'WFPC2_WF' , 'Hubble Space Telescope (HST), Wide-Field Planetary Camera 2 (WFPC2), Wide Field photometric system' , NULL, 'gname=HST&gname2=WFPC2_WF' )
, ( 'WFPC3_IR' , 'Hubble Space Telescope (HST), Wide-Field Planetary Camera 3 (WFPC3), IR channel photometric system' , NULL, 'gname=HST&gname2=WFC3_IR' )

, ( 'NIRCam' , 'James Webb Space Telescope (JWST), Near Infrared Camera (NIRCam) photometric system' , NULL, 'gname=JWST&gname2=NIRCam' )
, ( 'MegaCam', 'Canada-France-Hawaii Telescope (CFHT), MegaCam photometric system', NULL, 'gname=CFHT&gname2=MegaCam' )
, ( 'WIRCam', 'Canada-France-Hawaii Telescope (CFHT), Wide-field InfraRed Camera (WIRCam) photometric system', NULL, 'gname=CFHT&gname2=Wircam' )

, ( 'SDSS' , 'Sloan Digital Sky Survey photometric system' , '1998AJ....116.3040G', 'gname=SLOAN&gname2=SDSS' )
, ( 'PS1' , 'Panoramic Survey Telescope and Rapid Response System (Pan-STARRS), PS1 photometric system' , '2012ApJ...750...99T', 'gname=PAN-STARRS' )
, ( 'DECam' , 'Dark Energy Camera (DECam) photometric system (at the prime focus of the Blanco 4-m telescope)' , '2015AJ....150..150F', 'gname=CTIO&gname2=DECam' )
, ( 'HSC' , 'Hyper Suprime-Cam (HSC) photometric system (at the prime focus of Subaru Telescope)' , NULL, 'gname=Subaru&gname2=HSC' )
, ( '2MASS' , 'Two Micron All Sky Survey (2MASS) photometric system' , '2003AJ....126.1090C', 'gname=2MASS' )
, ( 'DENIS' , 'Deep Near Infrared Survey of the Southern Sky (DENIS) photometric system' , '1994Ap&SS.217....3E', 'gname=DENIS' )
, ( 'UKIDSS' , 'United Kingdom Infrared Telescope (UKIRT), Infrared Deep Sky Survey (UKIDSS) ZYJHK photometric system' , NULL, 'gname=UKIRT&gname2=UKIDSS' )

, ( 'GALEX' , 'Galaxy Evolution Explorer (GALEX) photometric system' , '2007ApJS..173..185G', 'gname=GALEX' )
, ( 'IRAS' , 'Infrared Astronomical Satellite (IRAS) photometric system' , '1984ApJ...278L...1N', 'gname=IRAS' )
, ( 'WISE' , 'Wide-field Infrared Survey Explorer (WISE) photometric system' , '2010AJ....140.1868W', 'gname=WISE' )
, ( 'Swift', 'The Swift Gamma-Ray Burst Mission', NULL, 'gname=Swift' )
, ( 'IRAC' , 'Spitzer Space Telescope, the InfraRed Array Camera (IRAC) photometric system', '2004ApJS..154...10F', 'gname=Spitzer&gname2=IRAC' )

, ( 'Holmberg' , 'Holmberg m_pg, m_pv photographic magnitudes' , NULL, NULL )
, ( 'GSC2' , 'Second-Generation Guide Star Catalog, Palomar (north) Bj, Rf, In photographic passbands', '2008AJ....136..735L' , 'gname=Palomar&gname2=GSC2' )
;


-------------- Filter description ---------------
CREATE TABLE photometry.bands (
  id	text	PRIMARY KEY
, name	text	NOT NULL
, photsys	text	NOT NULL	REFERENCES photometry.systems (id) ON DELETE restrict ON UPDATE cascade
, waveref	real	NOT NULL
, fwhm	real	NOT NULL
, extinction	real
, svo_id	text	UNIQUE
) ;
CREATE INDEX ON photometry.bands (waveref) ;
CREATE INDEX ON photometry.bands (name) ;
CREATE INDEX ON photometry.bands (photsys) ;

COMMENT ON TABLE photometry.bands	IS 'List of filters' ;
COMMENT ON COLUMN photometry.bands.id 	IS 'Filter ID' ;
COMMENT ON COLUMN photometry.bands.name	IS 'Common filter designation' ;
COMMENT ON COLUMN photometry.bands.photsys	IS 'Photometric system' ;
COMMENT ON COLUMN photometry.bands.waveref	IS 'The reference wavelength of the filter transmission' ;
COMMENT ON COLUMN photometry.bands.fwhm	IS 'The Full Width Half Maximum of the filter transmission' ;
COMMENT ON COLUMN photometry.bands.extinction	IS 'Relative extinction. Ratio between extintion at λref, Af, and visual extintion, Av' ;
COMMENT ON COLUMN photometry.bands.svo_id	IS '{"description" : "The Spanish Virtual Observatory filter ID", "url" : "http://svo2.cab.inta-csic.es/theory/fps/index.php?id=", "ucd" : "meta.ref.url"}' ;


-------------- Calibrated properties -----------
CREATE TABLE photometry.calib_bands (
  id	text	PRIMARY KEY
, band	text	NOT NULL	REFERENCES photometry.bands (id) ON DELETE restrict ON UPDATE cascade
, magsys	photometry.MagSysType
, UNIQUE (band,magsys)
) ;

COMMENT ON TABLE photometry.calib_bands	IS 'List of calibrated bands' ; 
COMMENT ON COLUMN photometry.calib_bands.id	IS 'Calibrated band ID' ;
COMMENT ON COLUMN photometry.calib_bands.band	IS 'Band ID' ;
COMMENT ON COLUMN photometry.calib_bands.magsys	IS 'Magnitude system' ;


-- CREATE VIEW photometry.calib_bandsview AS
-- SELECT
--   d.*
-- , b.name
-- , b.waveref
-- , b.fwhm
-- , b.extinction
-- , b.svo_id
-- , b.photsys
-- , s.bibcode
-- , s.description
-- FROM
--   photometry.calib_bands AS d
--   LEFT JOIN photometry.bands AS b ON (b.id=d.band)
--   LEFT JOIN photometry.systems AS s ON (s.id=b.photsys)
-- ;
-- 
-- COMMENT ON VIEW photometry.calib_bandsview	IS 'Band list' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.id	IS 'Calibrated band ID' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.band	IS 'Band ID' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.magsys	IS 'Magnitude system' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.name	IS '{"description":"Common filter designation","ucd":"instr.bandpass"}' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.photsys	IS 'Photometric system' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.waveref	IS '{"description":"Reference wavelength (pivot wavelength) of the filter transmission", "unit":"Angstrom", "ucd":"em.wl"}' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.fwhm	IS '{"description":"The Full Width Half Maximum of the filter transmission", "unit":"Angstrom", "ucd":"instr.bandwidth" }' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.extinction	IS 'Relative extinction. Ratio between extintion at λref, Af, and visual extintion, Av' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.svo_id	IS '{"description" : "The Spanish Virtual Observatory filter ID", "url" : "http://svo2.cab.inta-csic.es/theory/fps/index.php?id=", "ucd" : "meta.ref.ivoid;meta.ref.url"}' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.description	IS 'Description of the photometric system' ;
-- COMMENT ON COLUMN photometry.calib_bandsview.bibcode	IS '{"description" : "ADS bibcode", "url" : "https://ui.adsabs.harvard.edu/abs/", "ucd" : "meta.ref.url"}' ;


--------------- DATA -----------------
COPY photometry.bands (id,name,photsys,waveref,fwhm,extinction,svo_id) FROM STDIN;
FUV	FUV	GALEX	1535.08	233.93	2.62759	GALEX/GALEX.FUV
NUV	NUV	GALEX	2300.78	795.19	2.85878	GALEX/GALEX.NUV
UVW2	UVW2	Swift	2054.61	584.89	2.99964	Swift/UVOT.UVW2
UVM2	UVM2	Swift	2246.43	527.13	3.01684	Swift/UVOT.UVM2
UVW1	UVW1	Swift	2580.74	656.60	2.18468	Swift/UVOT.UVW1
U_Swift	U	Swift	3467.05	778.49	1.63943	Swift/UVOT.U
B_Swift	B	Swift	4349.56	978.33	1.31480	Swift/UVOT.B
V_Swift	V	Swift	5425.33	744.99	1.02056	Swift/UVOT.V
U	U	UBVRIJHKL	3511.89	683.73	1.61966	Generic/Johnson_UBVRIJHKL.U
B	B	UBVRIJHKL	4382.77	1011.11	1.30391	Generic/Johnson_UBVRIJHKL.B
V	V	UBVRIJHKL	5501.40	876.67	1.00171	Generic/Johnson_UBVRIJHKL.V
R	R	UBVRIJHKL	6819.05	2093.33	0.76112	Generic/Johnson_UBVRIJHKL.R
I	I	UBVRIJHKL	8657.44	2205.45	0.53488	Generic/Johnson_UBVRIJHKL.I
J	J	UBVRIJHKL	12317.30	3193.55	0.30707	Generic/Johnson_UBVRIJHKL.J
H	H	UBVRIJHKL	16396.38	2983.81	0.19401	Generic/Johnson_UBVRIJHKL.H
K	K	UBVRIJHKL	21735.85	5926.09	0.12389	Generic/Johnson_UBVRIJHKL.K
Rc	R	Cousins	6414.42	1516.49	0.83459	Generic/Cousins.R
Ic	I	Cousins	7858.32	1093.68	0.62548	Generic/Cousins.I
U_Bessell	U	Bessell	3584.78	652.84	1.58844	Generic/Bessell.U
B_Bessell	B	Bessell	4371.07	947.62	1.30775	Generic/Bessell.B
V_Bessell	V	Bessell	5477.70	852.44	1.00755	Generic/Bessell.V
R_Bessell	R	Bessell	6498.09	1567.06	0.81934	Generic/Bessell.R
I_Bessell	I	Bessell	8020.14	1543.11	0.60552	Generic/Bessell.I
u_SDSS	u	SDSS	3556.52	565.80	1.60055	SLOAN/SDSS.u
g_SDSS	g	SDSS	4702.50	1175.63	1.21355	SLOAN/SDSS.g
r_SDSS	r	SDSS	6175.58	1130.56	0.87774	SLOAN/SDSS.r
i_SDSS	i	SDSS	7489.98	1253.30	0.66911	SLOAN/SDSS.i
z_SDSS	z	SDSS	8946.71	998.50	0.51176	SLOAN/SDSS.z
g_PS1	g	PS1	4849.11	1148.66	1.17468	PAN-STARRS/PS1.g
r_PS1	r	PS1	6201.20	1397.73	0.87305	PAN-STARRS/PS1.r
i_PS1	i	PS1	7534.96	1292.39	0.66384	PAN-STARRS/PS1.i
z_PS1	z	PS1	8674.20	1038.82	0.53346	PAN-STARRS/PS1.z
y_PS1	y	PS1	9627.79	665.08	0.45589	PAN-STARRS/PS1.y
I_DENIS	I	DENIS	7897.13	1311.11	0.62077	DENIS/DENIS.I
J_DENIS	J	DENIS	12295.06	1991.11	0.30803	DENIS/DENIS.J
Ks_DENIS	Ks	DENIS	21561.52	3301.94	0.12529	DENIS/DENIS.Ks
J_2MASS	I	2MASS	12350.00	1830.20	0.30566	2MASS/2MASS.J
H_2MASS	J	2MASS	16620.00	2580.01	0.18873	2MASS/2MASS.H
Ks_2MASS	Ks	2MASS	21590.00	2771.26	0.12505	2MASS/2MASS.Ks
W1	W1	WISE	33526.00	6357.93	0.07166	WISE/WISE.W1
W2	W2	WISE	46028.00	11073.19	0.05049	WISE/WISE.W2
W3	W3	WISE	115608.00	62758.04	0.04304	WISE/WISE.W3
W4	W4	WISE	220883.00	47397.34	0.01960	WISE/WISE.W4
12mu	12mu	IRAS	110356.60	69306.43	0.05161	IRAS/IRAS.12mu
25mu	25mu	IRAS	230702.01	112542.87	0.01779	IRAS/IRAS.25mu
60mu	60mu	IRAS	581903.91	327605.04	0.00288	IRAS/IRAS.60mu
100mu	100mu	IRAS	995377.63	322249.87	0.00102	IRAS/IRAS.100mu
F435W_ACS	F435W	ACS_WFC	4329.85	900.04	1.32127	HST/ACS_WFC.F435W
F475W_ACS	F475W	ACS_WFC	4746.94	1398.86	1.20185	HST/ACS_WFC.F475W
F555W_ACS	F555W	ACS_WFC	5361.03	1236.10	1.03724	HST/ACS_WFC.F555W
F606W_ACS	F606W	ACS_WFC	5921.88	2253.40	0.92404	HST/ACS_WFC.F606W
F625W_ACS	F625W	ACS_WFC	6311.85	1389.28	0.85309	HST/ACS_WFC.F625W
F775W_ACS	F775W	ACS_WFC	7693.47	1517.31	0.64523	HST/ACS_WFC.F775W
F814W_ACS	F814W	ACS_WFC	8045.53	2098.15	0.60232	HST/ACS_WFC.F814W
F850LP_ACS	F850LP	ACS_WFC	9031.48	1273.50	0.50504	HST/ACS_WFC.F850LP
F300W_WFPC2	F300W	WFPC2_WF	2984.47	914.56	1.82725	HST/WFPC2_WF.F300W
F336W_WFPC2	F336W	WFPC2_WF	3344.09	486.34	1.69425	HST/WFPC2_WF.F336W
F439W_WFPC2	F439W	WFPC2_WF	4311.49	714.01	1.32729	HST/WFPC2_WF.F439W
F450W_WFPC2	F450W	WFPC2_WF	4556.22	810.07	1.25247	HST/WFPC2_WF.F450W
F467M_WFPC2	F467M	WFPC2_WF	4669.94	214.29	1.22208	HST/WFPC2_WF.F467M
F555W_WFPC2	F555W	WFPC2_WF	5442.21	1473.75	1.01636	HST/WFPC2_WF.F555W
F606W_WFPC2	F606W	WFPC2_WF	6001.01	2049.98	0.90978	HST/WFPC2_WF.F606W
F675W_WFPC2	F675W	WFPC2_WF	6718.09	1259.41	0.77885	HST/WFPC2_WF.F675W
F702W_WFPC2	F702W	WFPC2_WF	6918.77	2108.11	0.74476	HST/WFPC2_WF.F702W
F814W_WFPC2	F814W	WFPC2_WF	8001.59	1676.13	0.60786	HST/WFPC2_WF.F814W
F090W	F090W	NIRCam	9021.53	2088.06	0.50583	JWST/NIRCam.F090W
F115W	F115W	NIRCam	11542.61	2644.25	0.33959	JWST/NIRCam.F115W
F150W	F150W	NIRCam	15007.44	3349.30	0.22892	JWST/NIRCam.F150W
F200W	F200W	NIRCam	19886.48	4689.40	0.14166	JWST/NIRCam.F200W
F277W	F277W	NIRCam	27617.40	7064.64	0.09023	JWST/NIRCam.F277W
F356W	F356W	NIRCam	35683.62	8326.81	0.06685	JWST/NIRCam.F356W
F444W	F444W	NIRCam	44043.15	11144.05	0.05304	JWST/NIRCam.F444W
u_MegaCam	u	MegaCam	3676.12	456.42	1.55256	CFHT/MegaCam.u
g_MegaCam	g	MegaCam	4763.98	1532.24	1.19736	CFHT/MegaCam.g
r_MegaCam	r	MegaCam	6382.59	1477.66	0.84035	CFHT/MegaCam.r
i_MegaCam	i	MegaCam	7682.93	1538.12	0.64647	CFHT/MegaCam.i
z_MegaCam	z	MegaCam	8979.62	774.01	0.50916	CFHT/MegaCam.z
Y_WIRCam	Y	WIRCam	10241.51	1105.33	0.41289	CFHT/WIRCam.Y
J_WIRCam	J	WIRCam	12518.72	1587.53	0.29837	CFHT/WIRCam.J
W_WIRCam	W	WIRCam	14524.26	884.59	0.24090	CFHT/WIRCam.W
H_WIRCam	H	WIRCam	16243.54	2911.26	0.19786	CFHT/WIRCam.H
Ks_WIRCam	Ks	WIRCam	21434.00	3270.46	0.12636	CFHT/WIRCam.Ks
u_DECam	u	DECam	3814.33	245.32	1.50330	CTIO/DECam.u
g_DECam	g	DECam	4808.49	1110.21	1.18559	CTIO/DECam.g
r_DECam	r	DECam	6417.65	1477.92	0.83400	CTIO/DECam.r
i_DECam	i	DECam	7814.58	1468.81	0.63078	CTIO/DECam.i
z_DECam	z	DECam	9168.85	1476.78	0.49398	CTIO/DECam.z
Y_DECam	Y	DECam	9896.11	676.44	0.43505	CTIO/DECam.Y
Z_UKIDSS	Z	UKIDSS	8817.00	917.02	0.52194	UKIRT/UKIDSS.Z
Y_UKIDSS	Y	UKIDSS	10305.00	1026.81	0.40917	UKIRT/UKIDSS.Y
J_UKIDSS	J	UKIDSS	12483.00	1581.88	0.29990	UKIRT/UKIDSS.J
H_UKIDSS	H	UKIDSS	16313.00	2952.17	0.19609	UKIRT/UKIDSS.H
K_UKIDSS	K	UKIDSS	22010.00	3511.37	0.12187	UKIRT/UKIDSS.K
I1	I1	IRAC	35378.41	7431.71	0.06748	Spitzer/IRAC.I1
I2	I2	IRAC	44780.49	10096.82	0.05205	Spitzer/IRAC.I2
I3	I3	IRAC	56961.78	13911.89	0.03959	Spitzer/IRAC.I3
I4	I4	IRAC	77978.40	28311.77	0.03466	Spitzer/IRAC.I4
pg	pg	Holmberg	4300	1300	1.33105	\N
pv	pv	Holmberg	5500	1000	1.00201	\N
Bj	Bj	GSC2	3384.97	1059.59	1.67600	Palomar/GSC2.Bj
Rf	Rf	GSC2	4992.74	647.10	1.13599	Palomar/GSC2.Rf
In	In	GSC2	6793.20	2132.52	0.76550	Palomar/GSC2.In
\.


COPY photometry.calib_bands (id,band,magsys) FROM STDIN;
FUV	FUV	AB
NUV	NUV	AB
UVW2	UVW2	Vega
UVM2	UVM2	Vega
UVW1	UVW1	Vega
U_Swift	U_Swift	Vega
B_Swift	B_Swift	Vega
V_Swift	V_Swift	Vega
U	U	Vega
B	B	Vega
V	V	Vega
R	R	Vega
I	I	Vega
J	J	Vega
H	H	Vega
K	K	Vega
U_AB	U	AB
B_AB	B	AB
V_AB	V	AB
R_AB	R	AB
I_AB	I	AB
J_AB	J	AB
H_AB	H	AB
K_AB	K	AB
Rc	Rc	Vega
Ic	Ic	Vega
U_Bessell	U_Bessell	Vega
B_Bessell	B_Bessell	Vega
V_Bessell	V_Bessell	Vega
R_Bessell	R_Bessell	Vega
I_Bessell	I_Bessell	Vega
u	u_SDSS	AB
g	g_SDSS	AB
r	r_SDSS	AB
i	i_SDSS	AB
z	z_SDSS	AB
g_PS1	g_PS1	AB
r_PS1	r_PS1	AB
i_PS1	i_PS1	AB
z_PS1	z_PS1	AB
y_PS1	y_PS1	AB
I_D	I_DENIS	Vega
J_D	J_DENIS	Vega
Ks_D	Ks_DENIS	Vega
J_2M	J_2MASS	Vega
H_2M	H_2MASS	Vega
Ks_2M	Ks_2MASS	Vega
W1	W1	Vega
W2	W2	Vega
W3	W3	Vega
W4	W4	Vega
12mu	12mu	AB
25mu	25mu	AB
60mu	60mu	AB
100mu	100mu	AB
F435W_ACS	F435W_ACS	Vega
F475W_ACS	F475W_ACS	Vega
F555W_ACS	F555W_ACS	Vega
F606W_ACS	F606W_ACS	Vega
F625W_ACS	F625W_ACS	Vega
F775W_ACS	F775W_ACS	Vega
F814W_ACS	F814W_ACS	Vega
F850LP_ACS	F850LP_ACS	Vega
F300W_WFPC2	F300W_WFPC2	Vega
F336W_WFPC2	F336W_WFPC2	Vega
F439W_WFPC2	F439W_WFPC2	Vega
F450W_WFPC2	F450W_WFPC2	Vega
F467M_WFPC2	F467M_WFPC2	Vega
F555W_WFPC2	F555W_WFPC2	Vega
F606W_WFPC2	F606W_WFPC2	Vega
F675W_WFPC2	F675W_WFPC2	Vega
F702W_WFPC2	F702W_WFPC2	Vega
F814W_WFPC2	F814W_WFPC2	Vega
F090W	F090W	Vega
F115W	F115W	Vega
F150W	F150W	Vega
F200W	F200W	Vega
F277W	F277W	Vega
F356W	F356W	Vega
F444W	F444W	Vega
F435W_ACS_AB	F435W_ACS	AB
F475W_ACS_AB	F475W_ACS	AB
F555W_ACS_AB	F555W_ACS	AB
F606W_ACS_AB	F606W_ACS	AB
F625W_ACS_AB	F625W_ACS	AB
F775W_ACS_AB	F775W_ACS	AB
F814W_ACS_AB	F814W_ACS	AB
F850LP_ACS_AB	F850LP_ACS	AB
F300W_WFPC2_AB	F300W_WFPC2	AB
F336W_WFPC2_AB	F336W_WFPC2	AB
F439W_WFPC2_AB	F439W_WFPC2	AB
F450W_WFPC2_AB	F450W_WFPC2	AB
F467M_WFPC2_AB	F467M_WFPC2	AB
F555W_WFPC2_AB	F555W_WFPC2	AB
F606W_WFPC2_AB	F606W_WFPC2	AB
F675W_WFPC2_AB	F675W_WFPC2	AB
F702W_WFPC2_AB	F702W_WFPC2	AB
F814W_WFPC2_AB	F814W_WFPC2	AB
F090W_AB	F090W	AB
F115W_AB	F115W	AB
F150W_AB	F150W	AB
F200W_AB	F200W	AB
F277W_AB	F277W	AB
F356W_AB	F356W	AB
F444W_AB	F444W	AB
u_MegaCam	u_MegaCam	Vega
g_MegaCam	g_MegaCam	Vega
r_MegaCam	r_MegaCam	Vega
i_MegaCam	i_MegaCam	Vega
z_MegaCam	z_MegaCam	Vega
Y_WIRCam	Y_WIRCam	Vega
J_WIRCam	J_WIRCam	Vega
W_WIRCam	W_WIRCam	Vega
H_WIRCam	H_WIRCam	Vega
Ks_WIRCam	Ks_WIRCam	Vega
u_MegaCam_AB	u_MegaCam	AB
g_MegaCam_AB	g_MegaCam	AB
r_MegaCam_AB	r_MegaCam	AB
i_MegaCam_AB	i_MegaCam	AB
z_MegaCam_AB	z_MegaCam	AB
Y_WIRCam_AB	Y_WIRCam	AB
J_WIRCam_AB	J_WIRCam	AB
W_WIRCam_AB	W_WIRCam	AB
H_WIRCam_AB	H_WIRCam	AB
Ks_WIRCam_AB	Ks_WIRCam	AB
u_DECam	u_DECam	AB
g_DECam	g_DECam	AB
r_DECam	r_DECam	AB
i_DECam	i_DECam	AB
z_DECam	z_DECam	AB
Y_DECam	Y_DECam	AB
Z_UKIDSS	Z_UKIDSS	Vega
Y_UKIDSS	Y_UKIDSS	Vega
J_UKIDSS	J_UKIDSS	Vega
H_UKIDSS	H_UKIDSS	Vega
K_UKIDSS	K_UKIDSS	Vega
I1	I1	Vega
I2	I2	Vega
I3	I3	Vega
I4	I4	Vega
pg	pg	Vega
pv	pv	Vega
Bj	Bj	Vega
Rf	Rf	Vega
In	In	Vega
\.


COMMIT;
-- ROLLBACK;
