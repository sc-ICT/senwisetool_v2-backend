from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RepeatCountSource(BaseModel):
    source_type: Literal["QUESTION"]

    question_id: int = Field(
        gt=0,
    )


class SectionRepeatConfig(BaseModel):
    enabled: bool = False

    mode: Literal["COUNT"] = "COUNT"

    count_source: RepeatCountSource | None = None

    minimum: int = Field(
        default=0,
        ge=0,
    )

    maximum: int | None = Field(
        default=None,
        ge=0,
    )

    @model_validator(mode="after")
    def validate_repeat_config(self):
        if self.enabled and self.count_source is None:
            raise ValueError(
                "Une section répétable doit définir " "une source pour le nombre de répétitions."
            )

        if self.maximum is not None and self.maximum < self.minimum:
            raise ValueError("maximum doit être supérieur ou égal à minimum.")

        return self
