"""
Learning Engine for FPL Assistant
Tracks predictions vs actual results and improves accuracy over time
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Try to import numpy, fall back to basic math if not available
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    
    # Basic numpy replacements
    class np:
        @staticmethod
        def mean(arr):
            return sum(arr) / len(arr) if arr else 0
        
        @staticmethod
        def corrcoef(x, y):
            # Simple correlation coefficient calculation
            if len(x) != len(y) or len(x) < 2:
                return [[1, 0], [0, 1]]
            
            mean_x = sum(x) / len(x)
            mean_y = sum(y) / len(y)
            
            numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
            sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(len(x)))
            sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(len(y)))
            
            denominator = (sum_sq_x * sum_sq_y) ** 0.5
            if denominator == 0:
                return [[1, 0], [0, 1]]
            
            corr = numerator / denominator
            return [[1, corr], [corr, 1]]
        
        @staticmethod
        def isnan(x):
            return x != x

logger = logging.getLogger(__name__)

@dataclass
class PredictionRecord:
    """Record of a prediction made by the system"""
    prediction_id: str
    player_id: int
    gameweek: int
    prediction_type: str  # 'points', 'transfer_value', 'captain_score'
    predicted_value: float
    actual_value: Optional[float] = None
    confidence: float = 0.5  # 0-1 scale
    factors_used: Dict = None  # What factors influenced this prediction
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.factors_used is None:
            self.factors_used = {}

@dataclass
class LearningInsight:
    """Insight gained from prediction analysis"""
    factor_name: str
    importance_score: float  # How important this factor is for predictions
    accuracy_impact: float  # How much this factor improves accuracy
    sample_size: int
    confidence_level: float

class LearningEngine:
    """Machine learning system that improves predictions over time"""
    
    def __init__(self, data_file: str = "prediction_history.json"):
        self.data_file = data_file
        self.predictions: List[PredictionRecord] = []
        self.factor_weights: Dict[str, float] = {
            'form_weight': 0.30,
            'value_weight': 0.25,
            'minutes_weight': 0.20,
            'recent_weight': 0.15,
            'bonus_weight': 0.10,
            'fixture_difficulty_weight': 0.15,
            'injury_risk_weight': 0.10
        }
        self.load_prediction_history()
    
    def record_prediction(self, prediction: PredictionRecord):
        """Record a new prediction"""
        self.predictions.append(prediction)
        self._save_predictions()
        logger.info(f"Recorded prediction {prediction.prediction_id} for player {prediction.player_id}")
    
    def update_actual_result(self, prediction_id: str, actual_value: float):
        """Update a prediction with the actual result"""
        for pred in self.predictions:
            if pred.prediction_id == prediction_id:
                pred.actual_value = actual_value
                self._save_predictions()
                logger.info(f"Updated prediction {prediction_id} with actual value {actual_value}")
                return True
        return False
    
    def analyze_prediction_accuracy(self, gameweeks_back: int = 10) -> Dict:
        """Analyze how accurate recent predictions have been"""
        cutoff_date = datetime.now() - timedelta(weeks=gameweeks_back)
        recent_predictions = [
            p for p in self.predictions 
            if p.actual_value is not None and p.timestamp >= cutoff_date
        ]
        
        if not recent_predictions:
            return {"error": "No completed predictions to analyze"}
        
        # Calculate overall accuracy metrics
        errors = []
        absolute_errors = []
        
        for pred in recent_predictions:
            error = pred.actual_value - pred.predicted_value
            errors.append(error)
            absolute_errors.append(abs(error))
        
        accuracy_metrics = {
            'total_predictions': len(recent_predictions),
            'mean_error': np.mean(errors),
            'mean_absolute_error': np.mean(absolute_errors),
            'accuracy_score': max(0, 1 - (np.mean(absolute_errors) / 10)),  # Normalize to 0-1
            'prediction_types': {}
        }
        
        # Analyze by prediction type
        prediction_types = set(p.prediction_type for p in recent_predictions)
        for pred_type in prediction_types:
            type_predictions = [p for p in recent_predictions if p.prediction_type == pred_type]
            type_errors = [abs(p.actual_value - p.predicted_value) for p in type_predictions]
            
            accuracy_metrics['prediction_types'][pred_type] = {
                'count': len(type_predictions),
                'mean_absolute_error': np.mean(type_errors),
                'accuracy_score': max(0, 1 - (np.mean(type_errors) / 10))
            }
        
        return accuracy_metrics
    
    def get_learning_insights(self) -> List[LearningInsight]:
        """Analyze which factors most impact prediction accuracy"""
        insights = []
        
        completed_predictions = [p for p in self.predictions if p.actual_value is not None]
        
        if len(completed_predictions) < 10:
            return insights
        
        # Analyze each factor's impact on accuracy
        for factor_name in ['form', 'value_per_point', 'minutes', 'fixture_difficulty']:
            factor_predictions = [
                p for p in completed_predictions 
                if factor_name in p.factors_used
            ]
            
            if len(factor_predictions) < 5:
                continue
            
            # Calculate correlation between factor value and prediction accuracy
            factor_values = [p.factors_used[factor_name] for p in factor_predictions]
            prediction_errors = [abs(p.actual_value - p.predicted_value) for p in factor_predictions]
            
            # Simple correlation analysis
            if len(set(factor_values)) > 1:  # Avoid division by zero
                correlation = np.corrcoef(factor_values, prediction_errors)[0, 1]
                importance_score = abs(correlation) if not np.isnan(correlation) else 0
                
                insights.append(LearningInsight(
                    factor_name=factor_name,
                    importance_score=importance_score,
                    accuracy_impact=1 - np.mean(prediction_errors) / 10,  # Normalize
                    sample_size=len(factor_predictions),
                    confidence_level=min(len(factor_predictions) / 50, 1.0)  # More samples = higher confidence
                ))
        
        return sorted(insights, key=lambda x: x.importance_score, reverse=True)
    
    def update_factor_weights(self) -> Dict[str, float]:
        """Update factor weights based on learning insights"""
        insights = self.get_learning_insights()
        
        if not insights:
            return self.factor_weights
        
        # Gradually adjust weights based on insights
        learning_rate = 0.1  # How quickly to adapt
        
        for insight in insights:
            if insight.confidence_level > 0.3:  # Only adjust if we have enough data
                current_weight = self.factor_weights.get(f"{insight.factor_name}_weight", 0.1)
                
                if insight.accuracy_impact > 0.7:  # High accuracy factor
                    new_weight = current_weight + (learning_rate * insight.importance_score)
                else:  # Low accuracy factor
                    new_weight = current_weight - (learning_rate * insight.importance_score * 0.5)
                
                self.factor_weights[f"{insight.factor_name}_weight"] = max(0.05, min(0.5, new_weight))
        
        # Normalize weights to sum to 1.0
        total_weight = sum(self.factor_weights.values())
        if total_weight > 0:
            self.factor_weights = {k: v / total_weight for k, v in self.factor_weights.items()}
        
        logger.info("Updated factor weights based on learning insights")
        return self.factor_weights
    
    def get_prediction_confidence(self, player_id: int, prediction_type: str) -> float:
        """Calculate confidence for a new prediction based on historical accuracy"""
        player_predictions = [
            p for p in self.predictions 
            if p.player_id == player_id and p.prediction_type == prediction_type and p.actual_value is not None
        ]
        
        if len(player_predictions) < 3:
            return 0.5  # Default confidence
        
        # Calculate accuracy for this specific player/prediction type
        recent_predictions = player_predictions[-10:]  # Last 10 predictions
        errors = [abs(p.actual_value - p.predicted_value) for p in recent_predictions]
        avg_error = np.mean(errors)
        
        # Convert error to confidence (lower error = higher confidence)
        confidence = max(0.1, min(0.95, 1 - (avg_error / 15)))
        
        return confidence
    
    def generate_learning_report(self) -> Dict:
        """Generate a comprehensive learning report"""
        accuracy_metrics = self.analyze_prediction_accuracy()
        insights = self.get_learning_insights()
        
        report = {
            'summary': {
                'total_predictions_made': len(self.predictions),
                'completed_predictions': len([p for p in self.predictions if p.actual_value is not None]),
                'overall_accuracy': accuracy_metrics.get('accuracy_score', 0),
                'learning_confidence': min(len(self.predictions) / 100, 1.0)
            },
            'accuracy_metrics': accuracy_metrics,
            'top_insights': [
                {
                    'factor': insight.factor_name,
                    'importance': round(insight.importance_score, 3),
                    'accuracy_impact': round(insight.accuracy_impact, 3),
                    'confidence': round(insight.confidence_level, 3)
                }
                for insight in insights[:5]
            ],
            'current_weights': self.factor_weights,
            'recommendations': self._generate_recommendations(insights)
        }
        
        return report
    
    def _generate_recommendations(self, insights: List[LearningInsight]) -> List[str]:
        """Generate actionable recommendations based on insights"""
        recommendations = []
        
        if not insights:
            recommendations.append("Continue collecting data to generate insights")
            return recommendations
        
        # Identify strongest factors
        strong_factors = [i for i in insights if i.importance_score > 0.3 and i.confidence_level > 0.5]
        if strong_factors:
            recommendations.append(f"Focus on {strong_factors[0].factor_name} as it shows strongest prediction impact")
        
        # Identify weak factors
        weak_factors = [i for i in insights if i.accuracy_impact < 0.4 and i.confidence_level > 0.3]
        if weak_factors:
            recommendations.append(f"Review {weak_factors[0].factor_name} calculation - it may need adjustment")
        
        # Data collection recommendations
        total_predictions = len([p for p in self.predictions if p.actual_value is not None])
        if total_predictions < 50:
            recommendations.append("Collect more prediction data for improved learning insights")
        
        return recommendations
    
    def load_prediction_history(self):
        """Load prediction history from file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.predictions = [
                    PredictionRecord(**pred_data) for pred_data in data.get('predictions', [])
                ]
                self.factor_weights = data.get('factor_weights', self.factor_weights)
                logger.info(f"Loaded {len(self.predictions)} predictions from {self.data_file}")
        except FileNotFoundError:
            logger.info(f"No existing prediction history found at {self.data_file}")
        except Exception as e:
            logger.error(f"Error loading prediction history: {e}")
    
    def _save_predictions(self):
        """Save predictions to file"""
        try:
            data = {
                'predictions': [asdict(pred) for pred in self.predictions],
                'factor_weights': self.factor_weights,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Error saving predictions: {e}")

# Utility functions for integration
def create_prediction_id(player_id: int, gameweek: int, prediction_type: str) -> str:
    """Create a unique prediction ID"""
    return f"{prediction_type}_{player_id}_{gameweek}_{datetime.now().strftime('%Y%m%d')}"

def extract_prediction_factors(player_data, fixture_difficulty: float = 3.0) -> Dict:
    """Extract factors that influence predictions"""
    return {
        'form': player_data.get('form_float', 0),
        'value_per_point': player_data.get('value_per_point', 1),
        'minutes': player_data.get('minutes', 0),
        'fixture_difficulty': fixture_difficulty,
        'total_points': player_data.get('total_points', 0),
        'selected_by_percent': player_data.get('selected_by_percent', 0)
    }
