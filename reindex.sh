#!/bin/bash

set -e
echo "Deleting existing index..."
curl -X DELETE http://localhost:8000/index

echo -e "\n\nReindexing...\n"

curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/Users/knotbott/Projects/EnterPriseResourceDashboard"
}'
echo -e "\n\n"
curl http://localhost:8000/graph/summary

echo -e "\n\nDone!\n"