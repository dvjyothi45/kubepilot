from pydantic import BaseModel
from typing import Dict


class SecretUpdate(BaseModel):
    data: Dict[str, str]