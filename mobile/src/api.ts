export const API_URL = "http://192.168.1.20:8000";
; 
// Android emulator: http://10.0.2.2:8000
// Physical device: http://YOUR_LAPTOP_IP:8000

export async function signup(email: string, password: string) {
  const res = await fetch(`${API_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function login(email: string, password: string) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
