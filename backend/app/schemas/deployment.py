from pydantic import BaseModel


class DeploymentCreate(BaseModel):
    name: str
    image: str
    replicas: int = 1