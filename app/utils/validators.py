from functools import wraps
from flask import request
from app.utils.responses import error_response

def validate_json(required_fields):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return error_response('Invalid JSON', 400)
            data = request.get_json()
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return error_response(f'Missing fields: {", ".join(missing_fields)}', 400)
            return f(data=data, *args, **kwargs)
        return wrapper
    return decorator