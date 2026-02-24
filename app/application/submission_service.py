
from sqlalchemy.orm import Session

from app.infrastructure.repositories.submission_repository import SubmissionRepository
from app.infrastructure.repositories.challenge_repository import ChallengeRepository
from app.infrastructure.repositories.user_repository import UserRepository

from app.infrastructure.models.submission_model import Submission

from app.domain.services.scoring_engine import ScoringEngine

class SubmissionService:

    def __init__(self, db: Session):
        self.db = db
        self.submission_repo = SubmissionRepository(db)
        self.challenge_repo = ChallengeRepository(db)
        self.user_repo = UserRepository(db)

    def process_submission(
        self,
        user_id: int,
        challenge_version_id: int,
        input_text: str,
        attempt_number: int
    ):
        # Validate the user exist
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
    
        submission = Submission(
            user_id=user_id,
            challenge_version_id=challenge_version_id,
            input_text=input_text,
            attempt_number=attempt_number,
            score_awarded=0.0
        )

        submission = self.submission_repo.create(submission)
    
        # Basic submision
        simulated_results = [
            {"objective_id": 1, "score": 10.0, "max_score": 10.0},
            {"objective_id": 2, "score": 5.0, "max_score": 10.0}
        ]
    
        evaluation = ScoringEngine.evaluate_submission(
            submission_id=submission.id,
            objective_results=simulated_results
        )

        final_percentage = evaluation.percentage

        self.submission_repo.update_score(
            submission=submission,
            score=final_percentage
        )

        return {
            "submission_id": submission.id,
            "total_score": evaluation.total_score,
            "max_score": evaluation.max_score,
            "percentage": evaluation.percentage
        }