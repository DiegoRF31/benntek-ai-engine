from pydantic import BaseModel


class SubmissionCreate(BaseModel):
    user_id: int
    challenge_version_id: int
    input_text: str
    attempt_number: int