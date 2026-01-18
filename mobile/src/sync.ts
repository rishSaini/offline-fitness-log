import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL } from "./api";
import { upsertLocalWorkout, getPendingOps, markOpsDone } from "./db";

const LAST_SYNC_KEY = "last_sync_ms";

async function getLastSyncMs() {
  const v = await AsyncStorage.getItem(LAST_SYNC_KEY);
  return v ? parseInt(v, 10) : 0;
}

async function setLastSyncMs(ms: number) {
  await AsyncStorage.setItem(LAST_SYNC_KEY, String(ms));
}

async function pullChanges(token: string, sinceMs: number) {
  const res = await fetch(`${API_URL}/sync/pull?since=${sinceMs}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }

  const data = await res.json();

  const workouts = data.workouts ?? [];
  for (const w of workouts) {
    // If your local UI should hide deleted workouts later, we’ll handle that in Step 4.
    await upsertLocalWorkout(w);
  }

  const serverTime = data.server_time_ms ?? Date.now();
  await setLastSyncMs(serverTime);

  return data;
}

export async function syncNow(token: string) {
  const sinceMs = await getLastSyncMs();

  // --- PUSH ---
  const pending = await getPendingOps(50);
  if (pending.length) {
    const ops = pending.map((p) => ({
      op_id: p.op_id,
      type: p.type,
      entity_id: p.entity_id,
      payload: p.payload ? JSON.parse(p.payload) : null, 
      client_updated_at: p.client_updated_at,
    }));

    const pushRes = await fetch(`${API_URL}/sync/push`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ ops }),
    });

    if (!pushRes.ok) throw new Error(await pushRes.text());
    const pushData = await pushRes.json();

    await markOpsDone(pushData.applied_op_ids ?? []);
  }

  // --- PULL ---
  const pullData = await pullChanges(token, sinceMs);

  return { ok: true, pulled: pullData.workouts?.length ?? 0 };
}

