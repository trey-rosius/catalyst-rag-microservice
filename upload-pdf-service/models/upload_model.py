from pydantic import BaseModel, EncodedStr


class UploadModel(BaseModel):
    filePath: str
    file_name_ext: str
    base_64_encoded: bytes
