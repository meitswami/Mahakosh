"use client";

import { Plug, Wifi, WifiOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { AccountingConnector } from "@/services/accounting-api";

const STATUS_VARIANT: Record<string, "success" | "destructive" | "warning" | "secondary"> = {
  connected: "success",
  disconnected: "secondary",
  error: "destructive",
  connecting: "warning",
};

export function ConnectionsPanel({
  connections,
  onSync,
  syncing,
}: {
  connections: AccountingConnector[] | undefined;
  onSync: (id: string) => void;
  syncing: boolean;
}) {
  if (!connections?.length) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        No Tally connections yet. Connect using a connector type below.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {connections.map((conn) => (
        <Card key={conn.id}>
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                {conn.status === "connected" ? (
                  <Wifi className="h-4 w-4 text-primary" />
                ) : (
                  <WifiOff className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
              <div>
                <p className="text-sm font-medium">{conn.name}</p>
                <p className="text-xs text-muted-foreground">
                  {conn.connector_type} · priority {conn.priority}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={STATUS_VARIANT[conn.status] || "secondary"}>{conn.status}</Badge>
              <Button size="sm" variant="outline" disabled={syncing} onClick={() => onSync(conn.id)}>
                <Plug className="mr-1 h-3 w-3" />
                Sync
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
