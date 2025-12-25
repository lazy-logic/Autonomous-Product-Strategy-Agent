"""
============================================================
Data Quality Validation Module
============================================================
PURPOSE: Validate extracted data before synthesis.

ADDRESSES GAP: "Data Quality Validation" - Catch bad/placeholder data

Validates:
1. Numeric ranges (ratings 0-5, revenue positive, etc.)
2. Placeholder text detection
3. Required field completeness
4. Data consistency checks
5. Source verification

100% PYDANTIC COMPLIANT
============================================================
"""

import re
import logging
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""
    ERROR = "error"      # Data is invalid, must fix
    WARNING = "warning"  # Data is suspicious, review
    INFO = "info"        # Minor issue, informational


class ValidationIssue(BaseModel):
    """
    A single validation issue found in the data.
    
    100% Pydantic with strict validation.
    """
    field: str = Field(..., description="Field path with the issue (e.g., 'competitors[0].rating')")
    message: str = Field(..., description="Human-readable description of the issue")
    severity: ValidationSeverity = Field(..., description="How serious the issue is")
    actual_value: Optional[Any] = Field(default=None, description="The problematic value")
    suggested_fix: Optional[str] = Field(default=None, description="How to fix the issue")
    
    model_config = {"validate_assignment": True}


class ValidationResult(BaseModel):
    """
    Result of a data quality validation.
    
    100% Pydantic with computed properties.
    """
    is_valid: bool = Field(..., description="Whether data passed all critical validations")
    issues: list[ValidationIssue] = Field(default_factory=list, description="List of issues found")
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall quality score 0-1")
    error_count: int = Field(default=0, ge=0, description="Number of ERROR severity issues")
    warning_count: int = Field(default=0, ge=0, description="Number of WARNING severity issues")
    validated_at: str = Field(default="", description="Timestamp of validation")
    
    model_config = {"validate_assignment": True}
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue and update counts."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.error_count += 1
            self.is_valid = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warning_count += 1
        
        # Recalculate quality score
        self._update_quality_score()
    
    def _update_quality_score(self) -> None:
        """Update quality score based on issues."""
        penalty = (self.error_count * 0.2) + (self.warning_count * 0.05)
        self.quality_score = max(0.0, 1.0 - penalty)
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        status = "✅ PASSED" if self.is_valid else "❌ FAILED"
        return (
            f"{status} | Quality: {self.quality_score:.0%} | "
            f"Errors: {self.error_count}, Warnings: {self.warning_count}"
        )


# Placeholder patterns to detect
PLACEHOLDER_PATTERNS = [
    r"\[NEEDS? VERIFICATION\]",
    r"\[PLACEHOLDER\]",
    r"\[TODO\]",
    r"\[TBD\]",
    r"\[UNKNOWN\]",
    r"\[INSERT .+\]",
    r"placeholder",
    r"example\.com",
    r"xxx",
    r"N/A",
]


class DataQualityValidator(BaseModel):
    """
    Validator for MRD data quality.
    
    100% Pydantic with validation methods.
    """
    strict_mode: bool = Field(default=False, description="If True, warnings become errors")
    check_sources: bool = Field(default=True, description="Validate source URLs")
    min_description_length: int = Field(default=20, ge=0, description="Minimum description length")
    
    model_config = {"validate_assignment": True}
    
    def validate_rating(self, value: Any, field_name: str, result: ValidationResult) -> None:
        """Validate a rating is between 0-5."""
        if value is None:
            return  # None is acceptable for optional fields
        
        try:
            rating = float(value)
            if rating < 0 or rating > 5:
                result.add_issue(ValidationIssue(
                    field=field_name,
                    message=f"Rating {rating} is outside valid range 0-5",
                    severity=ValidationSeverity.ERROR,
                    actual_value=value,
                    suggested_fix="Rating should be between 0.0 and 5.0"
                ))
        except (ValueError, TypeError):
            result.add_issue(ValidationIssue(
                field=field_name,
                message=f"Rating is not a valid number: {value}",
                severity=ValidationSeverity.ERROR,
                actual_value=value,
                suggested_fix="Convert to a numeric value"
            ))
    
    def validate_revenue(self, value: Any, field_name: str, result: ValidationResult) -> None:
        """Validate revenue is positive or None."""
        if value is None:
            return
        
        try:
            revenue = float(value)
            if revenue < 0:
                result.add_issue(ValidationIssue(
                    field=field_name,
                    message=f"Revenue {revenue} is negative",
                    severity=ValidationSeverity.WARNING,
                    actual_value=value,
                    suggested_fix="Revenue should be positive (or None if unknown)"
                ))
        except (ValueError, TypeError):
            result.add_issue(ValidationIssue(
                field=field_name,
                message=f"Revenue is not a valid number: {value}",
                severity=ValidationSeverity.ERROR,
                actual_value=value
            ))
    
    def validate_percentage(self, value: Any, field_name: str, result: ValidationResult) -> None:
        """Validate percentage is between -100 and 1000 (reasonable range for growth)."""
        if value is None:
            return
        
        try:
            pct = float(value)
            if pct < -100 or pct > 1000:
                result.add_issue(ValidationIssue(
                    field=field_name,
                    message=f"Percentage {pct}% seems unrealistic",
                    severity=ValidationSeverity.WARNING,
                    actual_value=value,
                    suggested_fix="Verify this percentage is correct"
                ))
        except (ValueError, TypeError):
            pass  # Let other validators handle type issues
    
    def validate_no_placeholders(self, value: Any, field_name: str, result: ValidationResult) -> None:
        """Check for placeholder text in strings."""
        if not isinstance(value, str):
            return
        
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                severity = ValidationSeverity.ERROR if self.strict_mode else ValidationSeverity.WARNING
                result.add_issue(ValidationIssue(
                    field=field_name,
                    message=f"Contains placeholder text matching '{pattern}'",
                    severity=severity,
                    actual_value=value[:100] + "..." if len(value) > 100 else value,
                    suggested_fix="Replace placeholder with actual data"
                ))
                break  # Only report first match per field
    
    def validate_url(self, value: Any, field_name: str, result: ValidationResult) -> None:
        """Validate URL format."""
        if not value or not isinstance(value, str):
            return
        
        # Basic URL validation
        if not value.startswith(("http://", "https://")):
            result.add_issue(ValidationIssue(
                field=field_name,
                message=f"URL should start with http:// or https://",
                severity=ValidationSeverity.WARNING,
                actual_value=value
            ))
        
        # Check for example.com
        if "example.com" in value.lower():
            result.add_issue(ValidationIssue(
                field=field_name,
                message="URL contains example.com (placeholder)",
                severity=ValidationSeverity.ERROR,
                actual_value=value,
                suggested_fix="Use actual URL"
            ))
    
    def validate_min_length(self, value: Any, field_name: str, min_len: int, result: ValidationResult) -> None:
        """Validate string has minimum length."""
        if not isinstance(value, str):
            return
        
        if len(value.strip()) < min_len:
            result.add_issue(ValidationIssue(
                field=field_name,
                message=f"Content too short ({len(value)} chars, minimum {min_len})",
                severity=ValidationSeverity.WARNING,
                actual_value=value[:50] if value else "(empty)"
            ))
    
    def validate_list_not_empty(self, value: Any, field_name: str, result: ValidationResult) -> None:
        """Validate list has at least one item."""
        if value is None:
            return
        
        if isinstance(value, list) and len(value) == 0:
            result.add_issue(ValidationIssue(
                field=field_name,
                message="List is empty, should have at least one item",
                severity=ValidationSeverity.WARNING,
                actual_value=[]
            ))


def validate_mrd_data(mrd_data: dict, strict: bool = False) -> ValidationResult:
    """
    Validate an MRD data dictionary for quality issues.
    
    Args:
        mrd_data: MRD output as dictionary
        strict: If True, warnings become errors
        
    Returns:
        ValidationResult with all issues found
    """
    from datetime import datetime
    
    result = ValidationResult(
        is_valid=True,
        validated_at=datetime.utcnow().isoformat()
    )
    
    validator = DataQualityValidator(strict_mode=strict)
    
    # Validate strategic analysis
    strategic = mrd_data.get("strategic_analysis", {})
    
    validator.validate_min_length(
        strategic.get("executive_summary"), 
        "strategic_analysis.executive_summary",
        100,
        result
    )
    validator.validate_no_placeholders(
        strategic.get("executive_summary"),
        "strategic_analysis.executive_summary",
        result
    )
    
    # Validate market size
    market_size = strategic.get("market_size", {})
    for field in ["tam", "sam", "cagr"]:
        value = market_size.get(field)
        if value is not None:
            validator.validate_revenue(value, f"market_size.{field}", result)
    
    # Validate competitors
    competitors = mrd_data.get("competitors", [])
    for i, comp in enumerate(competitors):
        prefix = f"competitors[{i}]"
        
        # Name and description
        validator.validate_no_placeholders(comp.get("name"), f"{prefix}.name", result)
        validator.validate_no_placeholders(comp.get("description"), f"{prefix}.description", result)
        validator.validate_min_length(comp.get("description"), f"{prefix}.description", 20, result)
        
        # Website
        validator.validate_url(comp.get("website"), f"{prefix}.website", result)
        
        # App metrics
        app_metrics = comp.get("app_metrics", {})
        validator.validate_rating(app_metrics.get("app_store_rating"), f"{prefix}.app_store_rating", result)
        
        # Financials
        financials = comp.get("financials", {})
        validator.validate_revenue(financials.get("revenue_annual"), f"{prefix}.revenue_annual", result)
        validator.validate_percentage(financials.get("revenue_growth_yoy"), f"{prefix}.revenue_growth_yoy", result)
        validator.validate_revenue(financials.get("funding_total"), f"{prefix}.funding_total", result)
        
        # Lists
        validator.validate_list_not_empty(comp.get("key_strengths"), f"{prefix}.key_strengths", result)
        validator.validate_list_not_empty(comp.get("key_weaknesses"), f"{prefix}.key_weaknesses", result)
    
    # Validate SWOT
    swot = mrd_data.get("swot", {})
    for key in ["strengths", "weaknesses", "opportunities", "threats"]:
        validator.validate_list_not_empty(swot.get(key), f"swot.{key}", result)
    
    # Validate feature recommendations
    features = mrd_data.get("feature_recommendations", [])
    for i, feat in enumerate(features):
        prefix = f"feature_recommendations[{i}]"
        validator.validate_no_placeholders(feat.get("name"), f"{prefix}.name", result)
        validator.validate_no_placeholders(feat.get("description"), f"{prefix}.description", result)
        validator.validate_min_length(feat.get("description"), f"{prefix}.description", 20, result)
    
    # Validate regulatory
    regulatory = mrd_data.get("regulatory", {})
    jurisdictions = regulatory.get("jurisdictions", [])
    for i, jur in enumerate(jurisdictions):
        prefix = f"regulatory.jurisdictions[{i}]"
        validator.validate_no_placeholders(jur.get("summary"), f"{prefix}.summary", result)
    
    logger.info(f"Data validation complete: {result.get_summary()}")
    
    return result


def validate_and_clean(mrd_data: dict) -> tuple[dict, ValidationResult]:
    """
    Validate and optionally clean MRD data.
    
    Returns the data with minor fixes applied and validation result.
    """
    # First validate
    result = validate_mrd_data(mrd_data)
    
    # Apply automatic fixes for common issues
    cleaned = mrd_data.copy()
    
    # Remove [NEEDS VERIFICATION] placeholders in numeric fields
    def clean_numeric(value):
        if isinstance(value, str) and "[NEEDS VERIFICATION]" in value:
            return None
        return value
    
    # Clean competitor data
    if "competitors" in cleaned:
        for comp in cleaned["competitors"]:
            if "financials" in comp:
                comp["financials"]["revenue_annual"] = clean_numeric(comp["financials"].get("revenue_annual"))
                comp["financials"]["funding_total"] = clean_numeric(comp["financials"].get("funding_total"))
                comp["financials"]["revenue_growth_yoy"] = clean_numeric(comp["financials"].get("revenue_growth_yoy"))
            if "app_metrics" in comp:
                comp["app_metrics"]["app_store_rating"] = clean_numeric(comp["app_metrics"].get("app_store_rating"))
    
    return cleaned, result
