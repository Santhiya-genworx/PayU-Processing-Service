from pydantic import BaseModel


class MatchingOutput(BaseModel):
    status: str
    confidence_score: float
    command: str
    mail_to: str | None
    mail_subject: str | None
    mail_body: str | None


class GraphResult(BaseModel):
    output: MatchingOutput
