# src/ultron/sarif_converter.py
from typing import List, Optional, Dict, Union
from pathlib import Path
from enum import Enum


from .models import ReviewData, HighConfidenceVulnerabilityIssue, LowPrioritySuggestionIssue, ReviewIssueTypeEnum, SeverityAssessmentEnum
from .sarif_models import (
    SarifLog, SarifRun, SarifTool, SarifToolComponent, SarifResult,
    SarifReportingDescriptor, SarifLocation, SarifPhysicalLocation,
    SarifArtifactLocation, SarifRegion, SarifVersion
)
from . import __version__ as ultron_version


def _level_from_issue(issue: Union[HighConfidenceVulnerabilityIssue, LowPrioritySuggestionIssue]) -> str:
    if isinstance(issue, HighConfidenceVulnerabilityIssue):
        if issue.severity_assessment:
            sev_map = {
                SeverityAssessmentEnum.CRITICAL: "error",
                SeverityAssessmentEnum.HIGH: "error",
                SeverityAssessmentEnum.MEDIUM: "warning",
                SeverityAssessmentEnum.LOW: "note" # or "warning"
            }
            # Handle if severity_assessment is string
            return sev_map.get(issue.severity_assessment if isinstance(issue.severity_assessment, Enum) else SeverityAssessmentEnum(str(issue.severity_assessment).capitalize()), "warning")
        return "error" # Default for high confidence
    return "note" # Default for low priority

def _generate_rule_id(issue: Union[HighConfidenceVulnerabilityIssue, LowPrioritySuggestionIssue]) -> str:
    # Basic rule ID, can be made more specific e.g. ULTRON-SECURITY-SQLI
    issue_type_str = str(issue.type.value if isinstance(issue.type, Enum) else issue.type).upper().replace(" ", "_")
    return f"ULTRON-{issue_type_str}"


def convert_review_to_sarif(review_data: ReviewData, file_path: Optional[Path] = None, tool_name: str = "Ultron Code Reviewer") -> SarifLog:
    results: List[SarifResult] = []
    rules_map: Dict[str, SarifReportingDescriptor] = {} # To store unique rules

    all_issues = review_data.high_confidence_vulnerabilities + review_data.low_priority_suggestions

    for issue in all_issues:
        rule_id = _generate_rule_id(issue)
        
        if rule_id not in rules_map:
            rules_map[rule_id] = SarifReportingDescriptor(
                id=rule_id,
                name=str(issue.type.value if isinstance(issue.type, Enum) else issue.type),
                short_description={"text": f"Issue of type: {issue.type.value if isinstance(issue.type, Enum) else issue.type}"},
                full_description={"text": issue.description[:200]} # Truncate for brevity
            )

        message_text = f"{issue.type.value if isinstance(issue.type, Enum) else issue.type}: {issue.description}"
        if hasattr(issue, 'impact') and issue.impact: # For HighConfidenceVulnerabilityIssue
             message_text += f"\nImpact: {issue.impact}"
        if issue.suggestion:
            message_text += f"\nSuggestion: {issue.suggestion}"
        
        sarif_result = SarifResult(
            ruleId=rule_id,
            level=_level_from_issue(issue),
            message={"text": message_text}
        )

        if file_path:
            # Try to convert line to int, handle 'N/A' or ranges if your model provides them
            start_line = None
            try:
                if isinstance(issue.line, str) and '-' in issue.line: # e.g. "10-15"
                    start_line = int(issue.line.split('-')[0])
                elif issue.line != "N/A":
                    start_line = int(issue.line)
            except ValueError:
                pass # Keep start_line as None

            sarif_result.locations = [
                SarifLocation(
                    physicalLocation=SarifPhysicalLocation(
                        artifactLocation=SarifArtifactLocation(uri=file_path.as_uri()),
                        region=SarifRegion(startLine=start_line) if start_line else None
                    )
                )
            ]
        results.append(sarif_result)

    tool_component = SarifToolComponent(
        name=tool_name,
        version=ultron_version,
        rules=list(rules_map.values()) if rules_map else None
    )

    sarif_run = SarifRun(
        tool=SarifTool(driver=tool_component),
        results=results if results else None # SARIF spec allows empty results array or no results property
    )

    return SarifLog(version=SarifVersion.V2_1_0, runs=[sarif_run])