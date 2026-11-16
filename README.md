# EduGuard – Student Dropout Early-Warning System

## Data dashboard and EDA (Member 1)

The FastAPI landing page provides dataset uploads, quality profiling, outcome charts, and comparison views. See the [dashboard guide](docs/member1_eda_dashboard.md), [measured EDA findings](docs/eda_findings.md), [notebooks](notebooks/), and [feature-group handoff](config/feature_groups.json). Downloaded CSVs and executed notebook outputs are kept under `data/` and excluded from Git. Run `.venv/bin/python scripts/run_eda.py` after downloading the two source files to regenerate report figures.

## Supervised learning plan (Member 3)

- **Logistic Regression**
- **K-Nearest Neighbours (KNN)**

The objective is to identify students who may be at risk of dropping out and provide interpretable prediction results to support early intervention.

## Responsibilities

### 1. Dataset Preparation for Model Training

- Inspect the prepared datasets and verify their target labels and feature columns.
- Use source-specific datasets for the initial experiments because the UCI and Kaggle datasets have different schemas and target definitions.
- Select appropriate input features and exclude identifiers and target-related columns from model training.
- Handle missing values, categorical features, and numerical scaling through fitted preprocessing pipelines.
- Use stratified training and testing splits where appropriate.
- Prevent data leakage by fitting preprocessing steps using training data only.

### 2. Machine Learning Model Development

Develop and train the following supervised learning algorithms:

**Logistic Regression**

- Train a classification model for student dropout prediction.
- Generate class predictions and prediction probabilities.
- Evaluate model performance using appropriate classification metrics.

**K-Nearest Neighbours (KNN)**

- Train a KNN classification model.
- Experiment with suitable values of K.
- Apply feature scaling because KNN is distance-based.
- Evaluate and compare its performance with Logistic Regression.

### 3. Model Evaluation and Comparison

Evaluate both models using:

- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC, where applicable
- Confusion Matrix
- Classification Report

Compare the models using consistent data splits and evaluation procedures. Pay particular attention to dropout-class precision and recall rather than relying only on overall accuracy.

### 4. Dropout Risk Prediction

The prediction system will:

- Accept student academic and relevant demographic information.
- Allow selection between Logistic Regression and KNN.
- Generate a dropout prediction.
- Display the predicted class and probability, where supported.
- Categorise students into Low, Medium, or High risk using documented thresholds.
- Provide results in a clear format for users.

Risk thresholds must be selected and documented using validation data rather than arbitrarily chosen.

### 5. Model Persistence and Backend Integration

- Save trained models together with their fitted preprocessing pipelines.
- Maintain model versions and associated evaluation metrics.
- Load the selected model for prediction.
- Integrate the prediction functionality with the FastAPI backend.
- Validate incoming student feature data before generating predictions.
- Provide APIs for prediction, model selection, prediction history, and model evaluation.

### 6. Frontend Integration

The prediction interface will include:

- Student feature-input form.
- Machine learning model selection.
- Dropout prediction results.
- Dropout probability and risk category.
- Prediction history.
- Model performance comparison.
- Confusion matrices and evaluation charts.

## Proposed Module Structure

```text
ml/
├── train_uci.py
├── train_kaggle.py
├── evaluate.py
├── model_comparison.py
└── predict.py

models/
├── logistic_regression/
└── knn/

tests/
└── test_models.py
```

The structure may be adjusted as implementation progresses.

## Training and Evaluation Methodology

1. Verify the prepared dataset and its target labels.
2. Conduct exploratory analysis and inspect class distributions.
3. Select the appropriate prediction target and input features.
4. Split the data into training and testing sets using stratification where feasible.
5. Fit preprocessing and model training using training data only.
6. Train Logistic Regression and KNN independently.
7. Evaluate both models using consistent metrics and validation procedures.
8. Compare model performance and select a suitable model.
9. Save the complete fitted preprocessing and model pipeline.
10. Integrate the selected models with the FastAPI prediction service.

**Important dataset considerations:**

- UCI dataset 697 contains three original outcomes: Dropout, Graduate, and Enrolled.
- For a binary dropout experiment, Enrolled records must be handled according to the documented target policy rather than automatically treating them as non-dropouts.
- Kaggle and UCI experiments should initially be evaluated separately.
- Pooled or cross-source experiments should be reported separately because similar feature names do not necessarily represent equivalent measurements.
- Features unavailable at the intended prediction time must not be used. In particular, post-outcome academic information must be excluded from an early-stage prediction model.

## Expected Deliverables

- Logistic Regression training implementation.
- KNN training implementation.
- Model evaluation and comparison reports.
- Confusion matrices and performance visualisations.
- Saved model and preprocessing pipelines.
- Dropout prediction functionality.
- FastAPI prediction and evaluation integration.
- Frontend prediction and model comparison interfaces.
- Model-related automated tests and documentation.
