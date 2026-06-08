"""Generate report figures for the Jupia contributing basin report."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EDA_DIR = Path(__file__).resolve().parent
FIG_DIR = EDA_DIR / "figures"
ANALYTIC_DIR = ROOT / "data" / "analytic" / "jupia_bacia"
CONTEXT_PATH = EDA_DIR / "report_context.json"

FIG_DIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "GRANDE": "#1B75BB",
    "PARANAIBA": "#0F7B5F",
    "TIETE": "#C75D2C",
    "PARANA": "#87714D",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.dpi": 140,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titleweight": "bold",
    "axes.labelcolor": "#334155",
    "xtick.color": "#475569",
    "ytick.color": "#475569",
})


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    monthly = pd.read_csv(ANALYTIC_DIR / "jupia_system_monthly.csv", parse_dates=["date"])
    annual = pd.read_csv(ANALYTIC_DIR / "jupia_system_annual.csv")
    coverage = pd.read_csv(ANALYTIC_DIR / "jupia_coverage_matrix.csv")
    return monthly, annual, coverage


def save(fig: plt.Figure, filename: str) -> None:
    path = FIG_DIR / filename
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"saved {path}")


def fig1_system_overview(monthly: pd.DataFrame) -> None:
    summary = (
        monthly.groupby(["basin_key", "basin_label"], as_index=False)
        .agg(reservoirs=("reservoir_key", "nunique"), mean_inflow=("inflow_m3s", "mean"))
    )
    order = ["PARANAIBA", "GRANDE", "TIETE", "PARANA"]
    summary = summary.set_index("basin_key").reindex(order).reset_index()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axis("off")
    xs = [0.12, 0.38, 0.64, 0.88]
    y = 0.60
    for _, row in summary.iterrows():
        x = xs[order.index(row["basin_key"])]
        color = COLORS[row["basin_key"]]
        ax.text(x, y + 0.18, row["basin_label"], ha="center", va="center", fontsize=14, fontweight="bold", color="#011E42")
        ax.text(
            x,
            y,
            f"{int(row['reservoirs'])} reservatorios\\n{row['mean_inflow']:.0f} m3/s medio",
            ha="center",
            va="center",
            fontsize=11,
            color="#334155",
            bbox=dict(boxstyle="round,pad=0.55,rounding_size=0.08", fc="white", ec=color, lw=2),
        )
        ax.annotate("", xy=(0.50, 0.25), xytext=(x, y - 0.11), arrowprops=dict(arrowstyle="->", lw=2, color=color))

    ax.text(0.50, 0.18, "UHE JUPIA\\nno integrador do Alto Parana", ha="center", va="center", fontsize=14, fontweight="bold", color="#011E42",
            bbox=dict(boxstyle="round,pad=0.65,rounding_size=0.08", fc="#F8FAFC", ec="#87714D", lw=2))
    ax.text(0.02, 0.94, "Sistema contribuinte de Jupia - leitura operacional ONS (2000-2025)", fontsize=15, fontweight="bold", color="#011E42")
    ax.text(0.02, 0.88, "Fonte: ONS Dados Hidrologicos de Reservatorios. Sucuriu nao aparece como identificador proprio na base local.", fontsize=10, color="#64748B")
    save(fig, "fig1_basin_system_overview.svg")


def fig2_monthly_inflow(monthly: pd.DataFrame) -> None:
    basin_month = (
        monthly.groupby(["basin_key", "basin_label", "date"], as_index=False)["inflow_m3s"].mean()
        .sort_values("date")
    )
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for key, sub in basin_month.groupby("basin_key"):
        sub = sub.sort_values("date")
        rolling = sub["inflow_m3s"].rolling(12, min_periods=6).mean()
        ax.plot(sub["date"], rolling, label=sub["basin_label"].iloc[0], color=COLORS.get(key, "#475569"), lw=2)
    ax.axvspan(pd.Timestamp("2014-01-01"), pd.Timestamp("2016-01-01"), color="#F59E0B", alpha=0.12)
    ax.set_title("Vazao afluente mensal por contribuinte - media movel de 12 meses")
    ax.set_ylabel("Vazao afluente media (m3/s)")
    ax.set_xlabel("Ano")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
    ax.text(0.01, -0.25, "Faixa laranja: crise hidrica 2014-2015. Fonte: ONS Dados Abertos.", transform=ax.transAxes, fontsize=9, color="#64748B")
    save(fig, "fig2_monthly_inflow_by_basin.svg")


def fig3_jupia_node(monthly: pd.DataFrame) -> None:
    jupia = monthly[monthly["reservoir_key"] == "JUPIA"].sort_values("date")
    fig, ax1 = plt.subplots(figsize=(12, 5.5))
    ax2 = ax1.twinx()
    ax1.plot(jupia["date"], jupia["inflow_m3s"].rolling(12, min_periods=6).mean(), color="#1B75BB", lw=2, label="Afluencia")
    ax1.plot(jupia["date"], jupia["outflow_m3s"].rolling(12, min_periods=6).mean(), color="#0F7B5F", lw=2, label="Defluencia")
    ax2.plot(jupia["date"], jupia["useful_volume_pct"].rolling(12, min_periods=6).mean(), color="#C75D2C", lw=1.8, label="Volume util")
    ax1.set_title("UHE Jupia - afluencia, defluencia e volume util")
    ax1.set_ylabel("Vazao (m3/s)")
    ax2.set_ylabel("Volume util (%)")
    ax1.grid(True, axis="y", alpha=0.25)
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [line.get_label() for line in lines], ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
    ax1.text(0.01, -0.25, "Serie ONS identificada como JUPIA na bacia PARANA. Sucuriu requer coleta complementar.", transform=ax1.transAxes, fontsize=9, color="#64748B")
    save(fig, "fig3_jupia_node_series.svg")


def fig4_annual_min_volume(annual: pd.DataFrame) -> None:
    pivot = annual.pivot_table(index="reservoir_label", columns="year", values="min_useful_volume_pct", aggfunc="mean")
    row_order = (
        annual.groupby("reservoir_label")["natural_flow_m3s"].mean().sort_values(ascending=False).index.tolist()
    )
    pivot = pivot.reindex(row_order)

    fig, ax = plt.subplots(figsize=(13, 8))
    data = pivot.to_numpy(dtype=float)
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn", vmin=0, vmax=100)
    ax.set_title("Volume util minimo anual por reservatorio selecionado")
    ax.set_xticks(np.arange(len(pivot.columns))[::2], labels=[str(c) for c in pivot.columns[::2]], rotation=45, ha="right")
    ax.set_yticks(np.arange(len(pivot.index)), labels=pivot.index, fontsize=8)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Volume util minimo anual (%)")
    ax.text(0.0, -0.10, "Fonte: ONS Dados Abertos. Cores vermelhas indicam anos de menor armazenamento relativo.", transform=ax.transAxes, fontsize=9, color="#64748B")
    save(fig, "fig4_annual_min_volume_heatmap.svg")


def fig5_count_and_flow(monthly: pd.DataFrame) -> None:
    summary = (
        monthly.groupby(["basin_key", "basin_label"], as_index=False)
        .agg(reservoirs=("reservoir_key", "nunique"), mean_inflow=("inflow_m3s", "mean"))
        .sort_values("mean_inflow", ascending=False)
    )
    x = np.arange(len(summary))
    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    ax2 = ax1.twinx()
    colors = [COLORS[k] for k in summary["basin_key"]]
    ax1.bar(x - 0.18, summary["reservoirs"], width=0.36, color=colors, alpha=0.85, label="Reservatorios")
    ax2.bar(x + 0.18, summary["mean_inflow"], width=0.36, color="#94A3B8", alpha=0.85, label="Vazao media")
    ax1.set_xticks(x, labels=summary["basin_label"], rotation=15, ha="right")
    ax1.set_ylabel("Reservatorios selecionados")
    ax2.set_ylabel("Vazao afluente media (m3/s)")
    ax1.set_title("Cobertura operacional e escala hidrologica por contribuinte")
    for i, row in summary.iterrows():
        ax1.text(x[i] - 0.18, row["reservoirs"] + 0.2, str(int(row["reservoirs"])), ha="center", fontsize=9)
    ax1.grid(True, axis="y", alpha=0.2)
    ax1.text(0.0, -0.25, "A leitura de Jupia ganha escala ao combinar quantidade de pontos e magnitude hidrologica.", transform=ax1.transAxes, fontsize=9, color="#64748B")
    save(fig, "fig5_reservoir_count_and_flow.svg")


def fig6_coverage(coverage: pd.DataFrame) -> None:
    coverage = coverage.sort_values(["basin_key", "reservoir_label"])
    fig, ax = plt.subplots(figsize=(12, 8))
    y = np.arange(len(coverage))
    colors = [COLORS.get(k, "#64748B") for k in coverage["basin_key"]]
    ax.barh(y, coverage["years"], color=colors, alpha=0.85)
    ax.axvline(20, color="#B91C1C", linestyle="--", lw=1.5, label="Alvo 20 anos")
    ax.set_yticks(y, labels=[f"{b} - {r}" for b, r in zip(coverage["basin_label"], coverage["reservoir_label"])], fontsize=8)
    ax.set_xlabel("Anos com registros")
    ax.set_title("Cobertura temporal por reservatorio selecionado")
    ax.set_xlim(0, max(coverage["years"].max() + 2, 22))
    ax.invert_yaxis()
    ax.grid(True, axis="x", alpha=0.2)
    ax.legend(frameon=False, loc="lower right")
    ax.text(0.0, -0.08, "Fonte: ONS Dados Abertos, 2000-2025. A principal lacuna e a ausencia local de identificador Sucuriu.", transform=ax.transAxes, fontsize=9, color="#64748B")
    save(fig, "fig6_coverage_matrix.svg")


def fig7_station_collection_evidence() -> None:
    if not CONTEXT_PATH.exists():
        return
    context = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    summary = context.get("collection_summary", {})
    requested = context.get("requested_station_matches", [])
    values = {
        "Alvos tentados": int(summary.get("targets_total", 0)),
        "Artefatos coletados": int(summary.get("collected", 0)),
        "Linhas de inventario": int(summary.get("station_inventory_rows", 0)),
        "Matches UHE Jupia/Sucuriu": int(summary.get("requested_station_matches", 0)),
        "Series CSV coletadas": int(summary.get("station_series_collected", 0)),
    }

    fig, ax = plt.subplots(figsize=(12, 6.5))
    labels = list(values.keys())
    nums = list(values.values())
    colors = ["#1B75BB", "#0F7B5F", "#87714D", "#C75D2C", "#6B48A8"]
    y = np.arange(len(labels))
    ax.barh(y, nums, color=colors, alpha=0.85)
    ax.set_yticks(y, labels=labels)
    ax.set_xlabel("Quantidade")
    ax.set_title("Coleta operacional Jupia: inventario, series e documentos")
    ax.grid(True, axis="x", alpha=0.2)
    for i, value in enumerate(nums):
        ax.text(value + max(nums) * 0.015, i, str(value), va="center", fontsize=10, color="#334155")
    ax.invert_yaxis()

    station_lines = []
    for row in requested[:4]:
        station_lines.append(
            f"{row.get('Codigo', '')} - {row.get('Nome', '')} | {row.get('RioNome', '') or 'sem rio no registro'}"
        )
    station_text = "\n".join(station_lines) if station_lines else "Nenhum match direto encontrado."
    ax.text(
        0.02,
        -0.38,
        "Matches diretos no inventario ANA/Hidro:\n" + station_text,
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
        va="top",
        bbox=dict(boxstyle="round,pad=0.5,rounding_size=0.08", fc="#F8FAFC", ec="#CBD5E1", lw=1),
    )
    ax.text(
        0.02,
        -0.62,
        "Fonte: ANA Hidro SOAP, ANA GitHub hidro-dados-estacoes-convencionais, IBGE BHB250 e documentos CETESB/ANA preservados em data/runs.",
        transform=ax.transAxes,
        fontsize=9,
        color="#64748B",
    )
    save(fig, "fig7_station_collection_evidence.svg")


def main() -> None:
    monthly, annual, coverage = load()
    fig1_system_overview(monthly)
    fig2_monthly_inflow(monthly)
    fig3_jupia_node(monthly)
    fig4_annual_min_volume(annual)
    fig5_count_and_flow(monthly)
    fig6_coverage(coverage)
    fig7_station_collection_evidence()


if __name__ == "__main__":
    main()
