# ultron/models/data_models.py
from enum import Enum
from typing import List, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator

class ReviewIssueTypeEnum(str, Enum):
    BUG = "Bug"; SECURITY = "Security"; PERFORMANCE = "Performance"
    STYLE = "Style"; BEST_PRACTICE = "Best Practice"; SUGGESTION = "Suggestion"
    UNKNOWN = "Unknown Issue"

class ConfidenceScoreEnum(str, Enum):
    HIGH = "High"; MEDIUM = "Medium"; LOW = "Low"

class SeverityAssessmentEnum(str, Enum):
    CRITICAL = "Critical"; HIGH = "High"; MEDIUM = "Medium"; LOW = "Low"

class HighConfidenceVulnerability(BaseModel):
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
    # MODIFIED: Added analysis_source to track if the agent enhanced the finding.
    analysis_source: Optional[str] = Field(default="initial_scan", alias="analysisSource")
    investigation_log: Optional[List[str]] = Field(default=None, alias="investigationLog")

    @field_validator('type', 'confidence_score', 'severity_assessment', mode='before')
    @classmethod
    def _ensure_enum_or_str(cls, value: Any, field_info) -> Union[Enum, str, None]:
        if value is None: return None
        enum_map = {
            "type": ReviewIssueTypeEnum,
            "confidence_score": ConfidenceScoreEnum,
            "severity_assessment": SeverityAssessmentEnum,
        }
        target_enum = enum_map.get(field_info.field_name)
        if target_enum:
            try: return target_enum(value)
            except ValueError: return str(value)
        return str(value)

class LowPrioritySuggestion(BaseModel):
    type: Union[ReviewIssueTypeEnum, str] = Field(default=ReviewIssueTypeEnum.SUGGESTION)
    line: Union[str, int]
    description: str
    suggestion: Optional[str] = None

    @field_validator('type', mode='before')
    @classmethod
    def _ensure_valid_type(cls, value: Any) -> Union[ReviewIssueTypeEnum, str]:
        try: return ReviewIssueTypeEnum(value)
        except ValueError: return str(value)

class FileReviewData(BaseModel): # Represents review for a single file in the batch
    file_path: str = Field(alias="filePath")
    language_detected: Optional[str] = Field(default=None, alias="languageDetected")
    summary: str
    high_confidence_vulnerabilities: List[HighConfidenceVulnerability] = Field(default_factory=list, alias="highConfidenceVulnerabilities")
    low_priority_suggestions: List[LowPrioritySuggestion] = Field(default_factory=list, alias="lowPrioritySuggestions")
    error: Optional[str] = None # Error specific to this file's processing by LLM

class BatchReviewData(BaseModel): # Top-level model for the multi-file response
    overall_batch_summary: Optional[str] = Field(default="", alias="overallBatchSummary")
    file_reviews: List[FileReviewData] = Field(default_factory=list, alias="fileReviews")
    total_input_tokens: Optional[int] = Field(default=None, alias="totalInputTokens")
    llm_processing_notes: Optional[str] = Field(default=None, alias="llmProcessingNotes")
    error: Optional[str] = None # For errors processing the entire batch request