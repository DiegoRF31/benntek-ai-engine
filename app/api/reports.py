from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import require_role
from app.infrastructure.models.user_model import User
from app.application.services.reports_service import ReportsService
from app.schemas.reports_schema import ReportTypesResponse

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/types", response_model=ReportTypesResponse)
def get_report_types(
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    return ReportsService.get_report_types()


@router.get("/{report_type}")
def generate_report(
    report_type: str,
    format: str = Query(default="json", alias="format"),
    cohortId: Optional[int] = Query(default=None),
    startDate: Optional[str] = Query(default=None),
    endDate: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    csv_str, json_rows = ReportsService.generate_report(
        db=db,
        current_user=current_user,
        report_type=report_type,
        fmt=format,
        cohort_id=cohortId,
        start_date=startDate,
        end_date=endDate,
    )

    if format == "csv":
        filename = f"{report_type}_{_today()}.csv"
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return {"report_type": report_type, "generated_at": _today(), "rows": json_rows}


def _today() -> str:
    from datetime import date
    return date.today().isoformat()
