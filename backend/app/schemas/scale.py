from pydantic import BaseModel


class ScaleDeployment(BaseModel):
    replicas: int