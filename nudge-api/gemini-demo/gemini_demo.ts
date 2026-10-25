interface GeminiResponse {
  candidates: {
    content: {
      parts: {
        text?: string;
      }[];
    };
  }[];
}

async function askGemini() {
  const apikey = process.env.NUDGE_GEMINI_API_KEY
  if (!apikey) {
    throw new Error("NUDGE_GEMINI_API_KEY is missing");
  }
  const response = await fetch(
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": apikey,
      },
      body: JSON.stringify({
        contents: [
          {
            parts: [{ text: "What is artificial intelligence in 2 sentences" }],
          },
        ],
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data: GeminiResponse = await response.json();

  console.log(data.candidates[0]?.content.parts[0]?.text);
}

askGemini()