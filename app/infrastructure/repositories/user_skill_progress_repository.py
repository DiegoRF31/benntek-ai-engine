from app.infrastructure.models.user_skill_progress_model import UserSkillProgress
from .base_repository import BaseRepository


class UserSkillProgressRepository(BaseRepository):

    def get_by_user_and_skill(self, user_id: int, skill_id: int):
        return (
            self.db.query(UserSkillProgress)
            .filter(
                UserSkillProgress.user_id == user_id,
                UserSkillProgress.skill_id == skill_id
            )
            .first()
        )

    def create(self, progress: UserSkillProgress):
        self.db.add(progress)
        self.db.commit()
        self.db.refresh(progress)
        return progress

    def update(self, progress: UserSkillProgress):
        self.db.commit()
        self.db.refresh(progress)
        return progress