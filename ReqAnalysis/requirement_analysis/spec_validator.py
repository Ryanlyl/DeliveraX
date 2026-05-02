from pydantic import ValidationError

from .models import RequirementSpec, RequirementValidationError


def validate_requirement_spec_shape(
    spec: object,
) -> tuple[bool, list[RequirementValidationError], RequirementSpec | None]:
    try:
        parsed = RequirementSpec.model_validate(spec)
    except ValidationError as err:
        validation_errors: list[RequirementValidationError] = []
        for item in err.errors():
            location = (
                ".".join(str(part) for part in item.get("loc", []))
                or "RequirementSpec"
            )
            validation_errors.append(
                RequirementValidationError(
                    category="schema",
                    keyword=location,
                    message=f"LLM 返回内容缺少必要字段或字段类型错误：{location}",
                )
            )
        return False, validation_errors, None

    errors: list[RequirementValidationError] = []
    if len(parsed.goals.inScope) == 0:
        errors.append(
            RequirementValidationError(
                category="schema",
                keyword="goals.inScope",
                message="LLM 返回内容缺少必要字段：goals.inScope",
            )
        )
    if len(parsed.acceptanceCriteria.checklist) == 0:
        errors.append(
            RequirementValidationError(
                category="schema",
                keyword="acceptanceCriteria.checklist",
                message="LLM 返回内容缺少必要字段：acceptanceCriteria.checklist",
            )
        )

    return len(errors) == 0, errors, parsed
