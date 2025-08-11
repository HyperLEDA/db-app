from astropy import units as u
from astropy.coordinates import Angle, Latitude, Longitude, SkyCoord
from astroquery.hips2fits import hips2fits
from matplotlib import axes

from experiments import entities


def get_hips_map(
    obj: entities.CrossIDInfo,
    fov: float,
    hips_map: str,
    collision_data: list[entities.PGCObjectInfo],
    ax: axes.Axes,
) -> None:
    result = hips2fits.query(
        hips=hips_map,
        width=500,
        height=500,
        ra=Longitude(obj.ra * u.deg),
        dec=Latitude(obj.dec * u.deg),
        fov=Angle(fov * u.deg),
        projection="AIT",
        get_query_payload=False,
        format="jpg",
        min_cut=0.5,
        max_cut=99.5,
        cmap="viridis",
    )
    fov = fov * 0.5
    ax.imshow(result, extent=(obj.ra + fov, obj.ra - fov, obj.dec - fov, obj.dec + fov))
    ax.scatter(obj.ra, obj.dec, color="blue", marker="x")
    ax.errorbar(obj.ra, obj.dec, obj.pos_err, obj.pos_err, ecolor="blue")
    ax.set_title(f"{obj.name} | {obj.status}")

    for pgc_obj in collision_data:
        print(pgc_obj.ra, pgc_obj.dec, pgc_obj.name, pgc_obj.pos_err)
        ax.scatter(pgc_obj.ra, pgc_obj.dec, color="red", marker="s")
        ax.errorbar(pgc_obj.ra, pgc_obj.dec, pgc_obj.pos_err, pgc_obj.pos_err, ecolor="red")
        ax.text(pgc_obj.ra, pgc_obj.dec, pgc_obj.name, color="white", fontsize=8, ha="left", va="bottom")

        ax.plot([obj.ra, pgc_obj.ra], [obj.dec, pgc_obj.dec], color="yellow", linewidth=1, alpha=0.7)

        central_coord = SkyCoord(ra=obj.ra * u.deg, dec=obj.dec * u.deg)
        collision_coord = SkyCoord(ra=pgc_obj.ra * u.deg, dec=pgc_obj.dec * u.deg)
        distance = central_coord.separation(collision_coord)

        mid_ra = (obj.ra + pgc_obj.ra) / 2
        mid_dec = (obj.dec + pgc_obj.dec) / 2

        prob = obj.pgc_numbers[pgc_obj.pgc]
        ax.text(
            mid_ra,
            mid_dec,
            f'{distance.arcsec:.1f}" | {prob:.3f}',
            color="yellow",
            fontsize=8,
            ha="center",
            va="center",
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "black", "alpha": 0.7},
        )
