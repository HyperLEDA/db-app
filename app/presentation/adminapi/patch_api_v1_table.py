from aiohttp import web
from marshmallow import Schema, fields
from marshmallow_oneofschema import one_of_schema

from app.lib.web import responses, schema
from app.presentation.adminapi import interface


class PatchTableActionTypeChangeUCDSchema(schema.RequestSchema):
    column = fields.Str(required=True, description="Name of the column")
    ucd = fields.Str(required=True, description="New UCD value")

    class Meta:
        model = interface.PatchTableActionTypeChangeUCD


class PatchTableActionTypeChangeUnitSchema(schema.RequestSchema):
    column = fields.Str(required=True, description="Name of the column")
    unit = fields.Str(required=True, description="New unit value")

    class Meta:
        model = interface.PatchTableActionTypeChangeUnit


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


class PatchTableRequestSchema(schema.RequestSchema):
    table_id = fields.Int(required=True, description="ID of the table")
    actions = fields.List(
        fields.Nested(PatchTableActionSchema),
        required=True,
        description="List of actions to perform",
    )

    class Meta:
        model = interface.PatchTableRequest


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
