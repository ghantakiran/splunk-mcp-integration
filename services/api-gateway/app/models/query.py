"""
Query and QueryResult models for SPL translation and execution
"""

from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class QueryStatus(enum.Enum):
    """Query status enumeration"""
    PENDING = "pending"
    TRANSLATING = "translating"
    TRANSLATED = "translated"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationStatus(enum.Enum):
    """Query validation status"""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


class Query(BaseModel):
    """Query model for natural language to SPL translation"""
    
    __tablename__ = "queries"
    __table_args__ = {"schema": "spl"}
    
    # Foreign keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat.conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Query data
    natural_language_query = Column(Text, nullable=False)
    generated_spl = Column(Text, nullable=True)
    optimized_spl = Column(Text, nullable=True)
    final_spl = Column(Text, nullable=True)  # The actual SPL that was executed
    
    # Query status and validation
    status = Column(
        SQLEnum(QueryStatus),
        nullable=False,
        default=QueryStatus.PENDING,
        index=True
    )
    
    validation_status = Column(
        SQLEnum(ValidationStatus),
        nullable=False,
        default=ValidationStatus.PENDING,
        index=True
    )
    
    validation_errors = Column(JSONB, nullable=False, default=[], server_default='[]')
    validation_warnings = Column(JSONB, nullable=False, default=[], server_default='[]')
    
    # Execution metadata
    execution_time_ms = Column(Integer, nullable=True)
    result_count = Column(Integer, nullable=True)
    
    # Query metadata and context
    metadata = Column(JSONB, nullable=False, default={}, server_default='{}')
    context = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Performance tracking
    translation_time_ms = Column(Integer, nullable=True)
    validation_time_ms = Column(Integer, nullable=True)
    
    # Splunk execution details
    splunk_job_id = Column(String(255), nullable=True, index=True)
    splunk_search_id = Column(String(255), nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    
    # Query classification
    query_type = Column(String(50), nullable=True, index=True)  # search, stats, chart, etc.
    complexity_score = Column(Integer, nullable=True)  # 1-10 complexity rating
    
    # Relationships
    user = relationship("User", back_populates="queries")
    conversation = relationship("Conversation", back_populates="queries")
    results = relationship(
        "QueryResult",
        back_populates="query",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<Query(id={self.id}, status={self.status}, user_id={self.user_id})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if query execution is completed"""
        return self.status == QueryStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if query execution failed"""
        return self.status == QueryStatus.FAILED
    
    @property
    def is_pending(self) -> bool:
        """Check if query is pending execution"""
        return self.status in [QueryStatus.PENDING, QueryStatus.TRANSLATING, QueryStatus.VALIDATING]
    
    @property
    def is_executing(self) -> bool:
        """Check if query is currently executing"""
        return self.status == QueryStatus.EXECUTING
    
    @property
    def has_results(self) -> bool:
        """Check if query has results"""
        return self.results.count() > 0
    
    @property
    def latest_result(self) -> Optional["QueryResult"]:
        """Get the latest query result"""
        return self.results.order_by("QueryResult.created_at desc").first()
    
    def get_context_value(self, key: str, default: Any = None) -> Any:
        """Get context value by key"""
        if self.context and key in self.context:
            return self.context[key]
        return default
    
    def set_context_value(self, key: str, value: Any) -> None:
        """Set context value"""
        context_dict = dict(self.context) if self.context else {}
        context_dict[key] = value
        self.context = context_dict
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key"""
        if self.metadata and key in self.metadata:
            return self.metadata[key]
        return default
    
    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set metadata value"""
        metadata_dict = dict(self.metadata) if self.metadata else {}
        metadata_dict[key] = value
        self.metadata = metadata_dict
    
    def add_validation_error(self, error: str, code: str = None) -> None:
        """Add validation error"""
        errors = list(self.validation_errors) if self.validation_errors else []
        error_obj = {"message": error, "code": code} if code else {"message": error}
        errors.append(error_obj)
        self.validation_errors = errors
        self.validation_status = ValidationStatus.INVALID
    
    def add_validation_warning(self, warning: str, code: str = None) -> None:
        """Add validation warning"""
        warnings = list(self.validation_warnings) if self.validation_warnings else []
        warning_obj = {"message": warning, "code": code} if code else {"message": warning}
        warnings.append(warning_obj)
        self.validation_warnings = warnings
        
        if self.validation_status == ValidationStatus.PENDING:
            self.validation_status = ValidationStatus.WARNING
    
    def mark_translation_complete(self, spl: str, time_ms: int = None) -> None:
        """Mark translation as complete"""
        self.generated_spl = spl
        self.status = QueryStatus.TRANSLATED
        if time_ms:
            self.translation_time_ms = time_ms
    
    def mark_validation_complete(self, is_valid: bool, time_ms: int = None) -> None:
        """Mark validation as complete"""
        self.validation_status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if time_ms:
            self.validation_time_ms = time_ms
    
    def mark_execution_start(self, splunk_job_id: str = None) -> None:
        """Mark query execution start"""
        self.status = QueryStatus.EXECUTING
        if splunk_job_id:
            self.splunk_job_id = splunk_job_id
    
    def mark_execution_complete(self, result_count: int = None, time_ms: int = None) -> None:
        """Mark query execution as complete"""
        self.status = QueryStatus.COMPLETED
        if result_count is not None:
            self.result_count = result_count
        if time_ms:
            self.execution_time_ms = time_ms
    
    def mark_execution_failed(self, error: str, details: Dict[str, Any] = None) -> None:
        """Mark query execution as failed"""
        self.status = QueryStatus.FAILED
        self.error_message = error
        if details:
            self.error_details = details
    
    def get_total_time_ms(self) -> int:
        """Get total processing time in milliseconds"""
        total = 0
        if self.translation_time_ms:
            total += self.translation_time_ms
        if self.validation_time_ms:
            total += self.validation_time_ms
        if self.execution_time_ms:
            total += self.execution_time_ms
        return total
    
    def to_dict(self, include_spl: bool = True, include_errors: bool = True) -> Dict[str, Any]:
        """Convert to dictionary with options to exclude sensitive data"""
        data = super().to_dict()
        
        # Add computed fields
        data['is_completed'] = self.is_completed
        data['is_failed'] = self.is_failed
        data['is_pending'] = self.is_pending
        data['is_executing'] = self.is_executing
        data['has_results'] = self.has_results
        data['total_time_ms'] = self.get_total_time_ms()
        
        if not include_spl:
            # Remove SPL fields for security
            data.pop('generated_spl', None)
            data.pop('optimized_spl', None)
            data.pop('final_spl', None)
        
        if not include_errors:
            # Remove error details
            data.pop('error_message', None)
            data.pop('error_details', None)
            data.pop('validation_errors', None)
        
        return data


class QueryResult(BaseModel):
    """Query result model for storing SPL execution results"""
    
    __tablename__ = "query_results"
    __table_args__ = {"schema": "spl"}
    
    # Foreign key to query
    query_id = Column(
        UUID(as_uuid=True),
        ForeignKey("spl.queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Result data
    result_data = Column(JSONB, nullable=True)  # The actual query results
    result_metadata = Column(JSONB, nullable=False, default={}, server_default='{}')
    execution_stats = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Caching
    cached_until = Column("cached_until", nullable=True)
    
    # Result format and size
    format_type = Column(String(50), nullable=True)  # json, csv, table, chart
    result_size_bytes = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    
    # Relationships
    query = relationship("Query", back_populates="results")
    
    def __repr__(self) -> str:
        return f"<QueryResult(id={self.id}, query_id={self.query_id}, rows={self.row_count})>"
    
    @property
    def is_cached(self) -> bool:
        """Check if result is still cached"""
        if not self.cached_until:
            return False
        from datetime import datetime
        return datetime.utcnow() < self.cached_until
    
    @property
    def size_mb(self) -> float:
        """Get result size in MB"""
        if self.result_size_bytes:
            return self.result_size_bytes / (1024 * 1024)
        return 0.0
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key"""
        if self.result_metadata and key in self.result_metadata:
            return self.result_metadata[key]
        return default
    
    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set metadata value"""
        metadata_dict = dict(self.result_metadata) if self.result_metadata else {}
        metadata_dict[key] = value
        self.result_metadata = metadata_dict
    
    def get_execution_stat(self, key: str, default: Any = None) -> Any:
        """Get execution statistic by key"""
        if self.execution_stats and key in self.execution_stats:
            return self.execution_stats[key]
        return default
    
    def set_execution_stat(self, key: str, value: Any) -> None:
        """Set execution statistic"""
        stats_dict = dict(self.execution_stats) if self.execution_stats else {}
        stats_dict[key] = value
        self.execution_stats = stats_dict
    
    def update_size_info(self) -> None:
        """Update size information based on result data"""
        if self.result_data:
            import json
            data_str = json.dumps(self.result_data)
            self.result_size_bytes = len(data_str.encode('utf-8'))
            
            # Update row/column counts for structured data
            if isinstance(self.result_data, list):
                self.row_count = len(self.result_data)
                if self.result_data and isinstance(self.result_data[0], dict):
                    self.column_count = len(self.result_data[0].keys())
            elif isinstance(self.result_data, dict) and 'rows' in self.result_data:
                self.row_count = len(self.result_data['rows'])
                if 'columns' in self.result_data:
                    self.column_count = len(self.result_data['columns'])
    
    def to_dict(self, include_data: bool = True) -> Dict[str, Any]:
        """Convert to dictionary with option to exclude large data"""
        data = super().to_dict()
        
        # Add computed fields
        data['is_cached'] = self.is_cached
        data['size_mb'] = self.size_mb
        
        if not include_data:
            # Remove large result data for performance
            data.pop('result_data', None)
        
        return data