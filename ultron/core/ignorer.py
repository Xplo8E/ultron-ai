# src/ultron/ignorer.py
from typing import List, Optional, Set, Tuple, Union
from pathlib import Path
from enum import Enum

# MODIFIED: Updated import path
from ..models.data_models import BatchReviewData, FileReviewData, HighConfidenceVulnerability, LowPrioritySuggestion

class ReviewIgnorer:
    def __init__(self, ignore_file_rules: Optional[List[str]] = None, ignore_line_rules: Optional[List[str]] = None):
        self.file_globs_to_ignore: Set[str] = set(rule.strip() for rule in ignore_file_rules) if ignore_file_rules else set()
        # line_specific_ignores: List of (file_glob_pattern, line_or_id_pattern_to_ignore)
        self.line_specific_ignores: List[Tuple[str, str]] = []
        if ignore_line_rules:
            for rule in ignore_line_rules:
                parts = rule.strip().split(':', 1)
                if len(parts) == 2:
                    self.line_specific_ignores.append((parts[0].strip(), parts[1].strip()))
                elif len(parts) == 1 and parts[0].strip(): # Treat as file glob if no colon
                     self.file_globs_to_ignore.add(parts[0].strip())


    def _is_issue_ignored(
        self,
        issue: Union[HighConfidenceVulnerability, LowPrioritySuggestion],
        file_path_str: str # Relative file path string
    ) -> bool:
        # Check if the file path itself matches any line-specific ignore rule's file glob
        for file_glob, line_pattern in self.line_specific_ignores:
            # Note: Path(file_path_str).match(file_glob) might be more robust if globs are complex
            # For simplicity, direct match or simple wildcard can be handled here.
            # More robust glob matching might be needed depending on pattern complexity.
            # This basic check assumes file_glob is a simple prefix or exact match for now.
            # Or use fnmatch.fnmatch(file_path_str, file_glob)
            
            # Simple check: if file_path_str starts with file_glob (if glob is a dir path like "tests/*")
            # or exact match. For true globbing, use Path.match or fnmatch.
            path_matches_glob = False
            try:
                # Using Path.match for proper globbing relative to some assumed root (tricky without a root)
                # For simplicity, let's assume ignore rules are for paths as they appear.
                 if Path(file_path_str).match(file_glob): # Requires file_glob to be a valid pattern
                    path_matches_glob = True
            except Exception: # Handle invalid glob patterns gracefully
                 if file_path_str == file_glob: # Fallback to exact match
                    path_matches_glob = True


            if path_matches_glob:
                issue_line_str = str(issue.line)
                # TODO: Extend line_pattern to handle CWEs or vulnerability types if needed
                # For now, it's a direct line number string match
                if line_pattern == issue_line_str:
                    return True
        return False

    def filter_batch_review_data(self, batch_data: BatchReviewData) -> BatchReviewData:
        if not batch_data.file_reviews:
            return batch_data

        filtered_file_reviews: List[FileReviewData] = []
        total_hc_ignored = 0
        total_lp_ignored = 0

        for file_review in batch_data.file_reviews:
            # Check if the entire file is ignored by a file-level glob
            file_is_globally_ignored = False
            file_path_obj = Path(file_review.file_path) # Use Path for matching
            for glob_pattern in self.file_globs_to_ignore:
                if file_path_obj.match(glob_pattern):
                    file_is_globally_ignored = True
                    break
            
            if file_is_globally_ignored:
                print(f"Ignoring all findings for file: {file_review.file_path} due to global ignore rule: '{glob_pattern}'.")
                # We might still want to keep the file entry but with empty findings
                file_review.summary = f"All findings ignored by rule '{glob_pattern}'. Original: {file_review.summary}"
                total_hc_ignored += len(file_review.high_confidence_vulnerabilities)
                total_lp_ignored += len(file_review.low_priority_suggestions)
                file_review.high_confidence_vulnerabilities = []
                file_review.low_priority_suggestions = []
                filtered_file_reviews.append(file_review)
                continue

            original_hc_count = len(file_review.high_confidence_vulnerabilities)
            file_review.high_confidence_vulnerabilities = [
                issue for issue in file_review.high_confidence_vulnerabilities
                if not self._is_issue_ignored(issue, file_review.file_path)
            ]
            current_hc_ignored = original_hc_count - len(file_review.high_confidence_vulnerabilities)
            total_hc_ignored += current_hc_ignored

            original_lp_count = len(file_review.low_priority_suggestions)
            file_review.low_priority_suggestions = [
                issue for issue in file_review.low_priority_suggestions
                if not self._is_issue_ignored(issue, file_review.file_path)
            ]
            current_lp_ignored = original_lp_count - len(file_review.low_priority_suggestions)
            total_lp_ignored += current_lp_ignored
            
            if current_hc_ignored > 0 or current_lp_ignored > 0:
                 file_review.summary += f" (Note: {current_hc_ignored + current_lp_ignored} issues filtered by line-specific rules)."


            filtered_file_reviews.append(file_review)
        
        batch_data.file_reviews = filtered_file_reviews
        if total_hc_ignored > 0 or total_lp_ignored > 0:
            ignore_note = f" (Note: Total {total_hc_ignored} high-confidence and {total_lp_ignored} low-priority issues were filtered by ignore rules across all files)."
            batch_data.overall_batch_summary = (batch_data.overall_batch_summary or "") + ignore_note
            print(ignore_note.strip())


        return batch_data