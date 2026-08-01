from pydantic import BaseModel


class ServiceCreate(BaseModel):
    name: str
    selector: str
    port: int
    target_port: int
    type: str = "ClusterIP"