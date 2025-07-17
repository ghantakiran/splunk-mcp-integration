"""
Predictive Analytics Engine for Splunk MCP Integration

This module provides predictive analytics capabilities for Splunk data,
including trend analysis, forecasting, and predictive modeling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from scipy import stats
import json

logger = logging.getLogger(__name__)

class PredictiveAnalyticsEngine:
    """
    Advanced predictive analytics engine for Splunk data analysis.
    Provides forecasting, trend analysis, and predictive modeling capabilities.
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.model_metadata = {}
        
    async def analyze_trends(self, data: List[Dict[str, Any]], 
                           time_field: str = "_time", 
                           value_field: str = "value") -> Dict[str, Any]:
        """
        Analyze trends in time series data.
        
        Args:
            data: List of data points with time and value fields
            time_field: Field name for time data
            value_field: Field name for value data
            
        Returns:
            Dictionary containing trend analysis results
        """
        try:
            if not data:
                return {"error": "No data provided for trend analysis"}
            
            # Convert to pandas DataFrame
            df = pd.DataFrame(data)
            
            # Ensure time field is datetime
            df[time_field] = pd.to_datetime(df[time_field])
            df = df.sort_values(time_field)
            
            # Basic trend analysis
            df['time_numeric'] = df[time_field].astype(np.int64) // 10**9
            
            # Linear regression for trend
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                df['time_numeric'], df[value_field]
            )
            
            # Trend classification
            trend_type = "stable"
            if abs(slope) > std_err * 2:  # Significant trend
                trend_type = "increasing" if slope > 0 else "decreasing"
            
            # Calculate moving averages
            df['ma_7'] = df[value_field].rolling(window=min(7, len(df))).mean()
            df['ma_30'] = df[value_field].rolling(window=min(30, len(df))).mean()
            
            # Volatility analysis
            volatility = df[value_field].std() / df[value_field].mean() if df[value_field].mean() != 0 else 0
            
            # Seasonality detection (basic)
            seasonality_score = self._detect_seasonality(df[value_field])
            
            return {
                "trend_type": trend_type,
                "slope": slope,
                "r_squared": r_value**2,
                "p_value": p_value,
                "volatility": volatility,
                "seasonality_score": seasonality_score,
                "moving_averages": {
                    "7_day": df['ma_7'].iloc[-1] if len(df) >= 7 else df[value_field].mean(),
                    "30_day": df['ma_30'].iloc[-1] if len(df) >= 30 else df[value_field].mean()
                },
                "data_points": len(df),
                "time_range": {
                    "start": df[time_field].min().isoformat(),
                    "end": df[time_field].max().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {str(e)}")
            return {"error": f"Trend analysis failed: {str(e)}"}
    
    async def forecast_values(self, data: List[Dict[str, Any]], 
                            time_field: str = "_time", 
                            value_field: str = "value",
                            forecast_periods: int = 10,
                            model_type: str = "linear") -> Dict[str, Any]:
        """
        Generate forecasts for time series data.
        
        Args:
            data: Historical data points
            time_field: Field name for time data
            value_field: Field name for value data
            forecast_periods: Number of periods to forecast
            model_type: Type of model to use ('linear', 'random_forest')
            
        Returns:
            Dictionary containing forecast results
        """
        try:
            if not data or len(data) < 3:
                return {"error": "Insufficient data for forecasting (minimum 3 points required)"}
            
            # Prepare data
            df = pd.DataFrame(data)
            df[time_field] = pd.to_datetime(df[time_field])
            df = df.sort_values(time_field).reset_index(drop=True)
            
            # Feature engineering
            df['time_numeric'] = df[time_field].astype(np.int64) // 10**9
            df['hour'] = df[time_field].dt.hour
            df['day_of_week'] = df[time_field].dt.dayofweek
            df['month'] = df[time_field].dt.month
            
            # Prepare features
            features = ['time_numeric', 'hour', 'day_of_week', 'month']
            X = df[features]
            y = df[value_field]
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train model
            if model_type == "random_forest":
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            else:
                model = LinearRegression()
            
            model.fit(X_scaled, y)
            
            # Generate future timestamps
            last_time = df[time_field].iloc[-1]
            time_diff = df[time_field].diff().median()
            future_times = [last_time + (i + 1) * time_diff for i in range(forecast_periods)]
            
            # Prepare future features
            future_features = []
            for future_time in future_times:
                future_features.append([
                    future_time.timestamp(),
                    future_time.hour,
                    future_time.weekday(),
                    future_time.month
                ])
            
            future_X = np.array(future_features)
            future_X_scaled = scaler.transform(future_X)
            
            # Make predictions
            predictions = model.predict(future_X_scaled)
            
            # Calculate prediction intervals (simple approach)
            train_predictions = model.predict(X_scaled)
            mse = mean_squared_error(y, train_predictions)
            std_error = np.sqrt(mse)
            
            # Model evaluation
            r2 = r2_score(y, train_predictions)
            
            # Prepare results
            forecasts = []
            for i, (time, pred) in enumerate(zip(future_times, predictions)):
                confidence_interval = 1.96 * std_error  # 95% confidence interval
                forecasts.append({
                    "time": time.isoformat(),
                    "predicted_value": float(pred),
                    "upper_bound": float(pred + confidence_interval),
                    "lower_bound": float(pred - confidence_interval),
                    "confidence_level": 0.95
                })
            
            return {
                "forecasts": forecasts,
                "model_type": model_type,
                "model_performance": {
                    "r_squared": r2,
                    "mse": mse,
                    "rmse": np.sqrt(mse)
                },
                "forecast_periods": forecast_periods,
                "training_data_points": len(df)
            }
            
        except Exception as e:
            logger.error(f"Error in forecasting: {str(e)}")
            return {"error": f"Forecasting failed: {str(e)}"}
    
    async def detect_patterns(self, data: List[Dict[str, Any]], 
                            field: str = "value") -> Dict[str, Any]:
        """
        Detect patterns in data using statistical and ML methods.
        
        Args:
            data: Data points to analyze
            field: Field name to analyze for patterns
            
        Returns:
            Dictionary containing pattern detection results
        """
        try:
            if not data:
                return {"error": "No data provided for pattern detection"}
            
            values = [float(item[field]) for item in data if field in item]
            
            if len(values) < 10:
                return {"error": "Insufficient data for pattern detection (minimum 10 points required)"}
            
            df = pd.DataFrame({'value': values})
            
            # Statistical patterns
            patterns = {
                "distribution": {
                    "mean": float(np.mean(values)),
                    "median": float(np.median(values)),
                    "std": float(np.std(values)),
                    "skewness": float(stats.skew(values)),
                    "kurtosis": float(stats.kurtosis(values))
                },
                "outliers": self._detect_outliers(values),
                "cyclic_patterns": self._detect_cycles(values),
                "change_points": self._detect_change_points(values)
            }
            
            # Frequency analysis
            patterns["frequency_analysis"] = self._analyze_frequencies(values)
            
            return {
                "patterns": patterns,
                "data_points": len(values),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in pattern detection: {str(e)}")
            return {"error": f"Pattern detection failed: {str(e)}"}
    
    async def predict_resource_usage(self, historical_data: List[Dict[str, Any]], 
                                   resource_type: str = "cpu",
                                   prediction_horizon: int = 24) -> Dict[str, Any]:
        """
        Predict resource usage based on historical data.
        
        Args:
            historical_data: Historical resource usage data
            resource_type: Type of resource (cpu, memory, disk, network)
            prediction_horizon: Hours ahead to predict
            
        Returns:
            Dictionary containing resource usage predictions
        """
        try:
            if not historical_data:
                return {"error": "No historical data provided"}
            
            # Convert to time series
            df = pd.DataFrame(historical_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # Feature engineering for resource prediction
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            df['is_business_hours'] = df['hour'].between(9, 17).astype(int)
            
            # Rolling statistics
            df['usage_ma'] = df['usage'].rolling(window=24).mean()
            df['usage_std'] = df['usage'].rolling(window=24).std()
            
            # Prepare features (drop NaN values)
            features = ['hour', 'day_of_week', 'is_weekend', 'is_business_hours', 'usage_ma', 'usage_std']
            df_clean = df.dropna()
            
            if len(df_clean) < 48:  # Need at least 48 hours of data
                return {"error": "Insufficient data for resource prediction"}
            
            X = df_clean[features]
            y = df_clean['usage']
            
            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
            
            # Generate predictions
            last_timestamp = df['timestamp'].iloc[-1]
            predictions = []
            
            for i in range(prediction_horizon):
                future_time = last_timestamp + timedelta(hours=i + 1)
                
                # Calculate features for prediction
                future_features = {
                    'hour': future_time.hour,
                    'day_of_week': future_time.weekday(),
                    'is_weekend': 1 if future_time.weekday() in [5, 6] else 0,
                    'is_business_hours': 1 if 9 <= future_time.hour <= 17 else 0,
                    'usage_ma': df['usage'].tail(24).mean(),
                    'usage_std': df['usage'].tail(24).std()
                }
                
                # Make prediction
                X_future = np.array([[future_features[f] for f in features]])
                predicted_usage = model.predict(X_future)[0]
                
                predictions.append({
                    "timestamp": future_time.isoformat(),
                    "predicted_usage": float(predicted_usage),
                    "resource_type": resource_type,
                    "confidence": float(model.score(X, y))
                })
            
            # Calculate usage categories
            usage_stats = df['usage'].describe()
            usage_categories = self._categorize_usage_predictions(predictions, usage_stats)
            
            return {
                "predictions": predictions,
                "usage_categories": usage_categories,
                "model_accuracy": float(model.score(X, y)),
                "prediction_horizon": prediction_horizon,
                "resource_type": resource_type,
                "historical_data_points": len(df)
            }
            
        except Exception as e:
            logger.error(f"Error in resource usage prediction: {str(e)}")
            return {"error": f"Resource usage prediction failed: {str(e)}"}
    
    def _detect_seasonality(self, values: pd.Series) -> float:
        """Detect seasonality in time series data."""
        if len(values) < 24:
            return 0.0
        
        # Simple seasonality detection using autocorrelation
        autocorr_1h = values.autocorr(lag=1) if len(values) > 1 else 0
        autocorr_24h = values.autocorr(lag=24) if len(values) > 24 else 0
        autocorr_168h = values.autocorr(lag=168) if len(values) > 168 else 0
        
        seasonality_score = max(abs(autocorr_1h), abs(autocorr_24h), abs(autocorr_168h))
        return float(seasonality_score)
    
    def _detect_outliers(self, values: List[float]) -> Dict[str, Any]:
        """Detect outliers using statistical methods."""
        if len(values) < 10:
            return {"method": "insufficient_data", "outliers": []}
        
        # IQR method
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = [i for i, v in enumerate(values) if v < lower_bound or v > upper_bound]
        
        return {
            "method": "iqr",
            "outlier_indices": outliers,
            "outlier_count": len(outliers),
            "outlier_percentage": len(outliers) / len(values) * 100,
            "bounds": {"lower": lower_bound, "upper": upper_bound}
        }
    
    def _detect_cycles(self, values: List[float]) -> Dict[str, Any]:
        """Detect cyclic patterns in data."""
        if len(values) < 20:
            return {"cycles_detected": False, "period": None}
        
        # Simple cycle detection using autocorrelation
        autocorr_values = []
        for lag in range(1, min(len(values) // 2, 100)):
            series = pd.Series(values)
            autocorr_values.append(series.autocorr(lag=lag))
        
        # Find peaks in autocorrelation
        peaks = []
        for i in range(1, len(autocorr_values) - 1):
            if (autocorr_values[i] > autocorr_values[i-1] and 
                autocorr_values[i] > autocorr_values[i+1] and 
                autocorr_values[i] > 0.3):
                peaks.append(i + 1)
        
        if peaks:
            dominant_period = peaks[0]
            return {
                "cycles_detected": True,
                "dominant_period": dominant_period,
                "all_periods": peaks,
                "max_autocorr": max(autocorr_values)
            }
        
        return {"cycles_detected": False, "period": None}
    
    def _detect_change_points(self, values: List[float]) -> List[int]:
        """Detect change points in time series."""
        if len(values) < 10:
            return []
        
        # Simple change point detection using sliding window
        change_points = []
        window_size = max(5, len(values) // 10)
        
        for i in range(window_size, len(values) - window_size):
            before = values[i - window_size:i]
            after = values[i:i + window_size]
            
            # Use t-test to detect significant changes
            if len(before) > 1 and len(after) > 1:
                t_stat, p_value = stats.ttest_ind(before, after)
                if p_value < 0.05:  # Significant change
                    change_points.append(i)
        
        return change_points
    
    def _analyze_frequencies(self, values: List[float]) -> Dict[str, Any]:
        """Analyze frequency characteristics of the data."""
        if len(values) < 10:
            return {"insufficient_data": True}
        
        # Basic frequency analysis
        unique_values = len(set(values))
        value_counts = pd.Series(values).value_counts()
        
        return {
            "unique_values": unique_values,
            "uniqueness_ratio": unique_values / len(values),
            "most_common_value": float(value_counts.index[0]),
            "most_common_frequency": int(value_counts.iloc[0]),
            "entropy": float(stats.entropy(value_counts))
        }
    
    def _categorize_usage_predictions(self, predictions: List[Dict], 
                                    usage_stats: pd.Series) -> Dict[str, Any]:
        """Categorize usage predictions into low, medium, high."""
        low_threshold = usage_stats['25%']
        high_threshold = usage_stats['75%']
        
        categories = {"low": 0, "medium": 0, "high": 0}
        
        for pred in predictions:
            usage = pred['predicted_usage']
            if usage < low_threshold:
                categories["low"] += 1
            elif usage > high_threshold:
                categories["high"] += 1
            else:
                categories["medium"] += 1
        
        return {
            "categories": categories,
            "thresholds": {
                "low": float(low_threshold),
                "high": float(high_threshold)
            },
            "total_predictions": len(predictions)
        }

# Global instance
predictive_analytics = PredictiveAnalyticsEngine()