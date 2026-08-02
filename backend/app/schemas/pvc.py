from pydantic import BaseModel


class PVCCreate(BaseModel):
    name: str
    storage: str
    access_mode: str = "ReadWriteOnce"