export type ChatResponse = {
  sessionId: string;
  reply: string;
  turnsRetained: number;
};
import { API_BASE_URL, DEMO_MODE } from "./client";

function getDemoReply(text: string): string {
  const lower = text.toLowerCase();

  if (lower.includes("hello") || lower.includes("hi")) {
    return "Good evening. Jarvis interface is operating in workshop demo mode.";
  }

  if (lower.includes("what can you do")) {
    return "On Day 2, I will connect to the backend for AI chat, voice and safe actions.";
  }

  return `Demo mode received your message: "${text}".`;
}

export async function sendChatMessage(sessionId: string, text: string): Promise<ChatResponse> {
  if (DEMO_MODE) {
    await new Promise((resolve) => setTimeout(resolve, 700));

    return {
      sessionId,
      reply: getDemoReply(text),
      turnsRetained: 0,
    };
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId, text }),
    });
  } catch {
    throw new Error("Jarvis service is unavailable. Please try again shortly.");
  }

  if (!response.ok) {
    const body: { detail?: string } = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Jarvis could not process that message.");
  }

  return response.json() as Promise<ChatResponse>;
}
