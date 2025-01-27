from dataclasses import dataclass

from marshmallow import Schema, fields, post_load


@dataclass
class PGCObject:
    pgc: int
    catalogs: dict[str, dict]


class PGCObjectSchema(Schema):
    pgc = fields.Integer()
    catalogs = fields.Dict(keys=fields.String(), values=fields.Dict(keys=fields.String()))

    @post_load
    def make(self, data, **kwargs) -> PGCObject:
        return PGCObject(**data)
