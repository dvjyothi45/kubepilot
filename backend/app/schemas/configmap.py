from pydantic import BaseModel


class ConfigMapCreate(BaseModel):
    name: str
    data: dict[str, str]