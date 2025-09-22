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
        self.failure_predictors = {m.machine_id: create_failure_predictor() for m in self.machines}
        self.alert_sent = {m.machine_id: False for m in self.machines}
        self.timestep = 0

    def reset(self):
        self.machines = self.create_machines()
        try:
            self.failure_predictors = {m.machine_id: create_failure_predictor(self.fuzzy_params) for m in self.machines}
        except (AssertionError, ValueError): self.failure_predictors = None
        self.alert_sent = {m.machine_id: False for m in self.machines}
        self.timestep = 0
        self.fitness_score = 0

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[MQTT] Connected successfully to broker.")

    def create_machines(self):
        machine_configs = [
            {"class_name": "A", "machine_id": "A_1", "temp_base": 40, "temp_threshold": 120, "vib_base": 2, "vib_threshold": 18, "repair_time": 3},
            {"class_name": "B", "machine_id": "B_1", "temp_base": 50, "temp_threshold": 130, "vib_base": 4, "vib_threshold": 20, "repair_time": 5}
        ]
        return [Machine(**config) for config in machine_configs]

    def send_alert(self, alert):
        message = json.dumps(alert)
        self.mqtt_client.publish(f"{self.MQTT_ALERT_TOPIC}/{alert['machine_id']}", message)
            
    def _log_status(self):
        print(f"\n----- TIMESTEP {self.timestep} -----")
        for machine in self.machines:
            status = "WORKING 🔧" if machine.operational else "FAILED ❌"
            alert_status = "SENT 🚨" if self.alert_sent[machine.machine_id] else "---"
            
            predictor = self.failure_predictors[machine.machine_id]
            predictor.input['temperature'] = machine.temperature
            predictor.input['vibration'] = machine.vibration
            predictor.compute()
            risk_score = predictor.output.get('failure_risk', 0.0)
            
            print(f"  Machine_ID:   {machine.machine_id}\n  Status:       {status}\n  Temperature:  {machine.temperature:.1f}°C\n  Vibration:    {machine.vibration:.1f}\n  Risk_Score:   {risk_score:.2f}%\n  Alert_Status: {alert_status}\n" + "-"*20)

            CRITICAL_RISK_THRESHOLD = 75.0
            SAFE_RISK_THRESHOLD = 40.0
            
            if (risk_score > CRITICAL_RISK_THRESHOLD and machine.operational and not self.alert_sent[machine.machine_id]):
                alert = {"type": "PREDICTIVE_FAILURE_WARNING", "severity": "CRITICAL", "machine_id": machine.machine_id}
                self.send_alert(alert)
                self.alert_sent[machine.machine_id] = True
                print(f"  >> PREDICTIVE ALERT TRIGGERED FOR {machine.machine_id} <<")
            
            elif risk_score < SAFE_RISK_THRESHOLD and self.alert_sent[machine.machine_id]:
                self.alert_sent[machine.machine_id] = False
                print(f"  >> Alert for {machine.machine_id} has been reset <<")

    def process_timestep(self):
        self.timestep += 1
        for machine in self.machines:
            if random.random() < 0.7 and machine.operational:
                machine.process_job(random.uniform(5, 15), random.uniform(2, 4))
            else:
                machine.temperature = max(machine.temp_base, machine.temperature - 1.5)
                machine.vibration = max(machine.vib_base, machine.vibration - 0.3)
            
            if self.run_headless and self.failure_predictors:
                predictor = self.failure_predictors[machine.machine_id]
                predictor.input['temperature'] = machine.temperature
                predictor.input['vibration'] = machine.vibration
                predictor.compute()
                risk_score = predictor.output.get('failure_risk', 0)
                is_about_to_fail = (machine.temperature > machine.temp_threshold - 20) or (machine.vibration > machine.vib_threshold - 4)
                if is_about_to_fail:
                    self.fitness_score += (100 - abs(risk_score - 85.0))
                else:
                    self.fitness_score += (100 - risk_score) / 10
        if not self.run_headless: self._log_status()

    def run_simulation(self, max_timesteps=50):
        if self.failure_predictors is None: return None
        if not self.run_headless: print("--- Starting Simulation ---")
        try:
            while self.timestep < max_timesteps:
                self.process_timestep()
                if not self.run_headless: time.sleep(1)
        finally:
            if not self.run_headless: self.cleanup()
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