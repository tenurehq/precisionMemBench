from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import os

# Zep OSS uses the local server, not the cloud client
# We use the open source self-hosted version via graphiti
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

import asyncio
from datetime import datetime, timezone

app = FastAPI()

uuid_to_belief_id: dict[str, str] = {}


llm_config = LLMConfig(
    model=os.getenv("LLM_MODEL", "us.anthropic.claude-sonnet-4-6"),
    base_url=os.getenv("LLM_BASE_URL", "http://192.168.1.154:8000/api/v1"),
    api_key=os.getenv("LLM_API_KEY", "123456"),
)
llm_client = OpenAIGenericClient(config=llm_config)

embedder = OpenAIEmbedder(
    config=OpenAIEmbedderConfig(
        base_url=os.getenv("EMBEDDER_BASE_URL", "http://192.168.1.154:11434/v1"),
        embedding_model=os.getenv("EMBEDDER_MODEL", "mxbai-embed-large"),
        embedding_dim=int(os.getenv("EMBEDDER_DIM", "1024")),
        api_key=os.getenv("EMBEDDER_API_KEY", "ollama"),
    )
)

graphiti = Graphiti(
    uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
    user=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "password"),
    llm_client=llm_client,
    embedder=embedder,
    cross_encoder=OpenAIRerankerClient(client=llm_client, config=llm_config),
)


class AddRequest(BaseModel):
    text: str
    user_id: str
    metadata: dict = {}


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 20


class ResetRequest(BaseModel):
    user_id: str


@app.on_event("startup")
async def startup():
    await graphiti.build_indices_and_constraints()


@app.post("/add")
async def add(req: AddRequest):
    max_retries = 5
    base_delay = 2.0
    for attempt in range(max_retries):
        try:
            belief_id = req.metadata.get("beliefId")
            result = await graphiti.add_episode(
                name=belief_id,
                episode_body=req.text,
                source=EpisodeType.text,
                source_description=f"user:{req.user_id}",
                reference_time=datetime.now(timezone.utc),
                group_id=req.user_id,
            )
            if belief_id and result.episode.uuid:
                uuid_to_belief_id[result.episode.uuid] = belief_id
            return {"ok": True, "episodeUuid": result.episode.uuid}
        except Exception as e:
            if (
                "ThrottlingException" in str(e)
                or "Rate limit" in str(e)
                or "429" in str(e)
            ):
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
            raise

    return {"ok": False, "error": "max retries exceeded"}


@app.post("/search")
async def search(req: SearchRequest):
    results = await graphiti.search(
        query=req.query,
        group_ids=[req.user_id],
        num_results=req.limit,
    )

    seen = set()
    normalized = []

    for r in results:
        belief_id = None
        for ep_uuid in r.episodes or []:
            belief_id = uuid_to_belief_id.get(ep_uuid)
            if belief_id:
                break

        if not belief_id or belief_id in seen:
            continue

        seen.add(belief_id)
        normalized.append(
            {
                "id": belief_id,
                "memory": r.fact,
                "score": r.score if hasattr(r, "score") else 1.0,
            }
        )

    return {"results": normalized}


@app.delete("/reset")
async def reset():
    uuid_to_belief_id.clear()
    await graphiti.driver.execute_query(
        "MATCH (n) WHERE n.group_id = $group_id DETACH DELETE n",
        group_id="test-user",
    )
    await graphiti.driver.execute_query(
        "MATCH (n) WHERE n.group_id = $group_id DETACH DELETE n",
        group_id="other-user",
    )
    await graphiti.driver.execute_query(
        "MATCH (n) WHERE n.group_id = $group_id DETACH DELETE n",
        group_id="brand-new-user",
    )
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)