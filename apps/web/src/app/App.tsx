import { useState } from "react";
import { DataHub } from "../features/data-hub/DataHub";
import { Placeholder } from "../features/shell-placeholders/Placeholder";

const AREAS = [
  { key: "data-hub", label: "Data Hub", functional: true },
  { key: "cockpit", label: "Cockpit", functional: false },
  { key: "cost-analytics", label: "Cost Analytics", functional: false },
  { key: "investigacao", label: "Investigação/Relatórios", functional: false },
] as const;

type AreaKey = (typeof AREAS)[number]["key"];

export default function App() {
  const [active, setActive] = useState<AreaKey>("data-hub");
  const current = AREAS.find((a) => a.key === active)!;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          background: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          padding: "12px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <strong>FinOps AI</strong>{" "}
          <span style={{ color: "var(--text-muted)" }}>— workspace demo · Fase F1</span>
        </div>
        <span
          style={{
            fontSize: 12,
            border: "1px solid var(--accent2)",
            color: "var(--accent2)",
            borderRadius: 999,
            padding: "2px 10px",
          }}
        >
          Dados de demonstração — sintéticos
        </span>
      </header>

      <nav
        aria-label="Áreas do produto"
        style={{ display: "flex", gap: 4, padding: "8px 24px", borderBottom: "1px solid var(--border)" }}
      >
        {AREAS.map((area) => (
          <button
            key={area.key}
            onClick={() => setActive(area.key)}
            aria-current={area.key === active}
            style={{
              background: area.key === active ? "var(--card)" : "transparent",
              border: "1px solid var(--border)",
              borderBottom: area.key === active ? "2px solid var(--accent)" : "1px solid var(--border)",
              color: "var(--text)",
              padding: "8px 16px",
              borderRadius: "6px 6px 0 0",
              cursor: "pointer",
            }}
          >
            {area.label}
            {!area.functional && <span style={{ color: "var(--warn)" }}> ·</span>}
          </button>
        ))}
      </nav>

      <main style={{ padding: 24, flex: 1 }}>
        {current.functional ? <DataHub /> : <Placeholder area={current.label} />}
      </main>
    </div>
  );
}
