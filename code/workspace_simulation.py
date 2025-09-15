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
    # --- The __init__ method is now simplified ---
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

    # --- NEW METHOD: This makes the class a standard environment ---
    def reset(self):
        """Resets the environment for a new episode."""
        self.jobs_data = self.generate_random_jobs(num_jobs=random.randint(4, 8))
        
        ga = GeneticAlgorithm(self.jobs_data)
        self.schedule = ga.run()

        self.machines = self.create_machines()
        self.jobs = self.create_jobs()
        self.current_jobs = {}
        self.completed_jobs = []
        self.job_queue = [j for j in self.jobs]
        self.timestep = 0
        
        self.random_events = {
            'machine_failure': {'timestep': random.randint(25, 50), 'machine': random.choice([m['machine_id'] for m in self.machine_data['machines']])},
            'temperature_spike': {'timestep': random.randint(20, 40), 'machine': random.choice([m['machine_id'] for m in self.machine_data['machines']])}
        }
        
        return self.get_state()
    
    # --- The step() method now returns 4 values ---
    def step(self, action):
        """Executes one step and returns (next_state, reward, done, info)."""
        self.timestep += 1
        reward = -0.01
        done = False

        if action > 0:
            machine = self.machines[action - 1]
            job_to_assign = None
            if machine.operational and machine.machine_id not in self.current_jobs:
                for job in self.job_queue:
                    if job.machine_requirement[job.current_operation] == machine.machine_id:
                        job_to_assign = job
                        break
            
            if job_to_assign:
                self.current_jobs[machine.machine_id] = job_to_assign
                self.job_queue.remove(job_to_assign)
                reward += 0.1 + (job_to_assign.job_priority / 100.0)
            else:
                reward -= 0.1

        total_power_this_step = 0
        for machine in self.machines:
            if machine.machine_id in self.current_jobs:
                job = self.current_jobs[machine.machine_id]
                op_index = job.current_operation
                job.machine_processing_time[op_index] -= 1
                
                machine_power = machine.power_active_base + job.power_consumption[op_index]
                total_power_this_step += machine_power
                
                machine.process_job(
                    random.uniform(0.5, 1.5) * (machine_power / 10.0),
                    random.uniform(0.2, 1.0) * (machine_power / 10.0)
                )

                if job.machine_processing_time[op_index] <= 0:
                    machine.temperature -= job.threshold_temperature_reduction
                    job.current_operation += 1
                    del self.current_jobs[machine.machine_id]
                    
                    if job.current_operation >= len(job.operations):
                        if random.random() > job.job_failure_rate:
                            self.completed_jobs.append(job)
                            reward += 1.0 + (job.job_priority / 10.0)
                        else:
                            reward -= 0.5
                    else:
                        self.job_queue.append(job)
                        reward += 0.25
            else:
                total_power_this_step += machine.power_idle
                machine.temperature = max(machine.temp_base, machine.temperature - 1.5)
                machine.vibration = max(machine.vib_base, machine.vibration - 0.3)
                if not machine.operational:
                    machine.repair(self.silent_mode)
        
        reward -= total_power_this_step * 0.001
        
        self.handle_random_events()
        for m in self.machines:
            if self.check_sensor_readings(m): reward -= 0.1
        
        if len(self.completed_jobs) == len(self.jobs) or self.timestep >= 500:
            done = True
            if len(self.completed_jobs) == len(self.jobs):
                reward += 5.0

        next_state = self.get_state()
        info = {}
        return next_state, reward, done, info

    def get_legal_actions_mask(self):
        mask = [True] + [False] * len(self.machines)
        for i, machine in enumerate(self.machines):
            if machine.operational and machine.machine_id not in self.current_jobs:
                for job in self.job_queue:
                    if job.machine_requirement[job.current_operation] == machine.machine_id:
                        mask[i + 1] = True
                        break
        return np.array(mask, dtype=bool)

    def get_state(self):
        state = []
        for m in self.machines:
            state.extend([
                1 if m.operational else 0,
                m.temperature / m.temp_threshold,
                m.vibration / m.vib_threshold,
                1 if m.machine_id in self.current_jobs else 0
            ])
        self.job_queue.sort(key=lambda j: j.job_priority, reverse=True)
        for i in range(3):
            if i < len(self.job_queue):
                job = self.job_queue[i]
                op_index = job.current_operation
                state.extend([
                    job.job_priority / 10.0,
                    job.machine_processing_time[op_index] / 30.0,
                    job.power_consumption[op_index] / 20.0
                ])
            else:
                state.extend([0, 0, 0])
        return np.reshape(np.array(state), [1, len(state)])
        
    def generate_random_jobs(self, num_jobs=5):
        jobs_data = {}
        machine_ids = [m['machine_id'] for m in self.machine_data['machines']]
        for i in range(num_jobs):
            job_id = f"rand_job_{i+1}"
            priority = random.choice([1, 1, 1, 5, 5, 8, 10])
            operations = []
            num_ops = random.randint(1, 3)
            for op_num in range(num_ops):
                time = random.randint(10, 30)
                power = random.randint(5, 15)
                op = {"op": op_num + 1, "machine": random.choice(machine_ids), "time": time, "power": power}
                operations.append(op)
            jobs_data[job_id] = {"priority": priority, "operations": operations}
        return jobs_data

    def create_machines(self):
        return [Machine(**config) for config in self.machine_data['machines']]
    
    def create_jobs(self):
        jobs = []
        for job_id, details in self.jobs_data.items():
            jobs.append(Job(job_id=job_id, job_name=job_id, priority=details['priority'], operations=details['operations']))
        return jobs
        
    # ... (The rest of the file: on_connect, get_machine_by_id, etc. remains the same) ...
    def on_connect(self, client, userdata, flags, rc):
        if rc != 0 and not self.silent_mode: print(f"[MQTT] Connection failed with code {rc}.")
    def get_machine_by_id(self, machine_id):
        for machine in self.machines:
            if machine.machine_id == machine_id: return machine
        return None
    def check_sensor_readings(self, machine):
        alerts = []
        if machine.temperature >= machine.temp_threshold: alerts.append({"type": "TEMPERATURE_THRESHOLD_EXCEEDED", "machine_id": machine.machine_id})
        if machine.vibration >= machine.vib_threshold: alerts.append({"type": "VIBRATION_THRESHOLD_EXCEEDED", "machine_id": machine.machine_id})
        if not machine.operational: alerts.append({"type": "MACHINE_FAILURE", "machine_id": machine.machine_id})
        if self.enable_mqtt and not self.silent_mode:
            for alert in alerts: self.send_alert(alert)
        return alerts
    def send_alert(self, alert):
        if not self.enable_mqtt: return
        topic = f"{self.MQTT_ALERT_TOPIC}/{alert['machine_id']}"
        self.mqtt_client.publish(topic, json.dumps(alert))
    def simulate_machine_failure(self, machine_id):
        machine = self.get_machine_by_id(machine_id)
        if machine and machine.operational:
            machine.operational = False
            if not self.silent_mode: print(f"💥 Simulating failure of machine {machine_id}")
    def handle_random_events(self):
        for event_type, event_data in self.random_events.items():
            if self.timestep == event_data['timestep']:
                machine_id = event_data['machine']
                if event_type == 'machine_failure': self.simulate_machine_failure(machine_id)
                elif event_type == 'temperature_spike':
                    machine = self.get_machine_by_id(machine_id)
                    if machine and machine.operational:
                        machine.temperature += random.uniform(10, 20)
                        if not self.silent_mode: print(f"🔥 Temperature spike on machine {machine_id}")
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