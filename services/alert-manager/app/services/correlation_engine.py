"""
Alert correlation engine for intelligent alert grouping and noise reduction.
"""
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass

from ..core.logging import AlertLogger
from ..models.alert import AlertIncident


@dataclass
class CorrelationGroup:
    """Correlation group for related alerts."""
    id: str
    incidents: List[AlertIncident]
    correlation_type: str
    correlation_score: float
    created_at: datetime
    last_updated: datetime


class CorrelationEngine:
    """Engine for correlating and grouping related alerts."""
    
    def __init__(self):
        self.logger = AlertLogger("correlation_engine")
        
        # Correlation strategies
        self.correlation_strategies = [
            self._correlate_by_source,
            self._correlate_by_time_window,
            self._correlate_by_pattern,
            self._correlate_by_root_cause
        ]
        
        # Active correlation groups
        self.active_groups: Dict[str, CorrelationGroup] = {}
        
        # Configuration
        self.time_window_minutes = 15
        self.max_group_size = 20
        self.min_correlation_score = 0.5
    
    async def correlate_incident(self, incident: AlertIncident) -> Optional[str]:
        """Correlate a new incident with existing groups or create a new group."""
        try:
            # Check if incident should be correlated with existing groups
            best_group = await self._find_best_correlation_group(incident)
            
            if best_group:
                # Add to existing group
                best_group.incidents.append(incident)
                best_group.last_updated = datetime.utcnow()
                
                self.logger.info(
                    "Incident correlated to existing group",
                    incident_id=incident.id,
                    group_id=best_group.id,
                    group_size=len(best_group.incidents)
                )
                
                return best_group.id
            else:
                # Create new correlation group
                group_id = await self._create_correlation_group(incident)
                
                self.logger.info(
                    "New correlation group created",
                    incident_id=incident.id,
                    group_id=group_id
                )
                
                return group_id
                
        except Exception as e:
            self.logger.log_error("correlate_incident", str(e), {"incident_id": incident.id})
            return None
    
    async def _find_best_correlation_group(self, incident: AlertIncident) -> Optional[CorrelationGroup]:
        """Find the best correlation group for an incident."""
        best_group = None
        best_score = 0.0
        
        # Check against all active groups
        for group in self.active_groups.values():
            # Skip if group is too old or too large
            if self._is_group_expired(group) or len(group.incidents) >= self.max_group_size:
                continue
            
            # Calculate correlation score
            score = await self._calculate_correlation_score(incident, group)
            
            if score > best_score and score >= self.min_correlation_score:
                best_score = score
                best_group = group
        
        return best_group
    
    async def _calculate_correlation_score(self, incident: AlertIncident, group: CorrelationGroup) -> float:
        """Calculate correlation score between incident and group."""
        scores = []
        
        # Run all correlation strategies
        for strategy in self.correlation_strategies:
            try:
                score = await strategy(incident, group)
                if score > 0:
                    scores.append(score)
            except Exception as e:
                self.logger.log_error("correlation_strategy", str(e))
        
        # Return average score
        return sum(scores) / len(scores) if scores else 0.0
    
    async def _correlate_by_source(self, incident: AlertIncident, group: CorrelationGroup) -> float:
        """Correlate by source (same alert rule, host, etc.)."""
        if not group.incidents:
            return 0.0
        
        # Check if same rule
        if incident.rule_id == group.incidents[0].rule_id:
            return 0.8
        
        # Check if same trigger data source
        incident_sources = self._extract_sources(incident)
        group_sources = self._extract_sources_from_group(group)
        
        # Calculate overlap
        if incident_sources and group_sources:
            overlap = len(incident_sources.intersection(group_sources))
            total = len(incident_sources.union(group_sources))
            return overlap / total if total > 0 else 0.0
        
        return 0.0
    
    async def _correlate_by_time_window(self, incident: AlertIncident, group: CorrelationGroup) -> float:
        """Correlate by time proximity."""
        if not group.incidents:
            return 0.0
        
        # Find the most recent incident in the group
        latest_incident = max(group.incidents, key=lambda x: x.triggered_at)
        
        # Calculate time difference
        time_diff = abs((incident.triggered_at - latest_incident.triggered_at).total_seconds())
        window_seconds = self.time_window_minutes * 60
        
        # Score decreases linearly with time
        if time_diff <= window_seconds:
            return 1.0 - (time_diff / window_seconds)
        
        return 0.0
    
    async def _correlate_by_pattern(self, incident: AlertIncident, group: CorrelationGroup) -> float:
        """Correlate by similar patterns in trigger data."""
        if not group.incidents:
            return 0.0
        
        # Extract patterns from incident
        incident_patterns = self._extract_patterns(incident)
        
        # Check similarity with group patterns
        max_similarity = 0.0
        for group_incident in group.incidents:
            group_patterns = self._extract_patterns(group_incident)
            similarity = self._calculate_pattern_similarity(incident_patterns, group_patterns)
            max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    async def _correlate_by_root_cause(self, incident: AlertIncident, group: CorrelationGroup) -> float:
        """Correlate by potential root cause analysis."""
        if not group.incidents:
            return 0.0
        
        # Simple root cause correlation based on severity and type
        # In a real implementation, this would use more sophisticated analysis
        
        # Check if incidents are related by severity escalation
        if incident.severity == "critical":
            for group_incident in group.incidents:
                if group_incident.severity in ["high", "medium"]:
                    # Could be escalation of existing issue
                    return 0.6
        
        # Check for related error patterns
        incident_errors = self._extract_error_patterns(incident)
        for group_incident in group.incidents:
            group_errors = self._extract_error_patterns(group_incident)
            if incident_errors.intersection(group_errors):
                return 0.7
        
        return 0.0
    
    def _extract_sources(self, incident: AlertIncident) -> Set[str]:
        """Extract source identifiers from incident."""
        sources = set()
        
        # Add rule ID
        sources.add(f"rule:{incident.rule_id}")
        
        # Extract from trigger data
        if incident.trigger_data:
            for item in incident.trigger_data:
                if isinstance(item, dict):
                    if "host" in item:
                        sources.add(f"host:{item['host']}")
                    if "source" in item:
                        sources.add(f"source:{item['source']}")
                    if "index" in item:
                        sources.add(f"index:{item['index']}")
        
        return sources
    
    def _extract_sources_from_group(self, group: CorrelationGroup) -> Set[str]:
        """Extract all source identifiers from a correlation group."""
        all_sources = set()
        for incident in group.incidents:
            all_sources.update(self._extract_sources(incident))
        return all_sources
    
    def _extract_patterns(self, incident: AlertIncident) -> Set[str]:
        """Extract patterns from incident data."""
        patterns = set()
        
        # Extract from title and description
        if incident.title:
            patterns.add(f"title:{incident.title.lower()}")
        
        # Extract from trigger data
        if incident.trigger_data:
            for item in incident.trigger_data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, str):
                            patterns.add(f"{key}:{value.lower()}")
        
        return patterns
    
    def _extract_error_patterns(self, incident: AlertIncident) -> Set[str]:
        """Extract error patterns from incident."""
        patterns = set()
        
        # Look for common error patterns
        error_keywords = ["error", "exception", "failure", "timeout", "refused"]
        
        text_content = f"{incident.title} {incident.description}".lower()
        for keyword in error_keywords:
            if keyword in text_content:
                patterns.add(keyword)
        
        return patterns
    
    def _calculate_pattern_similarity(self, patterns1: Set[str], patterns2: Set[str]) -> float:
        """Calculate similarity between two pattern sets."""
        if not patterns1 or not patterns2:
            return 0.0
        
        overlap = len(patterns1.intersection(patterns2))
        total = len(patterns1.union(patterns2))
        
        return overlap / total if total > 0 else 0.0
    
    async def _create_correlation_group(self, incident: AlertIncident) -> str:
        """Create a new correlation group."""
        # Generate unique group ID
        group_id = self._generate_group_id(incident)
        
        # Create correlation group
        group = CorrelationGroup(
            id=group_id,
            incidents=[incident],
            correlation_type="initial",
            correlation_score=1.0,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow()
        )
        
        # Store in active groups
        self.active_groups[group_id] = group
        
        return group_id
    
    def _generate_group_id(self, incident: AlertIncident) -> str:
        """Generate unique group ID."""
        # Use combination of rule ID and timestamp
        content = f"{incident.rule_id}_{incident.triggered_at.isoformat()}"
        return f"group_{hashlib.md5(content.encode()).hexdigest()[:8]}"
    
    def _is_group_expired(self, group: CorrelationGroup) -> bool:
        """Check if correlation group has expired."""
        expiry_time = group.last_updated + timedelta(hours=24)
        return datetime.utcnow() > expiry_time
    
    async def cleanup_expired_groups(self):
        """Remove expired correlation groups."""
        expired_groups = [
            group_id for group_id, group in self.active_groups.items()
            if self._is_group_expired(group)
        ]
        
        for group_id in expired_groups:
            del self.active_groups[group_id]
            self.logger.info("Expired correlation group removed", group_id=group_id)
    
    async def get_correlation_group(self, group_id: str) -> Optional[CorrelationGroup]:
        """Get correlation group by ID."""
        return self.active_groups.get(group_id)
    
    async def get_group_statistics(self, group_id: str) -> Dict[str, Any]:
        """Get statistics for a correlation group."""
        group = self.active_groups.get(group_id)
        if not group:
            return {}
        
        # Calculate statistics
        severities = [incident.severity for incident in group.incidents]
        sources = self._extract_sources_from_group(group)
        
        return {
            "group_id": group_id,
            "incident_count": len(group.incidents),
            "correlation_type": group.correlation_type,
            "correlation_score": group.correlation_score,
            "created_at": group.created_at,
            "last_updated": group.last_updated,
            "severities": severities,
            "unique_sources": len(sources),
            "duration_minutes": (group.last_updated - group.created_at).total_seconds() / 60
        }