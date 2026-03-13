from pydantic import BaseModel
from typing import List


class ReportTypeItem(BaseModel):
    id: str
    name: str
    description: str
    filters: List[str]
    formats: List[str]


class ReportTypesResponse(BaseModel):
    report_types: List[ReportTypeItem]
