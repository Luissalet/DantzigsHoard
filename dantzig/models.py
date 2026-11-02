from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Nonnegative = Annotated[int, Field(strict=True, ge=0)]
Positive = Annotated[int, Field(strict=True, gt=0)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Job(Record):
    id: str = Field(min_length=1)
    durations: dict[str, Positive] = Field(min_length=1)
    release: Nonnegative = 0
    due: Nonnegative | None = None
    deadline: Nonnegative | None = None
    weight: Positive = 1
    family: str = ""
    after: list[str] = Field(default_factory=list)


class Problem(Record):
    name: str = Field(min_length=1)
    unit: str = "minutos"
    resources: list[str] = Field(min_length=1)
    jobs: list[Job] = Field(min_length=1)
    family_change: Nonnegative = 0
    horizon: Positive | None = None
    objective: Literal["tardiness_then_makespan", "makespan_then_tardiness"] = "tardiness_then_makespan"

    @model_validator(mode="after")
    def references(self):
        ids = [j.id for j in self.jobs]
        if len(set(ids)) != len(ids) or len(set(self.resources)) != len(self.resources):
            raise ValueError("Los identificadores de trabajos y recursos deben ser únicos")
        if any(not r.strip() for r in self.resources):
            raise ValueError("Cada recurso necesita un nombre")
        for j in self.jobs:
            if set(j.durations) - set(self.resources):
                raise ValueError(f"{j.id}: duración para un recurso desconocido")
            if set(j.after) - set(ids) or j.id in j.after:
                raise ValueError(f"{j.id}: precedencia desconocida o sobre sí mismo")
        return self


class SolveRequest(Record):
    problem: Problem
    seconds: float = Field(default=10, gt=0, allow_inf_nan=False)
