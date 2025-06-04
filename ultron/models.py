# src/ultron/models.py
from enum import Enum
from typing import List, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator

class ReviewIssueTypeEnum(str, Enum):
    BUG = "Bug"
    SECURITY = "Security"
    PERFORMANCE = "Performance"
    STYLE = "Style"
    BEST_PRACTICE = "Best Practice"
    SUGGESTION = "Suggestion"
    UNKNOWN = "Unknown Issue"

class ConfidenceScoreEnum(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class SeverityAssessmentEnum(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class HighConfidenceVulnerabilityIssue(BaseModel):
    type: Union[ReviewIssueTypeEnum, str] = Field(default=ReviewIssueTypeEnum.SECURITY)
    confidence_score: Optional[Union[ConfidenceScoreEnum, str]] = Field(default=None, alias="confidenceScore")
    severity_assessment: Optional[Union[SeverityAssessmentEnum, str]] = Field(default=None, alias="severityAssessment")
    line: Union[str, int]
    description: str
    impact: str
    proof_of_concept_code_or_command: Optional[str] = Field(default=None, alias="proofOfConceptCodeOrCommand")
    proof_of_concept_explanation: Optional[str] = Field(default=None, alias="proofOfConceptExplanation")
    poc_actionability_tags: Optional[List[str]] = Field(default_factory=list, alias="pocActionabilityTags")
    suggestion: Optional[str] = None

    @field_validator('type', 'confidence_score', 'severity_assessment', mode='before')
    @classmethod
    def ensure_enum_or_str(cls, value: Any, field_info) -> Union[Enum, str, None]:
        if value is None:
            return None
        
        enum_map = {
            "type": ReviewIssueTypeEnum,
            "confidence_score": ConfidenceScoreEnum,
            "severity_assessment": SeverityAssessmentEnum,
        }
        target_enum = enum_map.get(field_info.field_name)
        if target_enum:
            try:
                return target_enum(value)
            except ValueError:
                return str(value)
        return str(value)


class LowPrioritySuggestionIssue(BaseModel):
    type: Union[ReviewIssueTypeEnum, str] = Field(default=ReviewIssueTypeEnum.SUGGESTION)
    line: Union[str, int]
    description: str
    suggestion: Optional[str] = None

    @field_validator('type', mode='before')
    @classmethod
    def ensure_valid_type(cls, value: Any) -> Union[ReviewIssueTypeEnum, str]:
        try:
            return ReviewIssueTypeEnum(value)
        except ValueError:
            return str(value)

class ReviewData(BaseModel):
    summary: str
    high_confidence_vulnerabilities: List[HighConfidenceVulnerabilityIssue] = Field(default_factory=list, alias="highConfidenceVulnerabilities")
    low_priority_suggestions: List[LowPrioritySuggestionIssue] = Field(default_factory=list, alias="lowPrioritySuggestions")
    input_code_tokens: Optional[int] = Field(default=None, alias="inputCodeTokens")
    additional_context_tokens: Optional[int] = Field(default=None, alias="additionalContextTokens")
    error: Optional[str] = None