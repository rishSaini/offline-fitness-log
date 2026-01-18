import AsyncStorage from "@react-native-async-storage/async-storage";
import { resetLocalDb } from "./db";

const LAST_SYNC_KEY = "last_sync_ms";

export async function devResetAllLocal() {
  await resetLocalDb();
  await AsyncStorage.removeItem(LAST_SYNC_KEY);
}
