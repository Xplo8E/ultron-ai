# src/ultron/sarif_models.py
# Simplified SARIF Pydantic models. The full SARIF schema is very extensive.
# See: https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/sarif-v2.1.0-cs01.html
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class SarifVersion(str, Enum):
    V2_1_0 = "2.1.0"

class SarifReportingDescriptor(BaseModel):
    id: str # e.g., CWE-79, ULTRON-PERFORMANCE-001
    name: Optional[str] = None
    short_description: Optional[Dict[str, str]] = Field(default_factory=lambda: {"text": ""}, alias="shortDescription")
    full_description: Optional[Dict[str, str]] = Field(default_factory=lambda: {"text": ""}, alias="fullDescription")
    help_uri: Optional[str] = Field(default=None, alias="helpUri")
    # Could add properties for severity, etc.

class SarifArtifactLocation(BaseModel):
    uri: str
    uri_base_id: Optional[str] = Field(default=None, alias="uriBaseId")

class SarifRegion(BaseModel):
    start_line: Optional[int] = Field(default=None, alias="startLine")
    # Can add startColumn, endLine, endColumn

class SarifPhysicalLocation(BaseModel):
    artifact_location: SarifArtifactLocation = Field(alias="artifactLocation")
    region: Optional[SarifRegion] = None

class SarifLocation(BaseModel):
    physical_location: Optional[SarifPhysicalLocation] = Field(default=None, alias="physicalLocation")
    # message: Optional[Dict[str,str]] = None # Message specific to this location

class SarifResult(BaseModel):
    rule_id: str = Field(alias="ruleId") # Corresponds to ReportingDescriptor.id
    level: str # "error", "warning", "note", "none"
    message: Dict[str, str] # Main message for the result
    locations: Optional[List[SarifLocation]] = None
    # Can add partialFingerprints, relatedLocations, etc.

class SarifToolComponent(BaseModel):
    name: str
    version: Optional[str] = None
    information_uri: Optional[str] = Field(default=None, alias="informationUri")
    rules: Optional[List[SarifReportingDescriptor]] = None

class SarifTool(BaseModel):
    driver: SarifToolComponent

class SarifRun(BaseModel):
    tool: SarifTool
    results: Optional[List[SarifResult]] = None
    # Can add artifacts, invocations, etc.

class SarifLog(BaseModel):
    version: SarifVersion
    schema_uri: Optional[str] = Field(default="https://json.schemastore.org/sarif-2.1.0.json", alias="$schema")
    runs: List[SarifRun]