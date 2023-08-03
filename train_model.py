from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import numpy as np
import joblib
import matplotlib.pyplot as plt
from helper_methods import *
from sklearn.calibration import CalibratedClassifierCV

data = get_csv("data.csv")

data['goal'] = data['result'].apply(lambda i: 1 if i == 'Goal' else 0)
data['X'] = (1 - data['X']) * get_dimension_constant()
data['angle'] = data.apply(get_angle, axis=1)
data['Y'] = abs(0.5 - data['Y'])
data['foot'] = data['shotType'].apply(lambda i: 1 if i in ['RightFoot', 'LeftFoot'] else 0)
data['distance'] = np.hypot(data['Y'], data['X'])
data["Throughball"] = data['lastAction'].apply(lambda i: 1 if i == "Throughball" else 0)
data['Standard'] = data['lastAction'].apply(lambda i: 1 if i == 'Standard' else 0)
data["Rebound"] = data['lastAction'].apply(lambda i: 1 if i == "Rebound" else 0)
data["Cross"] = data['lastAction'].apply(lambda i: 1 if i == "Cross" else 0)
#Note: Penalty counts as a Standard
data['Penalty'] = data['situation'].apply(lambda i: 1 if i == "Penalty" else 0)

features = data[['X', 'Y', 'angle', 'distance', 'foot', "Throughball", "Standard", "Rebound", "Cross", "Penalty", "xG"]]
labels = data['goal']

x_train, x_test, y_train, y_test = train_test_split(features, labels, train_size=0.95, test_size=0.05)

#Save xGs for graphing at the end
xgs = x_test.pop('xG')
#The xGs from the training data aren't used, so they can be dropped
x_train = x_train.drop('xG', axis=1)

scaler = StandardScaler()
x_train = scaler.fit_transform(x_train)
x_test = scaler.transform(x_test)

scaler_json = {
    "mean": scaler.mean_.tolist(),
    "scale": scaler.scale_.tolist()
}

with open('scaler.json', 'w') as f:
    json.dump(scaler_json, f)

model = LogisticRegression(class_weight='balanced')
model.fit(x_train, y_train)

calibrated_model = CalibratedClassifierCV(model, method='isotonic', cv=5)
calibrated_model.fit(x_train, y_train)

joblib.dump(calibrated_model, 'model.pkl')

predictions_calibrated = calibrated_model.predict_proba(x_test)[:, 1]
predictions_uncalibrated = model.predict_proba(x_test)[:, 1]

plt.scatter(xgs.values.tolist(), predictions_calibrated)
plt.plot()
#0.1 above and below the Understat's xG estimation for the chance
plt.plot([0, 1], [0, 1], color='red')
plt.plot([0.1, 1], [0, 0.9], color='red', linestyle='dashed')
plt.plot([0, .9], [0.1, 1], color='red', linestyle='dashed')
plt.xlabel("Understat's xG")
plt.ylabel("My Model's Estimation")
plt.show()
