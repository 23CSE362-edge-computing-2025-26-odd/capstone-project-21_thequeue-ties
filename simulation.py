# simulation.py
import time
import random
import json
from collections import deque
from typing import List
import paho.mqtt.client as mqtt

from machines import Machine
from jobs import Job, INTENSITIES

TOPIC_JOB_STATUS   = "job/status"
TOPIC_JOBSHOP      = "jobshop/status"

class WorkspaceSimulation:
    def __init__(self,
                 broker="localhost",
                 port=1883,
                 keepalive=60,
                 tick_seconds=1.0):
        # MQTT
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.connect(broker, port, keepalive)
        self.client.loop_start()

        # Time
        self.t = 0
        self.tick_seconds = tick_seconds

        # Machines (adjust freely)
        self.machines: List[Machine] = [
            Machine("A", "A_1", temp_base=40, temp_threshold=85, vib_base=2.0, vib_threshold=8.0,  repair_time=3),
            Machine("A", "A_2", temp_base=41, temp_threshold=86, vib_base=2.2, vib_threshold=8.5,  repair_time=3),
            Machine("B", "B_1", temp_base=50, temp_threshold=90, vib_base=4.0, vib_threshold=12.0, repair_time=5),
            Machine("C", "C_1", temp_base=30, temp_threshold=80, vib_base=3.0, vib_threshold=10.0, repair_time=4),
        ]

        # Jobs queue (FIFO). In real flow you’ll build these from your job classes.
        self.jobs = deque()
        self._seed_jobs(14)  # create some jobs to run

    def _on_connect(self, client, userdata, flags, rc):
        print("[MQTT] Connected" if rc == 0 else f"[MQTT] Failed rc={rc}")

    def _seed_jobs(self, n: int):
        intensities = list(INTENSITIES.keys())
        for _ in range(n):
            self.jobs.append(Job.make(random.choice(intensities)))

    def _publish_jobshop_event(self, event_type: str, payload: dict):
        msg = {"type": event_type, **payload}
        self.client.publish(TOPIC_JOBSHOP, json.dumps(msg))

    def _publish_job_status(self, machine: Machine):
        self.client.publish(TOPIC_JOB_STATUS, machine.status_json(self.t))

    def _assign_jobs(self):
        # Dumb FIFO scheduling: give the next job to the first idle machine
        for m in self.machines:
            if not self.jobs:
                return
            if m.idle:
                job = self.jobs.popleft()
                m.assign(job)
                self._publish_jobshop_event("STARTED", {
                    "timestamp": self.t,
                    "job_id": job.job_id,
                    "intensity": job.intensity,
                    "machine_id": m.machine_id
                })

    def tick(self):
        self.t += 1
        # Assign
        self._assign_jobs()

        # Step all machines, publish live job/status each tick
        for m in self.machines:
            event, data = m.step()
            self._publish_job_status(m)

            if event == "FAILED":
                self._publish_jobshop_event("FAILED", {
                    "timestamp": self.t,
                    "machine_id": m.machine_id,
                    "reason": "threshold_exceeded",
                    "temperature": round(m.temperature, 2),
                    "vibration": round(m.vibration, 2),
                    "temp_threshold": m.temp_threshold,
                    "vib_threshold": m.vib_threshold,
                })

            elif event == "COMPLETED":
                finished_job: Job = data
                self._publish_jobshop_event("COMPLETED", {
                    "timestamp": self.t,
                    "job_id": finished_job.job_id,
                    "machine_id": m.machine_id
                })

    def run(self, max_ticks=60):
        try:
            for _ in range(max_ticks):
                self.tick()
                time.sleep(self.tick_seconds)
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print("[MQTT] Disconnected")
