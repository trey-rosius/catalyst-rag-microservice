from pydantic import BaseModel, EmailStr


class QueryModel(BaseModel):
    query: str
