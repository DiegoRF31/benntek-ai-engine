from app.infrastructure.models.submission_model import Submission
from .base_repository import BaseRepository


class SubmissionRepository(BaseRepository):

    def get_by_id(self, submission_id: int) -> Submission | None:
        return (
            self.db.query(Submission)
            .filter(Submission.id == submission_id)
            .first()
        )

    def create(self, submission: Submission) -> Submission:
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def update_score(self, submission: Submission, score: float):
        submission.score_awarded = score
        self.db.commit()
        self.db.refresh(submission)
        return submission
