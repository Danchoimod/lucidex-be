from typing import Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool
    data: DataT | None = None
    message: str | None = None
    error_code: str | None = None


class HealthData(BaseModel):
    status: str


class ValidationIssue(BaseModel):
    field: str
    message: str
    error_type: str


class ValidationErrorData(BaseModel):
    errors: list[ValidationIssue]
