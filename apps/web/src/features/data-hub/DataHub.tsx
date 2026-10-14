import { useCallback, useEffect, useRef, useState } from "react";
import { api, DatasetSummary, ImportStatus } from "../../app/api";

const SEVERITY_LABEL: Record<string, string> = {
  error: "Erro — bloqueia o commit",
  warning: "Aviso — não bloqueia",
  info: "Informativo",
};

function SeverityBadge({ severity, count }: { severity: string; count: number }) {
  const color = severity === "error" ? "var(--danger)" : severity === "warning" ? "var(--warn)" : "var(--text-muted)";
  return (
    <span
      style={{
        display: "inline-flex",
        gap: 6,
        alignItems: "center",
        border: `1px solid ${color}`,
        borderRadius: 999,
        padding: "2px 10px",
        fontSize: 13,
      }}
    >
      <strong>{count}</strong>
      <span>{SEVERITY_LABEL[severity] ?? severity}</span>
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const label: Record<string, string> = {
    uploaded: "Enviado",
    detected: "Esquema identificado",
    validated: "Validado",
    staged: "Pronto para commit / aguardando decisão",
    committed: "Comitado",
    rejected: "Rejeitado — corrigir e reimportar",
  };
  return <span className="mono">[{label[status] ?? status}]</span>;
}

export function DataHub() {
  const [importStatus, setImportStatus] = useState<ImportStatus | null>(null);
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshDatasets = useCallback(async () => {
    setDatasets(await api.listDatasets());
  }, []);

  useEffect(() => {
    refreshDatasets().catch(() => undefined);
  }, [refreshDatasets]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  function pollStatus(id: string) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const status = await api.getImport(id);
        setImportStatus(status);
        if (["staged", "committed", "rejected"].includes(status.status)) {
          if (pollRef.current) clearInterval(pollRef.current);
          if (status.status === "committed") refreshDatasets();
        }
      } catch {
        if (pollRef.current) clearInterval(pollRef.current);
      }
    }, 800);
  }

  async function onFileSelected(file: File) {
    setBusy(true);
    setMessage(null);
    setImportStatus(null);
    try {
      const created = await api.upload(file);
      pollStatus(created.id);
    } catch (err) {
      setMessage(`Falha no upload: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function onCommit() {
    if (!importStatus) return;
    setBusy(true);
    try {
      const result = await api.commit(importStatus.id);
      setMessage(`Resultado do commit: ${result.status}`);
      const refreshed = await api.getImport(importStatus.id);
      setImportStatus(refreshed);
      refreshDatasets();
    } catch (err) {
      setMessage(`Falha no commit: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 24 }}>
      <section
        style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, padding: 20 }}
      >
        <h2 style={{ marginTop: 0 }}>Importar arquivo</h2>
        <p style={{ color: "var(--text-muted)" }}>
          FOCUS 1.0r2 (.csv) ou export nativo Azure Cost Analysis (.csv). Dados de demonstração
          são sintéticos — nenhum dado real de organização é aceito nesta PoV.
        </p>
        <input
          type="file"
          accept=".csv,.parquet,.csv.gz"
          disabled={busy}
          aria-label="Selecionar arquivo de custo para importar"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onFileSelected(file);
          }}
        />
        {message && <p role="alert">{message}</p>}
      </section>

      {importStatus && (
        <section
          style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, padding: 20 }}
        >
          <h3 style={{ marginTop: 0 }}>
            Status da importação <StatusBadge status={importStatus.status} />
          </h3>
          <p>
            Provider: <span className="mono">{importStatus.provider}</span> · Esquema detectado:{" "}
            <span className="mono">{importStatus.schema_version}</span>
          </p>

          {Object.keys(importStatus.rejections_by_severity).length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "12px 0" }}>
              {Object.entries(importStatus.rejections_by_severity).map(([severity, count]) => (
                <SeverityBadge key={severity} severity={severity} count={count} />
              ))}
            </div>
          )}

          {importStatus.status === "rejected" && (
            <p style={{ color: "var(--danger)" }}>
              Commit bloqueado — toda linha de severidade "erro" bloqueia o lote inteiro (sem
              commit parcial em F1). Corrija o arquivo e reimporte.
            </p>
          )}

          {importStatus.status === "staged" && (
            <>
              <p style={{ color: "var(--warn)" }}>
                Sobreposição financeira detectada com dataset já existente, ou pronto para
                confirmação — revise antes de comitar.
              </p>
              <button onClick={onCommit} disabled={busy}>
                Confirmar commit
              </button>
            </>
          )}

          {importStatus.rejections.length > 0 && (
            <table style={{ width: "100%", marginTop: 16, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                  <th>Linha</th>
                  <th>Severidade</th>
                  <th>Motivo</th>
                  <th>Campo</th>
                </tr>
              </thead>
              <tbody>
                {importStatus.rejections.slice(0, 50).map((r, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td>{r.row_offset}</td>
                    <td>{SEVERITY_LABEL[r.severity] ?? r.severity}</td>
                    <td className="mono">{r.reason_code}</td>
                    <td className="mono">{r.field ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      <section
        style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, padding: 20 }}
      >
        <h3 style={{ marginTop: 0 }}>Datasets comitados</h3>
        {datasets.length === 0 ? (
          <p style={{ color: "var(--text-muted)" }}>Nenhum dataset comitado ainda.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                <th>Provider</th>
                <th>Escopo</th>
                <th>Período</th>
                <th>Moedas</th>
                <th>Linhas</th>
                <th>Granularidade</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td className="mono">{d.provider}</td>
                  <td className="mono">{d.scope_key}</td>
                  <td>
                    {d.period_start.slice(0, 10)} → {d.period_end.slice(0, 10)}
                  </td>
                  <td>{d.currency_set.join(", ")}</td>
                  <td>{d.row_count}</td>
                  <td>
                    {d.granularity} <span style={{ color: "var(--text-muted)" }}>({d.granularity_source})</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
