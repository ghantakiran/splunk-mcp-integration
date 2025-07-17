"""
Anomaly Detection System for Splunk MCP Integration

This module provides comprehensive anomaly detection capabilities for Splunk data,
including statistical, machine learning, and time series anomaly detection methods.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy import stats
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AnomalyResult:
    """Data class for anomaly detection results."""
    is_anomaly: bool
    score: float
    confidence: float
    method: str
    details: Dict[str, Any]
    timestamp: str

class AnomalyDetectionEngine:
    """
    Advanced anomaly detection engine for Splunk data analysis.
    Supports multiple detection methods and real-time anomaly scoring.
    """
    
    def __init__(self):
        self.models = {}
        self.thresholds = {}
        self.baseline_stats = {}
        self.detection_methods = [
            "statistical",
            "isolation_forest",
            "dbscan",
            "time_series",
            "behavioral"
        ]
        
    async def detect_anomalies(self, data: List[Dict[str, Any]], 
                             method: str = "auto",
                             sensitivity: float = 0.95) -> Dict[str, Any]:
        """
        Detect anomalies in data using specified or automatic method selection.
        
        Args:
            data: Data points to analyze
            method: Detection method ('auto', 'statistical', 'isolation_forest', etc.)
            sensitivity: Sensitivity threshold (0.0 to 1.0)
            
        Returns:
            Dictionary containing anomaly detection results
        """
        try:
            if not data:
                return {"error": "No data provided for anomaly detection"}
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Auto-select method based on data characteristics
            if method == "auto":
                method = self._select_optimal_method(df)
            
            # Apply selected detection method
            if method == "statistical":
                results = await self._statistical_anomaly_detection(df, sensitivity)
            elif method == "isolation_forest":
                results = await self._isolation_forest_detection(df, sensitivity)
            elif method == "dbscan":
                results = await self._dbscan_anomaly_detection(df, sensitivity)
            elif method == "time_series":
                results = await self._time_series_anomaly_detection(df, sensitivity)
            elif method == "behavioral":
                results = await self._behavioral_anomaly_detection(df, sensitivity)
            else:
                return {"error": f"Unknown detection method: {method}"}
            
            # Enhance results with additional context
            enhanced_results = self._enhance_anomaly_results(results, df, method)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {str(e)}")
            return {"error": f"Anomaly detection failed: {str(e)}"}
    
    async def real_time_anomaly_scoring(self, current_data: Dict[str, Any], 
                                      historical_data: List[Dict[str, Any]],
                                      field: str = "value") -> Dict[str, Any]:
        """
        Real-time anomaly scoring for streaming data.
        
        Args:
            current_data: Current data point
            historical_data: Historical baseline data
            field: Field to analyze for anomalies
            
        Returns:
            Dictionary containing real-time anomaly score
        """
        try:
            if not historical_data:
                return {"error": "No historical data provided for baseline"}
            
            # Extract historical values
            historical_values = [item[field] for item in historical_data if field in item]
            
            if len(historical_values) < 10:
                return {"error": "Insufficient historical data for baseline"}
            
            current_value = current_data.get(field)
            if current_value is None:
                return {"error": f"Field '{field}' not found in current data"}
            
            # Calculate baseline statistics
            baseline_mean = np.mean(historical_values)
            baseline_std = np.std(historical_values)
            baseline_median = np.median(historical_values)
            
            # Z-score based anomaly scoring
            z_score = abs(current_value - baseline_mean) / baseline_std if baseline_std > 0 else 0
            
            # Percentile-based scoring
            percentile_score = stats.percentileofscore(historical_values, current_value)
            percentile_anomaly = min(percentile_score, 100 - percentile_score)
            
            # Modified Z-score (more robust)
            median_absolute_deviation = np.median(np.abs(np.array(historical_values) - baseline_median))
            modified_z_score = 0.6745 * (current_value - baseline_median) / median_absolute_deviation if median_absolute_deviation > 0 else 0
            
            # Combine scores
            anomaly_score = max(z_score / 3, (100 - percentile_anomaly) / 100, abs(modified_z_score) / 3.5)
            anomaly_score = min(anomaly_score, 1.0)  # Cap at 1.0
            
            # Determine if anomaly
            is_anomaly = anomaly_score > 0.7  # Threshold for anomaly
            
            return {
                "is_anomaly": is_anomaly,
                "anomaly_score": float(anomaly_score),
                "confidence": float(min(len(historical_values) / 100, 1.0)),
                "current_value": current_value,
                "baseline_stats": {
                    "mean": baseline_mean,
                    "std": baseline_std,
                    "median": baseline_median
                },
                "scoring_details": {
                    "z_score": float(z_score),
                    "percentile_score": float(percentile_score),
                    "modified_z_score": float(abs(modified_z_score))
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in real-time anomaly scoring: {str(e)}")
            return {"error": f"Real-time anomaly scoring failed: {str(e)}"}
    
    async def detect_security_anomalies(self, security_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Specialized anomaly detection for security events.
        
        Args:
            security_data: Security event data
            
        Returns:
            Dictionary containing security anomaly results
        """
        try:
            if not security_data:
                return {"error": "No security data provided"}
            
            df = pd.DataFrame(security_data)
            
            # Security-specific anomaly patterns
            anomalies = {
                "failed_login_spikes": self._detect_failed_login_spikes(df),
                "unusual_user_behavior": self._detect_unusual_user_behavior(df),
                "suspicious_ip_activity": self._detect_suspicious_ip_activity(df),
                "privilege_escalation": self._detect_privilege_escalation(df),
                "data_exfiltration": self._detect_data_exfiltration_patterns(df)
            }
            
            # Calculate overall security risk score
            risk_score = self._calculate_security_risk_score(anomalies)
            
            return {
                "security_anomalies": anomalies,
                "overall_risk_score": risk_score,
                "recommendations": self._generate_security_recommendations(anomalies),
                "analysis_timestamp": datetime.now().isoformat(),
                "data_points_analyzed": len(df)
            }
            
        except Exception as e:
            logger.error(f"Error in security anomaly detection: {str(e)}")
            return {"error": f"Security anomaly detection failed: {str(e)}"}
    
    async def detect_performance_anomalies(self, performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect performance anomalies in system metrics.
        
        Args:
            performance_data: Performance metrics data
            
        Returns:
            Dictionary containing performance anomaly results
        """
        try:
            if not performance_data:
                return {"error": "No performance data provided"}
            
            df = pd.DataFrame(performance_data)
            
            # Performance-specific anomaly detection
            anomalies = {
                "cpu_anomalies": self._detect_cpu_anomalies(df),
                "memory_anomalies": self._detect_memory_anomalies(df),
                "disk_anomalies": self._detect_disk_anomalies(df),
                "network_anomalies": self._detect_network_anomalies(df),
                "response_time_anomalies": self._detect_response_time_anomalies(df)
            }
            
            # Calculate performance health score
            health_score = self._calculate_performance_health_score(anomalies)
            
            return {
                "performance_anomalies": anomalies,
                "health_score": health_score,
                "recommendations": self._generate_performance_recommendations(anomalies),
                "analysis_timestamp": datetime.now().isoformat(),
                "data_points_analyzed": len(df)
            }
            
        except Exception as e:
            logger.error(f"Error in performance anomaly detection: {str(e)}")
            return {"error": f"Performance anomaly detection failed: {str(e)}"}
    
    def _select_optimal_method(self, df: pd.DataFrame) -> str:
        """Select optimal detection method based on data characteristics."""
        data_size = len(df)
        num_features = len(df.columns)
        
        # Check if time series data
        has_time_field = any(col in df.columns for col in ['_time', 'timestamp', 'time'])
        
        if has_time_field and data_size > 50:
            return "time_series"
        elif data_size > 100 and num_features > 3:
            return "isolation_forest"
        elif data_size > 20:
            return "statistical"
        else:
            return "statistical"
    
    async def _statistical_anomaly_detection(self, df: pd.DataFrame, sensitivity: float) -> List[AnomalyResult]:
        """Statistical anomaly detection using z-score and IQR methods."""
        results = []
        
        for column in df.select_dtypes(include=[np.number]).columns:
            values = df[column].dropna()
            
            if len(values) < 10:
                continue
            
            # Z-score method
            z_scores = np.abs(stats.zscore(values))
            threshold = stats.norm.ppf(sensitivity)
            
            # IQR method
            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            for idx, (value, z_score) in enumerate(zip(values, z_scores)):
                is_anomaly_zscore = z_score > threshold
                is_anomaly_iqr = value < lower_bound or value > upper_bound
                
                is_anomaly = is_anomaly_zscore or is_anomaly_iqr
                
                if is_anomaly:
                    results.append(AnomalyResult(
                        is_anomaly=True,
                        score=float(z_score),
                        confidence=0.8,
                        method="statistical",
                        details={
                            "column": column,
                            "value": float(value),
                            "z_score": float(z_score),
                            "iqr_bounds": [float(lower_bound), float(upper_bound)]
                        },
                        timestamp=datetime.now().isoformat()
                    ))
        
        return results
    
    async def _isolation_forest_detection(self, df: pd.DataFrame, sensitivity: float) -> List[AnomalyResult]:
        """Isolation Forest anomaly detection."""
        results = []
        
        # Select numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) == 0:
            return results
        
        # Prepare data
        X = df[numeric_cols].fillna(0)
        
        if len(X) < 10:
            return results
        
        # Scale data
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train Isolation Forest
        contamination = 1 - sensitivity
        iso_forest = IsolationForest(contamination=contamination, random_state=42)
        anomaly_labels = iso_forest.fit_predict(X_scaled)
        anomaly_scores = iso_forest.decision_function(X_scaled)
        
        for idx, (label, score) in enumerate(zip(anomaly_labels, anomaly_scores)):
            if label == -1:  # Anomaly
                results.append(AnomalyResult(
                    is_anomaly=True,
                    score=float(abs(score)),
                    confidence=0.85,
                    method="isolation_forest",
                    details={
                        "data_point": df.iloc[idx].to_dict(),
                        "isolation_score": float(score)
                    },
                    timestamp=datetime.now().isoformat()
                ))
        
        return results
    
    async def _dbscan_anomaly_detection(self, df: pd.DataFrame, sensitivity: float) -> List[AnomalyResult]:
        """DBSCAN clustering-based anomaly detection."""
        results = []
        
        # Select numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) == 0:
            return results
        
        # Prepare data
        X = df[numeric_cols].fillna(0)
        
        if len(X) < 10:
            return results
        
        # Scale data
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Apply DBSCAN
        eps = 0.3 * (2 - sensitivity)  # Adjust eps based on sensitivity
        dbscan = DBSCAN(eps=eps, min_samples=max(2, int(len(X) * 0.05)))
        cluster_labels = dbscan.fit_predict(X_scaled)
        
        # Points with label -1 are anomalies
        for idx, label in enumerate(cluster_labels):
            if label == -1:
                results.append(AnomalyResult(
                    is_anomaly=True,
                    score=1.0,
                    confidence=0.7,
                    method="dbscan",
                    details={
                        "data_point": df.iloc[idx].to_dict(),
                        "cluster_label": int(label)
                    },
                    timestamp=datetime.now().isoformat()
                ))
        
        return results
    
    async def _time_series_anomaly_detection(self, df: pd.DataFrame, sensitivity: float) -> List[AnomalyResult]:
        """Time series specific anomaly detection."""
        results = []
        
        # Find time column
        time_col = None
        for col in ['_time', 'timestamp', 'time']:
            if col in df.columns:
                time_col = col
                break
        
        if time_col is None:
            return results
        
        # Sort by time
        df = df.sort_values(time_col)
        
        # Detect anomalies in each numeric column
        for col in df.select_dtypes(include=[np.number]).columns:
            if col == time_col:
                continue
            
            values = df[col].dropna()
            
            if len(values) < 20:
                continue
            
            # Calculate moving average and standard deviation
            window_size = min(10, len(values) // 4)
            moving_avg = values.rolling(window=window_size).mean()
            moving_std = values.rolling(window=window_size).std()
            
            # Detect anomalies
            threshold = stats.norm.ppf(sensitivity)
            
            for idx, (value, avg, std) in enumerate(zip(values, moving_avg, moving_std)):
                if pd.isna(avg) or pd.isna(std) or std == 0:
                    continue
                
                z_score = abs(value - avg) / std
                
                if z_score > threshold:
                    results.append(AnomalyResult(
                        is_anomaly=True,
                        score=float(z_score),
                        confidence=0.75,
                        method="time_series",
                        details={
                            "column": col,
                            "value": float(value),
                            "moving_average": float(avg),
                            "moving_std": float(std),
                            "z_score": float(z_score)
                        },
                        timestamp=datetime.now().isoformat()
                    ))
        
        return results
    
    async def _behavioral_anomaly_detection(self, df: pd.DataFrame, sensitivity: float) -> List[AnomalyResult]:
        """Behavioral anomaly detection for user/system behavior patterns."""
        results = []
        
        # Look for behavioral patterns
        behavior_columns = ['user', 'src_ip', 'dest_ip', 'action', 'bytes']
        available_columns = [col for col in behavior_columns if col in df.columns]
        
        if not available_columns:
            return results
        
        # Analyze behavioral patterns
        for col in available_columns:
            if df[col].dtype == 'object':
                # Categorical behavior analysis
                value_counts = df[col].value_counts()
                total_count = len(df)
                
                for value, count in value_counts.items():
                    frequency = count / total_count
                    
                    # Detect unusual frequencies
                    if frequency > 0.8 or frequency < 0.01:
                        results.append(AnomalyResult(
                            is_anomaly=True,
                            score=float(1 - frequency if frequency > 0.8 else frequency),
                            confidence=0.6,
                            method="behavioral",
                            details={
                                "column": col,
                                "value": str(value),
                                "frequency": float(frequency),
                                "count": int(count),
                                "anomaly_type": "unusual_frequency"
                            },
                            timestamp=datetime.now().isoformat()
                        ))
        
        return results
    
    def _detect_failed_login_spikes(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect spikes in failed login attempts."""
        if 'action' not in df.columns:
            return {"detected": False, "reason": "No action column found"}
        
        failed_logins = df[df['action'].str.contains('failed', case=False, na=False)]
        
        if len(failed_logins) == 0:
            return {"detected": False, "reason": "No failed logins found"}
        
        # Time-based analysis
        if '_time' in df.columns:
            failed_logins['_time'] = pd.to_datetime(failed_logins['_time'])
            hourly_failures = failed_logins.groupby(failed_logins['_time'].dt.hour).size()
            
            # Detect spikes (simple threshold)
            avg_failures = hourly_failures.mean()
            spike_threshold = avg_failures * 3
            
            spikes = hourly_failures[hourly_failures > spike_threshold]
            
            return {
                "detected": len(spikes) > 0,
                "spike_hours": spikes.to_dict(),
                "total_failed_logins": len(failed_logins),
                "avg_per_hour": float(avg_failures)
            }
        
        return {"detected": False, "reason": "No time field found"}
    
    def _detect_unusual_user_behavior(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect unusual user behavior patterns."""
        if 'user' not in df.columns:
            return {"detected": False, "reason": "No user column found"}
        
        user_activity = df['user'].value_counts()
        
        # Detect users with unusual activity levels
        mean_activity = user_activity.mean()
        std_activity = user_activity.std()
        
        unusual_users = []
        for user, count in user_activity.items():
            z_score = abs(count - mean_activity) / std_activity if std_activity > 0 else 0
            if z_score > 2:  # Threshold for unusual
                unusual_users.append({
                    "user": user,
                    "activity_count": int(count),
                    "z_score": float(z_score)
                })
        
        return {
            "detected": len(unusual_users) > 0,
            "unusual_users": unusual_users,
            "total_users": len(user_activity)
        }
    
    def _detect_suspicious_ip_activity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect suspicious IP address activity."""
        ip_columns = ['src_ip', 'dest_ip', 'ip']
        available_ip_col = None
        
        for col in ip_columns:
            if col in df.columns:
                available_ip_col = col
                break
        
        if available_ip_col is None:
            return {"detected": False, "reason": "No IP column found"}
        
        ip_activity = df[available_ip_col].value_counts()
        
        # Detect IPs with unusual activity
        suspicious_ips = []
        total_requests = len(df)
        
        for ip, count in ip_activity.items():
            frequency = count / total_requests
            
            # High frequency might indicate scanning or attack
            if frequency > 0.1:  # More than 10% of traffic
                suspicious_ips.append({
                    "ip": ip,
                    "request_count": int(count),
                    "frequency": float(frequency)
                })
        
        return {
            "detected": len(suspicious_ips) > 0,
            "suspicious_ips": suspicious_ips,
            "total_unique_ips": len(ip_activity)
        }
    
    def _detect_privilege_escalation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect potential privilege escalation attempts."""
        if 'action' not in df.columns:
            return {"detected": False, "reason": "No action column found"}
        
        # Look for privilege-related actions
        privilege_keywords = ['sudo', 'admin', 'root', 'escalate', 'privilege']
        
        privilege_events = df[df['action'].str.contains('|'.join(privilege_keywords), case=False, na=False)]
        
        if len(privilege_events) == 0:
            return {"detected": False, "reason": "No privilege-related events found"}
        
        # Analyze patterns
        if 'user' in df.columns:
            user_privilege_activity = privilege_events['user'].value_counts()
            
            escalation_attempts = []
            for user, count in user_privilege_activity.items():
                if count > 5:  # Threshold for suspicious activity
                    escalation_attempts.append({
                        "user": user,
                        "attempts": int(count)
                    })
            
            return {
                "detected": len(escalation_attempts) > 0,
                "escalation_attempts": escalation_attempts,
                "total_privilege_events": len(privilege_events)
            }
        
        return {
            "detected": True,
            "total_privilege_events": len(privilege_events)
        }
    
    def _detect_data_exfiltration_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect patterns indicating potential data exfiltration."""
        if 'bytes' not in df.columns:
            return {"detected": False, "reason": "No bytes column found"}
        
        # Look for unusual data transfer patterns
        bytes_data = df['bytes'].dropna()
        
        if len(bytes_data) == 0:
            return {"detected": False, "reason": "No bytes data found"}
        
        # Statistical analysis of data transfer
        mean_bytes = bytes_data.mean()
        std_bytes = bytes_data.std()
        
        # Detect unusually large transfers
        large_transfers = bytes_data[bytes_data > mean_bytes + 3 * std_bytes]
        
        exfiltration_indicators = []
        if len(large_transfers) > 0:
            for idx, bytes_val in large_transfers.items():
                exfiltration_indicators.append({
                    "index": int(idx),
                    "bytes": float(bytes_val),
                    "z_score": float((bytes_val - mean_bytes) / std_bytes)
                })
        
        return {
            "detected": len(exfiltration_indicators) > 0,
            "indicators": exfiltration_indicators,
            "total_transfers": len(bytes_data),
            "avg_bytes": float(mean_bytes)
        }
    
    def _detect_cpu_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect CPU usage anomalies."""
        if 'cpu_usage' not in df.columns:
            return {"detected": False, "reason": "No CPU usage data found"}
        
        cpu_data = df['cpu_usage'].dropna()
        
        if len(cpu_data) == 0:
            return {"detected": False, "reason": "No CPU data found"}
        
        # Detect high CPU usage
        high_cpu_threshold = 80  # 80% CPU usage threshold
        high_cpu_events = cpu_data[cpu_data > high_cpu_threshold]
        
        return {
            "detected": len(high_cpu_events) > 0,
            "high_cpu_events": len(high_cpu_events),
            "max_cpu_usage": float(cpu_data.max()),
            "avg_cpu_usage": float(cpu_data.mean())
        }
    
    def _detect_memory_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect memory usage anomalies."""
        if 'memory_usage' not in df.columns:
            return {"detected": False, "reason": "No memory usage data found"}
        
        memory_data = df['memory_usage'].dropna()
        
        if len(memory_data) == 0:
            return {"detected": False, "reason": "No memory data found"}
        
        # Detect high memory usage
        high_memory_threshold = 85  # 85% memory usage threshold
        high_memory_events = memory_data[memory_data > high_memory_threshold]
        
        return {
            "detected": len(high_memory_events) > 0,
            "high_memory_events": len(high_memory_events),
            "max_memory_usage": float(memory_data.max()),
            "avg_memory_usage": float(memory_data.mean())
        }
    
    def _detect_disk_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect disk usage anomalies."""
        if 'disk_usage' not in df.columns:
            return {"detected": False, "reason": "No disk usage data found"}
        
        disk_data = df['disk_usage'].dropna()
        
        if len(disk_data) == 0:
            return {"detected": False, "reason": "No disk data found"}
        
        # Detect high disk usage
        high_disk_threshold = 90  # 90% disk usage threshold
        high_disk_events = disk_data[disk_data > high_disk_threshold]
        
        return {
            "detected": len(high_disk_events) > 0,
            "high_disk_events": len(high_disk_events),
            "max_disk_usage": float(disk_data.max()),
            "avg_disk_usage": float(disk_data.mean())
        }
    
    def _detect_network_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect network traffic anomalies."""
        if 'network_traffic' not in df.columns:
            return {"detected": False, "reason": "No network traffic data found"}
        
        network_data = df['network_traffic'].dropna()
        
        if len(network_data) == 0:
            return {"detected": False, "reason": "No network data found"}
        
        # Statistical analysis
        mean_traffic = network_data.mean()
        std_traffic = network_data.std()
        
        # Detect traffic spikes
        traffic_spikes = network_data[network_data > mean_traffic + 3 * std_traffic]
        
        return {
            "detected": len(traffic_spikes) > 0,
            "traffic_spikes": len(traffic_spikes),
            "max_traffic": float(network_data.max()),
            "avg_traffic": float(mean_traffic)
        }
    
    def _detect_response_time_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect response time anomalies."""
        if 'response_time' not in df.columns:
            return {"detected": False, "reason": "No response time data found"}
        
        response_data = df['response_time'].dropna()
        
        if len(response_data) == 0:
            return {"detected": False, "reason": "No response time data found"}
        
        # Detect slow responses
        slow_response_threshold = response_data.quantile(0.95)  # 95th percentile
        slow_responses = response_data[response_data > slow_response_threshold]
        
        return {
            "detected": len(slow_responses) > 0,
            "slow_responses": len(slow_responses),
            "max_response_time": float(response_data.max()),
            "avg_response_time": float(response_data.mean()),
            "threshold": float(slow_response_threshold)
        }
    
    def _calculate_security_risk_score(self, anomalies: Dict[str, Any]) -> float:
        """Calculate overall security risk score."""
        risk_weights = {
            "failed_login_spikes": 0.3,
            "unusual_user_behavior": 0.2,
            "suspicious_ip_activity": 0.2,
            "privilege_escalation": 0.2,
            "data_exfiltration": 0.1
        }
        
        total_risk = 0.0
        for anomaly_type, weight in risk_weights.items():
            if anomaly_type in anomalies and anomalies[anomaly_type].get("detected", False):
                total_risk += weight
        
        return total_risk
    
    def _calculate_performance_health_score(self, anomalies: Dict[str, Any]) -> float:
        """Calculate overall performance health score."""
        health_weights = {
            "cpu_anomalies": 0.25,
            "memory_anomalies": 0.25,
            "disk_anomalies": 0.2,
            "network_anomalies": 0.15,
            "response_time_anomalies": 0.15
        }
        
        total_health_loss = 0.0
        for anomaly_type, weight in health_weights.items():
            if anomaly_type in anomalies and anomalies[anomaly_type].get("detected", False):
                total_health_loss += weight
        
        return 1.0 - total_health_loss
    
    def _generate_security_recommendations(self, anomalies: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on detected anomalies."""
        recommendations = []
        
        if anomalies.get("failed_login_spikes", {}).get("detected", False):
            recommendations.append("Implement account lockout policies to prevent brute force attacks")
            recommendations.append("Monitor and investigate failed login patterns")
        
        if anomalies.get("unusual_user_behavior", {}).get("detected", False):
            recommendations.append("Review user access permissions and behavior patterns")
            recommendations.append("Implement user behavior analytics (UBA) monitoring")
        
        if anomalies.get("suspicious_ip_activity", {}).get("detected", False):
            recommendations.append("Implement IP-based access controls and monitoring")
            recommendations.append("Consider blocking or throttling suspicious IP addresses")
        
        if anomalies.get("privilege_escalation", {}).get("detected", False):
            recommendations.append("Review and audit privileged access controls")
            recommendations.append("Implement just-in-time (JIT) access for elevated privileges")
        
        if anomalies.get("data_exfiltration", {}).get("detected", False):
            recommendations.append("Implement data loss prevention (DLP) controls")
            recommendations.append("Monitor and alert on unusual data transfer patterns")
        
        return recommendations
    
    def _generate_performance_recommendations(self, anomalies: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on detected anomalies."""
        recommendations = []
        
        if anomalies.get("cpu_anomalies", {}).get("detected", False):
            recommendations.append("Investigate high CPU usage and consider scaling resources")
            recommendations.append("Optimize application performance and resource utilization")
        
        if anomalies.get("memory_anomalies", {}).get("detected", False):
            recommendations.append("Monitor memory usage and consider increasing memory allocation")
            recommendations.append("Check for memory leaks in applications")
        
        if anomalies.get("disk_anomalies", {}).get("detected", False):
            recommendations.append("Monitor disk usage and consider cleanup or expansion")
            recommendations.append("Implement disk usage monitoring and alerting")
        
        if anomalies.get("network_anomalies", {}).get("detected", False):
            recommendations.append("Investigate network traffic patterns and bandwidth usage")
            recommendations.append("Consider network optimization or capacity planning")
        
        if anomalies.get("response_time_anomalies", {}).get("detected", False):
            recommendations.append("Optimize application response times and database queries")
            recommendations.append("Consider load balancing and caching strategies")
        
        return recommendations
    
    def _enhance_anomaly_results(self, results: List[AnomalyResult], 
                                df: pd.DataFrame, method: str) -> Dict[str, Any]:
        """Enhance anomaly results with additional context."""
        anomaly_count = len(results)
        total_points = len(df)
        
        # Calculate severity distribution
        severity_distribution = {"low": 0, "medium": 0, "high": 0}
        for result in results:
            if result.score < 0.3:
                severity_distribution["low"] += 1
            elif result.score < 0.7:
                severity_distribution["medium"] += 1
            else:
                severity_distribution["high"] += 1
        
        return {
            "anomalies_detected": anomaly_count,
            "total_data_points": total_points,
            "anomaly_rate": anomaly_count / total_points if total_points > 0 else 0,
            "detection_method": method,
            "severity_distribution": severity_distribution,
            "anomaly_details": [
                {
                    "is_anomaly": result.is_anomaly,
                    "score": result.score,
                    "confidence": result.confidence,
                    "method": result.method,
                    "details": result.details,
                    "timestamp": result.timestamp
                }
                for result in results
            ],
            "analysis_timestamp": datetime.now().isoformat()
        }

# Global instance
anomaly_detector = AnomalyDetectionEngine()