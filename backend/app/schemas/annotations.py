from pydantic import BaseModel
from typing import Dict


class AnnotationsUpdate(BaseModel):
    annotations: Dict[str, str]