import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

def create_failure_predictor(params):
    t_norm_mid, t_hot_start, t_hot_mid = params[0:3]
    v_low_mid, v_med_start, v_med_mid, v_med_end, v_high_start, v_high_mid = params[3:9]
    r_low_mid, r_med_mid, r_crit_mid = params[9:12]

    temp = ctrl.Antecedent(np.arange(0, 201, 1), 'temperature')
    vib = ctrl.Antecedent(np.arange(0, 31, 1), 'vibration')
    risk = ctrl.Consequent(np.arange(0, 101, 1), 'failure_risk')

    temp['normal'] = fuzz.trimf(temp.universe, [0, t_norm_mid, t_hot_start])
    temp['hot'] = fuzz.trimf(temp.universe, [t_hot_start, t_hot_mid, 200])
    
    vib['low'] = fuzz.trimf(vib.universe, [0, v_low_mid, v_med_start])
    vib['medium'] = fuzz.trimf(vib.universe, [v_low_mid, v_med_mid, v_high_start])
    vib['high'] = fuzz.trimf(vib.universe, [v_med_end, v_high_mid, 30])
    
    risk['low'] = fuzz.trimf(risk.universe, [0, r_low_mid, 50])
    risk['medium'] = fuzz.trimf(risk.universe, [30, r_med_mid, 80])
    risk['critical'] = fuzz.trimf(risk.universe, [60, r_crit_mid, 100])

    rules = [
        ctrl.Rule(temp['hot'] | vib['high'], risk['critical']),
        ctrl.Rule(temp['normal'] & vib['medium'], risk['medium']),
        ctrl.Rule(temp['normal'] & vib['low'], risk['low']),
        ctrl.Rule(temp['hot'] & vib['low'], risk['medium'])
    ]
    return ctrl.ControlSystemSimulation(ctrl.ControlSystem(rules))