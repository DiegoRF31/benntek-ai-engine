from typing import List
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.objective_result_model import ObjectiveResult
from sqlalchemy.orm import Session


class ScoringService:

    @staticmethod
    def evaluate_submission(
        db: Session,
        submission: Submission
    ) -> float:
        
        challenge_version = submission.challenge_version
        objectives = challenge_version.objectives
        scoring_rules = challenge_version.scoring_rules

        total_score = 0.0

        for objective in objectives:

            objective_id = objective["id"]
            max_points = scoring_rules.get(str(objective_id), 0)

            #pending validation
            passed = True

            points_awarded = max_points if passed else 0

            result = ObjectiveResult(
                submission_id=submission.id,
                objective_id=objective_id,
                passed=passed,
                points_awarded=points_awarded
            )

            db.add(result)
            total_score += points_awarded

        submission.score_awarded = total_score

        return total_score