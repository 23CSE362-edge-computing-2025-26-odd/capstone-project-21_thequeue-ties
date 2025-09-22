import random

class Job:
    def __init__(self, job_id, job_name, priority, operations):
        self.job_id = job_id
        self.job_name = job_name
        self.job_priority = priority
        
        # All core data now comes from the dataset 
        self.operations = operations
        self.machine_requirement = [op['machine'] for op in self.operations]
        self.machine_processing_time = [op['time'] for op in self.operations]
        self.power_consumption = [op['power'] for op in self.operations]
        
        self.total_processing_time = sum(self.machine_processing_time)
        self.current_operation = 0 # Track which operation is next
        
        # These attributes represent inherent job risk/properties and can remain random
        self.threshold_temperature_reduction = random.uniform(0.1, 0.5)
        self.job_failure_rate = random.uniform(0.01, 0.05) # Lowered for a more realistic simulation
        
        self.status = 'Not Started'