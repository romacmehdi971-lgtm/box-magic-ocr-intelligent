# MCP Memory Proxy

FastAPI service providing REST API access to IAPF Memory Hub for GPT integration.

## Quick Start

```bash
# Build Docker image
docker build -t memory-proxy:latest .

# Run locally
docker run -p 8080:8080 \
  -v /path/to/sa-key.json:/app/sa-key.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/sa-key.json \
  -e GOOGLE_SHEET_ID=1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ \
  memory-proxy:latest
```

## API Endpoints

### System
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs-json` - API documentation

### Sheets (Read-Only)
- `GET /sheets` - List all sheets
- `GET /sheets/{name}` - Get sheet data

### Proposals (Write with Validation)
- `POST /propose` - Create memory entry proposal
- `GET /proposals` - List proposals
- `POST /proposals/{id}/validate` - Approve/reject proposal

### Operations
- `POST /close-day` - Close day (export snapshot)
- `POST /audit` - Run autonomous audit

## Architecture

- **Service**: mcp-memory-proxy
- **Runtime**: Python 3.11 + FastAPI
- **Auth**: Cloud Run IAM (Bearer token)
- **Google Sheet**: 1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ
- **Service Account**: mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com

## Deployment

See `DEPLOYMENT.md` for full deployment instructions.

## Environment Variables

- `GOOGLE_SHEET_ID` - Hub spreadsheet ID (required)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account key (required)
- `READ_ONLY_MODE` - Enable read-only mode (default: false)
- `ENABLE_NOTIFICATIONS` - Enable email notifications (default: false)
- `LOG_LEVEL` - Logging level (default: INFO)
- `ARCHIVES_FOLDER_ID` - Drive folder ID for archives (optional, read from SETTINGS)

## IAM Configuration

### Service Account Permissions
```bash
# Grant Sheets editor role
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/sheets.editor"

# Grant Drive file role
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/drive.file"
```

### GPT Client Access
```bash
# Grant Cloud Run invoker role to GPT client
gcloud run services add-iam-policy-binding mcp-memory-proxy \
  --region=us-central1 \
  --member="user:romacmehdi971@gmail.com" \
  --role="roles/run.invoker"
```

## Testing

```bash
# Health check
curl https://mcp-memory-proxy-xxx-uc.a.run.app/health

# List sheets
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://mcp-memory-proxy-xxx-uc.a.run.app/sheets

# Get MEMORY_LOG
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://mcp-memory-proxy-xxx-uc.a.run.app/sheets/MEMORY_LOG

# Create proposal
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"entry_type":"DECISION","title":"Test","details":"Test details","source":"GPT"}' \
  https://mcp-memory-proxy-xxx-uc.a.run.app/propose
```

## Features

✅ **Read Access**: All 18 Hub sheets accessible via REST API  
✅ **Write Protection**: Proposals require human validation  
✅ **Autonomous Audit**: Auto-detect changes, update tabs, create snapshots  
✅ **Day Closure**: Export snapshot to Drive (no Apps Script API)  
✅ **IAM Security**: Cloud Run authentication required  
✅ **Logging**: All operations logged to MEMORY_LOG  
✅ **Documentation**: Auto-generated API docs

## Workflow

1. **GPT Read**: Direct access via `GET /sheets/{name}`
2. **GPT Write**: 
   - Propose entry via `POST /propose`
   - Returns `PROP-YYYYMMDDHHMMSS` ID
   - Human validates via `POST /proposals/{id}/validate`
   - If approved, appended to MEMORY_LOG
3. **Audit**: `POST /audit` detects changes, updates tabs, creates snapshot
4. **Close Day**: `POST /close-day` exports XLSX to Drive

## Security

- No public access (IAM required)
- Service account with minimal permissions
- All writes logged and audited
- Mandatory human validation for memory entries
- No direct MEMORY_LOG writes (proposals only)

## Cost

- Cloud Run: < $1/month (minimal traffic)
- Artifact Registry: < $0.10/month (single image)
- **Total**: < $2/month

## Support

For issues or questions, contact: romacmehdi971@gmail.com
