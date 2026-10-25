// Gemini API test (Sprint 3, Part 6).
// Run: npm run gemini            (needs GEMINI_API_KEY in .env)
//
// 1. Ask a student question with "hints only" on and print the reply
// 2. Send a photo of handwritten work and print the reply
// 3. Embed one sentence and check it has 768 numbers

import { readFile } from "node:fs/promises";

import { chatModel, embed, embeddingModel, generate, replyText } from "./gemini/client.ts";

const photoPath = process.argv[2] ?? new URL("../samples/handwritten-work.jpg", import.meta.url).pathname;

// The same rules the backend sends on every question (Part 4).
const SYSTEM_RULES = [
  "You are Nudge, a study assistant for one course.",
  "Use only the course material provided.",
  "Use the same notation and methods as the course material.",
  "Cite the file and page for each point, like (Lecture 6, p. 4).",
  "If the material does not cover the question, say so instead of guessing.",
  "Hints only is ON: give hints and questions, never the final answer.",
].join("\n");

// Stand-ins for the chunks the backend would find with its two searches.
const COURSE_MATERIAL = `
[Lecture 6 - Substitution, page 4]
For an integral of a product f(g(x)) g'(x), let u = g(x), so du = g'(x) dx.
Rewrite the integral in terms of u, integrate, then substitute back to x.

[Problem Set 4, page 1]
Problem 3. Evaluate the integral of x cos(x^2) dx. Show your substitution.
`.trim();

function heading(text: string) {
  console.log(`\n=== ${text} ===`);
}

function mimeFor(path: string): string {
  if (/\.png$/i.test(path)) return "image/png";
  if (/\.(heic|heif)$/i.test(path)) return "image/heic";
  if (/\.webp$/i.test(path)) return "image/webp";
  return "image/jpeg";
}

async function main() {
  console.log(`Chat model: ${chatModel}. Embedding model: ${embeddingModel}.`);

  heading("1. Question with hints only");
  const question = "What's the answer to problem 3 on PS 4? I don't get the integral.";
  console.log(`Student: ${question}`);
  const textReply = await generate(SYSTEM_RULES, [
    { text: `Course material:\n${COURSE_MATERIAL}\n\nStudent question: ${question}` },
  ]);
  console.log(`Nudge: ${replyText(textReply)}`);
  console.log(`(tokens: ${textReply.usageMetadata?.totalTokenCount ?? "?"}, model: ${textReply.modelVersion ?? chatModel})`);

  heading("2. Photo of handwritten work");
  const photo = await readFile(photoPath);
  console.log(`Photo: ${photoPath} (${Math.round(photo.length / 1024)} KB)`);
  const photoReply = await generate(SYSTEM_RULES, [
    { text: `Course material:\n${COURSE_MATERIAL}\n\nHere is my work on problem 3. Is it right?` },
    { inline_data: { mime_type: mimeFor(photoPath), data: photo.toString("base64") } },
  ]);
  console.log(`Nudge: ${replyText(photoReply)}`);

  heading("3. Embedding");
  const sentence = "For an integral of a product, let u = g(x) so du = g'(x) dx.";
  const vector = await embed(sentence, 768);
  console.log(`"${sentence}"`);
  console.log(`Length: ${vector.length} ${vector.length === 768 ? "(matches vector(768) in the chunks table)" : "(expected 768!)"}`);
  console.log(`First 5 values: [${vector.slice(0, 5).map((v) => v.toFixed(4)).join(", ")}]`);
  if (vector.length !== 768) process.exit(1);
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
