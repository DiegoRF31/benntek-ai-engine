from app.infrastructure.models.challenge_model import Challenge
from .base_repository import BaseRepository


class ChallengeRepository(BaseRepository):

    def get_by_id(self, challenge_id: int) -> Challenge | None:
        return (
            self.db.query(Challenge)
            .filter(Challenge.id == challenge_id)
            .first()
        )
