import { BaseAdapter } from "./baseAdapter.js";
import type { Belief } from "../types/belief.js";
export type { ProviderName } from "./baseAdapter.js";
export type { BuiltContext, PersonaLookup } from "./baseAdapter.js";

export class UniversalSessionAdapter extends BaseAdapter {
  protected override seedMetadata(belief: Belief): Record<string, unknown> {
    return {
      beliefId: belief._id,
      scope: belief.scope[0],
      type: belief.type,
      pinned: belief.pinned,
      superseded_by: belief.superseded_by ?? null,
    };
  }

  async ingestBelief(belief: Belief): Promise<void> {
    this.seedIndex.set(belief._id as string, belief);

    await fetch(`${this.baseUrl}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: this.beliefToText(belief),
        user_id: belief.user_id as string,
        metadata: this.seedMetadata(belief),
      }),
    });
  }

  async updateBeliefAliases(
    beliefId: string,
    addAliases: string[],
  ): Promise<void> {
    const belief = this.seedIndex.get(beliefId);
    if (!belief) return;

    const existing = (belief.aliases as string[]) ?? [];
    belief.aliases = [
      ...new Set([
        ...existing,
        ...addAliases.map((a) => a.trim().toLowerCase()),
      ]),
    ];

    if (this.supportsUpdate) {
      await fetch(`${this.baseUrl}/update`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          beliefId,
          text: this.beliefToText(belief),
          user_id: belief.user_id as string,
          metadata: this.seedMetadata(belief),
        }),
      });
    } else {
      await fetch(`${this.baseUrl}/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: this.beliefToText(belief),
          user_id: belief.user_id as string,
          metadata: this.seedMetadata(belief),
        }),
      });
    }
  }
}
