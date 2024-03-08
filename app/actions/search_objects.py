import dataclasses
import logging

from app.server.schema import SearchObjectsRequest, SearchObjectsResponse
from app.server.schema.object import CoordsInfo, ObjectInfo, PositionInfo


def search_objects(r: SearchObjectsRequest) -> SearchObjectsResponse:
    logging.info(dataclasses.asdict(r))

    logging.info(dataclasses.asdict(r))

    return SearchObjectsResponse(
        objects=[
            ObjectInfo(
                name="M33",
                type="galaxy",
                position=PositionInfo(
                    coordinate_system="equatorial",
                    epoch="J2000",
                    coords=CoordsInfo(
                        ra=150.34,
                        dec=-55.7,
                    ),
                ),
            ),
            ObjectInfo(
                name="M31",
                type="galaxy",
                position=PositionInfo(
                    coordinate_system="equatorial",
                    epoch="J2000",
                    coords=CoordsInfo(
                        ra=150.34,
                        dec=-55.7,
                    ),
                ),
            ),
        ],
    )
