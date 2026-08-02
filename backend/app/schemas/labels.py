from pydantic import BaseModel
from typing import Dict


class LabelsUpdate(BaseModel):
    labels: Dict[str, str]