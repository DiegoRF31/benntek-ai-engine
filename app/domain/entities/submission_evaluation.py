from dataclasses import dataclass
from typing import List


@dataclass
class ObjectiveScore:
    objective_id: int
    score: float
    max_score: float


@dataclass
class SubmissionEvaluation:
    submission_id: int
    total_score: float
    max_score: float
    objective_scores: List[ObjectiveScore]

    @property
    def percentage(self) -> float:
        if self.max_score == 0:
            return 0.0
        return (self.total_score / self.max_score) * 100