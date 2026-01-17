import { API_URL } from "./api";
import {
  getPendingOps,
  markOpsDone,
  markOpsFailed,
  upsertLocalWorkout,
} from "./db";

function safeJsonParse(s: string | null) {
  if (!s) return null;
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
}

async function readErr(res: Response) {
  const t = await res.text();
  try {
    const j = JSON.parse(t);
    return j?.detail ? JSON.stringify(j.detail) : t;
  } catch {
    return t;
  }
}

export async function syncNow(token: string) {
  const pending = await getPendingOps(50);
  if (pending.length === 0) {
    return { applied_op_ids: [], updated_entities: [], conflicts: [] };
  }

  const ops = pending.map((p) => ({
    op_id: p.op_id,
    type: p.type,
    entity_id: p.entity_id,
    payload: safeJsonParse(p.payload),
    client_updated_at: p.client_updated_at,
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
    // Don't lose ops; mark failed (optional) but keep them for debugging
    const msg = await readErr(res);
    throw new Error(msg);
  }

  const data = await res.json();

  // mark ops done
  const applied: string[] = data.applied_op_ids ?? [];
  await markOpsDone(applied);

  // reconcile local with server “truth”
  const updated = data.updated_entities ?? [];
  for (const item of updated) {
    if (item.entity === "workout" && item.data) {
      await upsertLocalWorkout(item.data);
    }
  }

  // if you want, mark conflicts as DONE too (server wins in our backend impl)
  const conflicts = data.conflicts ?? [];
  const conflictOpIds = conflicts.map((c: any) => c.op_id).filter(Boolean);
  if (conflictOpIds.length) await markOpsDone(conflictOpIds);

  return data;
}
