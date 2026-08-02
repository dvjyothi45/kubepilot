from pydantic import BaseModel

class NamespaceCreate(BaseModel):
    name: str