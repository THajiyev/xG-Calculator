const baseUrl = 'http://127.0.0.1:5000/';//localhost
const fieldHeight = 464;
const fieldWidth = 733;
const startingY = 11;
const startingX = 12;
const dimension_constant = 1.57292;

const scaler = {
  "mean": [
      0.2394734909063207,
      0.10393066863969803,
      0.47537257711595665,
      0.27252740960914523,
      0.8266877450293573,
      0.020038543795321342,
      0.05554219065167565,
      0.04387330776083813,
      0.14119242553618966,
      0.012533342497838851
  ],
  "scale": [
      0.1235526235919178,
      0.07545033173129002,
      0.28530483080379593,
      0.12180291908362229,
      0.3785169973034681,
      0.1401320825431647,
      0.2290354900649429,
      0.20481318470001122,
      0.34821993697575265,
      0.1112486306597556
  ]
};

function changeTooltipDisplay(show) {
  const tooltip = document.getElementById("tooltip");
  if(show){
    tooltip.style.display = "block";
  }
  else{
    tooltip.style.display = "none";
  }
}

function scaleData(inputData) {
  var scaledData = new Float32Array(inputData.length);
  for (let i = 0; i < inputData.length; i++) {
    scaledData[i] = (inputData[i] - scaler.mean[i]) / scaler.scale[i];
  }
  return scaledData;
}

async function getProbability(rawData) {
  var scaledData = scaleData(rawData);
  try {
    const response = await fetch(`${baseUrl}/probability`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ data: scaledData }), 
    });
    if (!response.ok) {
      throw new Error('Failed to fetch.');
    }
    const result = await response.json();
    return result.probability;
  } catch (error) {
    console.error('Error:', error);
    return 0;
  }
}

class RawData {
  constructor(coordinates, foot, situation) {
    this.x = coordinates[0] * dimension_constant;
    this.y = coordinates[1];
    this.foot = foot;
    this.situation = situation;
  }

  distance() {
    return Math.hypot(this.x, Math.abs(this.y - 0.5));
  }

  angle() {
    var a = Math.hypot(this.x, this.y - 0.44);
    var b = Math.hypot(this.x, this.y - 0.56);
    var acosValue = (a ** 2 + b ** 2 - 0.12 ** 2) / (2 * a * b);
    if (-1 <= acosValue && acosValue <= 1) {
      return Math.acos(acosValue);
    } else {
      return Math.PI;
    }
  }

  format_data() {
    return [
      this.x,
      Math.abs(this.y - 0.5),
      this.angle(),
      this.distance(),
      this.foot ? 1 : 0,
      this.situation == "Throughball" ? 1 : 0,
      this.situation == "Standard" || this.situation == "Penalty" ? 1 : 0,
      this.situation == "Rebound" ? 1 : 0,
      this.situation == "Cross" ? 1 : 0,
      this.situation == "Penalty" ? 1 : 0
    ];
  }

}

function getCoordinates(x, y) {
  var modified_x = (x - startingX) / fieldWidth;
  var modified_y = (y - startingY) / fieldHeight;
  return [modified_x, modified_y];
}

document.addEventListener("DOMContentLoaded", function () {
  const soccerField = document.getElementById("soccer-field");
  const confirmButton = document.getElementById("confirm-button");
  const addNewPointButton = document.getElementById("add-new-point");
  const questionsDiv = document.getElementById("questions");
  const situationDropdown = document.getElementById("situation-dropdown");
  const situationDropdownDefault = "Other";
  const footSwitch = document.getElementById("foot-switch");
  const xG_label = document.getElementById("counter");
  confirmButton.disabled = true;
  var isDragging = false;
  var selectedPoint = null;
  var offsetX = 0;
  var offsetY = 0;
  var temporaryPoints = [];
  const pointSize = 10;
  var xG = 0;

  function createPoint(x, y, isConfirmed = false) {
    questionsDiv.style.display = "flex";
    situationDropdown.value = situationDropdownDefault;
    footSwitch.checked = true;
    const point = document.createElement("div");
    point.className = "point";
    point.style.left = x + "px";
    point.style.top = y + "px";
    if (isConfirmed) {
      point.classList.add("confirmed");
    } else {
      point.classList.add("temporary");
    }

    function movePoint(e) {
      if (!point.classList.contains("confirmed") && isDragging && selectedPoint === point) {
        const x = e.pageX - offsetX;
        const y = e.pageY - offsetY;
        const maxX = soccerField.clientWidth - point.clientWidth;
        const maxY = soccerField.clientHeight - point.clientHeight;
        point.style.left = Math.max(0, Math.min(x, maxX)) + "px";
        point.style.top = Math.max(0, Math.min(y, maxY)) + "px";
      }
    }

    point.addEventListener("mousedown", function (e) {
      isDragging = true;
      selectedPoint = point;
      offsetX = e.pageX - point.offsetLeft;
      offsetY = e.pageY - point.offsetTop;
      document.addEventListener("mousemove", movePoint);
    });

    document.addEventListener("mouseup", function () {
      isDragging = false;
      selectedPoint = null;
      document.removeEventListener("mousemove", movePoint);
    });

    soccerField.appendChild(point);
    if (!isConfirmed) {
      temporaryPoints.push(point);
    }
  }

  confirmButton.addEventListener("click", function () {
    if (temporaryPoints.length > 0) {
      const tempPoint = temporaryPoints[temporaryPoints.length - 1];
      tempPoint.classList.remove("temporary");
      tempPoint.classList.add("confirmed");
      temporaryPoints.pop();
      confirmButton.disabled = true;
      addNewPointButton.disabled = false;
      var rawX = parseInt(tempPoint.style.left) + 0.5 * pointSize;
      var rawY = parseInt(tempPoint.style.top) + 0.5 * pointSize;
      var coordinates = getCoordinates(rawX, rawY);
      const situation_type = situationDropdown.value;
      const foot_bool = footSwitch.checked;
      questionsDiv.style.display = "none";
      var dataInput = new RawData(coordinates, foot_bool, situation_type);

      getProbability(dataInput.format_data())
        .then((probability) => {
          xG += probability;
          xG_label.innerHTML = "Total xG: "+xG.toFixed(3);
        })
        .catch((error) => {
          console.error('Error:', error);
        });
    }
  });

  addNewPointButton.addEventListener("click", function () {
    addNewPointButton.disabled = true;
    confirmButton.disabled = false;
    const x = 0.5 * (fieldWidth - pointSize) + startingX;
    const y = 0.5 * (fieldHeight - pointSize) + startingY;
    createPoint(x, y, false);
  });
});

