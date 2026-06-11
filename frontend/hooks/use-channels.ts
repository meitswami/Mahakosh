"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { channelsApi, type ChannelConnectRequest, type ChannelLinkRequest } from "@/services/channels-api";

export function useChannelDashboard() {
  return useQuery({
    queryKey: ["channels-dashboard"],
    queryFn: () => channelsApi.dashboard(),
    refetchInterval: 15000,
  });
}

export function useChannelHealth() {
  return useQuery({
    queryKey: ["channels-health"],
    queryFn: () => channelsApi.health(),
    refetchInterval: 30000,
  });
}

export function useChannelSessions(channelType?: string) {
  return useQuery({
    queryKey: ["channel-sessions", channelType],
    queryFn: () => channelsApi.sessions(channelType),
  });
}

export function useChannelMessages(sessionId?: string) {
  return useQuery({
    queryKey: ["channel-messages", sessionId],
    queryFn: () => channelsApi.messages(sessionId),
    enabled: !!sessionId,
  });
}

export function useConnectChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ChannelConnectRequest) => channelsApi.connect(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channels-dashboard"] });
      qc.invalidateQueries({ queryKey: ["channels-health"] });
    },
  });
}

export function useLinkChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ChannelLinkRequest) => channelsApi.link(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["channels-dashboard"] }),
  });
}

export function useChannelReceive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ channelType, message, sessionId }: { channelType: string; message: string; sessionId?: string }) =>
      channelsApi.receive(channelType, message, sessionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channel-sessions"] });
      qc.invalidateQueries({ queryKey: ["channel-messages"] });
    },
  });
}
