"""
MCP Memory Proxy - Infrastructure Inspection Endpoints (P0)
Date: 2026-02-18
Purpose: READ-ONLY inspection endpoints for runtime, Cloud Run, and logs
"""
import logging
import os
import subprocess
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from google.cloud import logging as cloud_logging
from google.cloud import run_v2
from google.auth import default

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/infra", tags=["Infrastructure"])


# ==================== MODELS ====================

class AuditSafeConfig(BaseModel):
    """Audit-safe runtime configuration flags"""
    read_only_mode: str
    enable_actions: str
    dry_run_mode: str
    log_level: str


class WhoAmIResponse(BaseModel):
    """Runtime identity and configuration"""
    project_id: str
    region: str
    service_account_email: str
    cloud_run_service: str
    cloud_run_revision: str
    image_digest: str
    auth_mode: str = Field(..., description="IAM|API_KEY|DUAL")
    version: str
    config: AuditSafeConfig


class LogEntry(BaseModel):
    """Single log entry"""
    timestamp: str
    severity: str
    message: str
    correlation_id: Optional[str] = None


class LogsQueryRequest(BaseModel):
    """Request for log query (flexible input)"""
    resource_type: Optional[str] = Field(None, description="cloud_run_service|cloud_run_job")
    name: Optional[str] = Field(None, description="Resource name")
    time_range_minutes: int = Field(10, ge=1, le=60, description="Time range in minutes (1-60)")
    limit: int = Field(50, ge=1, le=200, description="Max entries (1-200)")
    contains: Optional[str] = Field(None, description="Optional text filter")
    filter: Optional[str] = Field(None, description="Raw Cloud Logging filter (alternative to resource_type+name)")


class LogsQueryResponse(BaseModel):
    """Response for log query"""
    entries: List[LogEntry]
    total_count: int
    query_time_ms: int


class CloudRunService(BaseModel):
    """Cloud Run service info"""
    name: str
    url: str
    region: str
    revision: str
    image_digest: str
    traffic_percent: int


class CloudRunJob(BaseModel):
    """Cloud Run job info"""
    name: str
    region: str
    last_execution: Optional[str]
    last_status: Optional[str]


class CloudRunJobExecution(BaseModel):
    """Cloud Run job execution info"""
    execution_id: str
    status: str
    start_time: Optional[str]
    end_time: Optional[str]
    duration_seconds: Optional[float]


# ==================== HELPER FUNCTIONS ====================

def get_project_id() -> str:
    """Get GCP project ID"""
    try:
        _, project = default()
        if project:
            return project
    except Exception:
        pass
    
    # Fallback to env var
    return os.environ.get("GCP_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT", "unknown"))


def get_region() -> str:
    """Get GCP region"""
    return os.environ.get("GCP_REGION", os.environ.get("CLOUD_RUN_REGION", "us-central1"))


def get_service_account_email() -> str:
    """Get service account email from metadata server or ADC"""
    # Method 1: Try metadata server (most reliable for Cloud Run)
    try:
        import requests
        response = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
            headers={"Metadata-Flavor": "Google"},
            timeout=1
        )
        if response.status_code == 200:
            return response.text.strip()
    except Exception:
        pass
    
    # Method 2: Try ADC credentials
    try:
        credentials, _ = default()
        if hasattr(credentials, 'service_account_email'):
            return credentials.service_account_email
        # For compute credentials, extract from signer_email
        if hasattr(credentials, 'signer_email'):
            return credentials.signer_email
    except Exception:
        pass
    
    # Fallback to env var
    return os.environ.get("SERVICE_ACCOUNT_EMAIL", "default")


def get_cloud_run_metadata() -> Dict[str, str]:
    """Get Cloud Run metadata from environment"""
    return {
        "service": os.environ.get("K_SERVICE", "unknown"),
        "revision": os.environ.get("K_REVISION", "unknown"),
        "configuration": os.environ.get("K_CONFIGURATION", "unknown")
    }


def get_image_digest() -> str:
    """Get container image digest from env var or metadata"""
    # Priority 1: Env var (set at deploy time)
    digest = os.environ.get("IMAGE_DIGEST", "")
    if digest and digest != "unknown":
        return digest
    
    # Priority 2: Try to read from metadata server
    try:
        import requests
        response = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/attributes/image",
            headers={"Metadata-Flavor": "Google"},
            timeout=1
        )
        if response.status_code == 200:
            image = response.text
            if "@sha256:" in image:
                return image.split("@")[1]
    except Exception:
        pass
    
    # Return placeholder that indicates need for env var
    return "sha256:not-set-use-IMAGE_DIGEST-env-var"


def determine_auth_mode(request_headers: dict = None) -> str:
    """Determine authentication mode based on env and runtime"""
    # Check if API_KEY is configured
    has_api_key_env = bool(os.environ.get("API_KEY"))
    
    # Check if running on Cloud Run (IAM-enabled by default)
    is_cloud_run = bool(os.environ.get("K_SERVICE"))
    
    # If request headers provided, check active auth
    if request_headers:
        has_api_key_header = bool(request_headers.get("x-api-key"))
        has_iam_header = bool(request_headers.get("authorization"))
        
        if has_api_key_header and has_iam_header:
            return "DUAL"
        elif has_api_key_header:
            return "API_KEY"
        elif has_iam_header:
            return "IAM"
    
    # Static determination
    if has_api_key_env and is_cloud_run:
        return "DUAL"
    elif has_api_key_env:
        return "API_KEY"
    elif is_cloud_run:
        return "IAM"
    else:
        return "NONE"


# ==================== ENDPOINTS ====================

@router.get("/whoami", response_model=WhoAmIResponse)
async def whoami():
    """
    Identify runtime MCP
    
    Returns precise runtime identity including:
    - GCP project and region
    - Service account email (from metadata server)
    - Cloud Run service/revision (from K_* env vars)
    - Container image digest (from IMAGE_DIGEST env var)
    - Authentication mode (IAM/API_KEY/DUAL)
    - Version (from VERSION env var)
    """
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] GET /infra/whoami")
    
    try:
        project_id = get_project_id()
        region = get_region()
        service_account_email = get_service_account_email()
        metadata = get_cloud_run_metadata()
        image_digest = get_image_digest()
        auth_mode = determine_auth_mode()
        version = os.environ.get("VERSION", os.environ.get("BUILD_VERSION", os.environ.get("API_VERSION", "v3.1.0-p0")))
        
        # Build audit-safe config
        config = AuditSafeConfig(
            read_only_mode=os.environ.get("READ_ONLY_MODE", "false"),
            enable_actions=os.environ.get("ENABLE_ACTIONS", "false"),
            dry_run_mode=os.environ.get("DRY_RUN_MODE", "true"),
            log_level=os.environ.get("LOG_LEVEL", "INFO")
        )
        
        response = WhoAmIResponse(
            project_id=project_id,
            region=region,
            service_account_email=service_account_email,
            cloud_run_service=metadata["service"],
            cloud_run_revision=metadata["revision"],
            image_digest=image_digest,
            auth_mode=auth_mode,
            version=version,
            config=config
        )
        
        logger.info(f"[{correlation_id}] whoami successful: {service_account_email}")
        return response
    
    except Exception as e:
        logger.error(f"[{correlation_id}] whoami failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "correlation_id": correlation_id,
                "error": "whoami_failed",
                "message": str(e)
            }
        )


@router.post("/logs/query", response_model=LogsQueryResponse)
async def query_logs(request: LogsQueryRequest):
    """
    Query Cloud Logging (READ-ONLY)
    
    Retrieve logs for Cloud Run services or jobs.
    
    Constraints:
    - READ ONLY (no modifications)
    - No secrets exposed
    - Max limit = 200
    
    Returns structured JSON with correlation_id if present.
    """
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] POST /infra/logs/query: {request.resource_type}/{request.name}")
    
    try:
        start_time = datetime.now()
        
        # Get project ID
        project_id = get_project_id()
        
        # Initialize Cloud Logging client
        logging_client = cloud_logging.Client(project=project_id)
        
        # Build filter
        time_ago = datetime.now(timezone.utc) - timedelta(minutes=request.time_range_minutes)
        time_filter = f'timestamp>="{time_ago.isoformat()}"'
        
        # Option 1: Use raw filter if provided
        if request.filter:
            filter_str = f'{request.filter} AND {time_filter}'
        # Option 2: Build from resource_type + name
        elif request.resource_type and request.name:
            if request.resource_type == "cloud_run_service":
                resource_filter = f'resource.type="cloud_run_revision" AND resource.labels.service_name="{request.name}"'
            elif request.resource_type == "cloud_run_job":
                resource_filter = f'resource.type="cloud_run_job" AND resource.labels.job_name="{request.name}"'
            else:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "correlation_id": correlation_id,
                        "error": "invalid_resource_type",
                        "message": f"Invalid resource_type: {request.resource_type}. Must be 'cloud_run_service' or 'cloud_run_job'"
                    }
                )
            
            filter_str = f'{resource_filter} AND {time_filter}'
            
            # Add text filter if provided
            if request.contains:
                # Escape quotes in contains string
                contains_escaped = request.contains.replace('"', '\\"')
                filter_str += f' AND jsonPayload.message=~"{contains_escaped}"'
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "correlation_id": correlation_id,
                    "error": "invalid_request",
                    "message": "Must provide either 'filter' OR both 'resource_type' and 'name'"
                }
            )
        
        logger.info(f"[{correlation_id}] Log filter: {filter_str}")
        
        # Fetch logs
        entries_list = []
        try:
            # Use list_entries with max_results
            entries_iterator = logging_client.list_entries(
                filter_=filter_str,
                order_by=cloud_logging.DESCENDING,
                max_results=request.limit
            )
            
            for entry in entries_iterator:
                # Extract message
                message = ""
                if hasattr(entry, 'payload'):
                    if isinstance(entry.payload, dict):
                        message = entry.payload.get('message', str(entry.payload))
                    else:
                        message = str(entry.payload)
                elif hasattr(entry, 'text_payload'):
                    message = entry.text_payload
                
                # Extract correlation_id if present
                corr_id = None
                if isinstance(entry.payload, dict):
                    corr_id = entry.payload.get('correlation_id')
                
                entries_list.append(LogEntry(
                    timestamp=entry.timestamp.isoformat() if entry.timestamp else datetime.now(timezone.utc).isoformat(),
                    severity=entry.severity or "INFO",
                    message=message,
                    correlation_id=corr_id
                ))
        
        except Exception as fetch_error:
            logger.warning(f"[{correlation_id}] Log fetch warning: {fetch_error}")
            # Return empty list on fetch error (permissions, etc.)
        
        # Calculate query time
        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        logger.info(f"[{correlation_id}] Logs query successful: {len(entries_list)} entries in {query_time_ms}ms")
        
        return LogsQueryResponse(
            entries=entries_list,
            total_count=len(entries_list),
            query_time_ms=query_time_ms
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{correlation_id}] Logs query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "correlation_id": correlation_id,
                "error": "logs_query_failed",
                "message": str(e)
            }
        )


@router.get("/cloudrun/services", response_model=List[CloudRunService])
async def list_cloud_run_services():
    """
    List Cloud Run services (READ-ONLY)
    
    Returns list of all Cloud Run services in the project/region.
    """
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] GET /infra/cloudrun/services")
    
    try:
        project_id = get_project_id()
        region = get_region()
        
        # Initialize Cloud Run client
        client = run_v2.ServicesClient()
        
        # Build parent path
        parent = f"projects/{project_id}/locations/{region}"
        
        # List services
        services_list = []
        try:
            request = run_v2.ListServicesRequest(parent=parent)
            services = client.list_services(request=request)
            
            for service in services:
                # Extract service name
                name = service.name.split("/")[-1] if "/" in service.name else service.name
                
                # Get URL
                url = service.uri or "unknown"
                
                # Get latest revision
                revision = "unknown"
                image_digest = "unknown"
                traffic_percent = 100
                
                if service.latest_ready_revision:
                    revision = service.latest_ready_revision.split("/")[-1]
                
                if service.template and service.template.containers:
                    container = service.template.containers[0]
                    if container.image and "@sha256:" in container.image:
                        image_digest = container.image.split("@")[1]
                
                if service.traffic:
                    for traffic in service.traffic:
                        if traffic.type_ == run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST:
                            traffic_percent = traffic.percent or 100
                            break
                
                services_list.append(CloudRunService(
                    name=name,
                    url=url,
                    region=region,
                    revision=revision,
                    image_digest=image_digest,
                    traffic_percent=traffic_percent
                ))
        
        except Exception as list_error:
            logger.warning(f"[{correlation_id}] Cloud Run services list warning: {list_error}")
            # Return empty list on error (permissions, etc.)
        
        logger.info(f"[{correlation_id}] Cloud Run services list successful: {len(services_list)} services")
        return services_list
    
    except Exception as e:
        logger.error(f"[{correlation_id}] Cloud Run services list failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "correlation_id": correlation_id,
                "error": "services_list_failed",
                "message": str(e)
            }
        )


@router.get("/cloudrun/jobs", response_model=List[CloudRunJob])
async def list_cloud_run_jobs():
    """
    List Cloud Run jobs (READ-ONLY)
    
    Returns list of all Cloud Run jobs in the project/region.
    """
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] GET /infra/cloudrun/jobs")
    
    try:
        project_id = get_project_id()
        region = get_region()
        
        # Initialize Cloud Run client
        client = run_v2.JobsClient()
        
        # Build parent path
        parent = f"projects/{project_id}/locations/{region}"
        
        # List jobs
        jobs_list = []
        try:
            request = run_v2.ListJobsRequest(parent=parent)
            jobs = client.list_jobs(request=request)
            
            for job in jobs:
                # Extract job name
                name = job.name.split("/")[-1] if "/" in job.name else job.name
                
                # Get last execution info
                last_execution = None
                last_status = None
                
                if job.latest_created_execution:
                    exec_name = job.latest_created_execution.name
                    last_execution = exec_name.split("/")[-1] if "/" in exec_name else exec_name
                    
                    # Try to get execution status
                    try:
                        exec_client = run_v2.ExecutionsClient()
                        execution = exec_client.get_execution(name=job.latest_created_execution.name)
                        
                        if execution.completion_time:
                            last_status = "SUCCEEDED"
                        elif execution.start_time:
                            last_status = "RUNNING"
                        else:
                            last_status = "PENDING"
                    except Exception:
                        last_status = "UNKNOWN"
                
                jobs_list.append(CloudRunJob(
                    name=name,
                    region=region,
                    last_execution=last_execution,
                    last_status=last_status
                ))
        
        except Exception as list_error:
            logger.warning(f"[{correlation_id}] Cloud Run jobs list warning: {list_error}")
            # Return empty list on error (permissions, etc.)
        
        logger.info(f"[{correlation_id}] Cloud Run jobs list successful: {len(jobs_list)} jobs")
        return jobs_list
    
    except Exception as e:
        logger.error(f"[{correlation_id}] Cloud Run jobs list failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "correlation_id": correlation_id,
                "error": "jobs_list_failed",
                "message": str(e)
            }
        )


@router.get("/cloudrun/job/{name}/executions", response_model=List[CloudRunJobExecution])
async def list_job_executions(
    name: str,
    limit: int = Query(10, ge=1, le=50, description="Max executions (1-50)")
):
    """
    List Cloud Run job executions (READ-ONLY)
    
    Returns list of recent executions for a specific job.
    """
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] GET /infra/cloudrun/job/{name}/executions?limit={limit}")
    
    try:
        project_id = get_project_id()
        region = get_region()
        
        # Initialize Cloud Run client
        client = run_v2.ExecutionsClient()
        
        # Build parent path
        parent = f"projects/{project_id}/locations/{region}/jobs/{name}"
        
        # List executions
        executions_list = []
        try:
            request = run_v2.ListExecutionsRequest(parent=parent)
            executions = client.list_executions(request=request)
            
            count = 0
            for execution in executions:
                if count >= limit:
                    break
                
                # Extract execution ID
                exec_id = execution.name.split("/")[-1] if "/" in execution.name else execution.name
                
                # Get times
                start_time = execution.start_time.isoformat() if execution.start_time else None
                end_time = execution.completion_time.isoformat() if execution.completion_time else None
                
                # Calculate duration
                duration_seconds = None
                if execution.start_time and execution.completion_time:
                    duration = execution.completion_time - execution.start_time
                    duration_seconds = duration.total_seconds()
                
                # Determine status
                if execution.completion_time:
                    # Check if succeeded or failed
                    status = "SUCCEEDED"
                    if hasattr(execution, 'conditions'):
                        for condition in execution.conditions:
                            if condition.type == "Completed" and condition.status == "False":
                                status = "FAILED"
                                break
                elif execution.start_time:
                    status = "RUNNING"
                else:
                    status = "PENDING"
                
                executions_list.append(CloudRunJobExecution(
                    execution_id=exec_id,
                    status=status,
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration_seconds
                ))
                
                count += 1
        
        except Exception as list_error:
            logger.warning(f"[{correlation_id}] Job executions list warning: {list_error}")
            # Return empty list on error (permissions, etc.)
        
        logger.info(f"[{correlation_id}] Job executions list successful: {len(executions_list)} executions")
        return executions_list
    
    except Exception as e:
        logger.error(f"[{correlation_id}] Job executions list failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "correlation_id": correlation_id,
                "error": "executions_list_failed",
                "message": str(e)
            }
        )
