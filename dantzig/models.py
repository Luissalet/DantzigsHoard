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


class Unavailable(Record):
    start: Nonnegative
    end: Positive

    @model_validator(mode="after")
    def interval(self):
        if self.end <= self.start:
            raise ValueError("El fin del periodo sin disponibilidad debe ser posterior al inicio")
        return self


class Problem(Record):
    name: str = Field(min_length=1)
    unit: str = "minutos"
    resources: list[str] = Field(min_length=1)
    jobs: list[Job] = Field(min_length=1)
    unavailability: dict[str, list[Unavailable]] = Field(default_factory=dict)
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
        if set(self.unavailability) - set(self.resources):
            raise ValueError("Periodo sin disponibilidad para un recurso desconocido")
        for j in self.jobs:
            if set(j.durations) - set(self.resources):
                raise ValueError(f"{j.id}: duración para un recurso desconocido")
            if set(j.after) - set(ids) or j.id in j.after:
                raise ValueError(f"{j.id}: precedencia desconocida o sobre sí mismo")
        pending = {j.id: set(j.after) for j in self.jobs}
        ready = [key for key, parents in pending.items() if not parents]
        reached = set()
        while ready:
            key = ready.pop()
            reached.add(key)
            for child, parents in pending.items():
                if key in parents:
                    parents.remove(key)
                    if not parents:
                        ready.append(child)
        if len(reached) != len(ids):
            raise ValueError("Dependencias cíclicas o bloqueadas por un ciclo: " + ", ".join(sorted(set(ids)-reached)))
        return self


class SolveRequest(Record):
    problem: Problem
    seconds: float = Field(default=10, gt=0, allow_inf_nan=False)


class ExportRequest(Record):
    document: dict | list[dict]
    kind: Literal["problem", "results"] = "problem"
