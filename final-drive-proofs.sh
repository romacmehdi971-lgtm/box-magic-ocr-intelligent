#!/bin/bash

SERVICE_URL="https://mcp-memory-proxy-522732657254.us-central1.run.app"

echo "=========================================="
echo "PREUVE 1: /drive/file/{id}/metadata"
echo "=========================================="
curl -s "$SERVICE_URL/drive/file/1LwUZ67zVstl2tuogcdYYihPilUAXQai3/metadata" | jq '{
  ok,
  run_id,
  file: {
    id: .file.id,
    name: .file.name,
    mimeType: .file.mimeType,
    modifiedTime: .file.modifiedTime,
    shared: .file.shared
  }
}'

echo ""
echo "=========================================="
echo "PREUVE 2: /drive/search"
echo "=========================================="
curl -s "$SERVICE_URL/drive/search?query=00_GOUVERNANCE&folder_id=1LwUZ67zVstl2tuogcdYYihPilUAXQai3&limit=10" | jq '{
  ok,
  run_id,
  query,
  folder_id,
  total_results,
  results_count: (.results | length),
  first_result: (if .results[0] then {
    id: .results[0].id,
    name: .results[0].name,
    mimeType: .results[0].mimeType
  } else "no results" end)
}'

echo ""
echo "=========================================="
echo "PREUVE 3: /drive/tree"
echo "=========================================="
curl -s "$SERVICE_URL/drive/tree?folder_id=1LwUZ67zVstl2tuogcdYYihPilUAXQai3&max_depth=2&limit=100" | jq '{
  ok,
  run_id,
  folder: {
    id: .folder.id,
    name: .folder.name,
    path: .folder.path
  },
  total_items,
  children_count: (.children | length),
  sample_children: (.children[0:3] | map({
    id,
    name,
    mimeType,
    children_count: (if .children then (.children | length) else 0 end)
  }))
}'

echo ""
echo "=========================================="
echo "✅ LES 3 PREUVES CURL COMPLÉTÉES"
echo "=========================================="
