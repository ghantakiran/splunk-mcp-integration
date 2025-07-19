"""
Report generation service for scheduled reports.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
import tempfile
import json

import httpx
from jinja2 import Template

from app.core.config import settings
from app.models.schedule_models import ReportConfiguration, ReportFormat
from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class ReportGeneratorService:
    """Service for generating reports from scheduled executions."""
    
    def __init__(self):
        self.http_client = None
        self.export_services = {
            ReportFormat.PDF: settings.PDF_EXPORT_SERVICE_URL,
            ReportFormat.EXCEL: settings.CSV_EXPORT_SERVICE_URL,  # For Excel compatibility
            ReportFormat.POWERPOINT: settings.POWERPOINT_EXPORT_SERVICE_URL,
            ReportFormat.WORD: settings.WORD_EXPORT_SERVICE_URL,
            ReportFormat.CSV: settings.CSV_EXPORT_SERVICE_URL,
            ReportFormat.JSON: settings.JSON_XML_EXPORT_SERVICE_URL,
            ReportFormat.XML: settings.JSON_XML_EXPORT_SERVICE_URL,
            ReportFormat.HTML: settings.HTML_REPORT_SERVICE_URL,
        }
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client for service communication."""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
            )
        return self.http_client
    
    async def generate_report(
        self,
        execution_id: str,
        report_config: ReportConfiguration,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a report based on the configuration.
        
        Args:
            execution_id: Execution ID for tracking
            report_config: Report configuration
            user_context: User context for authentication
            
        Returns:
            Dictionary with generation results
        """
        try:
            logger.info(f"Starting report generation for execution {execution_id}")
            
            # Step 1: Process the query and get data
            query_result = await self._process_query(
                report_config.query,
                report_config.query_type,
                report_config.time_range,
                user_context
            )
            
            if not query_result.get("success"):
                raise ValueError(f"Query processing failed: {query_result.get('error')}")
            
            # Step 2: Generate visualization if needed
            visualization_result = None
            if report_config.visualization_config:
                visualization_result = await self._generate_visualization(
                    query_result["data"],
                    report_config.visualization_config,
                    user_context
                )
            
            # Step 3: Generate the report in requested format
            report_result = await self._generate_formatted_report(
                execution_id,
                report_config,
                query_result["data"],
                visualization_result,
                user_context
            )
            
            # Step 4: Store result in Redis cache
            redis_client = await get_redis_client()
            await redis_client.cache_schedule_result(
                execution_id,
                report_result,
                ttl_seconds=3600  # Cache for 1 hour
            )
            
            logger.info(f"Report generation completed for execution {execution_id}")
            
            return {
                "success": True,
                "execution_id": execution_id,
                "file_path": report_result.get("file_path"),
                "file_size": report_result.get("file_size"),
                "format": report_config.format.value,
                "records_processed": len(query_result["data"]),
                "generation_time": report_result.get("generation_time"),
                "metadata": {
                    "query": report_config.query,
                    "query_type": report_config.query_type,
                    "time_range": report_config.time_range,
                    "has_visualization": visualization_result is not None,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Report generation failed for execution {execution_id}: {e}")
            return {
                "success": False,
                "execution_id": execution_id,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def _process_query(
        self,
        query: str,
        query_type: str,
        time_range: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process the query and return data."""
        try:
            http_client = await self._get_http_client()
            
            if query_type == "natural":
                # Use NLP Engine to translate natural language to SPL
                nlp_url = f"{settings.NLP_ENGINE_URL}/api/v1/translate"
                nlp_payload = {
                    "query": query,
                    "time_range": time_range,
                    "user_context": user_context
                }
                
                response = await http_client.post(
                    nlp_url,
                    json=nlp_payload,
                    headers={"Authorization": f"Bearer {user_context.get('token')}"}
                )
                response.raise_for_status()
                
                nlp_result = response.json()
                if not nlp_result.get("success"):
                    raise ValueError(f"NLP translation failed: {nlp_result.get('error')}")
                
                spl_query = nlp_result["spl_query"]
            else:
                # Use SPL directly
                spl_query = query
            
            # Execute the SPL query (simulated for now)
            # In a real implementation, this would call Splunk's API
            mock_data = self._generate_mock_data(spl_query, time_range)
            
            return {
                "success": True,
                "data": mock_data,
                "spl_query": spl_query,
                "record_count": len(mock_data)
            }
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_mock_data(self, spl_query: str, time_range: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate mock data for testing purposes."""
        # This is a simplified mock data generator
        # In production, this would execute the actual SPL query against Splunk
        
        import random
        from datetime import datetime, timedelta
        
        # Generate sample data based on query patterns
        data = []
        num_records = random.randint(10, 100)
        
        for i in range(num_records):
            record = {
                "_time": (datetime.now() - timedelta(hours=random.randint(0, 24))).isoformat(),
                "host": f"server-{random.randint(1, 10):02d}",
                "source": f"/var/log/app-{random.randint(1, 5)}.log",
                "sourcetype": "application_log",
                "index": "main",
                "event_id": f"evt_{i:06d}",
                "severity": random.choice(["INFO", "WARN", "ERROR", "DEBUG"]),
                "message": f"Sample log message {i}",
                "response_time": random.randint(50, 2000),
                "bytes": random.randint(1024, 102400),
                "user_agent": "Mozilla/5.0 (compatible; ReportBot/1.0)",
                "status_code": random.choice([200, 301, 404, 500])
            }
            data.append(record)
        
        return data
    
    async def _generate_visualization(
        self,
        data: List[Dict[str, Any]],
        viz_config: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate visualization for the data."""
        try:
            http_client = await self._get_http_client()
            
            viz_url = f"{settings.VISUALIZATION_SERVICE_URL}/api/v1/charts/generate"
            viz_payload = {
                "data": data,
                "chart_config": viz_config,
                "export_format": "png",  # For embedding in reports
                "user_context": user_context
            }
            
            response = await http_client.post(
                viz_url,
                json=viz_payload,
                headers={"Authorization": f"Bearer {user_context.get('token')}"}
            )
            response.raise_for_status()
            
            viz_result = response.json()
            if viz_result.get("success"):
                return viz_result
            else:
                logger.warning(f"Visualization generation failed: {viz_result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Visualization generation failed: {e}")
            return None
    
    async def _generate_formatted_report(
        self,
        execution_id: str,
        report_config: ReportConfiguration,
        data: List[Dict[str, Any]],
        visualization_result: Optional[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate the final formatted report."""
        try:
            service_url = self.export_services.get(report_config.format)
            if not service_url:
                raise ValueError(f"Unsupported report format: {report_config.format}")
            
            http_client = await self._get_http_client()
            
            # Prepare the export request based on format
            export_payload = await self._prepare_export_payload(
                execution_id,
                report_config,
                data,
                visualization_result,
                user_context
            )
            
            # Call the appropriate export service
            export_url = f"{service_url}/api/v1/{self._get_export_endpoint(report_config.format)}"
            
            response = await http_client.post(
                export_url,
                json=export_payload,
                headers={"Authorization": f"Bearer {user_context.get('token')}"}
            )
            response.raise_for_status()
            
            export_result = response.json()
            if not export_result.get("success"):
                raise ValueError(f"Export failed: {export_result.get('error')}")
            
            return export_result
            
        except Exception as e:
            logger.error(f"Formatted report generation failed: {e}")
            raise
    
    async def _prepare_export_payload(
        self,
        execution_id: str,
        report_config: ReportConfiguration,
        data: List[Dict[str, Any]],
        visualization_result: Optional[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare export payload based on format."""
        base_payload = {
            "data_source": {
                "type": "static",
                "config": {"data": data}
            },
            "filename": f"scheduled_report_{execution_id}",
            "metadata": {
                "execution_id": execution_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "query": report_config.query,
                "record_count": len(data)
            }
        }
        
        # Format-specific configurations
        if report_config.format in [ReportFormat.JSON, ReportFormat.XML]:
            base_payload["export_config"] = {
                "format": report_config.format.value.lower(),
                **(report_config.format_options or {})
            }
        elif report_config.format == ReportFormat.CSV:
            base_payload["export_config"] = {
                "format": "csv",
                "include_headers": True,
                "delimiter": ",",
                **(report_config.format_options or {})
            }
        elif report_config.format == ReportFormat.PDF:
            base_payload.update({
                "template": "default",
                "data": {
                    "title": f"Scheduled Report - {execution_id}",
                    "data": data,
                    "visualization": visualization_result,
                    "metadata": base_payload["metadata"]
                },
                **(report_config.format_options or {})
            })
        elif report_config.format == ReportFormat.HTML:
            base_payload.update({
                "template": "modern",
                "data": data,
                "chart_config": visualization_result,
                "title": f"Scheduled Report - {execution_id}",
                **(report_config.format_options or {})
            })
        
        return base_payload
    
    def _get_export_endpoint(self, format: ReportFormat) -> str:
        """Get the appropriate export endpoint for format."""
        endpoint_map = {
            ReportFormat.PDF: "pdf-exports/generate",
            ReportFormat.EXCEL: "csv-exports/generate",  # Will be converted to Excel
            ReportFormat.POWERPOINT: "powerpoint-exports/generate",
            ReportFormat.WORD: "word-exports/generate",
            ReportFormat.CSV: "csv-exports/generate",
            ReportFormat.JSON: "json-xml-exports/generate",
            ReportFormat.XML: "json-xml-exports/generate",
            ReportFormat.HTML: "html-reports/generate"
        }
        return endpoint_map.get(format, "exports/generate")
    
    async def cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
    
    async def close(self):
        """Close HTTP client connections."""
        if self.http_client:
            await self.http_client.aclose()