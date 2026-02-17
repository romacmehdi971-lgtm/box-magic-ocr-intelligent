"""
MCP Memory Proxy - Cloud Run Client (READ-ONLY)
Date: 2026-02-17
Purpose: Cloud Run inspection and monitoring endpoints
Security: READ-ONLY access via roles/run.viewer
"""
import logging
from typing import List, Dict, Any, Optional
from google.auth import default
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests

logger = logging.getLogger(__name__)

# Required IAM roles for READ-ONLY access:
# - roles/run.viewer
# - roles/logging.viewer
# - roles/artifactregistry.reader
# - roles/browser

SCOPES = [
    'https://www.googleapis.com/auth/cloud-platform.read-only'
]


class CloudRunClient:
    """Cloud Run inspection client (READ-ONLY)"""
    
    def __init__(self, project_id: str, region: str = "us-central1"):
        """Initialize Cloud Run client"""
        try:
            credentials, _ = default(scopes=SCOPES)
            self.credentials = credentials
            self.project_id = project_id
            self.region = region
            self.parent = f"projects/{project_id}/locations/{region}"
            
            # Build Cloud Run API client
            self.service = build('run', 'v2', credentials=credentials)
            logger.info(f"Cloud Run client initialized for project {project_id}, region {region}")
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Run client: {e}")
            raise
    
    def list_services(self) -> List[Dict[str, Any]]:
        """List all Cloud Run services in the project/region"""
        try:
            services = []
            request = self.service.projects().locations().services().list(parent=self.parent)
            
            while request is not None:
                response = request.execute()
                services.extend(response.get('services', []))
                request = self.service.projects().locations().services().list_next(request, response)
            
            logger.info(f"Listed {len(services)} Cloud Run services")
            return self._format_services(services)
        except HttpError as e:
            logger.error(f"Failed to list Cloud Run services: {e}")
            raise
    
    def get_service(self, service_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific service"""
        try:
            name = f"{self.parent}/services/{service_name}"
            service = self.service.projects().locations().services().get(name=name).execute()
            logger.info(f"Retrieved service: {service_name}")
            return self._format_service(service)
        except HttpError as e:
            logger.error(f"Failed to get service {service_name}: {e}")
            raise
    
    def list_revisions(self, service_name: str) -> List[Dict[str, Any]]:
        """List all revisions for a service"""
        try:
            parent = f"{self.parent}/services/{service_name}"
            revisions = []
            request = self.service.projects().locations().services().revisions().list(parent=parent)
            
            while request is not None:
                response = request.execute()
                revisions.extend(response.get('revisions', []))
                request = self.service.projects().locations().services().revisions().list_next(request, response)
            
            logger.info(f"Listed {len(revisions)} revisions for service {service_name}")
            return self._format_revisions(revisions)
        except HttpError as e:
            logger.error(f"Failed to list revisions for {service_name}: {e}")
            raise
    
    def get_revision(self, service_name: str, revision_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific revision"""
        try:
            name = f"{self.parent}/services/{service_name}/revisions/{revision_name}"
            revision = self.service.projects().locations().services().revisions().get(name=name).execute()
            logger.info(f"Retrieved revision: {revision_name}")
            return self._format_revision(revision)
        except HttpError as e:
            logger.error(f"Failed to get revision {revision_name}: {e}")
            raise
    
    def fetch_openapi_schema(self, service_url: str) -> Dict[str, Any]:
        """Fetch OpenAPI schema from a Cloud Run service"""
        try:
            # Try /openapi.json endpoint
            openapi_url = f"{service_url.rstrip('/')}/openapi.json"
            response = requests.get(openapi_url, timeout=10)
            response.raise_for_status()
            
            schema = response.json()
            logger.info(f"Fetched OpenAPI schema from {openapi_url}")
            return {
                "url": openapi_url,
                "schema": schema,
                "title": schema.get("info", {}).get("title"),
                "version": schema.get("info", {}).get("version"),
                "endpoints_count": len(schema.get("paths", {}))
            }
        except Exception as e:
            logger.error(f"Failed to fetch OpenAPI schema from {service_url}: {e}")
            raise
    
    def health_probe(self, service_url: str, health_path: str = "/health") -> Dict[str, Any]:
        """Perform health check on a Cloud Run service"""
        try:
            health_url = f"{service_url.rstrip('/')}{health_path}"
            response = requests.get(health_url, timeout=10)
            
            result = {
                "url": health_url,
                "status_code": response.status_code,
                "healthy": response.status_code == 200,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000)
            }
            
            # Try to parse JSON response
            try:
                result["body"] = response.json()
            except:
                result["body"] = response.text[:500]  # First 500 chars
            
            logger.info(f"Health probe for {service_url}: {result['status_code']}")
            return result
        except Exception as e:
            logger.error(f"Health probe failed for {service_url}: {e}")
            return {
                "url": f"{service_url}{health_path}",
                "status_code": 0,
                "healthy": False,
                "error": str(e)
            }
    
    def _format_services(self, services: List[Dict]) -> List[Dict[str, Any]]:
        """Format services list for API response"""
        formatted = []
        for service in services:
            formatted.append(self._format_service(service))
        return formatted
    
    def _format_service(self, service: Dict) -> Dict[str, Any]:
        """Format service detail for API response"""
        metadata = service.get('metadata', {})
        spec = service.get('spec', {})
        status = service.get('status', {})
        
        return {
            "name": metadata.get('name'),
            "namespace": metadata.get('namespace'),
            "created": metadata.get('creationTimestamp'),
            "generation": metadata.get('generation'),
            "labels": metadata.get('labels', {}),
            "annotations": metadata.get('annotations', {}),
            "image": spec.get('template', {}).get('spec', {}).get('containers', [{}])[0].get('image'),
            "url": status.get('url'),
            "ready": status.get('conditions', [{}])[0].get('status') == 'True',
            "traffic": status.get('traffic', []),
            "latest_revision": status.get('latestReadyRevisionName')
        }
    
    def _format_revisions(self, revisions: List[Dict]) -> List[Dict[str, Any]]:
        """Format revisions list for API response"""
        formatted = []
        for revision in revisions:
            formatted.append(self._format_revision(revision))
        return formatted
    
    def _format_revision(self, revision: Dict) -> Dict[str, Any]:
        """Format revision detail for API response"""
        metadata = revision.get('metadata', {})
        spec = revision.get('spec', {})
        status = revision.get('status', {})
        
        return {
            "name": metadata.get('name'),
            "created": metadata.get('creationTimestamp'),
            "generation": metadata.get('generation'),
            "labels": metadata.get('labels', {}),
            "image": spec.get('containers', [{}])[0].get('image'),
            "service_account": spec.get('serviceAccountName'),
            "timeout": spec.get('timeoutSeconds'),
            "memory": spec.get('containers', [{}])[0].get('resources', {}).get('limits', {}).get('memory'),
            "cpu": spec.get('containers', [{}])[0].get('resources', {}).get('limits', {}).get('cpu'),
            "env_vars": [
                {"name": env.get('name'), "value": env.get('value', '[SECRET]')}
                for env in spec.get('containers', [{}])[0].get('env', [])
            ],
            "ready": status.get('conditions', [{}])[0].get('status') == 'True',
            "serving": status.get('observedGeneration') == metadata.get('generation')
        }


# Global instance
_cloudrun_client: Optional[CloudRunClient] = None


def get_cloudrun_client(project_id: str = "box-magique-gp-prod", region: str = "us-central1") -> CloudRunClient:
    """Get or create the global CloudRunClient instance"""
    global _cloudrun_client
    if _cloudrun_client is None:
        _cloudrun_client = CloudRunClient(project_id, region)
    return _cloudrun_client
