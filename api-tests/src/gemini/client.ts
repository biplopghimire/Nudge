import { env, requireEnv } from "../env.ts";
import type {
  EmbedContentRequest,
  EmbedContentResponse,
  GeminiError,
  GenerateContentRequest,
  GenerateContentResponse,
  Part,
} from "./types.ts";

const baseUrl = "https://generativelanguage.googleapis.com/v1beta";
export const chatModel = env("GEMINI_MODEL", "gemini-3.5-flash");
export const embeddingModel = env("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001");

// Same key the backend uses (NUDGE_GEMINI_API_KEY) also works here.
function apiKey(): string {
  return process.env.NUDGE_GEMINI_API_KEY?.trim() || requireEnv("GEMINI_API_KEY");
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${baseUrl}/${path}`, {
    method: "POST",
    // Key goes in a header, not the URL, so it never shows up in logs.
    headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey() },
    body: JSON.stringify(body),
  });
  const json = (await response.json()) as T | GeminiError;
  if (!response.ok) {
    const error = (json as GeminiError).error;
    throw new Error(`Gemini ${response.status} ${error?.status ?? ""}: ${error?.message ?? response.statusText}`);
  }
  return json as T;
}

/** All text parts of the first candidate, joined. */
export function replyText(response: GenerateContentResponse): string {
  const candidate = response.candidates?.[0];
  const text = candidate?.content?.parts?.map((p) => p.text ?? "").join("").trim();
  if (!text) throw new Error(`Gemini returned no text (finishReason: ${candidate?.finishReason ?? "none"})`);
  return text;
}

export async function generate(system: string, parts: Part[]): Promise<GenerateContentResponse> {
  const request: GenerateContentRequest = {
    systemInstruction: { parts: [{ text: system }] },
    contents: [{ role: "user", parts }],
    generationConfig: { temperature: 0.3 },
  };
  return post<GenerateContentResponse>(`models/${chatModel}:generateContent`, request);
}

export async function embed(text: string, dimensions = 768): Promise<number[]> {
  const request: EmbedContentRequest = {
    content: { parts: [{ text }] },
    taskType: "RETRIEVAL_QUERY",
    outputDimensionality: dimensions,
  };
  const response = await post<EmbedContentResponse>(`models/${embeddingModel}:embedContent`, request);
  return response.embedding.values;
}
