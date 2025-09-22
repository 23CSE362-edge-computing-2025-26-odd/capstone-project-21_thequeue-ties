import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

def create_failure_predictor():
    """
    Creates the baseline, expert-driven Fuzzy Logic Control System.
    """
    temperature = ctrl.Antecedent(np.arange(0, 151, 1), 'temperature')
    vibration = ctrl.Antecedent(np.arange(0, 21, 1), 'vibration')
    failure_risk = ctrl.Consequent(np.arange(0, 101, 1), 'failure_risk')

    # Default membership functions
    temperature.automf(names=['low', 'normal', 'high'])
    vibration.automf(names=['low', 'medium', 'high'])

    # Default risk membership functions
    failure_risk['low'] = fuzz.trimf(failure_risk.universe, [0, 20, 40])
    failure_risk['medium'] = fuzz.trimf(failure_risk.universe, [30, 50, 70])
    failure_risk['critical'] = fuzz.trimf(failure_risk.universe, [60, 85, 100])
    
    # Expert-defined rules
    rules = [
        ctrl.Rule(temperature['high'] | vibration['high'], failure_risk['critical']),
        ctrl.Rule(temperature['normal'] & vibration['medium'], failure_risk['medium']),
        ctrl.Rule(temperature['normal'] & vibration['low'], failure_risk['low']),
        ctrl.Rule(temperature['high'] & vibration['low'], failure_risk['medium'])
    ]
    
    control_system = ctrl.ControlSystem(rules)
    return ctrl.ControlSystemSimulation(control_system)