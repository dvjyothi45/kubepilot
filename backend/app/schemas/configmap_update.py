from pydantic import BaseModel
from typing import Dict


class ConfigMapUpdate(BaseModel):
    data: Dict[str, str]