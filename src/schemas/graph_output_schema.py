"""module: graph_output_schema.py"""

from pydantic import BaseModel


class MatchingOutput(BaseModel):
    """Pydantic model representing the output of a matching process. This model includes fields for the status of the matching operation, a confidence score indicating the reliability of the match, a command that may be executed based on the match, and optional fields for email details (recipient, subject, and body) that can be used to notify relevant parties about the match. The status field is a string that indicates whether the matching process was successful or if any issues were encountered. The confidence_score is a float value that quantifies the confidence level of the match, typically ranging from 0.0 to 1.0, where higher values indicate greater confidence. The command field is a string that specifies an action or set of instructions to be executed based on the match results. The mail_to, mail_subject, and mail_body fields are optional strings that provide details for sending an email notification related to the match, allowing for communication with stakeholders or users about the outcome of the matching process."""

    status: str
    confidence_score: float
    command: str
    mail_to: str | None
    mail_subject: str | None
    mail_body: str | None


class GraphResult(BaseModel):
    """ ""Pydantic model representing the result of a graph-based validation process. This model includes a single field, output, which is an instance of the MatchingOutput model. The GraphResult model serves as a wrapper for the output of the graph validation, allowing for structured representation of the results that can be easily serialized and returned in API responses or used within the application logic. By encapsulating the MatchingOutput within the GraphResult, it provides a clear and consistent format for handling the results of graph-based validations across different parts of the system."""

    output: MatchingOutput
