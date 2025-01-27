from marshmallow import Schema, post_load


class RequestSchema(Schema):
    @post_load
    def make(self, data, **kwargs):
        return self.Meta.model(**data)
