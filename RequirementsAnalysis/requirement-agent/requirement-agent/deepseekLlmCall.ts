interface DeepSeekChatCompletionResponse {
  choices?: Array<{
    message?: {
      content?: string;
    };
  }>;
}

export async function deepseekLlmCall(prompt: string): Promise<string> {
  const apiKey = process.env.DEEPSEEK_API_KEY;
  if (!apiKey) {
    throw new Error("DEEPSEEK_API_KEY is not configured");
  }

  const response = await fetch("https://api.deepseek.com/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: process.env.DEEPSEEK_MODEL || "deepseek-v4-flash",
      messages: [
        {
          role: "system",
          content: "你是 Requirement Agent，只负责前端需求分析。你必须输出合法 JSON，不要输出 Markdown，不要输出代码块。",
        },
        {
          role: "user",
          content: prompt,
        },
      ],
      temperature: 0.2,
      stream: false,
    }),
  });

  const responseText = await response.text();
  if (!response.ok) {
    throw new Error(`DeepSeek API request failed with status ${response.status}: ${responseText}`);
  }

  const data = JSON.parse(responseText) as DeepSeekChatCompletionResponse;
  const content = data.choices?.[0]?.message?.content?.trim();
  if (!content) {
    throw new Error("DeepSeek returned empty content");
  }

  return content;
}
