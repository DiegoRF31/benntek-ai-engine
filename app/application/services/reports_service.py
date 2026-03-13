import csv
import io
from datetime import datetime, date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.infrastructure.models.user_model import User
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.challenge_model import Challenge
from app.infrastructure.models.challenge_version_model import ChallengeVersion
from app.infrastructure.models.cohort_model import Cohort, CohortEnrollment, CohortChallenge
from app.schemas.reports_schema import ReportTypesResponse, ReportTypeItem

_PASS_THRESHOLD = 70.0
_INSTRUCTOR_ROLES = {"instructor", "admin"}

REPORT_TYPES = [
    ReportTypeItem(
        id="student_performance",
        name="Student Performance",
        description="Best scores per challenge per student, including pass/fail status and attempt counts",
        filters=["cohortId", "startDate", "endDate"],
        formats=["csv", "json"],
    ),
    ReportTypeItem(
        id="challenge_statistics",
        name="Challenge Statistics",
        description="Aggregated challenge metrics: average scores, pass rates, and unique student counts",
        filters=["cohortId", "startDate", "endDate"],
        formats=["csv", "json"],
    ),
    ReportTypeItem(
        id="submission_history",
        name="Submission History",
        description="Complete raw submission log with scores, timestamps, and challenge details",
        filters=["cohortId", "startDate", "endDate"],
        formats=["csv", "json"],
    ),
    ReportTypeItem(
        id="cohort_summary",
        name="Cohort Summary",
        description="Per-student progress summary: challenges attempted/passed, average score, and pass rate",
        filters=["cohortId"],
        formats=["csv", "json"],
    ),
    ReportTypeItem(
        id="leaderboard",
        name="Leaderboard",
        description="Student rankings by average score with challenge completion counts",
        filters=["cohortId", "startDate", "endDate"],
        formats=["csv", "json"],
    ),
]


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _to_csv(rows: list[dict], fieldnames: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


class ReportsService:

    @staticmethod
    def get_report_types() -> ReportTypesResponse:
        return ReportTypesResponse(report_types=REPORT_TYPES)

    @staticmethod
    def generate_report(
        db: Session,
        current_user: User,
        report_type: str,
        fmt: str,
        cohort_id: Optional[int],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> tuple[str, list[dict]]:
        """
        Returns (csv_string, json_rows). Caller chooses which to use based on `fmt`.
        Raises HTTPException for unknown report types or access violations.
        """
        if current_user.role not in _INSTRUCTOR_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Instructor access required",
            )

        valid_ids = {rt.id for rt in REPORT_TYPES}
        if report_type not in valid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown report type: {report_type}",
            )

        start_dt = _parse_date(start_date)
        end_dt = _parse_date(end_date)

        # ── Scope resolution ───────────────────────────────────────────────
        if cohort_id is not None:
            cohort = db.query(Cohort).filter(
                Cohort.id == cohort_id,
                Cohort.tenant_id == current_user.tenant_id,
            ).first()
            if not cohort:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

            enrolled_ids = [
                row.user_id
                for row in db.query(CohortEnrollment.user_id)
                .filter(CohortEnrollment.cohort_id == cohort_id)
                .all()
            ]
            version_ids = [
                row.id
                for row in db.query(ChallengeVersion.id)
                .join(CohortChallenge, CohortChallenge.challenge_id == ChallengeVersion.challenge_id)
                .filter(CohortChallenge.cohort_id == cohort_id)
                .all()
            ]
        else:
            enrolled_ids = [
                row.id
                for row in db.query(User.id)
                .filter(User.tenant_id == current_user.tenant_id)
                .all()
            ]
            version_ids = [
                row.id
                for row in db.query(ChallengeVersion.id)
                .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
                .filter(Challenge.tenant_id == current_user.tenant_id)
                .all()
            ]

        if not enrolled_ids or not version_ids:
            return "", []

        dispatch = {
            "student_performance": ReportsService._student_performance,
            "challenge_statistics": ReportsService._challenge_statistics,
            "submission_history": ReportsService._submission_history,
            "cohort_summary": ReportsService._cohort_summary,
            "leaderboard": ReportsService._leaderboard,
        }
        return dispatch[report_type](db, enrolled_ids, version_ids, start_dt, end_dt)

    # ── Report generators ──────────────────────────────────────────────────

    @staticmethod
    def _base_submission_query(db: Session, enrolled_ids, version_ids, start_dt, end_dt):
        q = (
            db.query(Submission)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
                Submission.score_awarded.isnot(None),
            )
        )
        if start_dt:
            q = q.filter(Submission.created_at >= start_dt)
        if end_dt:
            q = q.filter(Submission.created_at <= end_dt)
        return q

    @staticmethod
    def _student_performance(db, enrolled_ids, version_ids, start_dt, end_dt):
        """Best score per student per challenge."""
        q = (
            db.query(
                User.username.label("student_name"),
                User.email,
                Challenge.title.label("challenge_title"),
                Challenge.category,
                Challenge.difficulty,
                func.max(Submission.score_awarded).label("best_score"),
                func.count(Submission.id).label("attempts"),
            )
            .join(User, Submission.user_id == User.id)
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
                Submission.score_awarded.isnot(None),
            )
        )
        if start_dt:
            q = q.filter(Submission.created_at >= start_dt)
        if end_dt:
            q = q.filter(Submission.created_at <= end_dt)

        rows_db = (
            q.group_by(User.id, User.username, User.email, Challenge.id, Challenge.title, Challenge.category, Challenge.difficulty)
            .order_by(User.username, Challenge.title)
            .all()
        )

        fields = ["student_name", "email", "challenge_title", "category", "difficulty", "best_score", "passed", "attempts"]
        rows = [
            {
                "student_name": r.student_name,
                "email": r.email,
                "challenge_title": r.challenge_title,
                "category": r.category or "",
                "difficulty": r.difficulty or "",
                "best_score": round(float(r.best_score or 0), 2),
                "passed": "Yes" if (r.best_score or 0) >= _PASS_THRESHOLD else "No",
                "attempts": int(r.attempts),
            }
            for r in rows_db
        ]
        return _to_csv(rows, fields), rows

    @staticmethod
    def _challenge_statistics(db, enrolled_ids, version_ids, start_dt, end_dt):
        q = (
            db.query(
                Challenge.title.label("challenge_title"),
                Challenge.category,
                Challenge.difficulty,
                func.count(Submission.id).label("total_submissions"),
                func.avg(Submission.score_awarded).label("avg_score"),
                func.count(func.distinct(Submission.user_id)).label("unique_students"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
                Submission.score_awarded.isnot(None),
            )
        )
        if start_dt:
            q = q.filter(Submission.created_at >= start_dt)
        if end_dt:
            q = q.filter(Submission.created_at <= end_dt)

        rows_db = (
            q.group_by(Challenge.id, Challenge.title, Challenge.category, Challenge.difficulty)
            .order_by(Challenge.title)
            .all()
        )

        # Pass counts via separate query
        pass_q = (
            db.query(
                Challenge.id.label("challenge_id"),
                func.count(func.distinct(Submission.user_id)).label("unique_passers"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
                Submission.score_awarded >= _PASS_THRESHOLD,
            )
            .group_by(Challenge.id)
        )
        if start_dt:
            pass_q = pass_q.filter(Submission.created_at >= start_dt)
        if end_dt:
            pass_q = pass_q.filter(Submission.created_at <= end_dt)

        pass_map = {r.challenge_id: int(r.unique_passers) for r in pass_q.all()}

        # Rebuild full challenge id map for pass lookups
        cid_q = (
            db.query(Challenge.title.label("title"), Challenge.id.label("id"))
            .join(ChallengeVersion, ChallengeVersion.challenge_id == Challenge.id)
            .filter(ChallengeVersion.id.in_(version_ids))
            .distinct()
            .all()
        )
        title_to_id = {r.title: r.id for r in cid_q}

        fields = ["challenge_title", "category", "difficulty", "total_submissions", "avg_score", "pass_rate", "unique_students", "unique_passers"]
        rows = []
        for r in rows_db:
            unique_students = int(r.unique_students or 0)
            cid = title_to_id.get(r.challenge_title)
            unique_passers = pass_map.get(cid, 0) if cid else 0
            pass_rate = round((unique_passers / unique_students) * 100, 1) if unique_students > 0 else 0.0
            rows.append({
                "challenge_title": r.challenge_title,
                "category": r.category or "",
                "difficulty": r.difficulty or "",
                "total_submissions": int(r.total_submissions),
                "avg_score": round(float(r.avg_score or 0), 2),
                "pass_rate": pass_rate,
                "unique_students": unique_students,
                "unique_passers": unique_passers,
            })
        return _to_csv(rows, fields), rows

    @staticmethod
    def _submission_history(db, enrolled_ids, version_ids, start_dt, end_dt):
        q = (
            db.query(
                User.username.label("student_name"),
                User.email,
                Challenge.title.label("challenge_title"),
                Challenge.category,
                Submission.score_awarded,
                Submission.created_at,
            )
            .join(User, Submission.user_id == User.id)
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
            )
        )
        if start_dt:
            q = q.filter(Submission.created_at >= start_dt)
        if end_dt:
            q = q.filter(Submission.created_at <= end_dt)

        rows_db = q.order_by(Submission.created_at.desc()).all()

        fields = ["student_name", "email", "challenge_title", "category", "score", "passed", "submitted_at"]
        rows = [
            {
                "student_name": r.student_name,
                "email": r.email,
                "challenge_title": r.challenge_title,
                "category": r.category or "",
                "score": round(float(r.score_awarded or 0), 2) if r.score_awarded is not None else "",
                "passed": "Yes" if (r.score_awarded or 0) >= _PASS_THRESHOLD else "No",
                "submitted_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows_db
        ]
        return _to_csv(rows, fields), rows

    @staticmethod
    def _cohort_summary(db, enrolled_ids, version_ids, start_dt, end_dt):
        # Per-student aggregate
        stats_rows = (
            db.query(
                Submission.user_id,
                func.avg(Submission.score_awarded).label("avg_score"),
                func.count(Submission.id).label("total_submissions"),
                func.count(func.distinct(ChallengeVersion.challenge_id)).label("challenges_attempted"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
                Submission.score_awarded.isnot(None),
            )
            .group_by(Submission.user_id)
            .all()
        )
        stats_map = {r.user_id: r for r in stats_rows}

        # Challenges passed (best score >= threshold)
        best_sub = (
            db.query(
                Submission.user_id,
                ChallengeVersion.challenge_id,
                func.max(Submission.score_awarded).label("best_score"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
            )
            .group_by(Submission.user_id, ChallengeVersion.challenge_id)
            .subquery()
        )
        passed_rows = (
            db.query(
                best_sub.c.user_id,
                func.count(best_sub.c.challenge_id).label("passed"),
            )
            .filter(best_sub.c.best_score >= _PASS_THRESHOLD)
            .group_by(best_sub.c.user_id)
            .all()
        )
        passed_map = {r.user_id: int(r.passed) for r in passed_rows}

        enrolled_users = db.query(User).filter(User.id.in_(enrolled_ids)).all()

        fields = ["student_name", "email", "challenges_attempted", "challenges_passed", "avg_score", "total_submissions", "pass_rate"]
        rows = []
        for u in enrolled_users:
            stats = stats_map.get(u.id)
            attempted = int(stats.challenges_attempted) if stats else 0
            passed = passed_map.get(u.id, 0)
            avg_score = round(float(stats.avg_score or 0), 2) if stats else 0.0
            total_subs = int(stats.total_submissions) if stats else 0
            pass_rate = round((passed / attempted) * 100, 1) if attempted > 0 else 0.0
            rows.append({
                "student_name": u.username,
                "email": u.email,
                "challenges_attempted": attempted,
                "challenges_passed": passed,
                "avg_score": avg_score,
                "total_submissions": total_subs,
                "pass_rate": pass_rate,
            })

        rows.sort(key=lambda r: r["avg_score"], reverse=True)
        return _to_csv(rows, fields), rows

    @staticmethod
    def _leaderboard(db, enrolled_ids, version_ids, start_dt, end_dt):
        q = (
            db.query(
                User.username.label("student_name"),
                User.email,
                func.avg(Submission.score_awarded).label("avg_score"),
                func.count(Submission.id).label("total_submissions"),
            )
            .join(User, Submission.user_id == User.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
                Submission.score_awarded.isnot(None),
            )
        )
        if start_dt:
            q = q.filter(Submission.created_at >= start_dt)
        if end_dt:
            q = q.filter(Submission.created_at <= end_dt)

        rows_db = (
            q.group_by(User.id, User.username, User.email)
            .order_by(func.avg(Submission.score_awarded).desc())
            .all()
        )

        # Challenges passed
        best_sub = (
            db.query(
                Submission.user_id,
                ChallengeVersion.challenge_id,
                func.max(Submission.score_awarded).label("best_score"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
            )
            .group_by(Submission.user_id, ChallengeVersion.challenge_id)
            .subquery()
        )
        passed_rows = (
            db.query(
                best_sub.c.user_id,
                func.count(best_sub.c.challenge_id).label("passed"),
            )
            .filter(best_sub.c.best_score >= _PASS_THRESHOLD)
            .group_by(best_sub.c.user_id)
            .all()
        )
        passed_map = {r.user_id: int(r.passed) for r in passed_rows}

        # Resolve user_id from rows_db via a second query
        user_id_map = {
            row.username: row.id
            for row in db.query(User.username, User.id).filter(User.id.in_(enrolled_ids)).all()
        }

        fields = ["rank", "student_name", "email", "avg_score", "challenges_passed", "total_submissions"]
        rows = []
        for rank, r in enumerate(rows_db, start=1):
            uid = user_id_map.get(r.student_name)
            rows.append({
                "rank": rank,
                "student_name": r.student_name,
                "email": r.email,
                "avg_score": round(float(r.avg_score or 0), 2),
                "challenges_passed": passed_map.get(uid, 0) if uid else 0,
                "total_submissions": int(r.total_submissions),
            })
        return _to_csv(rows, fields), rows
