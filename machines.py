import random
import json

class Machine:
    """
    Digital Twin Enabled Machine Class for Flexible Job Shop Simulation.
    """
    def __init__(self, class_name, machine_id, temp_base, temp_threshold, vib_base, vib_threshold, repair_time, power_idle, power_active):
        self.class_name = class_name
        self.machine_id = machine_id
        self.temp_base = temp_base
        self.temp_threshold = temp_threshold
        self.vib_base = vib_base
        self.vib_threshold = vib_threshold
        self.repair_time = repair_time
        self.power_idle = power_idle
        self.power_active_base = power_active

        self.temperature = temp_base
        self.vibration = vib_base
        self.operational = True
        self.repair_timer = 0

    def process_job(self, job_temp_increment, job_vib_increment):
        if not self.operational:
            return

        temp_change = job_temp_increment + random.uniform(-1.5, 1.5)
        vib_change = job_vib_increment + random.uniform(-1, 1)

        self.temperature += temp_change
        self.vibration += vib_change

        if self.temperature >= self.temp_threshold or self.vibration >= self.vib_threshold:
            self.operational = False

    def get_status(self, current_timestep):
        status_str = "Operational" if self.operational else f"Faulty (Repair {self.repair_timer}/{self.repair_time})"
        status_dict = {
            "timestamp": current_timestep,
            "machine_id": self.machine_id,
            "class_name": self.class_name,
            "temperature": round(self.temperature, 2),
            "vibration": round(self.vibration, 2),
            "status": status_str
        }
        return json.dumps(status_dict)

    def repair(self, silent_mode=False):
        """Processes the repair timer for a failed machine."""
        if not self.operational and self.repair_timer < self.repair_time:
            self.repair_timer += 1
            if self.repair_timer >= self.repair_time:
                self.operational = True
                self.repair_timer = 0
                self.temperature = self.temp_base
                self.vibration = self.vib_base
                if not silent_mode:
                    print(f"Machine {self.machine_id} has been repaired and is now operational.")