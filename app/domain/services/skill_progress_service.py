from sqlalchemy.orm import Session
from app.infrastructure.models.user_skill_progress_model import UserSkillProgress
from datetime import datetime


class SkillProgressService:

    @staticmethod
    def calculate_level(skill_score: float) -> int:
        if skill_score < 100:
            return 1
        elif skill_score < 250:
            return 2
        elif skill_score < 500:
            return 3
        return 4


    @staticmethod
    def update_user_skills(
        db: Session,
        submission,
        score: float
    ):

        skill_weights = submission.challenge_version.skills or {}

        for skill_name, weight in skill_weights.items():

            weighted_score = score * weight

            existing = db.query(UserSkillProgress).filter_by(
                user_id=submission.user_id,
                skill_name=skill_name
            ).first()

            if not existing:
                existing = UserSkillProgress(
                    user_id=submission.user_id,
                    skill_name=skill_name,
                    skill_score=0.0,
                    attempts_count=0
                )
                db.add(existing)

            existing.skill_score += weighted_score
            existing.attempts_count += 1
            existing.last_updated = datetime.utcnow()

            
            existing.level = SkillProgressService.calculate_level(
                existing.skill_score
            )