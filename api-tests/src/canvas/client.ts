import { requireEnv, env } from "../env.ts";
import type { CanvasError } from "./types.ts";

const token = requireEnv("CANVAS_API_TOKEN");
const domain = env("CANVAS_DOMAIN", "canvas.cmu.edu");
const baseUrl = `https://${domain}/api/v1`;

function buildUrl(path: string, params: Record<string, string | string[]> = {}): string {
  const url = new URL(baseUrl + path);
  for (const [key, value] of Object.entries(params)) {
    for (const v of Array.isArray(value) ? value : [value]) url.searchParams.append(key, v);
  }
  return url.toString();
}

async function request(url: string): Promise<Response> {
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as CanvasError | null;
    const message = body?.errors?.map((e) => e.message).join("; ") || response.statusText;
    throw new Error(`Canvas ${response.status} for ${url}: ${message}`);
  }
  return response;
}

// Link: <https://...&page=2>; rel="next", <https://...>; rel="last"
export function nextLink(linkHeader: string | null): string | null {
  if (!linkHeader) return null;
  for (const part of linkHeader.split(",")) {
    const match = part.match(/<([^>]+)>;\s*rel="next"/);
    if (match) return match[1];
  }
  return null;
}

/** GET one object. */
export async function canvasGet<T>(path: string, params?: Record<string, string | string[]>): Promise<T> {
  const response = await request(buildUrl(path, params));
  return (await response.json()) as T;
}

/** GET a list, following the "next" link until there is none. */
export async function canvasGetAll<T>(
  path: string,
  params: Record<string, string | string[]> = {},
): Promise<{ items: T[]; pages: number }> {
  let url: string | null = buildUrl(path, { per_page: "50", ...params });
  const items: T[] = [];
  let pages = 0;
  while (url) {
    const response = await request(url);
    items.push(...((await response.json()) as T[]));
    pages += 1;
    url = nextLink(response.headers.get("link"));
  }
  return { items, pages };
}

/** Download a file's bytes from the temporary link in CanvasFile.url. */
export async function canvasDownload(fileUrl: string): Promise<Uint8Array> {
  const response = await fetch(fileUrl, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error(`Canvas download ${response.status} for file`);
  return new Uint8Array(await response.arrayBuffer());
}
