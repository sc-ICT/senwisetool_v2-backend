"""
Schemas Pydantic du moteur Form Builder.
"""

from app.schemas.form_builder.project_definition import (
    ProjectDefinitionCreate,
    ProjectDefinitionListResponse,
    ProjectDefinitionResponse,
    ProjectDefinitionUpdate,
)
from app.schemas.form_builder.project_question import (
    ProjectQuestionCreate,
    ProjectQuestionListResponse,
    ProjectQuestionResponse,
    ProjectQuestionUpdate,
)
from app.schemas.form_builder.project_question_config import (
    ProjectQuestionConfig,
    ProjectQuestionDisplayConfig,
    ProjectQuestionValidationConfig,
)
from app.schemas.form_builder.project_question_dependency import (
    ProjectQuestionDependencyCreate,
    ProjectQuestionDependencyResponse,
)
from app.schemas.form_builder.project_section import (
    ProjectSectionCreate,
    ProjectSectionListResponse,
    ProjectSectionResponse,
    ProjectSectionUpdate,
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
    "ProjectDefinitionCreate",
    "ProjectDefinitionListResponse",
    "ProjectDefinitionResponse",
    "ProjectDefinitionUpdate",
    "ProjectSectionCreate",
    "ProjectSectionListResponse",
    "ProjectSectionResponse",
    "ProjectSectionUpdate",
    "ProjectQuestionCreate",
    "ProjectQuestionListResponse",
    "ProjectQuestionResponse",
    "ProjectQuestionUpdate",
    "ProjectQuestionConfig",
    "ProjectQuestionDisplayConfig",
    "ProjectQuestionValidationConfig",
    "ProjectQuestionDependencyCreate",
    "ProjectQuestionDependencyResponse",
]
