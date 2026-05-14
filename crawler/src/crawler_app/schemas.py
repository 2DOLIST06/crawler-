from pydantic import BaseModel
class ProjectCreate(BaseModel):
    name:str; start_url:str; allowed_domain:str
