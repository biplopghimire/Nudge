// The parts of the Gemini REST API that Nudge uses.
// Docs: https://ai.google.dev/api/generate-content and https://ai.google.dev/api/embeddings

export type Part =
  | { text: string }
  | { inline_data: { mime_type: string; data: string } };  // base64 image

export type Content = {
  role?: "user" | "model";
  parts: Part[];
};

// POST /v1beta/models/{model}:generateContent
export type GenerateContentRequest = {
  systemInstruction?: Content;
  contents: Content[];
  generationConfig?: { temperature?: number; maxOutputTokens?: number };
};

export type GenerateContentResponse = {
  candidates?: {
    content?: { role: string; parts?: { text?: string }[] };
    finishReason?: string;  // "STOP", "MAX_TOKENS", "SAFETY", ...
  }[];
  usageMetadata?: {
    promptTokenCount: number;
    candidatesTokenCount?: number;
    totalTokenCount: number;
  };
  modelVersion?: string;
};

// POST /v1beta/models/{model}:embedContent
export type EmbedContentRequest = {
  content: Content;
  taskType?: "RETRIEVAL_QUERY" | "RETRIEVAL_DOCUMENT" | "SEMANTIC_SIMILARITY";
  outputDimensionality?: number;
};

export type EmbedContentResponse = {
  embedding: { values: number[] };
};

export type GeminiError = {
  error: { code: number; message: string; status: string };
};
