from sqlalchemy.orm import Session
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.objective_result_model import ObjectiveResult
from app.infrastructure.models.user_skill_progress_model import UserSkillProgress
from app.domain.services.scoring_engine import ScoringEngine
from datetime import datetime


class SubmissionService:

    def __init__(self, db: Session):
        self.db = db

    def submit(
        self,
        user_id: int,
        challenge_version_id: int,
        input_text: str,
        objective_results_data: list
    ):
        # Create submission entity
        submission = Submission(
            user_id=user_id,
            challenge_version_id=challenge_version_id,
            input_text=input_text,
            attempt_number=1,
            score_awarded=0.0,
            created_at=datetime.utcnow()
        )

        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)

        # Store objective results
        total_score = 0
        max_score = 0

        for result in objective_results_data:

            objective_result = ObjectiveResult(
                submission_id=submission.id,
                objective_id=result["objective_id"],
                score=result["score"],
                max_score=result["max_score"]
            )

            self.db.add(objective_result)

            total_score += result["score"]
            max_score += result["max_score"]

        # Calculate final percentage
        percentage = (total_score / max_score) * 100 if max_score > 0 else 0

        submission.score_awarded = total_score

        self.db.commit()

        # Update user skills if challenge has skills defined
        challenge_version = submission.challenge_version

        if challenge_version.skills:

            for skill_name, weight in challenge_version.skills.items():

                weighted_score = percentage * weight

                existing = (
                    self.db.query(UserSkillProgress)
                    .filter_by(user_id=user_id, skill_name=skill_name)
                    .first()
                )

                if existing:
                    existing.skill_score += weighted_score
                    existing.attempts_count += 1
                    existing.last_updated = datetime.utcnow()
                else:
                    new_skill = UserSkillProgress(
                        user_id=user_id,
                        skill_name=skill_name,
                        skill_score=weighted_score,
                        attempts_count=1
                    )
                    self.db.add(new_skill)

        self.db.commit()

        # Return evaluation result object
        return type(
            "EvaluationResult",
            (),
            {
                "total_score": total_score,
                "percentage": percentage
            }
        )