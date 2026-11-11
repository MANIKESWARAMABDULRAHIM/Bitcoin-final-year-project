import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

MODEL_PATH = "rf_model.pkl"

def train():

    print("Loading Elliptic dataset...")

    # Load features (no header in file)
    features = pd.read_csv(r"elliptic_bitcoin_dataset\elliptic_txs_features.csv", header=None)

    # Load classes
    classes = pd.read_csv(r"elliptic_bitcoin_dataset\elliptic_txs_classes.csv")

    # Add class column
    features["class"] = classes["class"]

    # Remove unknown labels
    features = features[features["class"] != 0]

    # Convert:
    # 1 (illicit) → 1
    # 2 (licit) → 0
    features["class"] = features["class"].map({1: 1, 2: 0})

    # Separate X and y
    X = features.drop(columns=["class"])
    y =  classes["class"]

    print("Dataset shape:", X.shape)

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    print("Training model...")

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        n_jobs=-1,
        random_state=42
    )

    model.fit(X_train, y_train)

    # Evaluation
    y_pred = model.predict(X_test)

    print("\nModel Evaluation:")
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print(classification_report(y_test, y_pred))

    # Save model
    joblib.dump(model, MODEL_PATH)
    print("\nModel saved as rf_model.pkl")


if __name__ == "__main__":
    train()
