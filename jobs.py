# jobs.py
import itertools
from dataclasses import dataclass

_job_id_counter = itertools.count(1)

# Simple catalog of job “intensities”
INTENSITIES = {
    "light":    {"temp_inc": 3.0, "vib_inc": 0.8, "duration": 4},
    "moderate": {"temp_inc": 4.5, "vib_inc": 1.2, "duration": 5},
    "heavy":    {"temp_inc": 6.5, "vib_inc": 1.8, "duration": 6},
    "stress":   {"temp_inc": 8.0, "vib_inc": 2.4, "duration": 7},
}

@dataclass
class Job:
    job_id: str
    intensity: str
    remaining_steps: int
    temp_inc: float
    vib_inc: float

    @classmethod
    def make(cls, intensity: str) -> "Job":
        conf = INTENSITIES[intensity]
        jid = f"JOB_{next(_job_id_counter)}"
        return cls(
            job_id=jid,
            intensity=intensity,
            remaining_steps=conf["duration"],
            temp_inc=conf["temp_inc"],
            vib_inc=conf["vib_inc"],
        )
