"use client";

import { useState } from "react";
import {
  Calculator,
  Building2,
  BookOpen,
  Package,
  FileText,
  GitCompare,
  RefreshCw,
  Plus,
  ShieldCheck,
  Database,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConnectionsPanel } from "@/components/accounting/connections-panel";
import { CompanyBrowser } from "@/components/accounting/company-browser";
import { DataBrowser } from "@/components/accounting/data-browser";
import { VoucherCenter } from "@/components/accounting/voucher-center";
import { MappingCenter } from "@/components/accounting/mapping-center";
import { SyncDashboard } from "@/components/accounting/sync-dashboard";
import { DataQualityPanel } from "@/components/accounting/data-quality-panel";
import { DigitalTwinBrowser } from "@/components/accounting/digital-twin-browser";
import {
  useConnectorTypes,
  useAccountingConnectors,
  useAccountingOverview,
  useTallyCompanies,
  useAccountingLedgers,
  useAccountingItems,
  useAccountingVouchers,
  useLedgerMappings,
  useItemMappings,
  useConnectAccounting,
  useSyncAccounting,
  useImportAccounting,
  useApproveVoucher,
  useTwinOverview,
  useTwinLedgers,
  useTwinItems,
  useTwinParties,
  useTwinIssues,
  useNormalizeTwin,
  useResolveTwinIssue,
} from "@/hooks/use-accounting";

type Tab = "overview" | "data-quality" | "digital-twin";

export default function AccountingPage() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [selectedConnector, setSelectedConnector] = useState<string>("");
  const { data: connectorTypes } = useConnectorTypes();
  const { data: overview } = useAccountingOverview();
  const { data: connections } = useAccountingConnectors();
  const activeConnector = selectedConnector || connections?.[0]?.id || "";
  const { data: companies } = useTallyCompanies(activeConnector || undefined);
  const { data: ledgers } = useAccountingLedgers();
  const { data: items } = useAccountingItems();
  const { data: vouchers } = useAccountingVouchers();
  const { data: ledgerMappings } = useLedgerMappings(activeConnector || undefined);
  const { data: itemMappings } = useItemMappings(activeConnector || undefined);

  const { data: twinOverview } = useTwinOverview();
  const { data: twinLedgers } = useTwinLedgers(1, activeConnector || undefined);
  const { data: twinItems } = useTwinItems(1, activeConnector || undefined);
  const { data: twinParties } = useTwinParties(1, activeConnector || undefined);
  const { data: twinIssues } = useTwinIssues();

  const connectAccounting = useConnectAccounting();
  const syncAccounting = useSyncAccounting();
  const importAccounting = useImportAccounting();
  const approveVoucher = useApproveVoucher();
  const normalizeTwin = useNormalizeTwin();
  const resolveTwinIssue = useResolveTwinIssue();

  const handleConnect = async (connectorType: string) => {
    const result = await connectAccounting.mutateAsync({
      name: `Tally ${connectorType}`,
      connector_type: connectorType,
      config: { endpoint: "http://localhost:9000", allow_offline_fallback: true },
      priority: 1,
    });
    if (result.connector_id) {
      setSelectedConnector(result.connector_id);
    }
  };

  const handleSync = (connectorId: string) => {
    syncAccounting.mutate({
      connector_id: connectorId,
      sync_type: "ledgers",
      mode: "manual",
    });
  };

  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: "overview", label: "Overview", icon: Calculator },
    { id: "data-quality", label: "Data Quality", icon: ShieldCheck },
    { id: "digital-twin", label: "Digital Twin", icon: Database },
  ];

  return (
    <>
      <Header
        title="Accounting Center"
        description="ज्ञान से निर्णय तक — intelligence layer above Tally"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="flex gap-2 border-b pb-2">
            {tabs.map(({ id, label, icon: Icon }) => (
              <Button
                key={id}
                variant={activeTab === id ? "default" : "ghost"}
                size="sm"
                onClick={() => setActiveTab(id)}
              >
                <Icon className="mr-1.5 h-4 w-4" />
                {label}
              </Button>
            ))}
          </div>

          {activeTab === "overview" && (
            <OverviewTab
              overview={overview}
              connections={connections}
              connectorTypes={connectorTypes}
              companies={companies}
              ledgers={ledgers}
              items={items}
              vouchers={vouchers}
              ledgerMappings={ledgerMappings}
              itemMappings={itemMappings}
              connectAccounting={connectAccounting}
              syncAccounting={syncAccounting}
              importAccounting={importAccounting}
              approveVoucher={approveVoucher}
              activeConnector={activeConnector}
              onConnect={handleConnect}
              onSync={handleSync}
            />
          )}

          {activeTab === "data-quality" && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShieldCheck className="h-4 w-4" />
                  Data Quality
                </CardTitle>
              </CardHeader>
              <CardContent>
                <DataQualityPanel
                  overview={twinOverview}
                  issues={twinIssues?.items}
                  onResolve={(issueId) =>
                    resolveTwinIssue.mutate({
                      issueId,
                      resolution: "Reviewed and acknowledged by user",
                    })
                  }
                  onNormalize={() =>
                    normalizeTwin.mutate({
                      connector_id: activeConnector || undefined,
                      entity_types: ["ledger", "stock_item", "party", "voucher"],
                    })
                  }
                  resolving={resolveTwinIssue.isPending}
                  normalizing={normalizeTwin.isPending}
                />
              </CardContent>
            </Card>
          )}

          {activeTab === "digital-twin" && (
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <BookOpen className="h-4 w-4" />
                    Normalized Ledgers
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <DigitalTwinBrowser
                    title={`${twinLedgers?.total ?? 0} twin ledgers`}
                    objects={twinLedgers?.items}
                    emptyMessage="Import ledgers to populate the digital twin."
                    renderMeta={(obj) => {
                      const g = obj.normalized_fields.parent_group as string | undefined;
                      const bal = obj.normalized_fields.current_balance as number | undefined;
                      return g ? `${g}${bal !== undefined ? ` · ₹${bal.toLocaleString("en-IN")}` : ""}` : null;
                    }}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Package className="h-4 w-4" />
                    Normalized Items
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <DigitalTwinBrowser
                    title={`${twinItems?.total ?? 0} twin items`}
                    objects={twinItems?.items}
                    emptyMessage="Import stock items to populate the digital twin."
                    renderMeta={(obj) => {
                      const hsn = obj.normalized_fields.hsn_code as string | undefined;
                      const rate = obj.normalized_fields.gst_rate as number | undefined;
                      if (hsn) return `HSN ${hsn}${rate !== undefined ? ` · ${rate}%` : ""}`;
                      return rate !== undefined ? `${rate}% GST` : null;
                    }}
                  />
                </CardContent>
              </Card>

              <Card className="lg:col-span-2">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Building2 className="h-4 w-4" />
                    Normalized Parties
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <DigitalTwinBrowser
                    title={`${twinParties?.total ?? 0} twin parties`}
                    objects={twinParties?.items}
                    emptyMessage="Import vendors/customers to populate party records."
                    renderMeta={(obj) => {
                      const gstin = obj.normalized_fields.gstin as string | undefined;
                      const ptype = obj.normalized_fields.party_type as string | undefined;
                      return gstin || ptype || null;
                    }}
                  />
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function OverviewTab({
  overview,
  connections,
  connectorTypes,
  companies,
  ledgers,
  items,
  vouchers,
  ledgerMappings,
  itemMappings,
  connectAccounting,
  syncAccounting,
  importAccounting,
  approveVoucher,
  activeConnector,
  onConnect,
  onSync,
}: {
  overview: ReturnType<typeof useAccountingOverview>["data"];
  connections: ReturnType<typeof useAccountingConnectors>["data"];
  connectorTypes: ReturnType<typeof useConnectorTypes>["data"];
  companies: ReturnType<typeof useTallyCompanies>["data"];
  ledgers: ReturnType<typeof useAccountingLedgers>["data"];
  items: ReturnType<typeof useAccountingItems>["data"];
  vouchers: ReturnType<typeof useAccountingVouchers>["data"];
  ledgerMappings: ReturnType<typeof useLedgerMappings>["data"];
  itemMappings: ReturnType<typeof useItemMappings>["data"];
  connectAccounting: ReturnType<typeof useConnectAccounting>;
  syncAccounting: ReturnType<typeof useSyncAccounting>;
  importAccounting: ReturnType<typeof useImportAccounting>;
  approveVoucher: ReturnType<typeof useApproveVoucher>;
  activeConnector: string;
  onConnect: (type: string) => void;
  onSync: (id: string) => void;
}) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Calculator} label="Connections" value={overview?.connectors ?? connections?.length ?? 0} />
        <StatCard icon={Building2} label="Companies" value={overview?.connected_companies ?? companies?.length ?? 0} />
        <StatCard icon={BookOpen} label="Ledgers" value={overview?.ledger_count ?? ledgers?.total ?? 0} />
        <StatCard icon={Package} label="Items" value={overview?.item_count ?? items?.total ?? 0} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Calculator className="h-4 w-4" />
                Tally Connections
              </CardTitle>
              <div className="flex gap-1">
                {(connectorTypes?.connectors ?? []).slice(0, 2).map((ct) => (
                  <Button
                    key={ct.connector_type}
                    size="sm"
                    variant="outline"
                    disabled={connectAccounting.isPending}
                    onClick={() => onConnect(ct.connector_type)}
                  >
                    <Plus className="mr-1 h-3 w-3" />
                    {ct.name}
                  </Button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ConnectionsPanel
              connections={connections}
              onSync={onSync}
              syncing={syncAccounting.isPending}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <RefreshCw className="h-4 w-4" />
              Sync Dashboard
            </CardTitle>
          </CardHeader>
          <CardContent>
            <SyncDashboard
              overview={overview}
              loading={syncAccounting.isPending || importAccounting.isPending}
              onImport={() =>
                activeConnector &&
                importAccounting.mutate({
                  connector_id: activeConnector,
                  entity_type: "ledgers",
                  persist: true,
                })
              }
              onExport={() =>
                activeConnector &&
                syncAccounting.mutate({
                  connector_id: activeConnector,
                  sync_type: "trial_balance",
                  mode: "manual",
                })
              }
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Building2 className="h-4 w-4" />
            Company Browser
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CompanyBrowser companies={companies} />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <BookOpen className="h-4 w-4" />
              Ledger Browser
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DataBrowser
              title={`${ledgers?.total ?? 0} ledgers`}
              emptyMessage="No ledgers imported yet."
              rows={(ledgers?.items ?? []).map((l) => ({
                id: l.id,
                name: l.name,
                subtitle: l.parent_group,
                meta: `₹${l.current_balance.toLocaleString("en-IN")}`,
                badge: l.ledger_type,
              }))}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Package className="h-4 w-4" />
              Item Browser
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DataBrowser
              title={`${items?.total ?? 0} items`}
              emptyMessage="No stock items imported yet."
              rows={(items?.items ?? []).map((i) => ({
                id: i.id,
                name: i.name,
                subtitle: i.hsn_code ? `HSN ${i.hsn_code}` : null,
                meta: i.gst_rate ? `${i.gst_rate}% GST` : null,
                badge: i.unit,
              }))}
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-4 w-4" />
            Voucher Center
          </CardTitle>
        </CardHeader>
        <CardContent>
          <VoucherCenter
            vouchers={vouchers?.items}
            onApprove={(id) => approveVoucher.mutate(id)}
            approving={approveVoucher.isPending}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <GitCompare className="h-4 w-4" />
            Mapping Center
          </CardTitle>
        </CardHeader>
        <CardContent>
          <MappingCenter ledgerMappings={ledgerMappings} itemMappings={itemMappings} />
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
