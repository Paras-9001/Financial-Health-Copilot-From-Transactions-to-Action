export type User = {
  id: string;
  email: string;
  name: string | null;
  preferred_buffer_days: number;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

const base = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export async function api<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  let response: Response;
  const formData = options.body instanceof FormData;
  try {
    response = await fetch(`${base}/api/v1${path}`, {
      ...options,
      cache: "no-store",
      signal: AbortSignal.timeout(20000),
      headers: {
        ...(!formData ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(
      0,
      "connection_error",
      "Could not reach the server. Check the connection and try again.",
    );
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(
      response.status,
      body.error?.code ?? "request_failed",
      body.error?.message ?? "Please try again.",
      body.error?.details ?? {},
    );
  }
  return body as T;
}
