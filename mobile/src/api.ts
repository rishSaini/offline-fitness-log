export const API_URL = "https://thick-carpets-wink.loca.lt";
; 
type TokenResponse = { access_token: string; token_type: string };

async function parseError(res: Response) {
  const text = await res.text();
  try {
    const j = JSON.parse(text);
    return j?.detail ? JSON.stringify(j.detail) : text;
  } catch {
    return text;
  }
}

export async function signup(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function login(email: string, password: string) {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
