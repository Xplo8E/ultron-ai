# src/ultron/ignorer.py
from typing import List, Optional, Set, Tuple, Union
from pathlib import Path
import re

from .models import ReviewData, HighConfidenceVulnerabilityIssue, LowPrioritySuggestionIssue

class ReviewIgnorer:
    def __init__(self, ignore_file_rules: Optional[List[str]] = None, ignore_line_rules: Optional[List[str]] = None):
        # Rules are strings like "filepath_glob" or "filepath_glob:line_number" or "filepath_glob:CWE-ID"
        self.file_ignores: Set[str] = set() # Glob patterns for whole files
        self.line_specific_ignores: List[Tuple[str, str]] = [] # (filepath_glob, line_or_id_pattern)

        if ignore_file_rules:
            for rule in ignore_file_rules:
                self.file_ignores.add(rule.strip())
        
        if ignore_line_rules:
            for rule in ignore_line_rules:
                rule = rule.strip()
                if ':' in rule:
                    parts = rule.split(':', 1)
                    filepath_glob = parts[0].strip()
                    line_or_id_pattern = parts[1].strip()
                    self.line_specific_ignores.append((filepath_glob, line_or_id_pattern))
                else: # If no colon, assume it's a file-level glob ignore as well
                    self.file_ignores.add(rule)


    def _is_file_ignored(self, file_path: Optional[Path]) -> bool:
        if not file_path: # For direct code input
            return False
        for pattern in self.file_ignores:
            if file_path.match(pattern):
                return True
        return False

    def _is_issue_on_line_ignored(
        self,
        issue: Union[HighConfidenceVulnerabilityIssue, LowPrioritySuggestionIssue],
        file_path: Optional[Path]
    ) -> bool:
        if not file_path:
            return False

        issue_line_str = str(issue.line)
        # issue_cwe_or_type = str(issue.type.value if isinstance(issue.type, Enum) else issue.type) # Simplified for now

        for file_glob, line_pattern in self.line_specific_ignores:
            if file_path.match(file_glob):
                # Check if line_pattern is a direct line number or a more complex pattern (e.g., CWE-ID)
                # For simplicity, this example just checks direct line match.
                # For CWE-ID, you'd need to parse that from the issue if available.
                if line_pattern == issue_line_str: # or re.match(line_pattern, issue_cwe_or_type)
                    return True
        return False

    def filter_review_data(self, review_data: ReviewData, file_path: Optional[Path] = None) -> ReviewData:
        if self._is_file_ignored(file_path):
            print(f"Ignoring all findings for file: {file_path} due to ignore rule.")
            return ReviewData(
                summary=f"All findings for {file_path.name if file_path else 'direct input'} ignored by rule.",
                high_confidence_vulnerabilities=[],
                low_priority_suggestions=[],
                input_code_tokens=review_data.input_code_tokens,
                additional_context_tokens=review_data.additional_context_tokens
            )

        original_hc_count = len(review_data.high_confidence_vulnerabilities)
        original_lp_count = len(review_data.low_priority_suggestions)

        review_data.high_confidence_vulnerabilities = [
            issue for issue in review_data.high_confidence_vulnerabilities
            if not self._is_issue_on_line_ignored(issue, file_path)
        ]
        review_data.low_priority_suggestions = [
            issue for issue in review_data.low_priority_suggestions
            if not self._is_issue_on_line_ignored(issue, file_path)
        ]
        
        ignored_hc_count = original_hc_count - len(review_data.high_confidence_vulnerabilities)
        ignored_lp_count = original_lp_count - len(review_data.low_priority_suggestions)

        if ignored_hc_count > 0 or ignored_lp_count > 0:
            print(f"Ignored {ignored_hc_count} high-confidence and {ignored_lp_count} low-priority issues for {file_path.name if file_path else 'direct input'} based on line-specific rules.")
            review_data.summary += f" (Note: {ignored_hc_count + ignored_lp_count} issues were filtered by ignore rules for this file)."

        return review_data