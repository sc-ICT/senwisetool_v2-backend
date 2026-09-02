"""
Schemas Pydantic du moteur Form Builder.
"""

from app.schemas.form_builder.form_definition import (
    FormDefinitionCreate,
    FormDefinitionListResponse,
    FormDefinitionResponse,
    FormDefinitionUpdate,
)
from app.schemas.form_builder.form_question import (
    FormQuestionCreate,
    FormQuestionListResponse,
    FormQuestionResponse,
    FormQuestionUpdate,
)
from app.schemas.form_builder.form_question_config import (
    FormQuestionConfig,
    FormQuestionDisplayConfig,
    FormQuestionValidationConfig,
)
from app.schemas.form_builder.form_question_dependency import (
    FormQuestionDependencyCreate,
    FormQuestionDependencyResponse,
)
from app.schemas.form_builder.form_section import (
    FormSectionCreate,
    FormSectionListResponse,
    FormSectionResponse,
    FormSectionUpdate,
)
from app.schemas.form_builder.question_definition import (
    QuestionCreateRequest,
    QuestionDefinitionCreate,
    QuestionDefinitionDetailResponse,
    QuestionDefinitionListResponse,
    QuestionDefinitionResponse,
    QuestionDefinitionUpdate,
    QuestionDuplicateRequest,
    QuestionVersionListResponse,
)
from app.schemas.form_builder.question_group import (
    QuestionGroupCreate,
    QuestionGroupDetailResponse,
    QuestionGroupListResponse,
    QuestionGroupQuestionResponse,
    QuestionGroupResponse,
    QuestionGroupUpdate,
)
from app.schemas.form_builder.question_version import (
    QuestionOptionCreate,
    QuestionOptionResponse,
    QuestionOptionUpdate,
    QuestionVersionCreate,
    QuestionVersionListResponse,
    QuestionVersionResponse,
    QuestionVersionUpdate,
)

__all__ = [
    "QuestionDefinitionCreate",
    "QuestionDefinitionUpdate",
    "QuestionDefinitionResponse",
    "QuestionDefinitionListResponse",
    "QuestionOptionCreate",
    "QuestionOptionUpdate",
    "QuestionOptionResponse",
    "QuestionVersionCreate",
    "QuestionVersionUpdate",
    "QuestionVersionResponse",
    "QuestionVersionListResponse",
    "QuestionCreateRequest",
    "QuestionDefinitionDetailResponse",
    "QuestionDuplicateRequest",
    "QuestionVersionListResponse",
    "QuestionGroupCreate",
    "QuestionGroupListResponse",
    "QuestionGroupResponse",
    "QuestionGroupUpdate",
    "QuestionGroupDetailResponse",
    "QuestionGroupQuestionResponse",
    "FormDefinitionCreate",
    "FormDefinitionListResponse",
    "FormDefinitionResponse",
    "FormDefinitionUpdate",
    "FormSectionCreate",
    "FormSectionListResponse",
    "FormSectionResponse",
    "FormSectionUpdate",
    "FormQuestionCreate",
    "FormQuestionListResponse",
    "FormQuestionResponse",
    "FormQuestionUpdate",
    "FormQuestionConfig",
    "FormQuestionDisplayConfig",
    "FormQuestionValidationConfig",
    "FormQuestionDependencyCreate",
    "FormQuestionDependencyResponse",
]
