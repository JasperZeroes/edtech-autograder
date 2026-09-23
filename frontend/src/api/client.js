const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const ACCESS_TOKEN_KEY = "edtech.access_token";
const REFRESH_TOKEN_KEY = "edtech.refresh_token";

export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setTokens({ access_token, refresh_token }) {
  if (access_token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
  }

  if (refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
  }
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

function extractErrorMessage(payload, fallback) {
  if (!payload) return fallback;

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((item) => item.msg || JSON.stringify(item))
      .join(", ");
  }

  return fallback;
}

export async function apiRequest(
  path,
  {
    method = "GET",
    body,
    headers = {},
    authenticated = true,
  } = {},
) {
  const requestHeaders = new Headers(headers);
  const token = getAccessToken();

  if (authenticated && token) {
    requestHeaders.set("Authorization", `Bearer ${token}`);
  }

  let requestBody = body;

  if (
    body !== undefined &&
    body !== null &&
    !(body instanceof FormData) &&
    !(body instanceof URLSearchParams) &&
    typeof body !== "string"
  ) {
    requestHeaders.set("Content-Type", "application/json");
    requestBody = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: requestHeaders,
    body: requestBody,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    throw new ApiError(
      extractErrorMessage(payload, `Request failed with ${response.status}`),
      response.status,
      payload,
    );
  }

  return payload;
}

export async function loginRequest(email, password) {
  const body = new URLSearchParams({
    username: email,
    password,
  });

  return apiRequest("/auth/login", {
    method: "POST",
    body,
    authenticated: false,
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });
}

export { API_BASE_URL };
