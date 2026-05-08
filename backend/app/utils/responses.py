from fastapi.encoders import jsonable_encoder


def success_response(data, message: str = "ok") -> dict:
    return {"code": 0, "data": jsonable_encoder(data), "message": message}


def error_response(message: str, code: int) -> dict:
    return {"code": code, "data": None, "message": message}
