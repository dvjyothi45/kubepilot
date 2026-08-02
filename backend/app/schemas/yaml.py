from pydantic import BaseModel


class YAMLManifest(BaseModel):
    yaml: str