import itertools
import random
from dataclasses import dataclass, field
from typing import List, Tuple

_job_id_counter = itertools.count(1)

INTENSITIES = {
    "light":    {"temp_inc": 3.0, "vib_inc": 0.8},
    "moderate": {"temp_inc": 4.5, "vib_inc": 1.2},
    "heavy":    {"temp_inc": 5.5, "vib_inc": 1.5},
    "stress":   {"temp_inc": 6.0, "vib_inc": 2.0},
}

ROUTE_PATTERNS = [
    ["A", "B"],
    ["A", "B", "C"],
    ["C", "A"],
    ["B", "D"],
    ["A", "C"],
    ["B", "C"],
    ["A", "A", "B"],
]

DURATION_TOTAL_RANGE = (8, 18)
REDUCTION_RANGE = (0.2, 0.6)  # reduction percentage range


@dataclass
class Job:
    job_id: str
    intensity: str
    temp_inc: float
    vib_inc: float
    reduction: float = 0.0  # safe default for old calls

    steps: List[Tuple[str, int]] = field(default_factory=list)
    current_step: int = 0

    @property
    def done(self) -> bool:
        return self.current_step >= len(self.steps)

    @property
    def required_class(self) -> str:
        if self.done:
            return ""
        return self.steps[self.current_step][0]

    @property
    def remaining_ticks_on_step(self) -> int:
        if self.done:
            return 0
        return self.steps[self.current_step][1]

    def work_one_tick(self) -> None:
        if self.done:
            return
        cls_name, rem = self.steps[self.current_step]
        rem -= 1
        self.steps[self.current_step] = (cls_name, rem)
        if rem <= 0:
            self.current_step += 1

    def put_back_unfinished_step_front(self) -> None:
        return

    @classmethod
    def make_random(cls) -> "Job":
        jid = f"JOB_{next(_job_id_counter)}"
        intensity = random.choice(list(INTENSITIES.keys()))
        inc = INTENSITIES[intensity]

        pattern = random.choice(ROUTE_PATTERNS)
        total = random.randint(*DURATION_TOTAL_RANGE)

        base = [2] * len(pattern)
        remaining = max(0, total - sum(base))
        for _ in range(remaining):
            base[random.randrange(len(base))] += 1

        steps = [(cls_name, dur) for cls_name, dur in zip(pattern, base)]

        reduction_factor = random.uniform(*REDUCTION_RANGE)

        return cls(
            job_id=jid,
            intensity=intensity,
            temp_inc=inc["temp_inc"],
            vib_inc=inc["vib_inc"],
            steps=steps,
            reduction=reduction_factor,
        )

    @classmethod
    def make(cls, intensity: str) -> "Job":
        jid = f"JOB_{next(_job_id_counter)}"
        inc = INTENSITIES[intensity]
        pattern = random.choice(ROUTE_PATTERNS)
        total = random.randint(*DURATION_TOTAL_RANGE)
        base = [2] * len(pattern)
        remaining = max(0, total - sum(base))
        for _ in range(remaining):
            base[random.randrange(len(base))] += 1
        steps = [(cls_name, dur) for cls_name, dur in zip(pattern, base)]
        reduction_factor = random.uniform(*REDUCTION_RANGE)
        return cls(
            job_id=jid,
            intensity=intensity,
            temp_inc=inc["temp_inc"],
            vib_inc=inc["vib_inc"],
            steps=steps,
            reduction=reduction_factor,
        )
