import { type Collection } from "mongodb";
import type { Belief } from "../types/belief.js";
import { BeliefsReaderVector } from "../utils/beliefsReaderVector.js";
import type {
  BuiltContext,
  ContextBudget,
  PersonaLookup,
} from "./baseAdapter.js";

export class VectorAdapter {
  private reader: BeliefsReaderVector;

  ingestionReport: { beliefId: string; latencyMs: number }[] = [];

  constructor(col: Collection<Belief & { embedding?: number[] }>) {
    this.reader = new BeliefsReaderVector(col);
  }

  async buildContext(
    userId: string,
    scope: string[],
    rawQuery: string,
    persona: PersonaLookup,
    budget: Partial<ContextBudget> = {},
  ): Promise<BuiltContext> {
    const b = {
      maxBeliefs: 20,
      maxPinnedFacts: 10,
      maxQuestions: 15,
      ...budget,
    };

    const [personaDoc, pinnedFacts, questions] = await Promise.all([
      persona.get(userId),
      this.reader.listPinnedFacts(userId, scope),
      this.reader.listPinnedOpenQuestions(userId, scope),
    ]);

    const pinnedIds = new Set(pinnedFacts.map((f) => f._id as string));

    const rawResults =
      rawQuery.trim() && b.maxBeliefs > 0
        ? await this.reader.searchText(userId, rawQuery, scope, {
            limit: b.maxBeliefs,
            excludeIds: pinnedIds,
          })
        : [];

    const expansions =
      rawResults.length > 0
        ? await this.reader.expandRelationParticipants(
            userId,
            rawResults,
            scope,
            {
              excludeIds: new Set([
                ...pinnedIds,
                ...rawResults.map((r) => r._id as string),
              ]),
            },
          )
        : [];

    const allRelevant = [...rawResults, ...expansions];
    const cap = b.maxBeliefs;
    const cappedPinned = pinnedFacts.slice(0, cap);
    const cappedRelevant = allRelevant.slice(
      0,
      Math.max(0, cap - cappedPinned.length),
    );

    return {
      personaPrelude: personaDoc?.universal ?? "",
      pinnedFactsJson: JSON.stringify(cappedPinned.map(projectLean)),
      relevantBeliefsJson: JSON.stringify(cappedRelevant.map(projectLean)),
      openQuestionsJson: JSON.stringify(
        questions.slice(0, b.maxQuestions).map(projectQuestion),
      ),
      beliefCount: cappedPinned.length + cappedRelevant.length,
      questionCount: Math.min(questions.length, b.maxQuestions),
    };
  }
}

function projectLean(b: Belief): Record<string, unknown> {
  const out: Record<string, unknown> = {
    id: b._id,
    canonical_name: b.canonical_name,
    content: b.content,
    why_it_matters: b.why_it_matters,
  };
  if (b.type === "open_question" || b.type === "decision") out.type = b.type;
  return out;
}

function projectQuestion(q: Belief): Record<string, unknown> {
  return {
    id: q._id,
    canonical_name: q.canonical_name,
    content: q.content,
    scope: q.scope,
  };
}
