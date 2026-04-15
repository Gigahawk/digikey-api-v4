import json
from pathlib import Path

from bravado.client import SwaggerClient


def swagger_path(name: str) -> str:
    return str(Path(__file__).absolute().parent / "swagger" / name)


def swagger_dict(name: str) -> dict:
    with open(swagger_path(name), "r") as f:
        data = json.load(f)
        # Remove security definitions, seems to break parsing?
        if "security" in data:
            data["security"] = []
        return data


def swagger_client(
    name: str | None = None, _dict: dict | None = None, *args, **kwargs
) -> SwaggerClient:
    if _dict is None:
        if name is None:
            raise ValueError("A definition must be provided")
        _dict = swagger_dict(name)
    return SwaggerClient.from_spec(_dict, *args, **kwargs)
