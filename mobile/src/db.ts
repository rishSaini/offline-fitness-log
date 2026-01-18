import * as SQLite from "expo-sqlite";

type BindValue = SQLite.SQLiteBindValue;

let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;

async function getDb(): Promise<SQLite.SQLiteDatabase> {
  if (!dbPromise) {
    dbPromise = SQLite.openDatabaseAsync("fitness.db");
  }
  return dbPromise;
}

async function exec(sql: string) {
  const db = await getDb();
  await db.execAsync(sql);
}

async function run(sql: string, ...params: BindValue[]) {
  const db = await getDb();
  await db.runAsync(sql, ...params);
}

async function all<T>(sql: string, ...params: BindValue[]): Promise<T[]> {
  const db = await getDb();
  return db.getAllAsync<T>(sql, ...params);
}

export type WorkoutRow = {
  id: string;
  type: "run" | "lift";
  started_at: string;
  notes: string | null;
  distance_m: number | null;
  duration_s: number | null;
  rpe: number | null;
  version: number;
  updated_at: string | null;
  deleted_at: string | null;
};

export type SyncQueueRow = {
  op_id: string;
  type: string;
  entity_id: string;
  payload: string | null;
  client_updated_at: number;
  status: "PENDING" | "DONE" | "FAILED";
};

export async function initDb() {
  // WAL helps a bit with reliability for local writes
  await exec(`PRAGMA journal_mode = WAL;`);

  await exec(`
    CREATE TABLE IF NOT EXISTS workouts (
      id TEXT PRIMARY KEY NOT NULL,
      type TEXT NOT NULL,
      started_at TEXT NOT NULL,
      notes TEXT,
      distance_m INTEGER,
      duration_s INTEGER,
      rpe INTEGER,
      version INTEGER NOT NULL DEFAULT 0,
      updated_at TEXT,
      deleted_at TEXT
    );
  `);

  await exec(`
    CREATE TABLE IF NOT EXISTS workout_sets (
      id TEXT PRIMARY KEY NOT NULL,
      workout_id TEXT NOT NULL,
      position INTEGER NOT NULL DEFAULT 0,
      exercise_name TEXT,
      reps INTEGER,
      weight_kg REAL,
      distance_m INTEGER,
      duration_s INTEGER,
      notes TEXT,
      version INTEGER NOT NULL DEFAULT 0,
      updated_at TEXT,
      deleted_at TEXT
    );
  `);

  await exec(`
    CREATE TABLE IF NOT EXISTS sync_queue (
      op_id TEXT PRIMARY KEY NOT NULL,
      type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      payload TEXT,
      client_updated_at INTEGER NOT NULL,
      status TEXT NOT NULL
    );
  `);
}

export async function listLocalWorkouts(): Promise<WorkoutRow[]> {
  return all<WorkoutRow>(
    `SELECT * FROM workouts WHERE deleted_at IS NULL ORDER BY started_at DESC`
  );
}

export async function upsertLocalWorkout(w: Partial<WorkoutRow> & { id: string; type: "run" | "lift"; started_at: string }) {
  await run(
    `
    INSERT INTO workouts (id,type,started_at,notes,distance_m,duration_s,rpe,version,updated_at,deleted_at)
    VALUES (?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(id) DO UPDATE SET
      type=excluded.type,
      started_at=excluded.started_at,
      notes=excluded.notes,
      distance_m=excluded.distance_m,
      duration_s=excluded.duration_s,
      rpe=excluded.rpe,
      version=excluded.version,
      updated_at=excluded.updated_at,
      deleted_at=excluded.deleted_at
    `,
    w.id,
    w.type,
    w.started_at,
    w.notes ?? null,
    w.distance_m ?? null,
    w.duration_s ?? null,
    w.rpe ?? null,
    w.version ?? 0,
    w.updated_at ?? null,
    w.deleted_at ?? null
  );
}

export async function enqueueOp(op: {
  op_id: string;
  type: string;
  entity_id: string;
  payload: any;
  client_updated_at: number;
}) {
  await run(
    `
    INSERT INTO sync_queue (op_id,type,entity_id,payload,client_updated_at,status)
    VALUES (?,?,?,?,?,?)
    `,
    op.op_id,
    op.type,
    op.entity_id,
    op.payload ? JSON.stringify(op.payload) : null,
    op.client_updated_at,
    "PENDING"
  );
}

export async function getPendingOps(limit = 50): Promise<SyncQueueRow[]> {
  return all<SyncQueueRow>(
    `SELECT * FROM sync_queue WHERE status='PENDING' ORDER BY client_updated_at ASC LIMIT ?`,
    limit
  );
}

export async function markOpsDone(opIds: string[]) {
  if (opIds.length === 0) return;
  const placeholders = opIds.map(() => "?").join(",");
  await run(
    `UPDATE sync_queue SET status='DONE' WHERE op_id IN (${placeholders})`,
    ...opIds
  );
}

export async function markOpsFailed(opIds: string[]) {
  if (opIds.length === 0) return;
  const placeholders = opIds.map(() => "?").join(",");
  await run(
    `UPDATE sync_queue SET status='FAILED' WHERE op_id IN (${placeholders})`,
    ...opIds
  );
}

export async function resetLocalDb() {
  // wipe local tables
  await exec(`
    DELETE FROM sync_queue;
    DELETE FROM workout_sets;
    DELETE FROM workouts;
  `);

  // optional: reclaim space
  // await exec(`VACUUM;`);
}
