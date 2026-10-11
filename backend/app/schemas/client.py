from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClientListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_code: int
    inn: str
    name: str
    kpp: str | None = None
    department_id: UUID | None = None
    department_name: str | None = None
    is_active: bool
    is_system: bool


class ClientCreate(BaseModel):
    client_code: int
    inn: str
    name: str = Field(min_length=1, max_length=500)
    kpp: str | None = None
    department_id: UUID | None = None
    department_id_set: bool = False

    @model_validator(mode="before")
    @classmethod
    def mark_department(cls, data: object) -> object:
        if isinstance(data, dict) and "department_id" in data:
            return {**data, "department_id_set": True}
        return data


class ClientUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    kpp: str | None = None
    is_active: bool = True
    department_id: UUID | None = None


class ClientUploadError(BaseModel):
    row: int
    message: str


class ClientUploadResult(BaseModel):
    created: int
    errors: int
    message: str
    error_details: list[ClientUploadError]
