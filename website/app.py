from flask import Flask, render_template, request, jsonify
import joblib

app = Flask(__name__)

calibrated_model = joblib.load('model.pkl')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/probability', methods=['POST'])
def calibrate():
    data = list(request.json.get('data').values())
    probability = calibrated_model.predict_proba([data])[0][1]
    return jsonify(probability=probability)

if __name__ == '__main__':
    app.run()
