import math 
import pandas as pd
import json
from sklearn.preprocessing import StandardScaler

dimension_constant = 1.57292

def get_dimension_constant():
    return dimension_constant

#scaleX is only true when working with the raw data
def get_angle(row, scaleX=False):
    x = float(row['X'])
    if scaleX:
        x=(1-float(row['X']))*dimension_constant
    y = float(row['Y'])
    a = math.hypot(x, y-.44)
    b = math.hypot(x, y-.56)
    acos_value = (a**2 + b**2 - .12**2) / (2 * a * b)
    if -1<=acos_value<=1:
        return math.acos(acos_value)
    else:
        return math.pi

def get_csv(filename):
    data = pd.read_csv(filename)
    #Own goals are ignored in this model
    data = data[~data['result'].isin(['OwnGoal'])]
    return data

def load_scaler_from_json(json_file_path):
    with open(json_file_path, 'r') as file:
        scaler_data = json.load(file)
    scaler = StandardScaler() 
    scaler.mean_ = scaler_data["mean"]
    scaler.scale_ = scaler_data["scale"]
    return scaler