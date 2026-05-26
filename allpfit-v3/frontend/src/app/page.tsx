"use client";

import { useState, useEffect, useRef, useCallback } from "react";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────
interface ImportStatus {
  last_import: string | null;
  records: number;
  filename: string | null;
}

interface Entry {
  id: string;
  source: string;
  entry_type: "debit" | "credit";
  amount: number;
  date: string;
  description: string | null;
  counterpart_name: string | null;
  dre_group: string;
  dre_label: string;
  is_stone_mdr: boolean;
}

interface EntriesPage {
  total: number;
  page: number;
  page_size: number;
  entries: Entry[];
}

interface SimilarNotif {
  counterpart: string | null;
  count: number;
  group: string;
  label: string;
}

interface ManualDREData {
  period: string;
  filename: string;
  imported_at: string | null;
  receita_caixa: number | null;
  salarios: number | null;
  inss_patronal: number | null;
  fgts: number | null;
  prolabore: number | null;
  aulas_coletivas: number | null;
  pessoal_total: number | null;
  capex: number | null;
  cmv: number | null;
  despesas_total: number | null;
  resultado_operacional: number | null;
  resultado_liquido: number | null;
  saldo_inicial_itau: number | null;
  saldo_final_itau: number | null;
  saldo_sicoob: number | null;
  aportes: number | null;
}

interface DashboardData {
  period: { from: string; to: string };
  import_status: {
    evo: ImportStatus;
    stone: ImportStatus;
    itau: ImportStatus;
  };
  kpis: {
    receita_bruta: number;
    mdr_estimado: number;
    receita_liquida: number;
    despesas_total: number;
    movimentos_capital: number;
    resultado: number;
    margem_resultado_pct: number;
  };
  dre: {
    receita_por_tipo: Array<{ label: string; count: number; amount: number }>;
    mdr_detail: {
      evo_receita_total: number;
      stone_credits_total: number;
      evo_cartao_total: number;
      stone_vs_evo_diff: number;
    };
    despesas_por_grupo: Array<{ group: string; count: number; amount: number }>;
    despesas_detalhe: Array<{ group: string; label: string; count: number; amount: number }>;
    evo_inadimplencia: {
      total: number;
      paid: number;
      open: number;
      overdue: number;
      paid_amount: number;
      open_amount: number;
      overdue_amount: number;
    };
  };
  fluxo_caixa: {
    itau_entradas: number;
    itau_entradas_qty: number;
    itau_saidas: number;
    itau_saidas_qty: number;
    itau_liquido: number;
    stone_recebido: number;
    financeiro_recebido: number;
  };
  qualidade_dados: {
    unclassified_count: number;
    unclassified_amount: number;
  };
  manual_dre: ManualDREData | null;
  category_rules: Array<{
    id: number;
    keyword: string;
    dre_group: string;
    dre_label: string;
    priority: number;
  }>;
  generated_at: string;
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function brl(v: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);
}

function pct(v: number, decimals = 1) {
  return `${v.toFixed(decimals)}%`;
}

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso + "T12:00:00").toLocaleDateString("pt-BR");
}

function getMonthRange(): { from: string; to: string } {
  const now = new Date();
  const from = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const to = last.toISOString().slice(0, 10);
  return { from, to };
}

const DRE_LABELS: Record<string, string[]> = {
  "Pessoal":         ["Pessoal / RH", "Salários", "Pró-labore", "FGTS", "INSS", "Aulas Coletivas"],
  "Ocupação":        ["Aluguel e Ocupação", "IPTU", "Condomínio"],
  "Operacional":     ["Energia e Água", "Manutenção e Materiais", "Boletos", "Suprimentos"],
  "Tecnologia":      ["Sistema e Tecnologia", "Software / SaaS", "Infraestrutura TI"],
  "Financeiro":      ["Tarifas Bancárias", "Empréstimos e Mútuo", "Juros e IOF"],
  "Marketing":       ["Marketing", "Publicidade", "Redes Sociais"],
  "Administrativo":  ["Contabilidade", "Seguros", "Impostos e Taxas", "Direitos Autorais"],
  "CAPEX":           ["Financiamento Equipamentos", "Investimento"],
  "Transferências":  ["Transferências", "PIX Enviado", "Royalties / Franquia"],
  "Aplicações Financeiras": ["Aplicação Automática"],
  "Outros":          ["Não Classificado"],
};

const DRE_GROUPS = [
  "Pessoal",
  "Ocupação",
  "Operacional",
  "Tecnologia",
  "Financeiro",
  "Marketing",
  "Administrativo",
  "CAPEX",
  "Transferências",
  "Outros",
];

// ─────────────────────────────────────────────
// Spinner Component
// ─────────────────────────────────────────────
function Spinner({ size = "sm" }: { size?: "sm" | "md" }) {
  const cls = size === "sm" ? "w-4 h-4" : "w-6 h-6";
  return (
    <svg
      className={`animate-spin ${cls} text-blue-500`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

// ─────────────────────────────────────────────
// Skeleton Loader
// ─────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
      <div className="h-3 bg-gray-200 rounded w-1/2 mb-3" />
      <div className="h-7 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-3 bg-gray-200 rounded w-1/3" />
    </div>
  );
}

// ─────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────
export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [importing, setImporting] = useState<Record<string, boolean>>({});
  const [importMsg, setImportMsg] = useState<Record<string, { type: "success" | "error"; text: string } | null>>({});
  const [showRules, setShowRules] = useState(false);
  const [newRule, setNewRule] = useState({ keyword: "", dre_group: "Operacional", dre_label: "" });
  const [reclassifying, setReclassifying] = useState(false);
  const [dragOver, setDragOver] = useState<Record<string, boolean>>({});

  // ── Lançamentos tab state ──────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<"dashboard" | "lancamentos">("dashboard");
  const [entriesData, setEntriesData] = useState<EntriesPage | null>(null);
  const [entriesLoading, setEntriesLoading] = useState(false);
  const [entryFilter, setEntryFilter] = useState({
    source: "", entryType: "", dreGroup: "", search: "", onlyUnclassified: false,
    dateFrom: "", dateTo: "", page: 1, pageSize: 50,
  });
  const [editingEntry, setEditingEntry] = useState<{ id: string; group: string; label: string } | null>(null);
  const [savingEntry, setSavingEntry] = useState(false);
  const [similarNotif, setSimilarNotif] = useState<SimilarNotif | null>(null);
  const [bulkClassifying, setBulkClassifying] = useState(false);

  const evoRef = useRef<HTMLInputElement>(null);
  const stoneRef = useRef<HTMLInputElement>(null);
  const itauRef = useRef<HTMLInputElement>(null);
  const dreManualRef = useRef<HTMLInputElement>(null);

  const fileRefs: Record<string, React.RefObject<HTMLInputElement | null>> = {
    evo: evoRef,
    stone: stoneRef,
    itau: itauRef,
    "dre-manual": dreManualRef,
  };

  // Auto-dismiss import messages after 5 seconds
  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    Object.entries(importMsg).forEach(([source, msg]) => {
      if (msg) {
        const t = setTimeout(() => {
          setImportMsg((p) => ({ ...p, [source]: null }));
        }, 5000);
        timers.push(t);
      }
    });
    return () => timers.forEach(clearTimeout);
  }, [importMsg]);

  const loadDashboard = useCallback(
    async (from?: string, to?: string) => {
      setLoading(true);
      setError(null);
      try {
        const df = from ?? dateFrom;
        const dt = to ?? dateTo;
        const qs = new URLSearchParams({ date_from: df, date_to: dt });
        const res = await fetch(`${API}/dashboard?${qs}`);
        if (!res.ok) throw new Error(`Erro ${res.status}`);
        setData(await res.json());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erro ao carregar");
      } finally {
        setLoading(false);
      }
    },
    [dateFrom, dateTo]
  );

  useEffect(() => {
    const { from, to } = getMonthRange();
    setDateFrom(from);
    setDateTo(to);
    loadDashboard(from, to);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleFileUpload(source: string, file: File) {
    setImporting((p) => ({ ...p, [source]: true }));
    setImportMsg((p) => ({ ...p, [source]: null }));
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API}/import/${source}`, { method: "POST", body: form });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? "Erro ao importar");
      let msg: string;
      if (source === "dre-manual") {
        const periods: string[] = json.periods ?? [];
        msg = `✓ DRE Manual — ${periods.join(", ")} importado(s)`;
      } else {
        msg = `✓ ${json.records} registros importados`;
      }
      setImportMsg((p) => ({ ...p, [source]: { type: "success", text: msg } }));
      await loadDashboard();
    } catch (e) {
      setImportMsg((p) => ({
        ...p,
        [source]: { type: "error", text: e instanceof Error ? e.message : "Erro" },
      }));
    } finally {
      setImporting((p) => ({ ...p, [source]: false }));
    }
  }

  async function handleDeleteRule(id: number) {
    try {
      await fetch(`${API}/rules/${id}`, { method: "DELETE" });
      await loadDashboard();
    } catch {
      // silently fail
    }
  }

  async function handleAddRule() {
    if (!newRule.keyword.trim() || !newRule.dre_label.trim()) return;
    try {
      await fetch(`${API}/rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newRule),
      });
      setNewRule({ keyword: "", dre_group: "Operacional", dre_label: "" });
      await loadDashboard();
    } catch {
      // silently fail
    }
  }

  async function handleReclassify() {
    setReclassifying(true);
    try {
      await fetch(`${API}/reclassify`, { method: "PUT" });
      await loadDashboard();
    } catch {
      // silently fail
    } finally {
      setReclassifying(false);
    }
  }

  // ── Lançamentos functions ─────────────────────────────────────────────
  const loadEntries = useCallback(async (filter?: typeof entryFilter) => {
    setEntriesLoading(true);
    try {
      const f = filter ?? entryFilter;
      const qs = new URLSearchParams();
      if (f.source)           qs.set("source", f.source);
      if (f.entryType)        qs.set("entry_type", f.entryType);
      if (f.dreGroup)         qs.set("dre_group", f.dreGroup);
      if (f.onlyUnclassified) qs.set("only_unclassified", "true");
      if (f.search)           qs.set("search", f.search);
      if (f.dateFrom)         qs.set("date_from", f.dateFrom);
      if (f.dateTo)           qs.set("date_to", f.dateTo);
      qs.set("page", String(f.page));
      qs.set("page_size", String(f.pageSize));
      const res = await fetch(`${API}/entries?${qs}`);
      if (!res.ok) throw new Error("Erro ao carregar lançamentos");
      setEntriesData(await res.json());
    } catch {
      // silently fail
    } finally {
      setEntriesLoading(false);
    }
  }, [entryFilter]);

  async function handleUpdateEntry(entryId: string, group: string, label: string) {
    setSavingEntry(true);
    try {
      const res = await fetch(`${API}/entries/${entryId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dre_group: group, dre_label: label }),
      });
      const json = await res.json();
      setEditingEntry(null);
      // Update locally
      setEntriesData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          entries: prev.entries.map((e) =>
            e.id === entryId ? { ...e, dre_group: group, dre_label: label } : e
          ),
        };
      });
      // Show similar notification
      if (json.similar_unclassified > 0) {
        setSimilarNotif({
          counterpart: json.counterpart_name,
          count: json.similar_unclassified,
          group,
          label,
        });
      }
    } catch {
      // silently fail
    } finally {
      setSavingEntry(false);
    }
  }

  async function handleBulkClassify(counterpart: string | null, group: string, label: string) {
    setBulkClassifying(true);
    try {
      const body: Record<string, string> = { dre_group: group, dre_label: label };
      if (counterpart) body.counterpart_name = counterpart;
      await fetch(`${API}/entries/bulk-classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setSimilarNotif(null);
      await loadEntries();
    } catch {
      // silently fail
    } finally {
      setBulkClassifying(false);
    }
  }

  // ─── DropZone ───────────────────────────────
  function DropZone({
    source,
    icon,
    title,
    subtitle,
    acceptLabel,
    status,
  }: {
    source: string;
    icon: string;
    title: string;
    subtitle: string;
    acceptLabel: string;
    status: ImportStatus | undefined;
  }) {
    const ref = fileRefs[source];
    const isLoading = importing[source] ?? false;
    const isDragOver = dragOver[source] ?? false;
    const msg = importMsg[source] ?? null;

    return (
      <div className="flex flex-col gap-2">
        <div
          className={`relative border-2 border-dashed rounded-xl p-5 transition-colors cursor-pointer ${
            isDragOver
              ? "border-blue-400 bg-blue-50"
              : "border-gray-200 hover:border-gray-300 bg-white"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver((p) => ({ ...p, [source]: true }));
          }}
          onDragLeave={() => {
            setDragOver((p) => ({ ...p, [source]: false }));
          }}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver((p) => ({ ...p, [source]: false }));
            const file = e.dataTransfer.files[0];
            if (file) handleFileUpload(source, file);
          }}
          onClick={() => ref?.current?.click()}
        >
          <input
            type="file"
            className="hidden"
            ref={ref as React.RefObject<HTMLInputElement>}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileUpload(source, file);
              e.target.value = "";
            }}
          />

          <div className="flex items-start gap-3">
            <span className="text-2xl">{icon}</span>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-gray-800 text-sm">{title}</p>
              <p className="text-xs text-gray-500">{subtitle}</p>
              <p className="text-xs text-gray-400 mt-1">{acceptLabel}</p>
            </div>
            {isLoading && <Spinner />}
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100">
            {isLoading ? (
              <p className="text-xs text-blue-500">Importando...</p>
            ) : (
              <p className="text-xs text-gray-400 italic">Arraste ou clique para importar</p>
            )}
            {status && (
              <div className="mt-2">
                <p className="text-xs text-gray-500">
                  Último: {fmtDate(status.last_import)}
                </p>
                {status.records > 0 && (
                  <p className="text-xs text-gray-500">{status.records.toLocaleString("pt-BR")} registros</p>
                )}
                {status.filename && (
                  <p className="text-xs text-gray-400 truncate" title={status.filename}>
                    {status.filename}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {msg && (
          <div
            className={`text-xs px-3 py-2 rounded-lg ${
              msg.type === "success"
                ? "bg-green-50 text-green-700 border border-green-200"
                : "bg-red-50 text-red-700 border border-red-200"
            }`}
          >
            {msg.text}
          </div>
        )}
      </div>
    );
  }

  // ─── KPI Card ──────────────────────────────
  function KpiCard({
    label,
    value,
    sub,
    variant = "default",
  }: {
    label: string;
    value: string;
    sub?: string;
    variant?: "default" | "positive" | "negative";
  }) {
    const bg =
      variant === "positive"
        ? "bg-green-50 border-green-200"
        : variant === "negative"
        ? "bg-red-50 border-red-200"
        : "bg-white border-gray-200";
    const valueColor =
      variant === "positive"
        ? "text-green-700"
        : variant === "negative"
        ? "text-red-600"
        : "text-gray-900";

    return (
      <div className={`rounded-xl border p-5 ${bg}`}>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">{label}</p>
        <p className={`text-2xl font-bold ${valueColor} leading-tight`}>{value}</p>
        {sub && <p className={`text-sm mt-1 ${valueColor} opacity-75`}>{sub}</p>}
      </div>
    );
  }

  // ─────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────
  const kpis = data?.kpis;
  const dre = data?.dre;
  const inadimplencia = dre?.evo_inadimplencia;
  const importStatus = data?.import_status;

  const resultado = kpis?.resultado ?? 0;
  const resultadoVariant = resultado > 0 ? "positive" : resultado < 0 ? "negative" : "default";

  // Inadimplência bar widths
  const totalInad = inadimplencia?.total ?? 0;
  const paidW = totalInad > 0 ? ((inadimplencia?.paid ?? 0) / totalInad) * 100 : 0;
  const openW = totalInad > 0 ? ((inadimplencia?.open ?? 0) / totalInad) * 100 : 0;
  const overdueW = totalInad > 0 ? ((inadimplencia?.overdue ?? 0) / totalInad) * 100 : 0;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">

      {/* ── HEADER ── */}
      <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">💪</span>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Allp Fit Finance</h1>
            <p className="text-xs text-gray-500">Dashboard financeiro</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 text-sm text-gray-600">
            <label className="text-xs font-medium text-gray-500">De:</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="border border-gray-200 rounded-lg px-2 py-1 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <div className="flex items-center gap-1 text-sm text-gray-600">
            <label className="text-xs font-medium text-gray-500">Até:</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="border border-gray-200 rounded-lg px-2 py-1 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <button
            onClick={() => loadDashboard()}
            disabled={loading}
            className="flex items-center gap-1 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition-colors"
          >
            {loading ? <Spinner /> : <span>↺</span>}
            Atualizar
          </button>
        </div>
      </header>

      {/* ── TAB BAR ── */}
      <div className="flex gap-1 border-b border-gray-200">
        {(["dashboard", "lancamentos"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setActiveTab(tab);
              if (tab === "lancamentos" && !entriesData) {
                const f = { ...entryFilter, dateFrom, dateTo };
                setEntryFilter(f);
                loadEntries(f);
              }
            }}
            className={`px-5 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === tab
                ? "bg-white border border-b-white border-gray-200 text-blue-600 -mb-px"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab === "dashboard" ? "📊 Dashboard" : "📋 Lançamentos"}
          </button>
        ))}
      </div>

      {/* ── ERROR BANNER ── */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm flex items-center justify-between">
          <span>⚠ {error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 ml-4">✕</button>
        </div>
      )}

      {activeTab === "dashboard" && (<><section>
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
          Importar Dados
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <DropZone
            source="evo"
            icon="📊"
            title="EVO"
            subtitle="Recebíveis"
            acceptLabel="CSV / XLSX"
            status={importStatus?.evo}
          />
          <DropZone
            source="stone"
            icon="💳"
            title="Stone"
            subtitle="Extrato"
            acceptLabel="CSV / XLSX"
            status={importStatus?.stone}
          />
          <DropZone
            source="itau"
            icon="🏦"
            title="Itaú"
            subtitle="Extrato OFX"
            acceptLabel="OFX / CSV"
            status={importStatus?.itau}
          />
          <DropZone
            source="dre-manual"
            icon="📋"
            title="DRE Manual"
            subtitle="Planilha colaboradora"
            acceptLabel="XLSX (abas por mês)"
            status={data?.manual_dre ? {
              last_import: data.manual_dre.imported_at,
              records: 1,
              filename: data.manual_dre.filename,
            } : undefined}
          />
        </div>
      </section>

      {/* ── KPIs ── */}
      <section>
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
          Indicadores do Período
        </h2>
        {loading ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)}
          </div>
        ) : !data ? (
          <div className="bg-white border border-gray-200 rounded-xl p-10 text-center text-gray-400">
            <p className="text-4xl mb-3">📂</p>
            <p className="text-sm font-medium text-gray-500">Importe os arquivos para ver o resultado</p>
            <p className="text-xs text-gray-400 mt-1">Use os campos acima para carregar EVO, Stone e Itaú</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard
              label="Receita Bruta"
              value={brl(kpis?.receita_bruta ?? 0)}
            />
            <KpiCard
              label="MDR Stone"
              value={brl(kpis?.mdr_estimado ?? 0)}
              variant="default"
            />
            <KpiCard
              label="Despesas Oper."
              value={brl(kpis?.despesas_total ?? 0)}
            />
            <KpiCard
              label="Resultado"
              value={brl(resultado)}
              sub={pct(kpis?.margem_resultado_pct ?? 0)}
              variant={resultadoVariant}
            />
          </div>
        )}
      </section>

      {/* ── ALERTA NÃO CLASSIFICADOS ── */}
      {data && (data.qualidade_dados?.unclassified_count ?? 0) > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-xl">⚠</span>
            <div>
              <p className="text-sm font-semibold text-amber-800">
                {data.qualidade_dados.unclassified_count.toLocaleString("pt-BR")} lançamentos sem classificação
              </p>
              <p className="text-xs text-amber-600">
                Total de {brl(data.qualidade_dados.unclassified_amount)} sem categoria — isso afeta a precisão da DRE
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              setActiveTab("lancamentos");
              const f = { ...entryFilter, onlyUnclassified: true, dateFrom, dateTo, page: 1 };
              setEntryFilter(f);
              loadEntries(f);
            }}
            className="shrink-0 bg-amber-500 hover:bg-amber-600 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors"
          >
            Classificar agora →
          </button>
        </div>
      )}

      {/* ── CONFERÊNCIA DE CAIXA ── */}
      {data && data.fluxo_caixa && (
        <section className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wide">
              Conferência: Competência vs Caixa
            </h2>
            <span className="text-xs text-gray-400">Entradas e saídas reais por fonte</span>
          </div>

          <div className="px-6 py-5 grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* Coluna 1 — EVO vs Stone */}
            <div className="space-y-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Receita: EVO vs Stone</p>

              <div className="flex justify-between items-center py-2 bg-blue-50 rounded-lg px-3 text-sm">
                <span className="text-gray-700 font-medium">EVO (competência)</span>
                <span className="font-bold text-blue-700">{brl(data.kpis.receita_bruta)}</span>
              </div>

              <div className="flex justify-between items-center py-2 bg-emerald-50 rounded-lg px-3 text-sm">
                <span className="text-gray-700 font-medium">Stone (caixa recebido)</span>
                <span className="font-bold text-emerald-700">{brl(data.fluxo_caixa.stone_recebido)}</span>
              </div>

              {(() => {
                const evoCartao = data.dre.mdr_detail.evo_cartao_total;
                const stoneCash = data.fluxo_caixa.stone_recebido;
                const diff = stoneCash - evoCartao;
                const isNeg = diff < 0;
                return (
                  <div className={`flex flex-col px-3 py-2 rounded-lg ${isNeg ? "bg-red-50 border border-red-100" : "bg-gray-50"}`}>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">Divergência EVO cartão vs Stone</span>
                      <span className={`font-bold ${isNeg ? "text-red-600" : "text-green-600"}`}>{brl(diff)}</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {isNeg
                        ? `Stone recebeu ${brl(Math.abs(diff))} a menos — possível antecipação pendente ou inadimplência`
                        : `Stone recebeu ${brl(diff)} a mais que o EVO cartão`}
                    </p>
                  </div>
                );
              })()}

              {(data.fluxo_caixa.financeiro_recebido ?? 0) > 0 && (
                <div className="flex justify-between items-center py-2 bg-purple-50 rounded-lg px-3 text-sm">
                  <span className="text-gray-700 font-medium">Financeiro recebido (mútuo)</span>
                  <span className="font-bold text-purple-700">{brl(data.fluxo_caixa.financeiro_recebido)}</span>
                </div>
              )}
            </div>

            {/* Coluna 2 — Itaú */}
            <div className="space-y-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Itaú — Movimentação</p>

              <div className="flex justify-between items-center py-2 bg-green-50 rounded-lg px-3 text-sm">
                <div>
                  <span className="text-gray-700 font-medium">Entradas</span>
                  <span className="text-xs text-gray-400 ml-2">{data.fluxo_caixa.itau_entradas_qty} lanç.</span>
                </div>
                <span className="font-bold text-green-700">+{brl(data.fluxo_caixa.itau_entradas)}</span>
              </div>

              <div className="flex justify-between items-center py-2 bg-red-50 rounded-lg px-3 text-sm">
                <div>
                  <span className="text-gray-700 font-medium">Saídas operacionais</span>
                  <span className="text-xs text-gray-400 ml-2">{data.fluxo_caixa.itau_saidas_qty} lanç.</span>
                </div>
                <span className="font-bold text-red-600">-{brl(data.fluxo_caixa.itau_saidas)}</span>
              </div>

              {(() => {
                const liq = data.fluxo_caixa.itau_liquido;
                const isPos = liq >= 0;
                return (
                  <div className={`flex justify-between items-center py-2 rounded-lg px-3 text-sm font-semibold ${isPos ? "bg-green-100" : "bg-red-100"}`}>
                    <span className={isPos ? "text-green-800" : "text-red-800"}>Líquido Itaú no período</span>
                    <span className={isPos ? "text-green-700" : "text-red-600"}>{brl(liq)}</span>
                  </div>
                );
              })()}

              {/* Manual DRE saldo se disponível */}
              {data.manual_dre && (data.manual_dre.saldo_final_itau ?? 0) > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-100 space-y-1.5">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Saldos bancários (DRE Manual)</p>
                  {data.manual_dre.saldo_inicial_itau != null && (
                    <div className="flex justify-between text-xs text-gray-600 px-1">
                      <span>Saldo inicial Itaú</span>
                      <span className="font-mono">{brl(data.manual_dre.saldo_inicial_itau)}</span>
                    </div>
                  )}
                  {data.manual_dre.saldo_final_itau != null && (
                    <div className="flex justify-between text-xs text-gray-600 px-1">
                      <span>Saldo final Itaú</span>
                      <span className="font-mono font-semibold">{brl(data.manual_dre.saldo_final_itau)}</span>
                    </div>
                  )}
                  {data.manual_dre.saldo_sicoob != null && (
                    <div className="flex justify-between text-xs text-gray-600 px-1">
                      <span>Saldo Sicoob</span>
                      <span className="font-mono">{brl(data.manual_dre.saldo_sicoob)}</span>
                    </div>
                  )}
                  {data.manual_dre.saldo_final_itau != null && (
                    <div className="flex justify-between text-xs font-semibold text-gray-700 px-1 pt-1 border-t border-gray-100">
                      <span>Total caixa</span>
                      <span className="font-mono">{brl((data.manual_dre.saldo_final_itau ?? 0) + (data.manual_dre.saldo_sicoob ?? 0))}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* ── DRE ── */}
      {data && dre && (
        <section className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          {/* DRE Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wide">
              DRE — Demonstração do Resultado
            </h2>
            <span className="text-xs text-gray-400">
              {fmtDate(data.period.from)} – {fmtDate(data.period.to)}
            </span>
          </div>

          <div className="px-6 py-5 space-y-1 text-sm">

            {/* ── Receita Bruta ── */}
            <div className="flex items-center justify-between py-2 bg-blue-50 rounded-lg px-3 font-semibold text-gray-800">
              <span>(+) Receita Bruta</span>
              <span>{brl(kpis?.receita_bruta ?? 0)}</span>
            </div>

            {dre.receita_por_tipo.map((item) => {
              const total = kpis?.receita_bruta ?? 0;
              const parcela = total > 0 ? (item.amount / total) * 100 : 0;
              return (
                <div key={item.label} className="flex items-center justify-between pl-8 pr-3 py-1 text-gray-600 hover:bg-gray-50 rounded">
                  <span>· {item.label}</span>
                  <div className="flex items-center gap-6 text-right">
                    <span className="text-gray-400 text-xs w-20">{item.count} rec.</span>
                    <span className="w-28">{brl(item.amount)}</span>
                    <span className="text-gray-400 text-xs w-12">{pct(parcela)}</span>
                  </div>
                </div>
              );
            })}

            {/* ── MDR ── */}
            <div className="flex items-center justify-between py-2 px-3 font-semibold text-gray-800 mt-2">
              <span>(-) MDR Stone</span>
              <span>{brl(kpis?.mdr_estimado ?? 0)}</span>
            </div>
            <div className="pl-8 pr-3 py-1 text-gray-400 text-xs">
              EVO receita: {brl(dre.mdr_detail.evo_receita_total)} &nbsp;|&nbsp; Créditos Stone: {brl(dre.mdr_detail.stone_credits_total)}
            </div>

            {/* ── Receita Líquida ── */}
            <div className="flex items-center justify-between py-2 bg-blue-50 rounded-lg px-3 font-semibold text-blue-800 mt-2">
              <span>
                (=) Receita Líquida{" "}
                <span className="font-normal text-xs text-blue-500 ml-2">
                  margem {pct(kpis?.receita_bruta ? ((kpis.receita_liquida / kpis.receita_bruta) * 100) : 100)}
                </span>
              </span>
              <span>{brl(kpis?.receita_liquida ?? 0)}</span>
            </div>

            {/* Divider */}
            <div className="border-t border-gray-100 my-3" />

            {/* ── Despesas Operacionais ── */}
            <div className="flex items-center justify-between py-2 px-3 font-semibold text-gray-800">
              <span>(-) Despesas Operacionais</span>
              <span>{brl(kpis?.despesas_total ?? 0)}</span>
            </div>

            {dre.despesas_por_grupo
              .filter((g) => g.group !== "Aplicações Financeiras")
              .map((grupo) => {
                const totalDesp = kpis?.despesas_total ?? 0;
                const parcela = totalDesp > 0 ? (grupo.amount / totalDesp) * 100 : 0;
                return (
                  <div key={grupo.group} className="flex items-center justify-between pl-8 pr-3 py-1 text-gray-600 hover:bg-gray-50 rounded">
                    <span>· {grupo.group}</span>
                    <div className="flex items-center gap-6 text-right">
                      <span className="text-gray-400 text-xs w-20">{grupo.count} lanç.</span>
                      <span className="w-28">{brl(grupo.amount)}</span>
                      <span className="text-gray-400 text-xs w-12">{pct(parcela)}</span>
                    </div>
                  </div>
                );
              })}

            {/* Despesas detalhe — excluindo Aplicações Financeiras */}
            {dre.despesas_detalhe.filter((d) => d.group !== "Aplicações Financeiras").length > 0 && (
              <div className="mt-2 space-y-0.5">
                {dre.despesas_detalhe
                  .filter((d) => d.group !== "Aplicações Financeiras")
                  .map((d, i) => {
                    const totalDesp = kpis?.despesas_total ?? 0;
                    const parcela = totalDesp > 0 ? (d.amount / totalDesp) * 100 : 0;
                    return (
                      <div key={i} className="flex items-center justify-between pl-12 pr-3 py-0.5 text-xs text-gray-400 hover:bg-gray-50 rounded">
                        <span>{d.group} › {d.label}</span>
                        <div className="flex items-center gap-6 text-right">
                          <span className="w-20">{d.count} lanç.</span>
                          <span className="w-28">{brl(d.amount)}</span>
                          <span className="w-12">{pct(parcela)}</span>
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}

            {/* Divider */}
            <div className="border-t border-gray-100 my-3" />

            {/* ── Resultado ── */}
            <div
              className={`flex items-center justify-between py-3 rounded-xl px-4 font-bold text-base mt-2 ${
                resultado >= 0
                  ? "bg-green-50 text-green-800"
                  : "bg-red-50 text-red-700"
              }`}
            >
              <span>
                (=) RESULTADO DO PERÍODO{" "}
                <span className="font-normal text-sm ml-2 opacity-75">
                  margem {pct(kpis?.margem_resultado_pct ?? 0)}
                </span>
              </span>
              <span>{brl(resultado)}</span>
            </div>

            {/* ── Aplicações Financeiras (movimentos de capital) ── */}
            {(kpis?.movimentos_capital ?? 0) > 0 && (
              <div className="mt-3 pl-3 pr-3 py-2 bg-gray-50 rounded-lg border border-gray-100">
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span className="font-medium">(*) Aplicações Financeiras</span>
                  <span>{brl(kpis?.movimentos_capital ?? 0)}</span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  Movimentos de capital (APL APLIC automático) — não computados no resultado operacional
                </p>
              </div>
            )}

            {/* ── EVO Inadimplência ── */}
            {inadimplencia && (
              <div className="mt-6 pt-4 border-t border-gray-100">
                <h3 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">
                  EVO — Recebíveis (por vencimento)
                </h3>

                <div className="flex items-center gap-4 text-xs text-gray-600 mb-3 flex-wrap">
                  <span>
                    Total: <strong>{inadimplencia.total.toLocaleString("pt-BR")}</strong>
                  </span>
                  <span className="text-green-600">
                    Pagos: <strong>{inadimplencia.paid.toLocaleString("pt-BR")}</strong>{" "}
                    <span className="text-gray-400">({brl(inadimplencia.paid_amount)})</span>
                  </span>
                  <span className="text-yellow-600">
                    Em aberto: <strong>{inadimplencia.open.toLocaleString("pt-BR")}</strong>{" "}
                    <span className="text-gray-400">({brl(inadimplencia.open_amount)})</span>
                  </span>
                  <span className="text-red-600">
                    Vencidos: <strong>{inadimplencia.overdue.toLocaleString("pt-BR")}</strong>{" "}
                    <span className="text-gray-400">({brl(inadimplencia.overdue_amount)})</span>
                  </span>
                </div>

                {/* Bar visual */}
                <div className="flex h-3 rounded-full overflow-hidden bg-gray-100">
                  {paidW > 0 && (
                    <div
                      className="bg-green-400 transition-all duration-500"
                      style={{ width: `${paidW}%` }}
                      title={`Pagos: ${pct(paidW)}`}
                    />
                  )}
                  {openW > 0 && (
                    <div
                      className="bg-yellow-400 transition-all duration-500"
                      style={{ width: `${openW}%` }}
                      title={`Em aberto: ${pct(openW)}`}
                    />
                  )}
                  {overdueW > 0 && (
                    <div
                      className="bg-red-400 transition-all duration-500"
                      style={{ width: `${overdueW}%` }}
                      title={`Vencidos: ${pct(overdueW)}`}
                    />
                  )}
                </div>
                <div className="flex gap-4 mt-2 text-xs text-gray-400">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-400 inline-block" />Pagos {pct(paidW)}</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" />Em aberto {pct(openW)}</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" />Vencidos {pct(overdueW)}</span>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── DRE MANUAL ── */}
      {data?.manual_dre && (
        <section className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div>
              <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wide">
                DRE Manual — Visão da Colaboradora
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Regime de caixa · {data.manual_dre.period} · {data.manual_dre.filename}
              </p>
            </div>
            <span className="text-xs text-gray-300">{fmtDate(data.manual_dre.imported_at)}</span>
          </div>

          <div className="px-6 py-5 space-y-1 text-sm">

            {/* Receita caixa vs EVO */}
            {data.manual_dre.receita_caixa != null && (
              <>
                <div className="flex justify-between items-center py-2 bg-blue-50 rounded-lg px-3 font-semibold text-gray-800">
                  <span>Receita (caixa — planilha)</span>
                  <span>{brl(data.manual_dre.receita_caixa)}</span>
                </div>
                <div className="flex justify-between items-center pl-8 pr-3 py-1 text-xs text-gray-400">
                  <span>EVO competência (sistema)</span>
                  <span>{brl(data.kpis.receita_bruta)}</span>
                </div>
                <div className="flex justify-between items-center pl-8 pr-3 py-1 text-xs">
                  {(() => {
                    const diff = data.manual_dre.receita_caixa! - data.kpis.receita_bruta;
                    return (
                      <span className={diff < 0 ? "text-red-500" : "text-green-600"}>
                        Divergência: {brl(diff)} {diff < 0 ? "(caixa < competência)" : "(caixa > competência)"}
                      </span>
                    );
                  })()}
                </div>
                <div className="border-t border-gray-100 my-2" />
              </>
            )}

            {/* Pessoal */}
            {(data.manual_dre.pessoal_total ?? data.manual_dre.salarios) != null && (
              <>
                <div className="flex justify-between items-center py-1.5 px-3 font-semibold text-gray-700">
                  <span>(-) Pessoal</span>
                  <span>{brl(data.manual_dre.pessoal_total ?? (
                    (data.manual_dre.salarios ?? 0) +
                    (data.manual_dre.inss_patronal ?? 0) +
                    (data.manual_dre.fgts ?? 0) +
                    (data.manual_dre.prolabore ?? 0) +
                    (data.manual_dre.aulas_coletivas ?? 0)
                  ))}</span>
                </div>
                {[
                  { label: "Salários",        val: data.manual_dre.salarios },
                  { label: "Pró-labore",      val: data.manual_dre.prolabore },
                  { label: "INSS Patronal",   val: data.manual_dre.inss_patronal },
                  { label: "FGTS",            val: data.manual_dre.fgts },
                  { label: "Aulas Coletivas", val: data.manual_dre.aulas_coletivas },
                ].filter(i => i.val != null && i.val > 0).map(item => (
                  <div key={item.label} className="flex justify-between items-center pl-8 pr-3 py-0.5 text-xs text-gray-500">
                    <span>· {item.label}</span>
                    <span>{brl(item.val!)}</span>
                  </div>
                ))}
              </>
            )}

            {/* CAPEX */}
            {(data.manual_dre.capex ?? 0) > 0 && (
              <div className="flex flex-col px-3 py-2 bg-orange-50 border border-orange-100 rounded-lg mt-2">
                <div className="flex justify-between items-center text-sm font-semibold text-orange-800">
                  <span>CAPEX — Parcela Financiamento</span>
                  <span>{brl(data.manual_dre.capex!)}</span>
                </div>
                <p className="text-xs text-orange-600 mt-0.5">
                  Não é despesa operacional — é amortização de dívida de equipamentos
                </p>
              </div>
            )}

            {/* CMV */}
            {(data.manual_dre.cmv ?? 0) > 0 && (
              <div className="flex justify-between items-center pl-3 pr-3 py-1.5 text-sm text-gray-600">
                <span>(-) CMV / Produtos</span>
                <span>{brl(data.manual_dre.cmv!)}</span>
              </div>
            )}

            {/* Despesas total */}
            {data.manual_dre.despesas_total != null && (
              <div className="flex justify-between items-center py-1.5 px-3 font-semibold text-gray-700 mt-1">
                <span>(-) Despesas Totais (planilha)</span>
                <span>{brl(data.manual_dre.despesas_total)}</span>
              </div>
            )}

            {/* Resultado */}
            {data.manual_dre.resultado_liquido != null && (
              <div className={`flex justify-between items-center py-2 rounded-xl px-4 font-bold text-base mt-2 ${
                data.manual_dre.resultado_liquido >= 0 ? "bg-green-50 text-green-800" : "bg-red-50 text-red-700"
              }`}>
                <span>Resultado Líquido (planilha)</span>
                <span>{brl(data.manual_dre.resultado_liquido)}</span>
              </div>
            )}

            {/* Aportes */}
            {(data.manual_dre.aportes ?? 0) > 0 && (
              <div className="flex flex-col px-3 py-2 bg-purple-50 border border-purple-100 rounded-lg mt-2">
                <div className="flex justify-between items-center text-sm font-semibold text-purple-800">
                  <span>Aportes / Empréstimos recebidos</span>
                  <span>{brl(data.manual_dre.aportes!)}</span>
                </div>
                <p className="text-xs text-purple-600 mt-0.5">
                  Entradas financeiras — não contam como receita operacional
                </p>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── REGRAS DE CATEGORIZAÇÃO ── */}
      {data && (
        <section className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <button
            onClick={() => setShowRules((v) => !v)}
            className="w-full flex items-center justify-between px-6 py-4 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <span>{showRules ? "▲" : "▼"} REGRAS DE CATEGORIZAÇÃO</span>
            <span className="text-xs font-normal text-gray-400">
              {data.category_rules.length} regras
            </span>
          </button>

          {showRules && (
            <div className="px-6 pb-6 border-t border-gray-100">

              {/* Rules table */}
              {data.category_rules.length > 0 ? (
                <div className="overflow-x-auto mt-4">
                  <table className="w-full text-xs text-gray-600">
                    <thead>
                      <tr className="border-b border-gray-100 text-gray-400 uppercase tracking-wide">
                        <th className="text-left py-2 font-medium">Keyword</th>
                        <th className="text-left py-2 font-medium">Grupo</th>
                        <th className="text-left py-2 font-medium">Rótulo</th>
                        <th className="text-left py-2 font-medium">Prioridade</th>
                        <th className="py-2" />
                      </tr>
                    </thead>
                    <tbody>
                      {data.category_rules.map((rule) => (
                        <tr key={rule.id} className="border-b border-gray-50 hover:bg-gray-50">
                          <td className="py-2 font-mono text-gray-700">{rule.keyword}</td>
                          <td className="py-2">{rule.dre_group}</td>
                          <td className="py-2">{rule.dre_label}</td>
                          <td className="py-2 text-gray-400">{rule.priority}</td>
                          <td className="py-2 text-right">
                            <button
                              onClick={() => handleDeleteRule(rule.id)}
                              className="text-red-400 hover:text-red-600 font-medium px-2 py-0.5 rounded hover:bg-red-50 transition-colors"
                              title="Excluir regra"
                            >
                              ✕
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-gray-400 mt-4 italic">Nenhuma regra cadastrada.</p>
              )}

              {/* Add new rule form */}
              <div className="mt-5 pt-4 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  Nova Regra
                </p>
                <div className="flex flex-wrap gap-2 items-end">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Keyword (regex)</label>
                    <input
                      type="text"
                      placeholder="ex: folha|salário"
                      value={newRule.keyword}
                      onChange={(e) => setNewRule((r) => ({ ...r, keyword: e.target.value }))}
                      className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400 w-48"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Grupo DRE</label>
                    <select
                      value={newRule.dre_group}
                      onChange={(e) => setNewRule((r) => ({ ...r, dre_group: e.target.value }))}
                      className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
                    >
                      {DRE_GROUPS.map((g) => (
                        <option key={g} value={g}>{g}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-400">Rótulo</label>
                    <input
                      type="text"
                      placeholder="ex: Pessoal / RH"
                      value={newRule.dre_label}
                      onChange={(e) => setNewRule((r) => ({ ...r, dre_label: e.target.value }))}
                      className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400 w-40"
                    />
                  </div>
                  <button
                    onClick={handleAddRule}
                    disabled={!newRule.keyword.trim() || !newRule.dre_label.trim()}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-200 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition-colors"
                  >
                    Adicionar
                  </button>
                </div>
              </div>

              {/* Reclassify button */}
              <div className="mt-4">
                <button
                  onClick={handleReclassify}
                  disabled={reclassifying}
                  className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 disabled:bg-amber-200 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors"
                >
                  {reclassifying ? <Spinner /> : <span>↻</span>}
                  Reaplicar todas as regras aos lançamentos existentes
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      </>)}

      {/* ── ABA LANÇAMENTOS ── */}
      {activeTab === "lancamentos" && (
        <section className="space-y-4">

          {/* Similar notification banner */}
          {similarNotif && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="text-sm text-amber-800">
                <strong>{similarNotif.count}</strong> outros lançamentos com a mesma razão social
                {similarNotif.counterpart && <span className="font-mono ml-1">&ldquo;{similarNotif.counterpart}&rdquo;</span>}
                {" "}ainda estão como <em>Não Classificado</em>.
                Reclassificar todos como <strong>{similarNotif.group} › {similarNotif.label}</strong>?
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => handleBulkClassify(similarNotif.counterpart, similarNotif.group, similarNotif.label)}
                  disabled={bulkClassifying}
                  className="bg-amber-500 hover:bg-amber-600 disabled:bg-amber-200 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
                >
                  {bulkClassifying ? "..." : "Sim, reclassificar todos"}
                </button>
                <button
                  onClick={() => {
                    if (similarNotif.counterpart) {
                      setNewRule({ keyword: similarNotif.counterpart.toLowerCase().split(" ").slice(0, 3).join(" "), dre_group: similarNotif.group, dre_label: similarNotif.label });
                    }
                    setSimilarNotif(null);
                    setActiveTab("dashboard");
                    setShowRules(true);
                  }}
                  className="bg-white border border-amber-300 text-amber-700 text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-amber-50 transition-colors"
                >
                  Criar regra automática
                </button>
                <button onClick={() => setSimilarNotif(null)} className="text-amber-400 hover:text-amber-600 px-2">✕</button>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="bg-white border border-gray-200 rounded-xl px-5 py-4">
            <div className="flex flex-wrap gap-3 items-end">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400">De</label>
                <input type="date" value={entryFilter.dateFrom}
                  onChange={(e) => setEntryFilter((f) => ({ ...f, dateFrom: e.target.value, page: 1 }))}
                  className="border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400">Até</label>
                <input type="date" value={entryFilter.dateTo}
                  onChange={(e) => setEntryFilter((f) => ({ ...f, dateTo: e.target.value, page: 1 }))}
                  className="border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400">Fonte</label>
                <select value={entryFilter.source}
                  onChange={(e) => setEntryFilter((f) => ({ ...f, source: e.target.value, page: 1 }))}
                  className="border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400">
                  <option value="">Todas</option>
                  <option value="stone">Stone</option>
                  <option value="itau">Itaú</option>
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400">Tipo</label>
                <select value={entryFilter.entryType}
                  onChange={(e) => setEntryFilter((f) => ({ ...f, entryType: e.target.value, page: 1 }))}
                  className="border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400">
                  <option value="">Todos</option>
                  <option value="debit">Débito</option>
                  <option value="credit">Crédito</option>
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400">Categoria</label>
                <select value={entryFilter.dreGroup}
                  onChange={(e) => setEntryFilter((f) => ({ ...f, dreGroup: e.target.value, onlyUnclassified: false, page: 1 }))}
                  className="border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400">
                  <option value="">Todas</option>
                  {DRE_GROUPS.map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400">Busca</label>
                <input type="text" placeholder="Descrição ou razão social..." value={entryFilter.search}
                  onChange={(e) => setEntryFilter((f) => ({ ...f, search: e.target.value, page: 1 }))}
                  className="border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400 w-52" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400 invisible">.</label>
                <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-600 border border-gray-200 rounded-lg px-2 py-1.5 hover:bg-gray-50">
                  <input type="checkbox" checked={entryFilter.onlyUnclassified}
                    onChange={(e) => setEntryFilter((f) => ({ ...f, onlyUnclassified: e.target.checked, dreGroup: "", page: 1 }))}
                    className="accent-amber-500" />
                  Só não classificados
                </label>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-400 invisible">.</label>
                <button onClick={() => loadEntries()}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition-colors flex items-center gap-1">
                  {entriesLoading ? <Spinner /> : <span>↺</span>} Buscar
                </button>
              </div>
            </div>
          </div>

          {/* Results info */}
          {entriesData && (
            <div className="flex items-center justify-between text-xs text-gray-400 px-1">
              <span>{entriesData.total.toLocaleString("pt-BR")} lançamentos encontrados — página {entriesData.page} de {Math.ceil(entriesData.total / entriesData.page_size)}</span>
              <div className="flex gap-2">
                <button disabled={entryFilter.page <= 1}
                  onClick={() => { const f = { ...entryFilter, page: entryFilter.page - 1 }; setEntryFilter(f); loadEntries(f); }}
                  className="px-3 py-1 rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed">← Anterior</button>
                <button disabled={entriesData.total <= entryFilter.page * entryFilter.pageSize}
                  onClick={() => { const f = { ...entryFilter, page: entryFilter.page + 1 }; setEntryFilter(f); loadEntries(f); }}
                  className="px-3 py-1 rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed">Próxima →</button>
              </div>
            </div>
          )}

          {/* Entries table */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            {entriesLoading ? (
              <div className="flex items-center justify-center py-16 text-gray-400">
                <Spinner size="md" />
                <span className="ml-3 text-sm">Carregando...</span>
              </div>
            ) : !entriesData || entriesData.entries.length === 0 ? (
              <div className="py-16 text-center text-gray-400">
                <p className="text-3xl mb-3">🔍</p>
                <p className="text-sm">Nenhum lançamento encontrado.</p>
                <p className="text-xs mt-1">Ajuste os filtros e clique em Buscar.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-gray-700">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr className="text-gray-400 uppercase tracking-wide">
                      <th className="text-left px-4 py-3 font-medium">Data</th>
                      <th className="text-left px-4 py-3 font-medium">Fonte</th>
                      <th className="text-left px-4 py-3 font-medium">Descrição</th>
                      <th className="text-left px-4 py-3 font-medium">Razão Social</th>
                      <th className="text-right px-4 py-3 font-medium">Valor</th>
                      <th className="text-left px-4 py-3 font-medium w-64">Categoria</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {entriesData.entries.map((entry) => {
                      const isEditing = editingEntry?.id === entry.id;
                      const isUnclassified = entry.dre_group === "Outros" && entry.dre_label === "Não Classificado";
                      return (
                        <tr key={entry.id} className={`hover:bg-gray-50 transition-colors ${isUnclassified ? "bg-amber-50/40" : ""}`}>
                          <td className="px-4 py-2.5 whitespace-nowrap text-gray-500">{fmtDate(entry.date)}</td>
                          <td className="px-4 py-2.5">
                            <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${entry.source === "stone" ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700"}`}>
                              {entry.source.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 max-w-[180px] truncate text-gray-600" title={entry.description ?? ""}>{entry.description ?? "—"}</td>
                          <td className="px-4 py-2.5 max-w-[180px] truncate font-medium" title={entry.counterpart_name ?? ""}>{entry.counterpart_name ?? "—"}</td>
                          <td className={`px-4 py-2.5 text-right font-mono font-semibold whitespace-nowrap ${entry.entry_type === "credit" ? "text-green-600" : "text-red-600"}`}>
                            {entry.entry_type === "credit" ? "+" : "-"}{brl(entry.amount)}
                          </td>
                          <td className="px-4 py-2.5">
                            {isEditing ? (
                              <div className="flex items-center gap-1.5">
                                <select
                                  value={editingEntry.group}
                                  onChange={(e) => {
                                    const g = e.target.value;
                                    const labels = DRE_LABELS[g] ?? [];
                                    setEditingEntry((prev) => prev ? { ...prev, group: g, label: labels[0] ?? "" } : null);
                                  }}
                                  className="border border-blue-300 rounded px-1.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                                >
                                  {DRE_GROUPS.map((g) => <option key={g} value={g}>{g}</option>)}
                                </select>
                                <input
                                  type="text"
                                  value={editingEntry.label}
                                  onChange={(e) => setEditingEntry((prev) => prev ? { ...prev, label: e.target.value } : null)}
                                  list={`labels-${entry.id}`}
                                  placeholder="Rótulo"
                                  className="border border-blue-300 rounded px-1.5 py-1 text-xs w-36 focus:outline-none focus:ring-1 focus:ring-blue-400"
                                />
                                <datalist id={`labels-${entry.id}`}>
                                  {(DRE_LABELS[editingEntry.group] ?? []).map((l) => <option key={l} value={l} />)}
                                </datalist>
                                <button
                                  disabled={savingEntry || !editingEntry.label.trim()}
                                  onClick={() => handleUpdateEntry(entry.id, editingEntry.group, editingEntry.label)}
                                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-200 text-white px-2 py-1 rounded text-xs font-medium transition-colors"
                                >
                                  {savingEntry ? "..." : "OK"}
                                </button>
                                <button onClick={() => setEditingEntry(null)} className="text-gray-400 hover:text-gray-600 px-1">✕</button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setEditingEntry({ id: entry.id, group: entry.dre_group, label: entry.dre_label })}
                                className={`group flex items-center gap-2 text-left rounded-lg px-2 py-1 hover:bg-blue-50 transition-colors w-full ${isUnclassified ? "text-amber-600" : "text-gray-600"}`}
                                title="Clique para reclassificar"
                              >
                                <span className="flex-1 truncate">
                                  <span className="font-medium">{entry.dre_group}</span>
                                  {entry.dre_label && entry.dre_label !== "Não Classificado" && (
                                    <span className="text-gray-400"> › {entry.dre_label}</span>
                                  )}
                                  {isUnclassified && <span className="ml-1 text-amber-400">●</span>}
                                </span>
                                <span className="opacity-0 group-hover:opacity-100 text-blue-400 text-xs">✎</span>
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Bottom pagination */}
          {entriesData && entriesData.total > entryFilter.pageSize && (
            <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
              <button disabled={entryFilter.page <= 1}
                onClick={() => { const f = { ...entryFilter, page: entryFilter.page - 1 }; setEntryFilter(f); loadEntries(f); }}
                className="px-4 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-30">← Anterior</button>
              <span>Página {entryFilter.page} de {Math.ceil(entriesData.total / entryFilter.pageSize)}</span>
              <button disabled={entriesData.total <= entryFilter.page * entryFilter.pageSize}
                onClick={() => { const f = { ...entryFilter, page: entryFilter.page + 1 }; setEntryFilter(f); loadEntries(f); }}
                className="px-4 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-30">Próxima →</button>
            </div>
          )}
        </section>
      )}

      {/* ── FOOTER ── */}
      {data && (
        <footer className="text-center text-xs text-gray-400 pb-4">
          Atualizado: {fmtDate(data.generated_at.slice(0, 10))}{" "}
          {new Date(data.generated_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
          {" · "}
          Período: {fmtDate(data.period.from)} – {fmtDate(data.period.to)}
        </footer>
      )}
    </div>
  );
}
