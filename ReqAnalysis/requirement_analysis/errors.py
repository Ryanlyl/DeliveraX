from .models import (
    RequirementAnalysisError,
    RequirementAnalysisResult,
    RequirementBoundaryValidation,
)


def failed_result(
    code: str,
    message: str,
    validation: RequirementBoundaryValidation | None = None,
) -> RequirementAnalysisResult:
    return RequirementAnalysisResult(
        spec=None,
        markdown=None,
        status="Failed",
        validation=(
            validation
            if validation
            else RequirementBoundaryValidation(valid=False, errors=[])
        ),
        error=RequirementAnalysisError(code=code, message=message),
        issues=[],
    )
