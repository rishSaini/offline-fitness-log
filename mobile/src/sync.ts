import { API_URL } from "./api";
import {
  getPendingOps,
  markOpsDone,
  markOpsFailed,
  upsertLocalWorkout,
} from "./db";

export async function syncNow(token: string) {
  const pending = await getPendingOps(100);
  if (pending.length === 0) return { ok: true, message: "Nothing to sync" };

  const ops = pending.map((row: any) => ({
    op_id: row.op_id,
    type: row.type,
    entity_id: row.entity_id,
    payload: row.payload ? JSON.parse(row.payload) : null,
    client_updated_at: row.client_updated_at,
  }));

  const res = await fetch(`${API_URL}/sync/push`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ ops }),
  });

  if (!res.ok) {
    await markOpsFailed(pending.map((p: any) => p.op_id));
    throw new Error(await res.text());
  }

  const data = await res.json();

  // Mark applied ops done
  const appliedIds = (data.applied_op_ids || []).map((x: any) => String(x));
  await markOpsDone(appliedIds);

  // Reconcile: server is canonical for any returned entities
  for (const ent of data.updated_entities || []) {
    if (ent.kind === "workout") {
      await upsertLocalWorkout(ent.data);
    }
    // sets omitted in UI MVP, but server supports them
  }

  // Conflicts: overwrite local with server copy (MVP resolution)
  for (const c of data.conflicts || []) {
    if (c.entity?.kind === "workout") {
      await upsertLocalWorkout(c.entity.data);
    }
  }

  return { ok: true, applied: appliedIds.length, conflicts: (data.conflicts || []).length };
}
