import time
import random
import json
import numpy as np

try:
    import paho.mqtt.client as mqtt
    PAHO_MQTT_AVAILABLE = True
except ImportError:
    PAHO_MQTT_AVAILABLE = False

from .machines import Machine
from .job import Job
from CI_Model.genetic_algorithm import GeneticAlgorithm


class WorkspaceSimulation:
    def __init__(self, jobs_data, machine_data, agent, silent_mode=False, enable_mqtt=False):
        self.agent = agent
        self.base_jobs_data = jobs_data
        self.machine_data = machine_data
        self.silent_mode = silent_mode
        self.enable_mqtt = enable_mqtt and PAHO_MQTT_AVAILABLE

        if self.enable_mqtt:
            self.MQTT_BROKER_ADDRESS = "localhost"
            self.MQTT_PORT = 1883
            self.MQTT_KEEPALIVE = 60
            self.MQTT_TOPIC_PREFIX = "shopfloor/machine"
            self.MQTT_ALERT_TOPIC = "shopfloor/alerts"

            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.connect(self.MQTT_BROKER_ADDRESS, self.MQTT_PORT, self.MQTT_KEEPALIVE)
            self.mqtt_client.loop_start()

    # ----------------- RESET -----------------
    def reset(self):
        """Resets environment for a new episode"""
        self.jobs_data = self.base_jobs_data  # use predefined jobs for training/eval
        ga = GeneticAlgorithm(self.jobs_data)
        self.schedule = ga.run()

        self.machines = self.create_machines()
        self.jobs = self.create_jobs()
        self.current_jobs = {}
        self.completed_jobs = []
        self.job_queue = [j for j in self.jobs]
        self.timestep = 0

        return self.get_state()

    # ----------------- STEP -----------------
    def step(self, action):
        """Executes one step and returns (next_state, reward, done, info)."""
        self.timestep += 1
        reward = -0.01  # small penalty per timestep (encourage faster completion)
        done = False

        reassigned = False  # ✅ track if this step was a reassignment

        # ---------------- ACTION HANDLING ----------------
        if action > 0:  # assign job to machine
            machine = self.machines[action - 1]
            job_to_assign = None

            if machine.operational and machine.machine_id not in self.current_jobs:
                # normal case: assign if machine matches job requirement
                for job in self.job_queue:
                    required_machine = job.machine_requirement[job.current_operation]

                    if required_machine == machine.machine_id:
                        # exact required machine
                        job_to_assign = job
                        break

                    else:
                        # ✅ Backup reassignment case
                        required_class = required_machine.split("_")[0]
                        candidate_class = machine.machine_id.split("_")[0]
                        req_machine_obj = self.get_machine_by_id(required_machine)

                        if not req_machine_obj.operational and required_class == candidate_class:
                            # find best backup among all machines of same class
                            backup_candidates = [
                                m for m in self.machines
                                if m.class_name == required_class and m.operational and m.machine_id not in self.current_jobs
                            ]

                            if backup_candidates:
                                # score backups
                                scored_backups = []
                                for backup in backup_candidates:
                                    est_time = job.machine_processing_time[job.current_operation]
                                    idle_bonus = 1.0 if backup.machine_id not in self.current_jobs else 0.0
                                    power_cost = backup.power_active_base + job.power_consumption[job.current_operation]
                                    efficiency_score = (1.0 / (est_time + 1)) + idle_bonus - (0.001 * power_cost)
                                    scored_backups.append((efficiency_score, backup))

                                # pick best backup
                                best_score, best_backup = max(scored_backups, key=lambda x: x[0])
                                if best_backup.machine_id == machine.machine_id:
                                    job_to_assign = job
                                    reassigned = True
                                    reward += 2.0 + 5.0 * best_score  # reward scaled by efficiency
                                    if not self.silent_mode:
                                        print(f"[t={self.timestep}] 🔄 REASSIGNED {job.job_id} → {machine.machine_id} "
                                            f"(eff_score={best_score:.2f})")
                                    break

            if job_to_assign:
                self.current_jobs[machine.machine_id] = job_to_assign
                self.job_queue.remove(job_to_assign)
                reward += 0.5 + (job_to_assign.job_priority / 10.0)

                if not self.silent_mode and not reassigned:
                    print(f"[t={self.timestep}] 🎯 Assigned {job_to_assign.job_id} → {machine.machine_id} "
                        f"(op {job_to_assign.current_operation+1}/{len(job_to_assign.operations)})")
            else:
                reward -= 1.0
                if not self.silent_mode:
                    print(f"[t={self.timestep}] ⚠️ Invalid assignment attempt on {machine.machine_id}")

        else:  # WAIT action
            stuck_jobs = 0
            for job in self.job_queue:
                req_machine = self.get_machine_by_id(job.machine_requirement[job.current_operation])
                if not req_machine.operational:
                    req_class = req_machine.machine_id.split("_")[0]
                    backups = [m for m in self.machines if m.class_name == req_class and m.operational]
                    if len(backups) == 0:
                        stuck_jobs += 1

            if stuck_jobs > 0:
                reward += 0.1
                if not self.silent_mode:
                    print(f"[t={self.timestep}] ⏸️ Agent waited (correct: stuck jobs exist)")
            else:
                reward -= 0.1
                if not self.silent_mode:
                    print(f"[t={self.timestep}] ⏸️ Agent waited (wasteful)")

        # ---------------- MACHINE PROCESSING ----------------
        total_power_this_step = 0
        for machine in self.machines:
            # ✅ NEW: if machine failed mid-job → eject job immediately
            if not machine.operational and machine.machine_id in self.current_jobs:
                failed_job = self.current_jobs[machine.machine_id]
                del self.current_jobs[machine.machine_id]
                self.job_queue.append(failed_job)
                reward -= 0.5
                if not self.silent_mode:
                    print(f"[t={self.timestep}] ❌ Machine {machine.machine_id} failed → Job {failed_job.job_id} returned to queue")
                continue  # skip further processing this step

            if machine.machine_id in self.current_jobs:
                job = self.current_jobs[machine.machine_id]
                op_index = job.current_operation
                job.machine_processing_time[op_index] -= 1

                machine_power = machine.power_active_base + job.power_consumption[op_index]
                total_power_this_step += machine_power

                machine.process_job(
                    random.uniform(0.5, 1.5) * (machine_power / 10.0),
                    random.uniform(0.2, 1.0) * (machine_power / 10.0),
                )

                if job.machine_processing_time[op_index] <= 0:
                    machine.temperature -= job.threshold_temperature_reduction
                    job.current_operation += 1
                    del self.current_jobs[machine.machine_id]

                    if job.current_operation >= len(job.operations):
                        if random.random() > job.job_failure_rate:
                            self.completed_jobs.append(job)
                            reward += 2.0 + (job.job_priority / 5.0)
                            if not self.silent_mode:
                                print(f"[t={self.timestep}] ✅ Job {job.job_id} COMPLETED")
                        else:
                            reward -= 1.0
                            if not self.silent_mode:
                                print(f"[t={self.timestep}] ❌ Job {job.job_id} FAILED")
                    else:
                        self.job_queue.append(job)
                        reward += 0.25
                        if not self.silent_mode:
                            print(f"[t={self.timestep}] 🔄 Job {job.job_id} returned to queue (next op {job.current_operation+1})")
            else:
                total_power_this_step += machine.power_idle
                machine.temperature = max(machine.temp_base, machine.temperature - 1.5)
                machine.vibration = max(machine.vib_base, machine.vibration - 0.3)
                if not machine.operational:
                    machine.repair(self.silent_mode)
                    if machine.operational and not self.silent_mode:
                        print(f"[t={self.timestep}] 🔧 Machine {machine.machine_id} repaired and operational again")

        reward -= total_power_this_step * 0.001

        # ---------------- TERMINATION ----------------
        if len(self.completed_jobs) == len(self.jobs) or self.timestep >= 500:
            done = True
            if len(self.completed_jobs) == len(self.jobs):
                reward += 10.0
                if not self.silent_mode:
                    print(f"[t={self.timestep}] 🎉 All jobs completed!")

        next_state = self.get_state()
        info = {}
        return next_state, reward, done, info






    # ----------------- ACTION MASK -----------------
    def get_legal_actions_mask(self):
        mask = [True] + [False] * len(self.machines)  # action 0 = wait
        for i, machine in enumerate(self.machines):
            if machine.operational and machine.machine_id not in self.current_jobs:
                for job in self.job_queue:
                    if job.machine_requirement[job.current_operation] == machine.machine_id:
                        mask[i + 1] = True
                        break
        return np.array(mask, dtype=bool)

    # ----------------- STATE -----------------
    def get_state(self):
        state = []
        for m in self.machines:
            state.extend([
                1 if m.operational else 0,
                m.temperature / m.temp_threshold,
                m.vibration / m.vib_threshold,
                1 if m.machine_id in self.current_jobs else 0,
            ])
        self.job_queue.sort(key=lambda j: j.job_priority, reverse=True)
        for i in range(3):
            if i < len(self.job_queue):
                job = self.job_queue[i]
                op_index = job.current_operation
                state.extend([
                    job.job_priority / 10.0,
                    job.machine_processing_time[op_index] / 30.0,
                    job.power_consumption[op_index] / 20.0,
                ])
            else:
                state.extend([0, 0, 0])
        return np.reshape(np.array(state), [1, len(state)])

    # ----------------- HELPERS -----------------
    def create_machines(self):
        return [Machine(**config) for config in self.machine_data["machines"]]

    def create_jobs(self):
        jobs = []
        for job_id, details in self.jobs_data.items():
            jobs.append(
                Job(
                    job_id=job_id,
                    job_name=job_id,
                    priority=details["priority"],
                    operations=details["operations"],
                )
            )
        return jobs

    def on_connect(self, client, userdata, flags, rc):
        if rc != 0 and not self.silent_mode:
            print(f"[MQTT] Connection failed with code {rc}.")

    def get_machine_by_id(self, machine_id):
        for machine in self.machines:
            if machine.machine_id == machine_id:
                return machine
        return None

    def check_sensor_readings(self, machine):
        alerts = []
        if machine.temperature >= machine.temp_threshold:
            alerts.append({"type": "TEMPERATURE_THRESHOLD_EXCEEDED", "machine_id": machine.machine_id})
        if machine.vibration >= machine.vib_threshold:
            alerts.append({"type": "VIBRATION_THRESHOLD_EXCEEDED", "machine_id": machine.machine_id})
        if not machine.operational:
            alerts.append({"type": "MACHINE_FAILURE", "machine_id": machine.machine_id})
        if self.enable_mqtt and not self.silent_mode:
            for alert in alerts:
                self.send_alert(alert)
        return alerts

    def send_alert(self, alert):
        if not self.enable_mqtt:
            return
        topic = f"{self.MQTT_ALERT_TOPIC}/{alert['machine_id']}"
        self.mqtt_client.publish(topic, json.dumps(alert))

    def simulate_machine_failure(self, machine_id):
        """Controlled breakdown trigger (used during evaluation)"""
        machine = self.get_machine_by_id(machine_id)
        if machine and machine.operational:
            machine.operational = False
            if not self.silent_mode:
                print(f"💥 Simulating failure of machine {machine_id}")

    def cleanup(self):
        if self.enable_mqtt:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        if not self.silent_mode:
            print("[MQTT] Disconnected gracefully.")
            print(f"\n📊 SIMULATION SUMMARY:")
            print(f"   Total timesteps: {self.timestep}")
            print(f"   Jobs completed: {len(self.completed_jobs)}/{len(self.jobs)}")
            print(f"\n🔧 MACHINE STATUS:")
            for machine in self.machines:
                status = "Operational" if machine.operational else "Failed"
                print(f"   {machine.machine_id}: {status} (Temp: {machine.temperature:.1f}°C, Vib: {machine.vibration:.1f})")
