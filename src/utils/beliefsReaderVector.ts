import type { Collection } from "mongodb";
import type { Belief } from "../types/belief.js";

const OLLAMA_BASE_URL = process.env.OLLAMA_URL ?? "http://localhost:11434";
const EMBED_MODEL = process.env.OLLAMA_EMBED_MODEL ?? "nomic-embed-text";

export const VECTOR_DIMENSIONS = 768;
export const VECTOR_INDEX_NAME = "nomic-embed-text";

type ScoredBelief = Belief & {
  _searchScore: number;
  _scoreDetails?: Record<string, unknown>;
};

export async function ollamaEmbed(text: string): Promise<number[]> {
  const res = await fetch(`${OLLAMA_BASE_URL}/api/embeddings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: EMBED_MODEL, prompt: text }),
  });
  if (!res.ok) {
    throw new Error(
      `Ollama embedding failed: ${res.status} ${await res.text()}`,
    );
  }
  const data = (await res.json()) as { embedding: number[] };
  return data.embedding;
}

export function beliefEmbedText(belief: {
  canonical_name: string;
  aliases: string[];
  content?: string;
  why_it_matters?: string;
}): string {
  const parts = [
    belief.canonical_name,
    ...belief.aliases,
    belief.content,
    belief.why_it_matters,
  ].filter(Boolean) as string[];
  return parts.join(" ");
}

export interface VectorSearchOptions {
  limit?: number;
  numCandidates?: number;
  scoreDetails?: boolean;
  excludeIds?: Set<string>;
}

export class BeliefsReaderVector {
  constructor(
    private readonly col: Collection<Belief & { embedding?: number[] }>,
    private readonly embed: (text: string) => Promise<number[]> = ollamaEmbed,
  ) {}

  async searchText(
    userId: string,
    query: string,
    scope?: string[],
    opts: VectorSearchOptions = {},
  ): Promise<ScoredBelief[]> {
    const { limit = 20, numCandidates = 150, excludeIds } = opts;

    if (!query.trim()) return [];

    const queryVector = await this.embed(query);

    const vectorStage = {
      $vectorSearch: {
        index: VECTOR_INDEX_NAME,
        path: "embedding",
        queryVector,
        numCandidates,
        limit: limit * 4,
        filter: {
          user_id: { $eq: userId },
          superseded_by: { $eq: null },
          resolved_at: { $eq: null },
        },
      },
    };

    const postMatch: Record<string, unknown> = {
      type: { $nin: ["open_question"] },
      subtype: { $ne: "expertise" },
    };

    if (scope?.length) {
      postMatch.scope = { $in: scope };
    }

    if (excludeIds?.size) {
      postMatch._id = { $nin: [...excludeIds] };
    }

    const pipeline = [
      vectorStage,
      { $addFields: { _searchScore: { $meta: "vectorSearchScore" } } },
      { $match: postMatch },
      { $limit: limit },
    ];

    return this.col.aggregate<ScoredBelief>(pipeline).toArray();
  }

  async expandRelationParticipants(
    userId: string,
    relationBeliefs: Belief[],
    scope?: string[],
    opts?: { excludeIds?: Set<string> },
  ): Promise<Belief[]> {
    const relations = relationBeliefs.filter((b) => b.type === "relation");
    if (relations.length === 0) return [];

    const participantIds = relations.flatMap(
      (rel) => (rel.participants as string[]) ?? [],
    );
    if (participantIds.length === 0) return [];

    const filter: Record<string, unknown> = {
      _id: { $in: participantIds },
      user_id: userId,
    };

    if (opts?.excludeIds?.size) {
      filter._id = { $in: participantIds, $nin: [...opts.excludeIds] };
    }

    if (scope?.length) {
      filter.scope = { $in: scope };
    }

    return this.col.find(filter as never).toArray();
  }

  async listPinnedFacts(userId: string, scope: string[]): Promise<Belief[]> {
    return this.col
      .find({
        user_id: userId,
        pinned: true,
        type: { $ne: "open_question" },
        superseded_by: null,
        resolved_at: null,
        scope: { $in: scope },
      } as never)
      .toArray();
  }

  async listPinnedOpenQuestions(
    userId: string,
    scope: string[],
  ): Promise<Belief[]> {
    return this.col
      .find({
        user_id: userId,
        type: "open_question",
        pinned: true,
        resolved_at: null,
        scope: { $in: scope },
      } as never)
      .toArray();
  }

  async listByScope(userId: string, scope: string[]): Promise<Belief[]> {
    return this.col
      .find({
        user_id: userId,
        scope: { $in: scope },
      } as never)
      .toArray();
  }

  async countActive(userId: string): Promise<number> {
    return this.col.countDocuments({
      user_id: userId,
    } as never);
  }
}
