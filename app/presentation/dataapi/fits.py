import datetime

from aiohttp import web
from marshmallow import ValidationError, fields, validate
from marshmallow_generic import GenericSchema

from app.lib.web import responses
from app.lib.web.errors import RuleValidationError
from app.presentation.dataapi import interface


class DelimitedListField(fields.List):
    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return value.split(",")
        except AttributeError as e:
            raise ValidationError(f"{attr} is not a delimited list it has a non string value {value}.") from e


class FITSRequestSchema(GenericSchema[interface.FITSRequest]):
    pgcs = DelimitedListField(fields.Integer(metadata={"description": "List of PGC numbers"}))
    ra = fields.Float(metadata={"description": "Right ascension of the center of the search area in degrees"})
    dec = fields.Float(metadata={"description": "Declination of the center of the search area in degrees"})
    radius = fields.Float(metadata={"description": "Radius of the search area in degrees"})
    name = fields.String(metadata={"description": "Name of the object"})
    cz = fields.Float(metadata={"description": "Redshift value"})
    cz_err_percent = fields.Float(metadata={"description": "Acceptable deviation of the redshift value in percent"})
    page_size = fields.Integer(
        metadata={"description": "Number of objects per page"},
        validate=validate.OneOf([10, 25, 50, 100, 1000, 10000, 100000]),
        load_default=25,
    )
    page = fields.Integer(metadata={"description": "Page number"}, load_default=0)


async def fits_handler(actions: interface.Actions, r: web.Request) -> responses.BinaryResponse:
    """---
    summary: Query data about objects and return as FITS file
    description: |
        Obtains data about the objects according to the specified parameters and returns it as a FITS file.
        All of the conditions are combined with the logical AND operator.
        For example, if both coordinates and designation are specified, object must be in the specified area and have
        the specified designation.
    parameters:
      - in: query
        schema: FITSRequestSchema
    responses:
        200:
            description: Success
            content:
                application/fits:
                    schema:
                        type: string
                        format: binary
    """
    try:
        request = FITSRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    fits_data = actions.query_fits(request)

    filename = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H-%M-%S")
    return responses.BinaryResponse(
        fits_data,
        content_type="application/fits",
        headers={"Content-Disposition": f'attachment; filename="{filename}.fits"'},
    )
