"use client";

import { useCallback, useRef, useState } from "react";
import {
  BookOpen,
  Search,
  Upload,
  Database,
  FileText,
  Layers,
  History,
  Network,
  Sparkles,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useKnowledgeOverview,
  useKnowledgeCollections,
  useKnowledgeGraph,
  useKnowledgeUpload,
} from "@/hooks/use-knowledge";
import { knowledgeApi, type KnowledgeSearchResult } from "@/services/knowledge-api";

const SEARCH_MODES = [
  { value: "hybrid", label: "Hybrid" },
  { value: "semantic", label: "Semantic" },
  { value: "keyword", label: "Keyword" },
  { value: "metadata", label: "Metadata" },
];

export default function KnowledgePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMode, setSearchMode] = useState("hybrid");
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[]>([]);
  const [searchMeta, setSearchMeta] = useState<{ ms: number; total: number } | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: overview, isLoading: overviewLoading } = useKnowledgeOverview();
  const { data: collections } = useKnowledgeCollections();
  const { data: graph } = useKnowledgeGraph(selectedDocId);
  const uploadMutation = useKnowledgeUpload();

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await knowledgeApi.search(searchQuery.trim(), searchMode);
      setSearchResults(res.results);
      setSearchMeta({ ms: res.processing_time_ms, total: res.total_found });
      if (res.results.length > 0) {
        setSelectedDocId(res.results[0].document_id);
      }
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery, searchMode]);

  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      await uploadMutation.mutateAsync({ file });
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [uploadMutation],
  );

  return (
    <>
      <Header
        title="Knowledge Base"
        description="ज्ञान से निर्णय तक — hybrid search, citations, and business intelligence"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={FileText}
              label="Indexed Documents"
              value={overview?.total_documents ?? 0}
              loading={overviewLoading}
            />
            <StatCard
              icon={Layers}
              label="Knowledge Chunks"
              value={overview?.total_chunks ?? 0}
              loading={overviewLoading}
            />
            <StatCard
              icon={History}
              label="Search Queries"
              value={overview?.total_queries ?? 0}
              loading={overviewLoading}
            />
            <StatCard
              icon={Database}
              label="Collections"
              value={overview?.collections?.length ?? collections?.length ?? 0}
              loading={overviewLoading}
            />
          </div>

          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search invoices, vendors, GST records, documents..."
                    className="pl-9"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  />
                </div>
                <div className="flex gap-2">
                  {SEARCH_MODES.map((m) => (
                    <Button
                      key={m.value}
                      variant={searchMode === m.value ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSearchMode(m.value)}
                    >
                      {m.label}
                    </Button>
                  ))}
                  <Button onClick={handleSearch} disabled={isSearching || !searchQuery.trim()}>
                    <Sparkles className="mr-2 h-4 w-4" />
                    {isSearching ? "Searching..." : "Search"}
                  </Button>
                </div>
              </div>
              {searchMeta && (
                <p className="mt-2 text-xs text-muted-foreground">
                  {searchMeta.total} results in {searchMeta.ms}ms
                </p>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-12">
            <div className="space-y-6 lg:col-span-8">
              {searchResults.length > 0 ? (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Search Results</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {searchResults.map((result) => (
                      <div
                        key={result.chunk_id}
                        className="cursor-pointer rounded-lg border p-4 transition-colors hover:bg-muted/50"
                        onClick={() => setSelectedDocId(result.document_id)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="font-medium">{result.document_title}</p>
                            <p className="text-xs text-muted-foreground">
                              {result.document_type} · {result.source_name}
                              {result.page_number != null && ` · Page ${result.page_number}`}
                            </p>
                          </div>
                          <Badge variant="secondary">{(result.score * 100).toFixed(0)}%</Badge>
                        </div>
                        <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">{result.content}</p>
                        {result.citation && (
                          <p className="mt-2 text-xs text-primary">{result.citation.citation_text}</p>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-16">
                    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
                      <BookOpen className="h-7 w-7 text-primary" />
                    </div>
                    <h3 className="mt-4 text-lg font-semibold">Search your business knowledge</h3>
                    <p className="mt-1 max-w-md text-center text-sm text-muted-foreground">
                      Hybrid search combines keyword, vector, and metadata retrieval with BGE reranking.
                    </p>
                  </CardContent>
                </Card>
              )}

              {selectedDocId && graph && (graph.nodes.length > 0 || graph.edges.length > 0) && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Network className="h-4 w-4" />
                      Knowledge Graph
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Nodes</p>
                        <div className="space-y-1">
                          {graph.nodes.map((node) => (
                            <div key={node.id} className="flex items-center gap-2 text-sm">
                              <Badge variant="outline">{node.type}</Badge>
                              <span>{node.label}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Relationships</p>
                        <div className="space-y-1">
                          {graph.edges.map((edge, i) => (
                            <p key={i} className="text-sm text-muted-foreground">
                              {edge.source} → {edge.target}{" "}
                              <span className="text-foreground">({edge.type})</span>
                            </p>
                          ))}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

            <div className="space-y-6 lg:col-span-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between pb-3">
                  <CardTitle className="text-base">Index Document</CardTitle>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt,.csv,.xlsx,.xls,.json"
                    className="hidden"
                    onChange={handleUpload}
                  />
                  <Button
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadMutation.isPending}
                  >
                    <Upload className="mr-2 h-4 w-4" />
                    {uploadMutation.isPending ? "Indexing..." : "Upload"}
                  </Button>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">
                    PDF · DOCX · TXT · CSV · Excel · JSON — chunked, embedded, and indexed in Qdrant.
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Collections</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {(collections || overview?.collections || []).map((col) => (
                    <div
                      key={col.id}
                      className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                    >
                      <div>
                        <p className="font-medium">{col.name}</p>
                        <p className="text-xs text-muted-foreground">{col.slug}</p>
                      </div>
                      <Badge variant="secondary">{col.document_count}</Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Top Sources</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {(overview?.top_sources || []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No sources indexed yet.</p>
                  ) : (
                    overview?.top_sources.map((src) => (
                      <div key={src.source} className="flex justify-between text-sm">
                        <span>{src.source}</span>
                        <Badge variant="outline">{src.count}</Badge>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Recent Queries</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {(overview?.recent_queries || []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No queries yet.</p>
                  ) : (
                    overview?.recent_queries.map((q, i) => (
                      <div key={i} className="rounded-md border px-3 py-2">
                        <p className="text-sm font-medium line-clamp-1">{q.query}</p>
                        <p className="text-xs text-muted-foreground">
                          {q.mode} · {q.results} results
                        </p>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>
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
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold">{loading ? "—" : value.toLocaleString()}</p>
        </div>
      </CardContent>
    </Card>
  );
}
