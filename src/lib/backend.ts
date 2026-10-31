import "server-only";


function backendConfig(): { baseUrl: string; token: string } {
  const baseUrl = process.env.MONTAGNE_BACKEND_URL?.replace(/\/$/, "");
  const token = process.env.MONTAGNE_BACKEND_TOKEN;
  if (!baseUrl || !token) {
    throw new Error("Montagne backend environment is not configured");
  }
  return { baseUrl, token };
}

export async function fetchBackend(path: string): Promise<Response> {
  const { baseUrl, token } = backendConfig();
  return fetch(`${baseUrl}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  });
}
