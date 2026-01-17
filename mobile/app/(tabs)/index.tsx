import "react-native-get-random-values";
import React, { useEffect, useMemo, useState } from "react";
import { SafeAreaView, View, Text, TextInput, Button, FlatList, Alert } from "react-native";
import NetInfo from "@react-native-community/netinfo";
import { v4 as uuidv4 } from "uuid";

import { initDb, listLocalWorkouts, upsertLocalWorkout, enqueueOp } from "../../src/db";
import { login, signup } from "../../src/api";
import { syncNow } from "../../src/sync";

type Workout = {
  id: string;
  type: "run" | "lift";
  started_at: string;
  notes?: string | null;
  distance_m?: number | null;
  duration_s?: number | null;
  rpe?: number | null;
  version?: number;
  updated_at?: string | null;
  deleted_at?: string | null;
};

export default function HomeScreen() {
  const [ready, setReady] = useState(false);

  const [email, setEmail] = useState("test@example.com");
  const [password, setPassword] = useState("password123");
  const [token, setToken] = useState<string | null>(null);

  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [notes, setNotes] = useState("");
  const [distanceKm, setDistanceKm] = useState("5");
  const [durationMin, setDurationMin] = useState("30");

  const [isOnline, setIsOnline] = useState<boolean>(true);

  useEffect(() => {
    (async () => {
      await initDb();
      await refreshWorkouts();
      setReady(true);
    })();
  }, []);

  useEffect(() => {
    const unsub = NetInfo.addEventListener((state) => {
      setIsOnline(!!state.isConnected);
    });
    return () => unsub();
  }, []);

  useEffect(() => {
    if (token && isOnline) {
      syncNow(token).catch(() => {});
    }
  }, [token, isOnline]);

  async function refreshWorkouts() {
    const rows = await listLocalWorkouts();
    setWorkouts(rows as any);
  }

  async function handleSignup() {
    try {
      const res = await signup(email, password);
      setToken(res.access_token);
      Alert.alert("Signed up", "You are logged in.");
    } catch (e: any) {
      Alert.alert("Signup failed", String(e.message || e));
    }
  }

  async function handleLogin() {
    try {
      const res = await login(email, password);
      setToken(res.access_token);
      Alert.alert("Logged in", "Success.");
    } catch (e: any) {
      Alert.alert("Login failed", String(e.message || e));
    }
  }

  async function createRunOffline() {
    const id = uuidv4();
    const started_at = new Date().toISOString();
    const distance_m = Math.round(parseFloat(distanceKm || "0") * 1000);
    const duration_s = Math.round(parseFloat(durationMin || "0") * 60);

    const w: Workout = {
      id,
      type: "run",
      started_at,
      notes: notes || null,
      distance_m: isFinite(distance_m) ? distance_m : null,
      duration_s: isFinite(duration_s) ? duration_s : null,
      rpe: null,
      version: 0,
      updated_at: null,
      deleted_at: null,
    };

    await upsertLocalWorkout(w);

    await enqueueOp({
      op_id: uuidv4(),
      type: "UPSERT_WORKOUT",
      entity_id: id,
      payload: {
        id,
        type: "run",
        started_at,
        notes: notes || null,
        distance_m: w.distance_m,
        duration_s: w.duration_s,
        rpe: null,
        version: 0,
      },
      client_updated_at: Date.now(),
    });

    setNotes("");
    await refreshWorkouts();
  }

  async function createLiftOffline() {
    const id = uuidv4();
    const started_at = new Date().toISOString();

    const w: Workout = {
      id,
      type: "lift",
      started_at,
      notes: notes || null,
      version: 0,
      updated_at: null,
      deleted_at: null,
    };

    await upsertLocalWorkout(w);

    await enqueueOp({
      op_id: uuidv4(),
      type: "UPSERT_WORKOUT",
      entity_id: id,
      payload: {
        id,
        type: "lift",
        started_at,
        notes: notes || null,
        version: 0,
      },
      client_updated_at: Date.now(),
    });

    setNotes("");
    await refreshWorkouts();
  }

  async function handleSyncNow() {
    if (!token) {
      Alert.alert("Not logged in", "Login first so we can sync.");
      return;
    }
    try {
      const res = await syncNow(token);
      await refreshWorkouts();
      Alert.alert("Sync complete", JSON.stringify(res));
    } catch (e: any) {
      Alert.alert("Sync failed", String(e.message || e));
    }
  }

  const header = useMemo(() => {
    return (
      <View style={{ padding: 12, gap: 8 }}>
        <Text style={{ fontSize: 20, fontWeight: "700" }}>Offline Fitness Log</Text>
        <Text>Network: {isOnline ? "Online" : "Offline"}</Text>
        <Text>Auth: {token ? "Logged in" : "Not logged in"}</Text>
      </View>
    );
  }, [isOnline, token]);

  if (!ready) {
    return (
      <SafeAreaView style={{ flex: 1, padding: 16 }}>
        <Text>Initializing...</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1 }}>
      {header}

      {!token && (
        <View style={{ padding: 12, gap: 8 }}>
          <Text style={{ fontWeight: "700" }}>Login / Signup</Text>
          <TextInput
            value={email}
            onChangeText={setEmail}
            placeholder="email"
            autoCapitalize="none"
            style={{ borderWidth: 1, padding: 8, borderRadius: 8 }}
          />
          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="password"
            secureTextEntry
            style={{ borderWidth: 1, padding: 8, borderRadius: 8 }}
          />
          <View style={{ flexDirection: "row", gap: 10 }}>
            <Button title="Signup" onPress={handleSignup} />
            <Button title="Login" onPress={handleLogin} />
          </View>
        </View>
      )}

      <View style={{ padding: 12, gap: 8 }}>
        <Text style={{ fontWeight: "700" }}>Create workout (offline-first)</Text>
        <TextInput
          value={notes}
          onChangeText={setNotes}
          placeholder="notes (optional)"
          style={{ borderWidth: 1, padding: 8, borderRadius: 8 }}
        />

        <View style={{ flexDirection: "row", gap: 10 }}>
          <TextInput
            value={distanceKm}
            onChangeText={setDistanceKm}
            placeholder="distance km"
            keyboardType="numeric"
            style={{ borderWidth: 1, padding: 8, borderRadius: 8, flex: 1 }}
          />
          <TextInput
            value={durationMin}
            onChangeText={setDurationMin}
            placeholder="duration min"
            keyboardType="numeric"
            style={{ borderWidth: 1, padding: 8, borderRadius: 8, flex: 1 }}
          />
        </View>

        <View style={{ flexDirection: "row", gap: 10 }}>
          <Button title="Save Run (Offline)" onPress={createRunOffline} />
          <Button title="Save Lift (Offline)" onPress={createLiftOffline} />
        </View>

        <Button title="Sync Now" onPress={handleSyncNow} />
      </View>

      <View style={{ paddingHorizontal: 12, paddingBottom: 8 }}>
        <Text style={{ fontWeight: "700" }}>Local workouts</Text>
      </View>

      <FlatList
        data={workouts}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 12, gap: 8 }}
        renderItem={({ item }) => (
          <View style={{ borderWidth: 1, borderRadius: 10, padding: 10 }}>
            <Text style={{ fontWeight: "700" }}>
              {item.type.toUpperCase()} — v{item.version ?? 0}
            </Text>
            <Text>{item.started_at}</Text>
            {item.distance_m != null && <Text>Distance: {item.distance_m} m</Text>}
            {item.duration_s != null && <Text>Duration: {item.duration_s} s</Text>}
            {item.notes ? <Text>Notes: {item.notes}</Text> : null}
          </View>
        )}
      />
    </SafeAreaView>
  );
}
