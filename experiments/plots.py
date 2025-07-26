from astropy import units as u
from astropy.coordinates import Angle, Latitude, Longitude
from astroquery.hips2fits import hips2fits
from matplotlib import axes


def get_hips_map(
    ra: float,
    dec: float,
    fov: float,
    hips_map: str,
    collision_data: list[tuple[float, float, str]],
    ax: axes.Axes,
) -> None:
    result = hips2fits.query(
        hips=hips_map,
        width=500,
        height=500,
        ra=Longitude(ra * u.deg),
        dec=Latitude(dec * u.deg),
        fov=Angle(fov * u.deg),
        projection="AIT",
        get_query_payload=False,
        format="jpg",
        min_cut=0.5,
        max_cut=99.5,
        cmap="viridis",
    )
    fov = fov * 0.5
    ax.imshow(result, extent=(ra + fov, ra - fov, dec - fov, dec + fov))
    ax.scatter(ra, dec, color="black", marker="x")

    for x, y, name in collision_data:
        print(x, y, name)
        ax.scatter(x, y, color="red", marker="x")
        ax.text(x, y, name, color="white", fontsize=8, ha="left", va="bottom")
