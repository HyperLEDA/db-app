import os

from marshmallow import fields


class EnvField(fields.Field):
    def __init__(self, env_var, field, *args, **kwargs):
        self.env_var = env_var
        self.field = field
        super().__init__(*args, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        val = os.getenv(self.env_var) or value

        return self.field.deserialize(val, attr, data, **kwargs)
