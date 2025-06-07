# src/ultron/sarif_converter.py
from typing import List, Optional, Dict, Union as PyUnion
from pathlib import Path
from enum import Enum

# MODIFIED: Updated import paths
from ..models.data_models import (
    BatchReviewData, FileReviewData, HighConfidenceVulnerability, LowPrioritySuggestion,
    ReviewIssueTypeEnum, SeverityAssessmentEnum
)
from ..models.sarif_models import (
    SarifLog, SarifRun, SarifTool, SarifToolComponent, SarifResult,
    SarifReportingDescriptor, SarifLocation, SarifPhysicalLocation,
    SarifArtifactLocation, SarifRegion, SarifVersion
)
from .. import __version__ as ultron_version

def _level_from_issue(issue: PyUnion[HighConfidenceVulnerability, LowPrioritySuggestion]) -> str:
    if isinstance(issue, HighConfidenceVulnerability):
        if issue.severity_assessment:
            sev = issue.severity_assessment
            sev_str = sev.value if isinstance(sev, Enum) else str(sev)
            sev_map = {
                "Critical": "error", "High": "error",
                "Medium": "warning", "Low": "note"
            }
            return sev_map.get(sev_str.capitalize(), "warning")
        return "error"
    return "note"

def _generate_rule_id(issue_type: PyUnion[ReviewIssueTypeEnum, str]) -> str:
    type_str = issue_type.value if isinstance(issue_type, Enum) else str(issue_type)
    return f"ULTRON-{type_str.upper().replace(' ', '_').replace('.', '')}"

def convert_batch_review_to_sarif(
    batch_review_data: BatchReviewData,
    project_root: Path,
    tool_name: str = "ULTRON-AI: Prime Directive Protocol"
) -> SarifLog:
    all_results: List[SarifResult] = []
    rules_map: Dict[str, SarifReportingDescriptor] = {}

    if batch_review_data.error: # Handle batch level error
        # Optionally create a notification result for the batch error
        # For now, returning an empty valid SARIF if there's a top-level error
         pass


    for file_review in batch_review_data.file_reviews:
        if file_review.error: # Skip files that had individual processing errors by LLM
            # Optionally create a notification for this file-specific error
            continue

        # Create an absolute path by joining the project root with the relative file path
        # from the review data. This ensures .as_uri() will work.
        absolute_file_path = project_root.joinpath(file_review.file_path).resolve()
        all_issues_for_file = file_review.high_confidence_vulnerabilities + file_review.low_priority_suggestions

        for issue in all_issues_for_file:
            rule_id = _generate_rule_id(issue.type)
            
            if rule_id not in rules_map:
                issue_type_str = issue.type.value if isinstance(issue.type, Enum) else str(issue.type)
                rules_map[rule_id] = SarifReportingDescriptor(
                    id=rule_id,
                    name=issue_type_str,
                    short_description={"text": f"ULTRON DETECTED: {issue_type_str}"},
                    full_description={"text": issue.description[:250] + ('...' if len(issue.description) > 250 else '')}
                )

            message_text = f"[{issue.type.value if isinstance(issue.type, Enum) else str(issue.type)}] {issue.description}"
            if isinstance(issue, HighConfidenceVulnerability) and issue.impact:
                 message_text += f"\nImpact: {issue.impact}"
            if issue.suggestion:
                message_text += f"\nSuggestion: {issue.suggestion}"
            
            sarif_result = SarifResult(
                ruleId=rule_id,
                level=_level_from_issue(issue),
                message={"text": message_text}
            )

            start_line = None
            try:
                if isinstance(issue.line, str) and '-' in issue.line:
                    start_line = int(issue.line.split('-')[0])
                elif str(issue.line).lower() != "n/a":
                    start_line = int(issue.line)
            except ValueError: pass

            # Use the absolute path to generate the URI
            sarif_result.locations = [
                SarifLocation(
                    physicalLocation=SarifPhysicalLocation(
                        artifactLocation=SarifArtifactLocation(uri=absolute_file_path.as_uri()),
                        region=SarifRegion(startLine=start_line) if start_line else None
                    )
                )
            ]
            all_results.append(sarif_result)

    tool_component = SarifToolComponent(
        name=tool_name,
        version=ultron_version,
        rules=list(rules_map.values()) if rules_map else None
    )
    sarif_run = SarifRun(
        tool=SarifTool(driver=tool_component),
        results=all_results if all_results else None
    )
    return SarifLog(version=SarifVersion.V2_1_0, runs=[sarif_run])