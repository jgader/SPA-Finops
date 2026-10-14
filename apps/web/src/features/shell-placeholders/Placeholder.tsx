export function Placeholder({ area }: { area: string }) {
  return (
    <div
      role="status"
      style={{
        border: "1px dashed var(--border)",
        borderRadius: 8,
        padding: "48px 24px",
        textAlign: "center",
        color: "var(--text-muted)",
      }}
    >
      <p style={{ fontSize: 14, letterSpacing: 1, textTransform: "uppercase", color: "var(--warn)" }}>
        Em desenvolvimento
      </p>
      <p>
        <strong>{area}</strong> faz parte do roadmap do FinOps AI, mas não está implementada na F1.
      </p>
      <p>Nenhum dado desta área é simulado — esta tela intencionalmente não mostra números.</p>
    </div>
  );
}
