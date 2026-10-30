BEGIN;

CREATE TABLE layer2.objects (
  pgc	Integer	PRIMARY KEY	REFERENCES common.pgc (id)	ON DELETE restrict ON UPDATE cascade
, name	Text	NOT NULL	UNIQUE
, objtype	Text	NOT NULL	REFERENCES nature.object_type(type_name)	ON DELETE restrict ON UPDATE cascade
, ra	Double Precision	CHECK (ra >= 0 AND ra < 360)
, dec	Double Precision	CHECK (dec >= -90 AND dec <= 90)
, e_ra	Double Precision	CHECK (e_ra >= 0)
, e_dec	Double Precision	CHECK (e_dec >= 0)
, l	Double Precision	CHECK (l >= 0 AND l < 360)
, b	Double Precision	CHECK (b >= -90 AND b <= 90)
, sgl	Double Precision	CHECK (sgl >= 0 AND sgl < 360)
, sgb	Double Precision	CHECK (sgb >= -90 AND sgb <= 90)
, ebv	Real	CHECK (ebv >= 0)
) ;

CREATE INDEX objects_sky_equatorial_idx ON layer2.objects USING gist (ST_MakePoint(ra, dec)) ;
CREATE INDEX objects_sky_galactic_idx ON layer2.objects USING gist (ST_MakePoint(l, b)) ;
CREATE INDEX objects_sky_supergalactic_idx ON layer2.objects USING gist (ST_MakePoint(sgl, sgb)) ;

CREATE INDEX ON layer2.objects (ra,dec) ;
CREATE INDEX ON layer2.objects (dec) ;
CREATE INDEX ON layer2.objects (l,b) ;
CREATE INDEX ON layer2.objects (b) ;
CREATE INDEX ON layer2.objects (sgl,sgb) ;
CREATE INDEX ON layer2.objects (sgb) ;


SELECT meta.setparams( 'layer2' , 'objects' , '{"description": "Main catalogue of astronomical objects in LEDA", "ucd": "meta.table;meta.main"}'::json ) ;

SELECT meta.setparams( 'layer2' , 'objects' , 'pgc', '{"description": "Principal Galaxy Catalog identifier", "ucd": "meta.id;meta.main"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'name', '{"description": "Principal designation of the object", "ucd": "meta.id"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'objtype', '{"description": "Object classification code", "ucd": "meta.code.class"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'ra', '{"description": "Right Ascension in the ICRS reference frame", "unit": "deg", "ucd": "pos.eq.ra;meta.main"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'dec', '{"description": "Declination in the ICRS reference frame", "unit": "deg", "ucd": "pos.eq.dec;meta.main"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'e_ra', '{"description": "One-sigma uncertainty in Right Ascension along RA axis (sigma_RA*cos(Dec))", "unit": "deg", "ucd": "stat.error;pos.eq.ra"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'e_dec', '{"description": "One-sigma uncertainty in Declination", "unit": "deg", "ucd": "stat.error;pos.eq.dec"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'l', '{"description": "Galactic longitude in the IAU Galactic coordinate system", "unit": "deg", "ucd": "pos.galactic.lon"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'b', '{"description": "Galactic latitude in the IAU Galactic coordinate system", "unit": "deg", "ucd": "pos.galactic.lat"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'sgl', '{"description": "Supergalactic longitude in the de Vaucouleurs supergalactic coordinate system improved by Lahav et al. (2000MNRAS.312..166L)", "unit": "deg", "ucd": "pos.supergalactic.lon"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'sgb', '{"description": "Supergalactic latitude in the de Vaucouleurs supergalactic coordinate system improved by Lahav et al. (2000MNRAS.312..166L)", "unit": "deg", "ucd": "pos.supergalactic.lat"}'::json ) ;
SELECT meta.setparams( 'layer2' , 'objects' , 'ebv', '{"description": "Galactic foreground color excess E(B-V) from the Schlegel, Finkbeiner & Davis (1998ApJ...500..525S) map", "unit": "mag", "ucd": "phot.color.excess"}'::json ) ;

COMMIT;