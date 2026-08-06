from pydantic import BaseModel


class ServiceUpdate(BaseModel):
    port: int
    target_port: int
    type: str = "ClusterIP"