# machines.py
import json
import random
from dataclasses import dataclass, field
from typing import Optional
from jobs import Job

@dataclass
class Machine:
    """
    Digital Twin Enabled Machine Class for Flexible Job Shop Simulation.
    """
    class_name: str
    machine_id: str
    temp_base: float
    temp_threshold: float
    vib_base: float
    vib_threshold: float
    repair_time: int

    temperature: float = field(init=False)
    vibration: float = field(init=False)
    busy_with: Optional[Job] = field(default=None, init=False)
    repairing_left: int = field(default=0, init=False)

    def __post_init__(self):
        self.temperature = self.temp_base
        self.vibration = self.vib_base

    @property
    def operational(self) -> bool:
        return self.repairing_left == 0

    @property
    def idle(self) -> bool:
        return self.operational and self.busy_with is None

    def assign(self, job: Job) -> bool:
        if not self.idle:
            return False
        self.busy_with = job
        return True

    def _cooldown(self):
        # natural drift back toward base when idle
        self.temperature = max(self.temp_base, self.temperature - 1.2)
        self.vibration  = max(self.vib_base,  self.vibration  - 0.25)

    def _maybe_spike(self):
        # Small chance to generate a spike *just above* threshold to cause a failure
        if random.random() < 0.07:  # 7% tick chance for temp
            self.temperature += random.uniform(2.0, 6.0)
        if random.random() < 0.05:  # 5% tick chance for vib
            self.vibration  += random.uniform(0.8, 2.0)

    def step(self):
        """
        One simulation tick.
        - If repairing: count down.
        - If running a job: update temp/vib with noise, maybe spike; decrement job steps.
        - If idle: cooldown slightly.
        Returns a tuple: (event, payload or None)
          event in {None, "FAILED", "COMPLETED"} for machine-level job result.
        """
        # Under repair
        if self.repairing_left > 0:
            self.repairing_left -= 1
            if self.repairing_left == 0:
                # Machine recovered
                self.temperature = self.temp_base
                self.vibration = self.vib_base
            return None, None

        # Running a job
        if self.busy_with:
            j = self.busy_with
            # Add job influence + small noise
            self.temperature += j.temp_inc + random.uniform(-1.0, 1.4)
            self.vibration  += j.vib_inc  + random.uniform(-0.4, 0.6)

            # occasional spike to trigger failure path
            self._maybe_spike()

            # Threshold check
            if self.temperature >= self.temp_threshold or self.vibration >= self.vib_threshold:
                # fail job
                self.busy_with = None
                self.repairing_left = self.repair_time
                return "FAILED", None

            # progress job
            j.remaining_steps -= 1
            if j.remaining_steps <= 0:
                finished = j
                self.busy_with = None
                return "COMPLETED", finished

            return None, None

        # Idle → cooldown
        self._cooldown()
        return None, None

    def status_json(self, timestamp: int) -> str:
        """
        Build a JSON payload for MQTT. `current_job` is never null:
        - "REPAIR" if under repair
        - job_id if running
        - "IDLE" if operational but not running
        """
        if self.repairing_left > 0:
            status = f"Repairing ({self.repair_time - self.repairing_left}/{self.repair_time})"
            current_job = "REPAIR"
        elif self.busy_with:
            status = "Operational"
            current_job = self.busy_with.job_id
        else:
            status = "Operational"
            current_job = "IDLE"

        doc = {
            "timestamp": timestamp,
            "machine_id": self.machine_id,
            "class_name": self.class_name,
            "temperature": round(self.temperature, 2),
            "vibration": round(self.vibration, 2),
            "status": status,
            "current_job": current_job,  # never null now
            "temp_threshold": self.temp_threshold,
            "vib_threshold": self.vib_threshold,
        }
        return json.dumps(doc)
