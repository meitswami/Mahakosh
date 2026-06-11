"use client";

import { useCallback, useEffect, useState } from "react";
import { platformApi, type TenantRow } from "@/services/platform-api";

export function usePlatformDashboard() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await platformApi.dashboard());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load platform dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, loading, error, refresh };
}

export function useTenants() {
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const result = await platformApi.listTenants(page);
      setTenants(result.tenants);
      setTotal(result.total);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { tenants, total, loading, refresh };
}

export function useUsage(days = 30) {
  const [usage, setUsage] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    platformApi.usage(days).then(setUsage).finally(() => setLoading(false));
  }, [days]);

  return { usage, loading };
}

export function useCompliance(tenantId: string | undefined) {
  const [compliance, setCompliance] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!tenantId) return;
    setLoading(true);
    platformApi.compliance(tenantId).then(setCompliance).finally(() => setLoading(false));
  }, [tenantId]);

  return { compliance, loading };
}
