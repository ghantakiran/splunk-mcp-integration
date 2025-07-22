# NLP Engine Service Documentation

## Overview

The NLP Engine Service provides advanced natural language processing capabilities for converting human language queries into Splunk SPL (Search Processing Language) queries. It includes intent classification, entity extraction, context management, and intelligent query optimization.

**Base URL**: `/api/v1/nlp`  
**Service Port**: 8001  
**Version**: 1.0

## Core Query Processing

### POST /process-query
Convert natural language query to SPL and execute.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "query": "show me errors from the last hour where severity is high",
  "conversation_id": "conv_123",
  "user_context": {
    "user_id": "user_123",
    "preferences": {
      "format": "json",
      "max_results": 1000
    }
  },
  "options": {
    "include_explanation": true,
    "suggest_visualizations": true,
    "optimize_query": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "original_query": "show me errors from the last hour where severity is high",
    "spl_query": "search earliest=-1h@h index=* error severity=high | stats count by source | sort -count",
    "interpretation": {
      "intent": "search_and_aggregate",
      "time_range": {
        "earliest": "-1h@h",
        "latest": "now",
        "description": "last hour"
      },
      "filters": [
        {
          "field": "search_terms",
          "value": "error",
          "type": "keyword"
        },
        {
          "field": "severity",
          "value": "high",
          "type": "field_value"
        }
      ],
      "aggregations": [
        {
          "function": "count",
          "field": null,
          "group_by": ["source"]
        }
      ]
    },
    "confidence": 0.92,
    "explanation": "This query searches for error events in the last hour with high severity, then counts them by source and sorts by frequency.",
    "suggested_visualizations": [
      {
        "type": "bar_chart",
        "title": "Error Count by Source",
        "confidence": 0.89
      },
      {
        "type": "table",
        "title": "Error Statistics",
        "confidence": 0.75
      }
    ],
    "estimated_execution_time": 2.5,
    "estimated_result_size": 250
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid query or parameters
- `429 Too Many Requests`: Rate limit exceeded
- `503 Service Unavailable`: NLP service temporarily unavailable

---

### POST /analyze-query
Analyze natural language query without execution.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "query": "find all failed login attempts in the last 24 hours",
  "conversation_id": "conv_123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "original_query": "find all failed login attempts in the last 24 hours",
    "analysis": {
      "intent": "security_search",
      "confidence": 0.95,
      "complexity": "medium",
      "entities": [
        {
          "text": "failed login attempts",
          "type": "security_event",
          "confidence": 0.98
        },
        {
          "text": "last 24 hours",
          "type": "time_range",
          "confidence": 0.99
        }
      ],
      "suggested_spl": "search earliest=-24h@h index=* (failed OR failure) (login OR authentication) | stats count by user, src_ip | sort -count",
      "alternative_interpretations": [
        {
          "description": "Focus on authentication logs only",
          "spl": "search earliest=-24h@h index=auth failed login | stats count by user",
          "confidence": 0.82
        }
      ]
    }
  }
}
```

---

### POST /suggest-completions
Get query completion suggestions based on partial input.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "partial_query": "show me errors from",
  "conversation_id": "conv_123",
  "limit": 5
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "suggestions": [
      {
        "completion": "show me errors from the last hour",
        "confidence": 0.89,
        "category": "time_range"
      },
      {
        "completion": "show me errors from web servers",
        "confidence": 0.85,
        "category": "source_filter"
      },
      {
        "completion": "show me errors from database connections",
        "confidence": 0.78,
        "category": "component_filter"
      },
      {
        "completion": "show me errors from application logs",
        "confidence": 0.75,
        "category": "log_type"
      },
      {
        "completion": "show me errors from specific index",
        "confidence": 0.70,
        "category": "index_filter"
      }
    ]
  }
}
```

## Context Management

### GET /conversations/{conversation_id}
Get conversation history and context.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "conversation_id": "conv_123",
    "created_at": "2025-01-22T10:00:00Z",
    "updated_at": "2025-01-22T10:15:00Z",
    "messages": [
      {
        "id": "msg_001",
        "timestamp": "2025-01-22T10:00:00Z",
        "type": "user_query",
        "content": "show me errors from last hour",
        "spl_generated": "search earliest=-1h@h error | stats count by source"
      },
      {
        "id": "msg_002",
        "timestamp": "2025-01-22T10:05:00Z",
        "type": "user_query",
        "content": "filter by web servers only",
        "spl_generated": "search earliest=-1h@h error source=*web* | stats count by source",
        "context_used": ["previous_query", "time_range"]
      }
    ],
    "context": {
      "current_time_range": "-1h@h",
      "active_filters": ["error", "source=*web*"],
      "user_preferences": {
        "visualization_type": "bar_chart",
        "result_format": "table"
      }
    }
  }
}
```

---

### DELETE /conversations/{conversation_id}
Clear conversation history and context.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Conversation history cleared"
  }
}
```

---

### PUT /conversations/{conversation_id}/context
Update conversation context manually.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "context": {
    "active_filters": ["error", "severity=high"],
    "time_range": "-1h@h",
    "focus_area": "security"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Context updated successfully"
  }
}
```

## Query Intelligence

### POST /optimize-query
Optimize existing SPL query for better performance.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "spl_query": "search * | eval severity=if(error_code>500,\"high\",\"low\") | where severity=\"high\" | stats count by source",
  "optimization_goals": ["performance", "accuracy"],
  "user_context": {
    "available_indexes": ["main", "security", "web"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "original_query": "search * | eval severity=if(error_code>500,\"high\",\"low\") | where severity=\"high\" | stats count by source",
    "optimized_query": "search index=main error_code>500 | stats count by source",
    "optimizations_applied": [
      {
        "type": "index_specification",
        "description": "Added specific index to reduce search scope",
        "performance_gain": "60-80%"
      },
      {
        "type": "early_filtering",
        "description": "Moved error_code filter to search command",
        "performance_gain": "30-50%"
      },
      {
        "type": "remove_unnecessary_eval",
        "description": "Eliminated eval and where commands",
        "performance_gain": "10-15%"
      }
    ],
    "estimated_improvement": {
      "execution_time": "75% faster",
      "resource_usage": "60% less"
    }
  }
}
```

---

### POST /explain-query
Get detailed explanation of SPL query.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "spl_query": "search index=security earliest=-24h failed login | stats count by user, src_ip | where count > 5"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query": "search index=security earliest=-24h failed login | stats count by user, src_ip | where count > 5",
    "explanation": {
      "overview": "This query identifies users with multiple failed login attempts from the same IP address, which could indicate brute force attacks.",
      "breakdown": [
        {
          "command": "search index=security earliest=-24h failed login",
          "description": "Searches the security index for events containing 'failed' and 'login' from the last 24 hours"
        },
        {
          "command": "stats count by user, src_ip",
          "description": "Groups results by user and source IP, counting occurrences of each combination"
        },
        {
          "command": "where count > 5",
          "description": "Filters to show only combinations with more than 5 failed attempts"
        }
      ],
      "security_implications": [
        "Potential brute force attack detection",
        "Account compromise risk assessment",
        "Network security monitoring"
      ],
      "suggested_actions": [
        "Review accounts with high failure counts",
        "Consider blocking suspicious IP addresses",
        "Implement account lockout policies"
      ]
    }
  }
}
```

## Entity Recognition

### POST /extract-entities
Extract entities from natural language text.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "text": "show me all 404 errors from web servers in the last 2 hours where response time is greater than 500ms",
  "entity_types": ["time_range", "status_code", "source_type", "metric"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "entities": [
      {
        "text": "404 errors",
        "type": "status_code",
        "value": "404",
        "confidence": 0.98,
        "start": 12,
        "end": 22
      },
      {
        "text": "web servers",
        "type": "source_type", 
        "value": "web",
        "confidence": 0.95,
        "start": 28,
        "end": 39
      },
      {
        "text": "last 2 hours",
        "type": "time_range",
        "value": "-2h@h",
        "confidence": 0.99,
        "start": 47,
        "end": 59
      },
      {
        "text": "response time is greater than 500ms",
        "type": "metric_condition",
        "value": "response_time>500",
        "confidence": 0.92,
        "start": 66,
        "end": 102
      }
    ]
  }
}
```

## Intent Classification

### POST /classify-intent
Classify the intent of a natural language query.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "query": "alert me when error rate exceeds 100 per minute",
  "context": {
    "conversation_id": "conv_123"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "primary_intent": {
      "type": "create_alert",
      "confidence": 0.96,
      "category": "alerting"
    },
    "secondary_intents": [
      {
        "type": "monitoring",
        "confidence": 0.78,
        "category": "observability"
      }
    ],
    "parameters": {
      "alert_condition": "error_rate > 100/minute",
      "metric": "error_rate",
      "threshold": 100,
      "time_unit": "minute"
    },
    "required_actions": [
      "create_search_query",
      "configure_alert_trigger",
      "setup_notification_channel"
    ]
  }
}
```

## Service Configuration

### GET /capabilities
Get NLP service capabilities and configuration.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "models": {
      "intent_classification": {
        "model": "fine-tuned-bert",
        "version": "1.2.0",
        "accuracy": 0.94
      },
      "entity_extraction": {
        "model": "spacy-en-core-web-lg",
        "version": "3.7.2",
        "accuracy": 0.91
      },
      "query_generation": {
        "model": "gpt-4-turbo",
        "version": "2024-09",
        "accuracy": 0.89
      }
    },
    "supported_languages": ["en", "es", "fr", "de"],
    "max_query_length": 1000,
    "max_conversation_history": 50,
    "features": {
      "context_awareness": true,
      "multi_turn_conversations": true,
      "query_optimization": true,
      "visualization_suggestions": true,
      "real_time_processing": true
    },
    "rate_limits": {
      "queries_per_minute": 60,
      "concurrent_queries": 10
    }
  }
}
```

---

### GET /health
NLP service health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-22T10:30:00Z",
  "dependencies": {
    "openai_api": "healthy",
    "anthropic_api": "healthy",
    "database": "healthy",
    "redis": "healthy"
  },
  "performance": {
    "avg_response_time": "180ms",
    "queries_processed_last_hour": 1247,
    "error_rate": 0.02
  }
}
```

---

### GET /metrics
Prometheus metrics for monitoring.

**Response:** Prometheus format
```
# HELP nlp_queries_total Total number of NLP queries processed
# TYPE nlp_queries_total counter
nlp_queries_total{intent="search",status="success"} 1250
nlp_queries_total{intent="alert",status="success"} 45

# HELP nlp_query_confidence Query confidence score
# TYPE nlp_query_confidence histogram
nlp_query_confidence_bucket{le="0.7"} 25
nlp_query_confidence_bucket{le="0.8"} 150
nlp_query_confidence_bucket{le="0.9"} 850
nlp_query_confidence_bucket{le="1.0"} 1250
```

## Error Handling

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_QUERY` | 400 | Query cannot be parsed or processed |
| `AMBIGUOUS_INTENT` | 400 | Query intent is unclear, clarification needed |
| `UNSUPPORTED_LANGUAGE` | 400 | Query language not supported |
| `QUERY_TOO_LONG` | 400 | Query exceeds maximum length |
| `CONVERSATION_NOT_FOUND` | 404 | Conversation ID does not exist |
| `PROCESSING_ERROR` | 500 | Internal processing error |
| `MODEL_UNAVAILABLE` | 503 | AI model temporarily unavailable |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

### Error Response Format
```json
{
  "success": false,
  "errors": [
    {
      "code": "AMBIGUOUS_INTENT",
      "message": "Could not determine clear intent from query. Please be more specific.",
      "details": {
        "possible_intents": ["search", "alert", "dashboard"],
        "confidence_scores": [0.45, 0.42, 0.38]
      },
      "suggestions": [
        "Try: 'search for errors in the last hour'",
        "Try: 'create alert for high error rate'",
        "Try: 'show me a dashboard of system metrics'"
      ]
    }
  ]
}
```

## Usage Examples

### Basic Query Processing
```bash
curl -X POST /api/v1/nlp/process-query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show me top 10 error sources from yesterday",
    "conversation_id": "conv_123"
  }'
```

### Context-Aware Follow-up
```bash
# First query
curl -X POST /api/v1/nlp/process-query \
  -d '{"query": "show me errors from last hour", "conversation_id": "conv_123"}'

# Follow-up query (uses context)
curl -X POST /api/v1/nlp/process-query \
  -d '{"query": "filter by severity high", "conversation_id": "conv_123"}'
```

### Query Optimization
```bash
curl -X POST /api/v1/nlp/optimize-query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "spl_query": "search * error | stats count by source",
    "optimization_goals": ["performance"]
  }'
```

---

*Last Updated: January 22, 2025*
*Service Version: 1.0*