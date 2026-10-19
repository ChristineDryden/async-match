import axios from "axios";
import http from "./http";

export interface ChatReply {
  reply: string;
  response_id: string;
  model: string;
  tools_used: string[];
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export async function sendChat(messages: ChatTurn[]) {
  try {
    const res = await http.post<ChatReply>(
      "/api/chat",
      { messages },
      { timeout: 180_000 },
    );
    return res.data;
  } catch (err) {
    if (axios.isAxiosError(err)) {
      const data = err.response?.data as { error?: string } | undefined;
      throw new Error(data?.error || err.message);
    }
    throw err;
  }
}
