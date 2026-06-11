"use client";

import { useState } from "react";
import {
  Radio,
  MessageSquare,
  Users,
  Upload,
  Bell,
  Send,
  Link2,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  useChannelDashboard,
  useChannelHealth,
  useChannelReceive,
  useChannelSessions,
  useConnectChannel,
} from "@/hooks/use-channels";

const CHANNEL_ICONS: Record<string, string> = {
  telegram: "✈️",
  whatsapp: "💬",
  email: "📧",
  webchat: "🌐",
  voice: "🎙️",
  mobile: "📱",
};

const STATUS_VARIANT: Record<string, "success" | "destructive" | "warning" | "secondary" | "default"> = {
  delivered: "success",
  active: "success",
  configured: "success",
  pending: "warning",
  failed: "destructive",
  inactive: "secondary",
  not_configured: "secondary",
};

export default function ChannelsPage() {
  const { data: dashboard, isLoading } = useChannelDashboard();
  const { data: health } = useChannelHealth();
  const { data: sessions } = useChannelSessions();
  const connectChannel = useConnectChannel();
  const channelReceive = useChannelReceive();

  const [connectName, setConnectName] = useState("");
  const [connectType, setConnectType] = useState("telegram");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [testMessage, setTestMessage] = useState("Show GST Summary");

  const handleConnect = async () => {
    if (!connectName.trim()) return;
    await connectChannel.mutateAsync({
      channel_type: connectType,
      name: connectName,
      webhook_url: webhookUrl || undefined,
    });
    setConnectName("");
  };

  const handleTestWebChat = async () => {
    if (!testMessage.trim()) return;
    await channelReceive.mutateAsync({ channelType: "webchat", message: testMessage });
  };

  return (
    <>
      <Header
        title="Channel Center"
        description="ज्ञान से निर्णय तक — omnichannel communication across Telegram, WhatsApp, Email, and Web"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={Radio}
              label="Connected Channels"
              value={dashboard?.connected_channels.length ?? 0}
              loading={isLoading}
            />
            <StatCard
              icon={MessageSquare}
              label="Total Messages"
              value={dashboard?.total_messages ?? 0}
              loading={isLoading}
            />
            <StatCard
              icon={Users}
              label="Active Users"
              value={dashboard?.active_users ?? 0}
              loading={isLoading}
            />
            <StatCard
              icon={Bell}
              label="Active Sessions"
              value={dashboard?.active_sessions ?? 0}
              loading={isLoading}
              accent
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Radio className="h-4 w-4" />
                  Channel Health
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2">
                  {(health ?? dashboard?.channel_health ?? []).map((ch) => (
                    <div
                      key={ch.channel}
                      className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/30 px-4 py-3"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-lg">{CHANNEL_ICONS[ch.channel] ?? "📡"}</span>
                        <div>
                          <p className="text-sm font-medium capitalize">{ch.channel}</p>
                          <p className="text-xs text-muted-foreground">
                            {ch.configured ? "Configured" : "Not configured"}
                          </p>
                        </div>
                      </div>
                      <HealthIcon status={ch.status} />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Link2 className="h-4 w-4" />
                  Connect Channel
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <select
                  value={connectType}
                  onChange={(e) => setConnectType(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="telegram">Telegram</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="email">Email</option>
                  <option value="webchat">Web Chat</option>
                </select>
                <Input
                  placeholder="Channel name"
                  value={connectName}
                  onChange={(e) => setConnectName(e.target.value)}
                />
                <Input
                  placeholder="Webhook base URL (optional)"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                />
                <Button
                  className="w-full"
                  onClick={handleConnect}
                  disabled={connectChannel.isPending || !connectName.trim()}
                >
                  {connectChannel.isPending ? "Connecting…" : "Connect"}
                </Button>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <MessageSquare className="h-4 w-4" />
                  Connected Channels
                </CardTitle>
              </CardHeader>
              <CardContent>
                {dashboard?.connected_channels.length ? (
                  <div className="space-y-2">
                    {dashboard.connected_channels.map((ch) => (
                      <div
                        key={ch.id}
                        className="flex items-center justify-between rounded-lg border border-border/60 px-4 py-3"
                      >
                        <div className="flex items-center gap-3">
                          <span>{CHANNEL_ICONS[ch.channel_type] ?? "📡"}</span>
                          <div>
                            <p className="text-sm font-medium">{ch.name}</p>
                            <p className="text-xs text-muted-foreground capitalize">
                              {ch.channel_type}
                              {ch.bot_username ? ` · @${ch.bot_username}` : ""}
                            </p>
                          </div>
                        </div>
                        <Badge variant={STATUS_VARIANT[ch.status] ?? "secondary"}>
                          {ch.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No channels connected yet. Connect Telegram, WhatsApp, or Email above.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Bell className="h-4 w-4" />
                  Recent Notifications
                </CardTitle>
              </CardHeader>
              <CardContent>
                {dashboard?.recent_notifications.length ? (
                  <div className="space-y-2">
                    {dashboard.recent_notifications.map((n) => (
                      <div
                        key={n.id}
                        className="flex items-start justify-between gap-3 rounded-lg border border-border/60 px-4 py-3"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{n.title}</p>
                          <p className="text-xs text-muted-foreground">
                            {n.channel} · {n.event.replace(/_/g, " ")}
                          </p>
                        </div>
                        <Badge variant={STATUS_VARIANT[n.status] ?? "secondary"} className="shrink-0">
                          {n.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Workflow and OCR notifications will appear here.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Send className="h-4 w-4" />
                  Web Chat Test
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  placeholder="Ask Mahakosh anything…"
                  value={testMessage}
                  onChange={(e) => setTestMessage(e.target.value)}
                  rows={3}
                />
                <Button
                  onClick={handleTestWebChat}
                  disabled={channelReceive.isPending || !testMessage.trim()}
                >
                  {channelReceive.isPending ? "Processing…" : "Send via Web Chat"}
                </Button>
                {channelReceive.data && (
                  <div className="rounded-lg bg-muted/50 p-3 text-sm">
                    <p className="font-medium text-muted-foreground">Response</p>
                    <p className="mt-1 whitespace-pre-wrap">{channelReceive.data.text}</p>
                    {channelReceive.data.agents_used.length > 0 && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        Agents: {channelReceive.data.agents_used.join(", ")}
                      </p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Upload className="h-4 w-4" />
                  Active Sessions
                </CardTitle>
              </CardHeader>
              <CardContent>
                {sessions?.length ? (
                  <div className="space-y-2">
                    {sessions.slice(0, 8).map((s) => (
                      <div
                        key={s.id}
                        className="flex items-center justify-between rounded-lg border border-border/60 px-4 py-2.5"
                      >
                        <div>
                          <p className="text-sm font-medium capitalize">{s.channel_type}</p>
                          <p className="text-xs text-muted-foreground">
                            {s.message_count} messages
                          </p>
                        </div>
                        <Badge variant={STATUS_VARIANT[s.status] ?? "secondary"}>{s.status}</Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Cross-channel sessions appear here when users interact via Telegram, WhatsApp, or Web.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  loading,
  accent,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  loading?: boolean;
  accent?: boolean;
}) {
  return (
    <Card className={accent ? "border-primary/30 bg-primary/5" : undefined}>
      <CardContent className="flex items-center gap-4 p-5">
        <div className={`rounded-lg p-2.5 ${accent ? "bg-primary/10" : "bg-muted"}`}>
          <Icon className={`h-5 w-5 ${accent ? "text-primary" : "text-muted-foreground"}`} />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold tabular-nums">
            {loading ? "—" : value}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function HealthIcon({ status }: { status: string }) {
  if (status === "healthy" || status === "configured" || status === "active") {
    return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
  }
  if (status === "degraded" || status === "simulated") {
    return <AlertCircle className="h-5 w-5 text-amber-500" />;
  }
  return <XCircle className="h-5 w-5 text-muted-foreground" />;
}
