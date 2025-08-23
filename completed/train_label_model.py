"""
Train a lightweight ML model for metrics-to-label mapping.
Alternative to declarative YAML rules for more complex decision boundaries.
"""

import json
import logging
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import joblib
import numpy as np

logger = logging.getLogger(__name__)

# Feature order for consistent model input
FEATURE_ORDER = ["ctr", "impressions", "position", "clicks", "volatility_index"]

# Label encoding
LABEL_MAPPING = {
    "MOMENTUM_POS": 0,
    "MOMENTUM_NEG": 1,
    "VOLATILE_SPIKE": 2,
    "NEUTRAL": 3
}
INVERSE_LABEL_MAPPING = {v: k for k, v in LABEL_MAPPING.items()}


def load_training_data(data_paths: List[str]) -> Tuple[pd.DataFrame, List[str]]:
    """
    Load training data from CSV files.
    
    Expected CSV format:
    tenant_id,date,ctr,impressions,position,clicks,volatility_index,label,mode
    
    Args:
        data_paths: List of paths to CSV files
    
    Returns:
        Tuple of (features DataFrame, labels list)
    """
    all_data = []
    
    for data_path in data_paths:
        if not Path(data_path).exists():
            logger.warning(f"Training data file not found: {data_path}")
            continue
        
        try:
            df = pd.read_csv(data_path)
            all_data.append(df)
            logger.info(f"Loaded {len(df)} records from {data_path}")
        except Exception as e:
            logger.error(f"Failed to load {data_path}: {e}")
    
    if not all_data:
        raise ValueError("No training data loaded")
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Extract features and labels
    features = combined_df[FEATURE_ORDER].copy()
    labels = combined_df["label"].tolist()
    
    # Handle missing values
    features = features.fillna(0.5)  # Fill with neutral values
    
    # Add mode as categorical feature
    if "mode" in combined_df.columns:
        features["mode_gsc"] = (combined_df["mode"] == "gsc").astype(int)
        features["mode_serp"] = (combined_df["mode"] == "serp").astype(int)
    
    logger.info(f"Loaded {len(features)} training samples with {len(features.columns)} features")
    return features, labels


def create_synthetic_training_data(n_samples: int = 1000) -> Tuple[pd.DataFrame, List[str]]:
    """
    Create synthetic training data for demonstration.
    In production, this would come from actual logged metrics + manual labels.
    
    Args:
        n_samples: Number of synthetic samples to generate
    
    Returns:
        Tuple of (features DataFrame, labels list)
    """
    np.random.seed(42)  # For reproducible results
    
    data = []
    labels = []
    
    for _ in range(n_samples):
        # Generate correlated features that make sense
        base_performance = np.random.beta(2, 2)  # Skewed toward middle values
        
        # Generate metrics with realistic correlations
        ctr = np.clip(base_performance + np.random.normal(0, 0.1), 0, 1)
        position = np.clip(1 - base_performance + np.random.normal(0, 0.15), 0, 1)  # Inverted
        clicks = np.clip(base_performance * ctr + np.random.normal(0, 0.05), 0, 1)
        impressions = np.clip(base_performance + np.random.normal(0, 0.2), 0, 1)
        volatility = np.random.beta(1, 3)  # Mostly low volatility
        
        # Determine label based on synthetic rules
        if ctr >= 0.7 and position >= 0.8 and clicks >= 0.6:
            label = "MOMENTUM_POS"
        elif ctr <= 0.3 and position <= 0.4 and clicks <= 0.3:
            label = "MOMENTUM_NEG"
        elif volatility >= 0.6:
            label = "VOLATILE_SPIKE"
        else:
            label = "NEUTRAL"
        
        data.append({
            "ctr": ctr,
            "impressions": impressions,
            "position": position,
            "clicks": clicks,
            "volatility_index": volatility,
            "mode_gsc": np.random.choice([0, 1]),
            "mode_serp": np.random.choice([0, 1])
        })
        labels.append(label)
    
    features_df = pd.DataFrame(data)
    logger.info(f"Generated {len(features_df)} synthetic training samples")
    
    # Print label distribution
    label_counts = pd.Series(labels).value_counts()
    logger.info(f"Label distribution: {label_counts.to_dict()}")
    
    return features_df, labels


def train_model(
    features: pd.DataFrame,
    labels: List[str],
    model_type: str = "random_forest",
    test_size: float = 0.2
) -> Tuple[Any, StandardScaler, Dict[str, Any]]:
    """
    Train a classification model for label prediction.
    
    Args:
        features: Feature DataFrame
        labels: List of label strings
        model_type: "random_forest" or "logistic_regression"
        test_size: Fraction of data to use for testing
    
    Returns:
        Tuple of (trained model, scaler, evaluation metrics)
    """
    # Encode labels as integers
    y = [LABEL_MAPPING[label] for label in labels]
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        features, y, test_size=test_size, random_state=42, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    if model_type == "random_forest":
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight="balanced"
        )
    elif model_type == "logistic_regression":
        model = LogisticRegression(
            random_state=42,
            class_weight="balanced",
            max_iter=1000
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    model.fit(X_train_scaled, y_train)
    
    # Evaluate model
    train_score = model.score(X_train_scaled, y_train)
    test_score = model.score(X_test_scaled, y_test)
    
    # Cross-validation
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
    
    # Predictions for detailed evaluation
    y_pred = model.predict(X_test_scaled)
    
    # Classification report
    target_names = [INVERSE_LABEL_MAPPING[i] for i in range(len(LABEL_MAPPING))]
    class_report = classification_report(y_test, y_pred, target_names=target_names, output_dict=True)
    
    # Feature importance (for tree-based models)
    feature_importance = None
    if hasattr(model, "feature_importances_"):
        feature_importance = dict(zip(features.columns, model.feature_importances_))
        feature_importance = {k: round(v, 4) for k, v in feature_importance.items()}
    
    evaluation = {
        "model_type": model_type,
        "train_accuracy": round(train_score, 4),
        "test_accuracy": round(test_score, 4),
        "cv_mean": round(cv_scores.mean(), 4),
        "cv_std": round(cv_scores.std(), 4),
        "classification_report": class_report,
        "feature_importance": feature_importance,
        "n_train_samples": len(X_train),
        "n_test_samples": len(X_test),
        "feature_names": list(features.columns)
    }
    
    logger.info(f"Model trained: {model_type}")
    logger.info(f"Train accuracy: {train_score:.4f}")
    logger.info(f"Test accuracy: {test_score:.4f}")
    logger.info(f"CV accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    
    return model, scaler, evaluation


def save_model(
    model: Any,
    scaler: StandardScaler,
    evaluation: Dict[str, Any],
    output_path: str
):
    """
    Save trained model, scaler, and metadata.
    
    Args:
        model: Trained scikit-learn model
        scaler: Fitted StandardScaler
        evaluation: Evaluation metrics dictionary
        output_path: Path to save model file
    """
    model_data = {
        "model": model,
        "scaler": scaler,
        "feature_order": FEATURE_ORDER,
        "label_mapping": LABEL_MAPPING,
        "inverse_label_mapping": INVERSE_LABEL_MAPPING,
        "evaluation": evaluation,
        "version": "1.0"
    }
    
    joblib.dump(model_data, output_path)
    logger.info(f"Model saved to {output_path}")


def load_model(model_path: str) -> Dict[str, Any]:
    """
    Load trained model and metadata.
    
    Args:
        model_path: Path to saved model file
    
    Returns:
        Dictionary containing model, scaler, and metadata
    """
    model_data = joblib.load(model_path)
    logger.info(f"Model loaded from {model_path}")
    return model_data


def predict_label(
    model_data: Dict[str, Any],
    metrics: Dict[str, float],
    mode: str = "serp"
) -> Tuple[str, float]:
    """
    Predict label from metrics using trained model.
    
    Args:
        model_data: Loaded model data dictionary
        metrics: Dictionary of normalized metrics
        mode: Processing mode ("serp" or "gsc")
    
    Returns:
        Tuple of (predicted label, confidence score)
    """
    model = model_data["model"]
    scaler = model_data["scaler"]
    feature_order = model_data["feature_order"]
    inverse_mapping = model_data["inverse_label_mapping"]
    
    # Prepare features in correct order
    features = []
    for feature_name in feature_order:
        features.append(metrics.get(feature_name, 0.5))  # Default to neutral
    
    # Add mode features
    features.extend([
        1 if mode == "gsc" else 0,  # mode_gsc
        1 if mode == "serp" else 0  # mode_serp
    ])
    
    # Scale and predict
    X = scaler.transform([features])
    prediction = model.predict(X)[0]
    confidence = model.predict_proba(X)[0].max()
    
    predicted_label = inverse_mapping[prediction]
    
    return predicted_label, confidence


def main():
    """CLI entry point for model training."""
    parser = argparse.ArgumentParser(description="Train label prediction model")
    parser.add_argument("--from", dest="data_paths", nargs="+", 
                       help="Paths to training CSV files")
    parser.add_argument("--synthetic", action="store_true",
                       help="Use synthetic training data for demo")
    parser.add_argument("--samples", type=int, default=1000,
                       help="Number of synthetic samples to generate")
    parser.add_argument("--model", choices=["random_forest", "logistic_regression"],
                       default="random_forest", help="Model type to train")
    parser.add_argument("--out", default="models/labeler.joblib",
                       help="Output path for trained model")
    parser.add_argument("--test-size", type=float, default=0.2,
                       help="Fraction of data for testing")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        level=logging.INFO
    )
    
    try:
        # Load or generate training data
        if args.synthetic:
            features, labels = create_synthetic_training_data(args.samples)
        else:
            if not args.data_paths:
                raise ValueError("Must provide --from paths or use --synthetic")
            features, labels = load_training_data(args.data_paths)
        
        # Train model
        model, scaler, evaluation = train_model(features, labels, args.model, args.test_size)
        
        # Create output directory
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        
        # Save model
        save_model(model, scaler, evaluation, args.out)
        
        # Print summary
        print(f"\n✅ Model Training Complete:")
        print(f"   🤖 Model: {args.model}")
        print(f"   📊 Train accuracy: {evaluation['train_accuracy']}")
        print(f"   🎯 Test accuracy: {evaluation['test_accuracy']}")
        print(f"   📈 CV accuracy: {evaluation['cv_mean']} ± {evaluation['cv_std']}")
        print(f"   💾 Saved to: {args.out}")
        
        if evaluation['feature_importance']:
            print(f"   🔍 Top features: {dict(list(sorted(evaluation['feature_importance'].items(), key=lambda x: x[1], reverse=True))[:3])}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())