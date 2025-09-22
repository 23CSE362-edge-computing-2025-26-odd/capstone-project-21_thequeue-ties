import time
import random
import json
import paho.mqtt.client as mqtt
from machines import Machine
from job import Job
from fuzzy_predictor import create_failure_predictor

class WorkspaceSimulation:
    def __init__(self, fuzzy_params, run_headless=False):
        self.fuzzy_params = fuzzy_params
        self.run_headless = run_headless

        if not self.run_headless:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            self.MQTT_BROKER_ADDRESS = "localhost"
            self.MQTT_PORT = 1883
            self.MQTT_KEEPALIVE = 60
            self.MQTT_ALERT_TOPIC = "shopfloor/alerts"
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.connect(self.MQTT_BROKER_ADDRESS, self.MQTT_PORT, self.MQTT_KEEPALIVE)
            self.mqtt_client.loop_start()

        self.machines = self.create_machines()
        try:
            self.failure_predictors = {m.machine_id: create_failure_predictor(self.fuzzy_params) for m in self.machines}
        except (AssertionError, ValueError):
            self.failure_predictors = None
        self.alert_sent = {m.machine_id: False for m in self.machines}
        self.timestep = 0
        self.fitness_score = 0

    def reset(self):
        """Resets the simulation state for a new validation run."""
        self.machines = self.create_machines()
        self.alert_sent = {m.machine_id: False for m in self.machines}
        self.timestep = 0
        self.fitness_score = 0

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0 and not self.run_headless:
            print("[MQTT] Connected successfully to broker.")

    def create_machines(self):
        """
        FIX: Added the missing 'power_idle' and 'power_active' parameters
        to match the updated Machine class constructor.
        """
        machine_configs = [
            {
                "class_name": "A", "machine_id": "A_1", "temp_base": 40, "temp_threshold": 120,
                "vib_base": 2, "vib_threshold": 18, "repair_time": 3,
                "power_idle": 0.5, "power_active": 3.5  # Added missing values
            },
            {
                "class_name": "A", "machine_id": "A_2", "temp_base": 42, "temp_threshold": 125,
                "vib_base": 2.5, "vib_threshold": 19, "repair_time": 3,
                "power_idle": 0.6, "power_active": 4.0  # Added missing values
            },
            {
                "class_name": "B", "machine_id": "B_1", "temp_base": 50, "temp_threshold": 130,
                "vib_base": 4, "vib_threshold": 20, "repair_time": 5,
                "power_idle": 1.0, "power_active": 7.5  # Added missing values
            }
        ]
        return [Machine(**config) for config in machine_configs]

    def send_alert(self, alert):
        if not self.run_headless:
            message = json.dumps(alert)
            self.mqtt_client.publish(f"{self.MQTT_ALERT_TOPIC}/{alert['machine_id']}", message)
            
    def _log_status(self):
        print(f"\n----- TIMESTEP {self.timestep} -----")
        for machine in self.machines:
            status = "WORKING" if machine.operational else "FAILED"
            alert_status = "SENT" if self.alert_sent[machine.machine_id] else "---"
            
            predictor = self.failure_predictors[machine.machine_id]
            predictor.input['temperature'] = machine.temperature
            predictor.input['vibration'] = machine.vibration
            predictor.compute()
            risk_score = predictor.output.get('failure_risk', 0.0)
            
            print(f"  Machine_ID:   {machine.machine_id}")
            print(f"  Status:       {status}")
            print(f"  Temperature:  {machine.temperature:.1f}°C")
            print(f"  Vibration:    {machine.vibration:.1f}")
            print(f"  Risk_Score:   {risk_score:.2f}%")
            print(f"  Alert_Status: {alert_status}")
            print("-" * 20)

            CRITICAL_RISK_THRESHOLD = 75.0
            SAFE_RISK_THRESHOLD = 40.0
            machine_id = machine.machine_id

            if (risk_score > CRITICAL_RISK_THRESHOLD and 
                machine.operational and not self.alert_sent[machine_id]):
                alert = {"type": "PREDICTIVE_FAILURE_WARNING", "severity": "CRITICAL", "machine_id": machine_id}
                self.send_alert(alert)
                self.alert_sent[machine_id] = True
                print(f"  >> PREDICTIVE ALERT TRIGGERED FOR {machine_id} <<")
            
            elif risk_score < SAFE_RISK_THRESHOLD and self.alert_sent[machine_id]:
                self.alert_sent[machine_id] = False
                print(f"  >> Alert for {machine_id} has been reset <<")

    def process_timestep(self):
        self.timestep += 1
        for machine in self.machines:
            should_process_job = random.random() < 0.7
            if should_process_job:
                temp_increment = random.uniform(5, 15)
                vib_increment = random.uniform(2, 4)
                machine.process_job(temp_increment, vib_increment)
            else:
                machine.process_job(0, 0)
            
            if self.run_headless and self.failure_predictors:
                predictor = self.failure_predictors[machine.machine_id]
                predictor.input['temperature'] = machine.temperature
                predictor.input['vibration'] = machine.vibration
                predictor.compute()
                risk_score = predictor.output.get('failure_risk', 0)

                is_about_to_fail = (machine.temperature > machine.temp_threshold - 20) or \
                                   (machine.vibration > machine.vib_threshold - 4)

                if is_about_to_fail:
                    TARGET_RISK = 85.0
                    error = abs(risk_score - TARGET_RISK)
                    self.fitness_score += (100 - error)
                else:
                    self.fitness_score += (100 - risk_score) / 10

        if not self.run_headless:
            self._log_status()

    def run_simulation(self, max_timesteps=50):
        if self.failure_predictors is None:
            return None
        if not self.run_headless:
            print("--- Starting Simulation with Evolved Fuzzy Model ---")
        try:
            while self.timestep < max_timesteps:
                if self.timestep >= max_timesteps: break
                self.process_timestep()
                if not self.run_headless:
                    time.sleep(1)
        finally:
            if not self.run_headless:
                self.cleanup()
        return self.fitness_score

    def cleanup(self):
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        print("\n[MQTT] Disconnected gracefully.")

if __name__ == "__main__":
    print("--- Running a DEMO of the simulation with a baseline, non-optimized model ---")
    baseline_params = [60, 80, 100, 5, 6, 8, 12, 10, 15, 25, 50, 85]
    simulation = WorkspaceSimulation(fuzzy_params=baseline_params, run_headless=False)
    simulation.run_simulation()