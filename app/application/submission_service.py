
from sqlalchemy.orm import Session
from typing import List

from app.infrastructure.repositories.submission_repository import SubmissionRepository
from app.infrastructure.repositories.challenge_repository import ChallengeRepository
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.objective_result_model import ObjectiveResult
from app.domain.services.scoring_engine import ScoringEngine


class SubmissionService:

    def __init__(self, db: Session):
        self.db = db
        self.submission_repo = SubmissionRepository(db)
        self.challenge_repo = ChallengeRepository(db)

    def submit(
        self,
        user_id: int,
        challenge_version_id: int,
        input_text: str,
        objective_results_data: List[dict]
    ):
        
        # Create submission entity
        submission = Submission(
            user_id=user_id,
            challenge_version_id=challenge_version_id,
            input_text=input_text,
            attempt_number=1,
        )

        submission = self.submission_repo.create(submission)

        # Evaluate using Domain Scoring Engine
        evaluation = ScoringEngine.evaluate_submission(
            submission_id=submission.id,
            objective_results=objective_results_data
        )

        # Persist objective results
        for obj in evaluation.objective_scores:
            result = ObjectiveResult(
                submission_id=submission.id,
                objective_id=obj.objective_id,
                passed=obj.score > 0,
                points_awarded=obj.score
            )
            self.db.add(result)

        self.db.commit()

        # Update submission score
        self.submission_repo.update_score(
            submission=submission,
            score=evaluation.total_score
        )

        return evaluation