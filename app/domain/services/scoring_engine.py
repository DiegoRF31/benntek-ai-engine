from typing import List
from app.domain.entities.submission_evaluation import (
    SubmissionEvaluation,
    ObjectiveScore
)


class ScoringEngine:

    @staticmethod
    def evaluate_submission(
        submission_id: int,
        objective_results: List[dict]
    ) -> SubmissionEvaluation:

        objective_scores = []
        total_score = 0.0
        max_score = 0.0

        for obj in objective_results:
            score = obj["score"]
            maximum = obj["max_score"]

            total_score += score
            max_score += maximum

            objective_scores.append(
                ObjectiveScore(
                    objective_id=obj["objective_id"],
                    score=score,
                    max_score=maximum
                )
            )

        return SubmissionEvaluation(
            submission_id=submission_id,
            total_score=total_score,
            max_score=max_score,
            objective_scores=objective_scores
        )