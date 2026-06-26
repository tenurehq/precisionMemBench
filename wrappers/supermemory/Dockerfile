FROM ubuntu:26.04 AS binary

ENV SUPERMEMORY_BINARY_URL="https://github.com/supermemoryai/supermemory/releases/download/server-v0.0.3/supermemory-server-linux-x64"
ENV SUPERMEMORY_BINARY_SHA256="4036486514bd3511099e8f8642e1c56ecc58550c5e194442e88a5438992c0957"

RUN apt-get update \
    && apt-get install -y curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "$SUPERMEMORY_BINARY_URL" -o /tmp/supermemory-server \
    && echo "$SUPERMEMORY_BINARY_SHA256  /tmp/supermemory-server" | sha256sum -c - \
    && chmod +x /tmp/supermemory-server

FROM ubuntu:26.04 AS runtime
WORKDIR /app

RUN apt-get update \
    && apt-get install -y python3 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY --from=binary /tmp/supermemory-server /usr/local/bin/supermemory-server

RUN uv init --bare
RUN uv add fastapi==0.138.1 uvicorn==0.49.0 httpx==0.28.1

COPY supermemory_service.py .

CMD supermemory-server & \
    until [ -f ./.supermemory/auth-secret ]; do sleep 0.5; done && \
    export SUPERMEMORY_API_KEY=$(cat ./.supermemory/auth-secret) && \
    uv run uvicorn supermemory_service:app --host 0.0.0.0 --port 8080