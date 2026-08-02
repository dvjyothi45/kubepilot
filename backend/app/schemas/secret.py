from pydantic import BaseModel


class SecretCreate(BaseModel):
    name: str
    data: dict[str, str]