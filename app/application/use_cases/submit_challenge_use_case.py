from sqlalchemy.orm import Session
from app.infrastructure.models.submission_model import Submission
from app.domain.services.scoring_service import ScoringService
from app.domain.services.skill_progress_service import SkillProgressService


class SubmitChallengeUseCase:

    @staticmethod
    def execute(db: Session, submission: Submission):

        # Calculate score
        score = ScoringService.evaluate_submission(db, submission)

        SkillProgressService.update_user_skills(
            db,
            submission,
            score
        )

        db.commit()

        return score