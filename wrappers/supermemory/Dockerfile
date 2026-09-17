FROM ubuntu:26.04@sha256:61ebaa5cc23ca45450db85eac015435199ec569e28ec222ea13f2aed2110b8a6 AS binary-download

ENV SUPERMEMORY_BINARY_URL="https://github.com/supermemoryai/supermemory/releases/download/server-v0.0.8/supermemory-server-linux-x64"
ENV SUPERMEMORY_BINARY_SHA256="87f32433d0179be80bb9d8a1bafbac65af4128324342a27ecb8bd1a77b5506f3"

RUN apt-get update \
    && apt-get install -y curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "$SUPERMEMORY_BINARY_URL" -o /tmp/supermemory-server \
    && echo "$SUPERMEMORY_BINARY_SHA256  /tmp/supermemory-server" | sha256sum -c - \
    && chmod +x /tmp/supermemory-server

FROM ubuntu:26.04 AS binary-runtime

WORKDIR /app

RUN apt-get update \
    && apt-get install -y ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=binary-download /tmp/supermemory-server /usr/local/bin/supermemory-server

CMD ["supermemory-server"]

FROM ubuntu:26.04 AS wrapper-runtime

WORKDIR /app

RUN apt-get update \
    && apt-get install -y python3 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"

RUN uv init --bare
RUN uv add fastapi==0.138.1 uvicorn==0.49.0 httpx==0.28.1

COPY supermemory_service.py .

CMD ["sh", "-lc", "until [ -s /data/api-key ]; do echo 'Waiting for Supermemory API key'; sleep 1; done; export SUPERMEMORY_API_KEY=\"$(cat /data/api-key)\"; exec uv run uvicorn supermemory_service:app --host 0.0.0.0 --port \"${WRAPPER_PORT:-8080}\" --log-level debug --access-log"]