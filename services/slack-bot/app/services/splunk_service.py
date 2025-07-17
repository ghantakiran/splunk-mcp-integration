"""
Service for communicating with Splunk MCP backend services.
"""

import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.config import settings
from ..core.logging import get_logger, LogContext

logger = get_logger(__name__)

class SplunkService:
    """Service for interacting with Splunk MCP backend."""
    
    def __init__(self):
        self.session = None
        self.api_gateway_url = settings.api_gateway_url
        self.nlp_engine_url = settings.nlp_engine_url
        self.visualization_url = settings.visualization_url
        self.alert_manager_url = settings.alert_manager_url
    
    async def initialize(self):
        """Initialize HTTP session."""
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
        timeout = aiohttp.ClientTimeout(total=settings.api_gateway_timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "Splunk-MCP-SlackBot/1.0"}
        )
        
        logger.info("Splunk service initialized")
    
    async def cleanup(self):
        """Cleanup HTTP session."""
        if self.session:
            await self.session.close()
    
    async def process_query(self, query: str, user_context: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Process a natural language query through the NLP engine."""
        with LogContext(service="nlp_engine", query_length=len(query)):
            try:
                # Prepare request payload
                payload = {
                    "query": query,
                    "context": {
                        "user_id": user_context.get("user_id"),
                        "roles": user_context.get("roles", []),
                        "accessible_indexes": user_context.get("accessible_indexes", []),
                        "session_id": session.get("id"),
                        "conversation_history": session.get("history", [])
                    },
                    "user_preferences": user_context.get("preferences", {}),
                    "conversation_history": session.get("history", [])
                }
                
                # Send to NLP engine
                async with self.session.post(
                    f"{self.nlp_engine_url}/api/v1/translate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=settings.nlp_engine_timeout)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # If we have SPL, execute it
                        if result.get("spl_query"):
                            execution_result = await self._execute_spl_query(
                                result["spl_query"],
                                user_context
                            )
                            
                            # Merge results
                            result.update(execution_result)
                        
                        # Generate visualizations if applicable
                        if result.get("data") and result.get("visualization_type"):
                            viz_result = await self._generate_visualization(
                                result["data"],
                                result["visualization_type"],
                                user_context
                            )
                            
                            if viz_result.get("success"):
                                result["visualizations"] = viz_result.get("visualizations", [])
                        
                        logger.info(
                            "Query processed successfully",
                            spl_generated=bool(result.get("spl_query")),
                            results_count=len(result.get("data", [])),
                            confidence=result.get("confidence_score", 0)
                        )
                        
                        return {"success": True, "data": result}
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"NLP engine error: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"Query processing failed: {response.status}"
                        }
                        
            except asyncio.TimeoutError:
                logger.error("NLP engine request timeout")
                return {"success": False, "error": "Query processing timed out"}
            except Exception as e:
                logger.error(f"Error processing query: {str(e)}")
                return {"success": False, "error": "Failed to process query"}
    
    async def _execute_spl_query(self, spl_query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SPL query through API gateway."""
        try:
            payload = {
                "spl": spl_query,
                "user_context": user_context,
                "max_results": settings.max_query_results
            }
            
            async with self.session.post(
                f"{self.api_gateway_url}/api/v1/queries/execute",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)  # Longer timeout for query execution
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return {
                        "data": result.get("data", []),
                        "execution_time": result.get("execution_time"),
                        "results_count": len(result.get("data", []))
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Query execution error: {response.status} - {error_text}")
                    return {"error": f"Query execution failed: {response.status}"}
                    
        except Exception as e:
            logger.error(f"Error executing SPL query: {str(e)}")
            return {"error": "Failed to execute query"}
    
    async def _generate_visualization(self, data: List[Dict], viz_type: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate visualization for query results."""
        try:
            payload = {
                "data": data,
                "chart_type": viz_type,
                "config": {
                    "width": 800,
                    "height": 400,
                    "theme": "light",
                    "export_format": "png"
                },
                "user_preferences": user_context.get("preferences", {})
            }
            
            async with self.session.post(
                f"{self.visualization_url}/api/v1/charts/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=settings.visualization_timeout)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return {"success": True, "visualizations": result.get("charts", [])}
                else:
                    logger.error(f"Visualization error: {response.status}")
                    return {"success": False, "error": "Visualization generation failed"}
                    
        except Exception as e:
            logger.error(f"Error generating visualization: {str(e)}")
            return {"success": False, "error": "Failed to generate visualization"}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status from all services."""
        try:
            services = {
                "api_gateway": f"{self.api_gateway_url}/health",
                "nlp_engine": f"{self.nlp_engine_url}/health",
                "visualization": f"{self.visualization_url}/health",
                "alert_manager": f"{self.alert_manager_url}/health"
            }
            
            status = {"status": "healthy", "services": {}}
            
            # Check each service
            for service_name, health_url in services.items():
                try:
                    async with self.session.get(
                        health_url,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            service_status = await response.json()
                            status["services"][service_name] = {
                                "status": service_status.get("status", "unknown"),
                                "response_time": response.headers.get("X-Response-Time", "unknown")
                            }
                        else:
                            status["services"][service_name] = {
                                "status": "unhealthy",
                                "error": f"HTTP {response.status}"
                            }
                            status["status"] = "degraded"
                            
                except Exception as e:
                    status["services"][service_name] = {
                        "status": "error",
                        "error": str(e)
                    }
                    status["status"] = "degraded"
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {
                "status": "error",
                "error": "Failed to check system status"
            }
    
    async def create_alert(self, alert_definition: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create an alert through the alert manager."""
        try:
            payload = {
                "alert_definition": alert_definition,
                "user_context": user_context
            }
            
            async with self.session.post(
                f"{self.alert_manager_url}/api/v1/alerts",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=settings.alert_manager_timeout)
            ) as response:
                
                if response.status == 201:
                    result = await response.json()
                    return {"success": True, "alert": result.get("alert")}
                else:
                    error_text = await response.text()
                    logger.error(f"Alert creation error: {response.status} - {error_text}")
                    return {"success": False, "error": "Failed to create alert"}
                    
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")
            return {"success": False, "error": "Failed to create alert"}
    
    async def get_user_dashboards(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get user's dashboards."""
        try:
            params = {
                "user_id": user_context.get("user_id"),
                "limit": 10
            }
            
            async with self.session.get(
                f"{self.visualization_url}/api/v1/dashboards",
                params=params,
                timeout=aiohttp.ClientTimeout(total=settings.visualization_timeout)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return {"success": True, "dashboards": result.get("dashboards", [])}
                else:
                    return {"success": False, "error": "Failed to get dashboards"}
                    
        except Exception as e:
            logger.error(f"Error getting dashboards: {str(e)}")
            return {"success": False, "error": "Failed to get dashboards"}