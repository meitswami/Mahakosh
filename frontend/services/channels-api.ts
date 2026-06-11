import { apiFetch } from "@/lib/api";

export interface ChannelSummary {
  id: string;
  channel_type: string;
  name: string;
  status: string;
  bot_username: string | null;
  is_active: boolean;
  last_sync_at: string | null;
}

export interface ChannelSession {
  id: string;
  channel_type: string;
  external_chat_id: string;
  chat_session_id: string | null;
  status: string;
  message_count: number;
  last_message_at: string | null;
}

export interface ChannelMessage {
  id: string;
  channel_type: string;
  direction: string;
  content: string;
  intent: string | null;
  agents_used: string[];
  created_at: string;
}

export interface ChannelHealth {
  channel: string;
  status: string;
  configured: boolean;
  capabilities?: Record<string, boolean>;
}

export interface ChannelDashboard {
  connected_channels: ChannelSummary[];
  active_sessions: number;
  total_messages: number;
  active_users: number;
  recent_notifications: Array<{
    id: string;
    channel: string;
    event: string;
    title: string;
    status: string;
    created_at: string;
  }>;
  channel_health: ChannelHealth[];
  rate_limits: Record<string, unknown>;
}

export interface ChannelConnectRequest {
  channel_type: string;
  name: string;
  config?: Record<string, unknown>;
  webhook_url?: string;
}

export interface ChannelLinkRequest {
  channel_type: string;
  external_user_id: string;
  external_chat_id: string;
  external_username?: string;
}

export const channelsApi = {
  dashboard: () => apiFetch<ChannelDashboard>("/channels/dashboard"),

  health: () => apiFetch<ChannelHealth[]>("/channels/health"),

  sessions: (channelType?: string) => {
    const params = channelType ? `?channel_type=${channelType}` : "";
    return apiFetch<ChannelSession[]>(`/channels/sessions${params}`);
  },

  messages: (sessionId?: string, limit = 50) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (sessionId) params.set("session_id", sessionId);
    return apiFetch<ChannelMessage[]>(`/channels/messages?${params}`);
  },

  connect: (data: ChannelConnectRequest) =>
    apiFetch<ChannelSummary>("/channels/connect", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  link: (data: ChannelLinkRequest) =>
    apiFetch<{ linked: boolean; channel_user_id?: string }>("/channels/link", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  send: (channelType: string, externalChatId: string, message: string) =>
    apiFetch<Record<string, unknown>>("/channels/send", {
      method: "POST",
      body: JSON.stringify({
        channel_type: channelType,
        external_chat_id: externalChatId,
        message,
      }),
    }),

  receive: (channelType: string, message: string, sessionId?: string) =>
    apiFetch<{
      text: string;
      session_id: string | null;
      chat_session_id: string | null;
      agents_used: string[];
      processing_time_ms: number;
    }>("/channels/receive", {
      method: "POST",
      body: JSON.stringify({
        channel_type: channelType,
        message,
        session_id: sessionId,
      }),
    }),
};
