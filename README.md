# xG Calculator

> Expected goals (xG) measure the quality of a chance by calculating the likelihood that it will be scored, using information from similar past shots.
>
> -- Source: [Opta Analyst](https://theanalyst.com/na)

This summer, I had the opportunity to read "The Expected Goals Philosophy" by James Tippett. Through this experience, I gained valuable insights into leveraging the concept of expected goals to gain a deeper understanding of the beautiful game of soccer. That book served as the inspiration for this project.

## Data Collection

I sourced my data from Understat, meticulously gathering information on every shot taken across the top 5 European leagues spanning from the 2014/15 season to the 2022/23 season. For each shot, I collected the following variables:

- X and Y coordinates (with the origin at the corner flag)
- Situation
- Shot Type
- Last Action
- Result
- Expected Goals (xG)

All data has been organized and stored within a CSV spreadsheet for future reference and analysis.

## Data Preprocessing

Given that the spreadsheet contains raw data, certain modifications are required to enhance the dataset:

- Angle to the goal is calculated using shot and goal post coordinates.
- Distance to the center of the goal from the shot location is determined.
- The Y column is transformed to represent the distance from the field's centerline.
- A "Foot" column is added to indicate whether a shot was taken using the left or right foot.
- A "Goal" column is introduced to represent whether the shot resulted in a goal.
- Separate columns are introduced to account for significant moments preceding the shot: throughballs, standards, crosses, and rebounds. Additionally, penalties are given special consideration, acknowledging the unique circumstances they present.

## Model Training

With 95% of the dataset earmarked for model training, the AI model takes the following input variables:

- X and Y coordinates
- Angle to the goal
- Distance to the goal
- Foot (whether the shot was taken with a foot)
- Preceding action indicators

It is trained to estimate the value in the "Goal" column (0 or 1). The output will be a number between 0 and 1 representing the probability of a goal.

## Calibration and Testing

Calibration is essential. A Standard Scaler is employed for this purpose, followed by graphing projections using Understat's xG data for comparison. The visual results typically display an upward-sloping graph.

## Saving and Testing the Model

Both the trained model and the Standard Scaler are saved for future applications. To assess the model's effectiveness, I conducted tests on league games' data. Expected scorelines were generated based on our estimations, and these were compared with actual scorelines and Understat's xG predictions. Consistency was observed between our model and Understat's official model's predictions.

## Interactive Website

To facilitate user-friendly interaction with the model, I developed a website that allows users to place dots on a field to represent shot locations and input relevant data. The website features an xG counter at the top, providing the combined xG value for all shots.

## Running the Code

First, install all the required libraries:

```
pip install -r requirements.txt
```

To train the model, execute `train_model.py`:

```
python train_model.py
```

To test the model on league games, run `check_match_predictions.py`:
```
python check_match_predictions.py
```

For data collection, the code is available in `collect_data.py`. To execute, simply run the following command:

```
python collect_data.py
```

To run the website, navigate to the website directory and execute `main.py`:

```
cd website 
python main.py
```