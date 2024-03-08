import dataclasses
import logging
from app.server.schema.object import CoordsInfo, GetObjectRequest, GetObjectResponse, ObjectInfo, PositionInfo


def get_object(r: GetObjectRequest) -> GetObjectResponse:
    logging.info(dataclasses.asdict(r))

    return GetObjectResponse(
        object=ObjectInfo(
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
    )
