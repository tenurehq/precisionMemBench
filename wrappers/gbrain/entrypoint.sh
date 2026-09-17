#!/bin/bash
set -e

OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://host.docker.internal:11434}"

until curl -sf "${OLLAMA_BASE_URL}/api/tags" > /dev/null 2>&1; do
  echo "Waiting for Ollama..."
  sleep 2
done


if [ ! -f /root/.gbrain/config.json ]; then
  gbrain init --pglite \
    --embedding-model ollama/nomic-embed-text
  gbrain config set provider_base_urls.ollama "${OLLAMA_BASE_URL}/v1"
  gbrain config set search.reranker.model llama-server-reranker:mixedbread-ai/mxbai-rerank-xsmall-v1
  gbrain config set search.reranker.enabled true
  gbrain config set provider_base_urls.llama-server-reranker http://infinity-reranker:7997
fi

python3 gbrain_service.py