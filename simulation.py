# simulation.py
import time
import random
import json
from collections import deque, defaultdict
from typing import List, Dict
import paho.mqtt.client as mqtt

from machines import Machine
from jobs import Job

TOPIC_JOB_STATUS = "job/status"
TOPIC_JOBSHOP    = "jobshop/status"

class WorkspaceSimulation:
    """
    Multi-step job shop with class-based routing and failure-aware rescheduling.
    - 8 machines total: A_1, A_2, A_3, B_1, B_2, C_1, C_2, D_1
    - Per-class FIFO queues
    - On failure: job returns to same-class queue with remaining ticks
    """

    def __init__(self,
                 broker="localhost",
                 port=1883,
                 keepalive=60,
                 tick_seconds=1.0,
                 seed_jobs=20):
        # MQTT
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.connect(broker, port, keepalive)
        self.client.loop_start()

        # Time
        self.t = 0
        self.tick_seconds = tick_seconds

        # 8 Machines
        self.machines: List[Machine] = [
            Machine("A", "A_1", temp_base=40, temp_threshold=85, vib_base=2.0, vib_threshold=8.0,  repair_time=3),
            Machine("A", "A_2", temp_base=41, temp_threshold=86, vib_base=2.2, vib_threshold=8.5,  repair_time=3),
            Machine("A", "A_3", temp_base=42, temp_threshold=87, vib_base=2.1, vib_threshold=8.5,  repair_time=3),
            Machine("B", "B_1", temp_base=50, temp_threshold=90, vib_base=4.0, vib_threshold=12.0, repair_time=5),
            Machine("B", "B_2", temp_base=49, temp_threshold=90, vib_base=3.8, vib_threshold=12.0, repair_time=5),
            Machine("C", "C_1", temp_base=30, temp_threshold=80, vib_base=3.0, vib_threshold=10.0, repair_time=4),
            Machine("C", "C_2", temp_base=31, temp_threshold=81, vib_base=3.2, vib_threshold=10.0, repair_time=4),
            Machine("D", "D_1", temp_base=35, temp_threshold=95, vib_base=1.5, vib_threshold=14.0, repair_time=6),
        ]

        # Per-class queues (FIFO) for current-step jobs
        self.class_queues: Dict[str, deque] = defaultdict(deque)

        # Seed jobs
        for _ in range(seed_jobs):
            self.enqueue_new_job()

    # --- MQTT helpers ---
    def _on_connect(self, client, userdata, flags, rc):
        print("[MQTT] Connected" if rc == 0 else f"[MQTT] Failed rc={rc}")

    def _publish_jobshop_event(self, event_type: str, payload: dict):
        msg = {"type": event_type, **payload}
        self.client.publish(TOPIC_JOBSHOP, json.dumps(msg))

    def _publish_job_status(self, machine: Machine):
        self.client.publish(TOPIC_JOB_STATUS, machine.status_json(self.t))

    # --- Job flow helpers ---
    def enqueue_new_job(self):
        job = Job.make_random()
        self.class_queues[job.required_class].append(job)

    def _enqueue_current_step_front(self, job: Job):
        """Requeue job at FRONT of current class queue (on failure)."""
        self.class_queues[job.required_class].appendleft(job)

    def _enqueue_next_step(self, job: Job):
        """After finishing a step, move job to the BACK of the next class queue."""
        if not job.done:
            self.class_queues[job.required_class].append(job)

    # --- Scheduling ---
    def _assign_jobs(self):
        """Greedy per-tick: each idle machine pulls from its class queue (FIFO)."""
        for m in self.machines:
            if m.idle and self.class_queues[m.class_name]:
                job = self.class_queues[m.class_name].popleft()
                if m.assign(job):
                    self._publish_jobshop_event("STARTED", {
                        "timestamp": self.t,
                        "job_id": job.job_id,
                        "machine_id": m.machine_id,
                        "required_class": m.class_name,
                        "step_remaining": job.remaining_ticks_on_step,
                    })
                else:
                    # shouldn't happen because class must match; push back front
                    self.class_queues[m.class_name].appendleft(job)

    # --- Per tick ---
    def tick(self):
        self.t += 1
        self._assign_jobs()

        for m in self.machines:
            event, data = m.step()
            self._publish_job_status(m)

            if event == "FAILED":
                j = data  # job returned by Machine.step()
                if j is not None:
                    # Put failed job to FRONT of its current required-class queue
                    self._enqueue_current_step_front(j)

                    self._publish_jobshop_event("FAILED", {
                        "timestamp": self.t,
                        "machine_id": m.machine_id,
                        "class": m.class_name,
                        "job_id": j.job_id,  # now logged
                        "reason": "threshold_exceeded",
                        "temperature": round(m.temperature, 2),
                        "vibration": round(m.vibration, 2),
                        "temp_threshold": m.temp_threshold,
                        "vib_threshold": m.vib_threshold,
                    })
                else:
                    # Fallback (shouldn't happen with fixed Machine.step)
                    self._publish_jobshop_event("FAILED", {
                        "timestamp": self.t,
                        "machine_id": m.machine_id,
                        "class": m.class_name,
                        "reason": "threshold_exceeded",
                        "temperature": round(m.temperature, 2),
                        "vibration": round(m.vibration, 2),
                        "temp_threshold": m.temp_threshold,
                        "vib_threshold": m.vib_threshold,
                    })

            elif event == "STEP_DONE":
                j: Job = data
                self._publish_jobshop_event("STEP_DONE", {
                    "timestamp": self.t,
                    "job_id": j.job_id,
                    "next_required_class": ("" if j.done else j.required_class),
                })
                if not j.done:
                    self._enqueue_next_step(j)

            elif event == "COMPLETED":
                j: Job = data
                self._publish_jobshop_event("COMPLETED", {
                    "timestamp": self.t,
                    "job_id": j.job_id,
                    "machine_id": m.machine_id
                })
                # keep system busy (optional)
                if random.random() < 0.0000000000000001:
                    self.enqueue_new_job()

    def run(self, max_ticks=120):
        try:
            for _ in range(max_ticks):
                self.tick()
                time.sleep(self.tick_seconds)
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print("[MQTT] Disconnected")
