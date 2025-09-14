from sqlalchemy.inspection import inspect

class BaseModel:
    def to_dict(self):
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}
