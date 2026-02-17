"""
MCP Memory Proxy Tool - HTTP Client for REST API access
Calls the MCP Memory Proxy REST API with X-API-Key authentication
Exposes HTTP status + body instead of opaque ClientResponseError
"""
import os
import json
from typing import Dict, Any, List, Optional
from ..utils import safe_logger

logger = safe_logger.get_safe_logger(__name__)

# Import conditionnel requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests library not available - proxy tool disabled")


class ProxyTool:
    """Client HTTP pour le MCP Memory Proxy REST API"""
    
    def __init__(self):
        """Initialize proxy client with API key from secret/env"""
        self.proxy_url = os.getenv("MCP_PROXY_URL", "https://mcp-memory-proxy-522732657254.us-central1.run.app")
        self.api_key = os.getenv("MCP_PROXY_API_KEY", "")
        
        if not self.api_key:
            logger.warning("MCP_PROXY_API_KEY not configured - proxy calls will fail with 403")
        
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        logger.info(f"ProxyTool initialized with proxy_url={self.proxy_url}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to proxy and return structured response
        
        Returns:
            {
                "success": bool,
                "http_status": int,
                "body": dict or str,
                "error": str (if failed),
                "correlation_id": str (if present)
            }
        """
        if not REQUESTS_AVAILABLE:
            return {
                "success": False,
                "http_status": 500,
                "error": "requests library not available",
                "body": None
            }
        
        url = f"{self.proxy_url}{endpoint}"
        
        try:
            logger.info(f"[ProxyTool] {method} {endpoint}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            
            # Parse response body
            try:
                body = response.json()
            except json.JSONDecodeError:
                body = response.text
            
            # Extract correlation_id if present
            correlation_id = None
            if isinstance(body, dict):
                correlation_id = body.get("correlation_id")
                if not correlation_id and isinstance(body.get("detail"), dict):
                    correlation_id = body.get("detail").get("correlation_id")
            
            success = 200 <= response.status_code < 300
            
            result = {
                "success": success,
                "http_status": response.status_code,
                "body": body,
                "correlation_id": correlation_id
            }
            
            if not success:
                error_msg = f"HTTP {response.status_code}"
                if isinstance(body, dict):
                    # Try detail.message first (custom errors)
                    error_msg = body.get("detail", {}).get("message") if isinstance(body.get("detail"), dict) else None
                    # Fallback to detail (string) or first validation error message
                    if not error_msg:
                        detail = body.get("detail")
                        if isinstance(detail, str):
                            error_msg = detail
                        elif isinstance(detail, list) and detail:
                            error_msg = detail[0].get("msg", str(detail[0]))
                        else:
                            error_msg = body.get("message") or f"HTTP {response.status_code}"
                result["error"] = error_msg
                logger.warning(f"[ProxyTool] Request failed: {error_msg} (correlation_id: {correlation_id})")
            else:
                logger.info(f"[ProxyTool] Request successful: HTTP {response.status_code}")
            
            return result
        
        except requests.exceptions.Timeout:
            logger.error(f"[ProxyTool] Request timeout: {url}")
            return {
                "success": False,
                "http_status": 504,
                "error": "Request timeout (30s)",
                "body": None
            }
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[ProxyTool] Connection error: {e}")
            return {
                "success": False,
                "http_status": 503,
                "error": f"Connection error: {str(e)}",
                "body": None
            }
        
        except Exception as e:
            logger.error(f"[ProxyTool] Unexpected error: {e}")
            return {
                "success": False,
                "http_status": 500,
                "error": f"Unexpected error: {str(e)}",
                "body": None
            }
    
    def list_sheets(self) -> Dict[str, Any]:
        """
        List all available sheets
        
        Returns:
            {
                "success": bool,
                "http_status": int,
                "sheets": List[dict],  # if success
                "error": str  # if failed
            }
        """
        result = self._make_request("GET", "/sheets")
        
        if result["success"] and isinstance(result["body"], dict):
            result["sheets"] = result["body"].get("sheets", [])
        
        return result
    
    def get_sheet_data(self, sheet_name: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get data from a specific sheet
        
        Args:
            sheet_name: Name of the sheet to read
            limit: Maximum number of rows (1-500, default 50)
        
        Returns:
            {
                "success": bool,
                "http_status": int,
                "sheet_name": str,
                "headers": List[str],
                "data": List[dict],  # if success
                "row_count": int,
                "error": str,  # if failed
                "correlation_id": str
            }
        """
        params = {}
        if limit is not None:
            params["limit"] = limit
        
        result = self._make_request("GET", f"/sheets/{sheet_name}", params=params)
        
        if result["success"] and isinstance(result["body"], dict):
            result.update({
                "sheet_name": result["body"].get("sheet_name"),
                "headers": result["body"].get("headers", []),
                "data": result["body"].get("data", []),
                "row_count": result["body"].get("row_count", 0)
            })
        
        return result
    
    def get_memory_log(self, limit: Optional[int] = 50) -> Dict[str, Any]:
        """
        Get MEMORY_LOG entries
        
        Args:
            limit: Maximum number of entries (1-500, default 50)
        
        Returns:
            {
                "success": bool,
                "http_status": int,
                "entries": List[dict],  # if success
                "total_entries": int,
                "error": str,  # if failed
                "correlation_id": str
            }
        """
        params = {"limit": limit} if limit else {}
        result = self._make_request("GET", "/gpt/memory-log", params=params)
        
        if result["success"] and isinstance(result["body"], dict):
            result.update({
                "entries": result["body"].get("entries", []),
                "total_entries": result["body"].get("total_entries", 0)
            })
        
        return result
    
    def get_snapshot_active(self) -> Dict[str, Any]:
        """
        Get active snapshot
        
        Returns:
            {
                "success": bool,
                "http_status": int,
                "snapshot": dict,  # if success
                "error": str,  # if failed
                "correlation_id": str
            }
        """
        result = self._make_request("GET", "/gpt/snapshot-active")
        
        if result["success"] and isinstance(result["body"], dict):
            result["snapshot"] = result["body"]
        
        return result
    
    def get_hub_status(self) -> Dict[str, Any]:
        """
        Get Hub health status
        
        Returns:
            {
                "success": bool,
                "http_status": int,
                "status": dict,  # if success
                "error": str,  # if failed
                "correlation_id": str
            }
        """
        result = self._make_request("GET", "/gpt/hub-status")
        
        if result["success"] and isinstance(result["body"], dict):
            result["status"] = result["body"]
        
        return result
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check proxy health
        
        Returns:
            {
                "success": bool,
                "http_status": int,
                "health": dict,  # if success
                "error": str  # if failed
            }
        """
        result = self._make_request("GET", "/health")
        
        if result["success"] and isinstance(result["body"], dict):
            result["health"] = result["body"]
        
        return result


def get_proxy_tool() -> ProxyTool:
    """Factory pour obtenir le Proxy Tool"""
    return ProxyTool()
