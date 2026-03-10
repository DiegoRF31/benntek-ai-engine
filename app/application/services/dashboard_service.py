from sqlalchemy.orm import Session

from app.infrastructure.models.user_model import User
from app.infrastructure.models.submission_model import Submission

from app.schemas.dashboard_schema import (
    DashboardResponse,
    DashboardUser,
    DashboardStats,
    RecentSubmission
)


class DashboardService:

    @staticmethod
    def get_dashboard(db: Session, current_user: User) -> DashboardResponse:

        total_users = db.query(User).filter(
            User.tenant_id == current_user.tenant_id
        ).count()

        total_submissions = db.query(Submission).filter(
            Submission.tenant_id == current_user.tenant_id
        ).count()

        recent_submissions = (
            db.query(Submission)
            .filter(Submission.tenant_id == current_user.tenant_id)
            .order_by(Submission.id.desc())
            .limit(5)
            .all()
        )

        recent_activity = [
            RecentSubmission(
                id=sub.id,
                challenge_version_id=sub.challenge_version_id,
                attempt_number=sub.attempt_number
            )
            for sub in recent_submissions
        ]

        return DashboardResponse(
            user=DashboardUser(
                id=current_user.id,
                email=current_user.email,
                role=current_user.role
            ),
            stats=DashboardStats(
                total_users=total_users,
                total_submissions=total_submissions
            ),
            recent_activity=recent_activity
        )