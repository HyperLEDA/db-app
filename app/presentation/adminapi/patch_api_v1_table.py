from aiohttp import web
from marshmallow import Schema, fields
from marshmallow_generic import GenericSchema
from marshmallow_oneofschema import one_of_schema

from app.lib.web import responses
from app.presentation.adminapi import interface


class PatchTableActionTypeChangeUCDSchema(GenericSchema[interface.PatchTableActionTypeChangeUCD]):
    column = fields.Str(required=True, metadata={"description": "Name of the column"})
    ucd = fields.Str(required=True, metadata={"description": "New UCD value"})


class PatchTableActionTypeChangeUnitSchema(GenericSchema[interface.PatchTableActionTypeChangeUnit]):
    column = fields.Str(required=True, metadata={"description": "Name of the column"})
    unit = fields.Str(required=True, metadata={"description": "New unit value"})


class PatchTableActionSchema(one_of_schema.OneOfSchema):
    type_schemas = {
        "change_ucd": PatchTableActionTypeChangeUCDSchema,
        "change_unit": PatchTableActionTypeChangeUnitSchema,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, interface.PatchTableActionTypeChangeUCD):
            return "change_ucd"

        if isinstance(obj, interface.PatchTableActionTypeChangeUnit):
            return "change_unit"

        raise Exception(f"Unknown object type: {obj.__class__.__name__}")


class PatchTableRequestSchema(GenericSchema[interface.PatchTableRequest]):
    table_name = fields.Str(required=True, metadata={"description": "Name of the table"})
    actions = fields.List(
        fields.Nested(PatchTableActionSchema),
        required=True,
        metadata={"description": "List of actions to perform"},
    )


class PatchTableResponseSchema(Schema):
    pass


async def patch_table_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Patch table schema
    description: |
        Patch the schema of the table, including column UCDs and units.
    tags: [table]
    requestBody:
        required: true
        content:
            application/json:
                schema: PatchTableRequestSchema
    responses:
        200:
            description: Table was successfully patched
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: PatchTableResponseSchema
    """
    request = PatchTableRequestSchema().load(await r.json())
    return responses.APIOkResponse(actions.patch_table(request))
