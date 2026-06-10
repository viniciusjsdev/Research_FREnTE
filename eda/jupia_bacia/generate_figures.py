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
STAGING_DIR = ROOT / "data" / "staging" / "jupia_bacia"
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


def fig0_data_origin_map() -> None:
    path = ANALYTIC_DIR / "jupia_evidence_locations.csv"
    if not path.exists():
        return
    locations = pd.read_csv(path)
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_facecolor("#F8FAFC")

    # Contorno esquematico da bacia: fonte unica em process_context_sources.BASIN_OUTLINE.
    from process_context_sources import BASIN_OUTLINE

    boundary_lon = [lon for _, lon in BASIN_OUTLINE]
    boundary_lat = [lat for lat, _ in BASIN_OUTLINE]
    ax.fill(boundary_lon, boundary_lat, facecolor="#DC2626", alpha=0.05, edgecolor="#DC2626", linewidth=2.6, label="Bacia contribuinte ate Jupia")

    # Areas esquematicas dos principais contribuintes. Sem basemap: o objetivo e
    # comunicar nivel espacial da fonte, nao substituir cartografia oficial.
    areas = [
        (-50.8, -22.8, 4.6, 2.1, "Rio Tiete", "#C75D2C"),
        (-50.2, -20.8, 3.8, 1.6, "Rio Grande", "#1B75BB"),
        (-51.1, -19.6, 4.4, 1.8, "Rio Paranaiba", "#0F7B5F"),
        (-54.5, -24.9, 6.5, 5.0, "Alto Parana / La Plata", "#87714D"),
    ]
    for lon, lat, width, height, label, color in areas:
        rect = plt.Rectangle((lon, lat), width, height, facecolor=color, edgecolor=color, alpha=0.08, lw=1.5)
        ax.add_patch(rect)
        ax.text(lon + 0.1, lat + height - 0.25, label, fontsize=9, color=color, fontweight="bold")

    rivers = [
        ("Rio Tiete", [-46.7, -48.4, -50.0, -51.45], [-23.5, -22.6, -21.8, -20.8], "#C75D2C"),
        ("Rio Grande", [-46.8, -48.4, -50.1, -51.45], [-20.3, -20.0, -20.2, -20.8], "#1B75BB"),
        ("Rio Paranaiba", [-47.8, -49.2, -50.5, -51.45], [-18.1, -18.8, -19.7, -20.8], "#0F7B5F"),
        ("Rio Parana", [-51.45, -51.6, -51.7], [-20.8, -21.0, -21.7], "#011E42"),
        ("Rio Sucuriu", [-52.6, -52.1, -51.65], [-20.0, -20.35, -20.65], "#6B48A8"),
    ]
    for label, xs, ys, color in rivers:
        ax.plot(xs, ys, color=color, lw=2.5, alpha=0.8)
        ax.annotate("", xy=(xs[-1], ys[-1]), xytext=(xs[-2], ys[-2]), arrowprops=dict(arrowstyle="->", color=color, lw=2))
        ax.text(xs[len(xs) // 2], ys[len(ys) // 2] + 0.18, label, fontsize=8.5, color=color, fontweight="bold")

    kind_styles = {
        "estacao ANA/Hidro": ("#B41E1E", "o", 70),
        "no receptor": ("#011E42", "*", 180),
        "area contribuinte": ("#1B75BB", "s", 80),
        "area academica": ("#87714D", "^", 90),
    }
    for kind, sub in locations.groupby("kind"):
        color, marker, size = kind_styles.get(kind, ("#64748B", "o", 60))
        ax.scatter(sub["longitude"], sub["latitude"], s=size, c=color, marker=marker, label=kind, alpha=0.9, edgecolors="white", linewidths=0.8)
        for _, row in sub.iterrows():
            label = str(row["name"]).replace("UHE JUPIÁ", "UHE Jupia").replace("UHE JUPIÃ", "UHE Jupia")
            if kind in {"estacao ANA/Hidro", "no receptor"}:
                ax.annotate(label[:28], (row["longitude"], row["latitude"]), xytext=(6, 5), textcoords="offset points", fontsize=8, color="#334155")

    ax.scatter([-51.628], [-20.868], s=240, marker="*", c="#DC2626", edgecolors="white", linewidths=1.2, zorder=5)
    ax.annotate(
        "Outlet Jupia\n-20.868, -51.628",
        (-51.628, -20.868),
        xytext=(-53.8, -22.15),
        textcoords="data",
        arrowprops=dict(arrowstyle="->", color="#DC2626", lw=1.6),
        fontsize=9,
        color="#991B1B",
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.35,rounding_size=0.08", fc="white", ec="#FCA5A5", lw=1),
    )

    ax.set_title("Recorte geografico: bacia contribuinte do Alto Parana ate a UHE Jupia")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_xlim(-54.8, -43.8)
    ax.set_ylim(-25.4, -14.9)
    ax.grid(True, color="#CBD5E1", alpha=0.45)
    ax.legend(loc="lower left", frameon=True, fontsize=8)
    ax.text(
        0.01,
        -0.15,
        "Leitura: area vermelha = bacia contribuinte ate Jupia (~480.000 km2 no delineamento de referencia); linhas = rios estruturantes; pontos = estacoes/locais de evidencia. Fonte: ANA/Hidro, ONS, OpenAlex e delineamento de referencia informado pelo usuario. Mapa esquematico, nao cartografia oficial.",
        transform=ax.transAxes,
        fontsize=9,
        color="#64748B",
    )
    save(fig, "fig0_data_origin_map.svg")


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
            f"{int(row['reservoirs'])} reservatorios\n{row['mean_inflow']:.0f} m3/s medio",
            ha="center",
            va="center",
            fontsize=11,
            color="#334155",
            bbox=dict(boxstyle="round,pad=0.55,rounding_size=0.08", fc="white", ec=color, lw=2),
        )
        ax.annotate("", xy=(0.50, 0.25), xytext=(x, y - 0.11), arrowprops=dict(arrowstyle="->", lw=2, color=color))

    ax.text(0.50, 0.18, "UHE JUPIA\nno integrador do Alto Parana", ha="center", va="center", fontsize=14, fontweight="bold", color="#011E42",
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


def fig8_openalex_theme_coverage() -> None:
    path = ANALYTIC_DIR / "jupia_openalex_theme_summary.csv"
    if not path.exists():
        return
    summary = pd.read_csv(path).sort_values("works", ascending=True)
    y = np.arange(len(summary))
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.barh(y, summary["works"], color="#1B75BB", alpha=0.82, label="Trabalhos")
    ax.barh(y, summary["with_pdf"], color="#C4A86C", alpha=0.85, label="Com PDF/arquivo")
    ax.set_yticks(y, labels=summary["theme"])
    ax.set_xlabel("Quantidade")
    ax.set_title("OpenAlex: cobertura academica por eixo analitico")
    ax.grid(True, axis="x", alpha=0.2)
    for i, row in summary.iterrows():
        ax.text(row["works"] + 0.4, list(summary.index).index(i), f"{int(row['works'])}", va="center", fontsize=9, color="#334155")
    ax.legend(frameon=False, loc="lower right")
    ax.text(0.0, -0.14, "Fonte: OpenAlex API /works. Eixos derivados das trilhas de busca Jupia.", transform=ax.transAxes, fontsize=9, color="#64748B")
    save(fig, "fig8_openalex_theme_coverage.svg")


def fig9_openalex_timeline() -> None:
    path = ANALYTIC_DIR / "jupia_academic_evidence.csv"
    if not path.exists():
        return
    works = pd.read_csv(path)
    works = works[pd.to_numeric(works["publication_year"], errors="coerce").notna()].copy()
    works["publication_year"] = works["publication_year"].astype(int)
    works = works[works["publication_year"] >= 1990]
    if works.empty:
        return
    counts = works.groupby(["publication_year", "theme"], as_index=False).size()
    pivot = counts.pivot(index="publication_year", columns="theme", values="size").fillna(0)
    rolling = pivot.rolling(3, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(12, 6))
    palette = ["#1B75BB", "#0F7B5F", "#C75D2C", "#87714D", "#6B48A8", "#B41E1E", "#64748B", "#0EA5E9"]
    for idx, column in enumerate(rolling.columns):
        ax.plot(rolling.index, rolling[column], lw=2, label=column, color=palette[idx % len(palette)])
    ax.set_title("Literatura OpenAlex por eixo - media movel de 3 anos")
    ax.set_xlabel("Ano de publicacao")
    ax.set_ylabel("Trabalhos/ano")
    ax.grid(True, axis="y", alpha=0.22)
    ax.legend(ncol=2, fontsize=8, frameon=False, loc="upper left")
    ax.text(0.0, -0.16, "Fonte: OpenAlex API /works; filtragem local por termos geograficos/hidricos.", transform=ax.transAxes, fontsize=9, color="#64748B")
    save(fig, "fig9_openalex_timeline.svg")


STATION_STYLE = {
    63001500: ("Alto Sucuriu (63001500)", "#0F7B5F"),
    63002000: ("Sao Jose do Sucuriu (63002000)", "#6B48A8"),
    63005000: ("Jupia - Ponte (63005000)", "#87714D"),
    63007080: ("UHE Jupia Barramento (63007080)", "#C75D2C"),
    63010000: ("UHE Jupia Jusante (63010000)", "#1B75BB"),
}


def fig11_ana_station_series() -> None:
    path = STAGING_DIR / "ana_jupia_station_monthly_series.csv"
    if not path.exists():
        return
    series = pd.read_csv(path, parse_dates=["date"])

    def monthly_smooth(sub: pd.DataFrame) -> pd.Series:
        # Reindexa para frequencia mensal: meses sem medicao viram NaN e quebram
        # a linha em vez de conectar decadas sem dado (ex.: 63007080, 1931 -> 1995).
        values = sub.sort_values("date").set_index("date")["monthly_mean"].asfreq("MS")
        return values.rolling(12, min_periods=3).mean()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    for code, sub in series[series["series_type"] == "vazoes"].groupby("station_code"):
        label, color = STATION_STYLE.get(int(code), (str(code), "#64748B"))
        smooth = monthly_smooth(sub)
        ax1.plot(smooth.index, smooth.values, lw=1.8, color=color, label=label)
    ax1.set_yscale("log")
    ax1.set_ylabel("Vazao media mensal (m3/s, escala log)")
    ax1.set_title("Estacoes convencionais ANA no eixo Sucuriu/Jupia - media movel de 12 meses")
    ax1.grid(True, axis="y", alpha=0.25)
    ax1.legend(frameon=False, fontsize=9, loc="upper left")

    for code, sub in series[series["series_type"] == "cotas"].groupby("station_code"):
        label, color = STATION_STYLE.get(int(code), (str(code), "#64748B"))
        smooth = monthly_smooth(sub)
        ax2.plot(smooth.index, smooth.values, lw=1.8, color=color, label=label)
    ax2.set_ylabel("Cota media mensal (cm)")
    ax2.set_xlabel("Ano")
    ax2.grid(True, axis="y", alpha=0.25)
    ax2.legend(frameon=False, fontsize=9, loc="upper left")

    ax2.text(
        0.0,
        -0.22,
        "Fonte: ANA GitHub hidro-dados-estacoes-convencionais (run operational-collect-jupia). Sucuriu em MS (verde/roxo); Rio Parana junto a Jupia (azul/dourado).\n"
        "As series encerram entre 2005 e 2014; trechos sem linha indicam meses sem medicao. Escala log na vazao para acomodar Sucuriu (~10^2 m3/s) e Parana (~10^4 m3/s).",
        transform=ax2.transAxes,
        fontsize=9,
        color="#64748B",
    )
    save(fig, "fig11_ana_station_series.svg")


def fig12_queimadas_pressao() -> None:
    path = ANALYTIC_DIR / "jupia_queimadas_bacia_estado_ano.csv"
    if not path.exists():
        return
    focos = pd.read_csv(path)
    style = {
        "MATO GROSSO DO SUL": ("#B41E1E", 3.0, 1.0),
        "SÃO PAULO": ("#C75D2C", 1.8, 0.9),
        "MINAS GERAIS": ("#1B75BB", 1.8, 0.9),
        "GOIÁS": ("#0F7B5F", 1.8, 0.9),
        "DISTRITO FEDERAL": ("#6B48A8", 1.4, 0.8),
        "PARANÁ": ("#64748B", 1.4, 0.7),
    }
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for estado, sub in focos.groupby("estado"):
        color, lw, alpha = style.get(estado, ("#94A3B8", 1.2, 0.6))
        sub = sub.sort_values("ano")
        ax.plot(sub["ano"], sub["focos"], lw=lw, color=color, alpha=alpha, label=estado.title())
    ax.set_yscale("log")
    ax.set_ylabel("Focos de calor por ano (escala log)")
    ax.set_xlabel("Ano")
    ax.set_title("Focos de calor INPE dentro da bacia contribuinte, por estado")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.14), frameon=False, fontsize=9)
    ax.text(
        0.0,
        -0.34,
        "Fonte: INPE/BDQueimadas via WFS TerraBrasilis, coleta com envelope da bacia e filtro point-in-polygon no contorno esquematico do recorte.\n"
        "Mato Grosso do Sul em vermelho cobre o entorno Tres Lagoas/Jupia e o eixo Sucuriu; Goias/MG cobrem as cabeceiras do Paranaiba e do Grande.",
        transform=ax.transAxes,
        fontsize=9,
        color="#64748B",
    )
    save(fig, "fig12_queimadas_pressao.svg")


QUALITY_PANELS = [
    ("od", "Oxigenio dissolvido (mg/L)", False),
    ("dbo", "DBO (mg/L)", False),
    ("fosforo_total", "Fosforo total (mg/L)", False),
    ("turbidez", "Turbidez (NTU)", False),
    ("ecoli", "E. coli (NMP/100mL)", True),
    ("iqa", "IQA", False),
]


def fig13_qualidade_agua() -> None:
    path = ANALYTIC_DIR / "jupia_quality_annual.csv"
    if not path.exists():
        return
    quality = pd.read_csv(path)
    if quality.empty:
        return
    quality["region"] = np.where(quality["uf"] == "MS", "MS / entorno Jupia", "Montante (SP, MG, GO, DF)")
    grouped = quality.groupby(["parameter", "region", "year"], as_index=False).agg(
        value=("mean", "mean"), stations=("station_code", "nunique")
    )
    colors = {"MS / entorno Jupia": "#B41E1E", "Montante (SP, MG, GO, DF)": "#1B75BB"}

    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True)
    for ax, (param, label, log_scale) in zip(axes.flat, QUALITY_PANELS):
        sub = grouped[grouped["parameter"] == param]
        for region, lines in sub.groupby("region"):
            lines = lines.sort_values("year")
            ax.plot(lines["year"], lines["value"], lw=1.8, color=colors[region], label=region)
        if log_scale and not sub.empty and (sub["value"] > 0).any():
            ax.set_yscale("log")
        ax.set_title(label, fontsize=10)
        ax.grid(True, axis="y", alpha=0.25)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=2, loc="lower center", bbox_to_anchor=(0.5, -0.04), frameon=False, fontsize=10)
    fig.suptitle("Qualidade da agua na bacia contribuinte - media anual das estacoes ANA/RNQA", fontweight="bold")
    fig.text(
        0.01,
        -0.10,
        "Fonte: ANA SNIRH ArcGIS, Indicadores de Qualidade (series historicas ate 2021). Media simples das medias anuais por estacao dentro do contorno da bacia;\n"
        "vermelho = estacoes em Mato Grosso do Sul (entorno Jupia/Sucuriu), azul = contribuintes a montante. Numero de estacoes varia por ano e parametro.",
        fontsize=9,
        color="#64748B",
    )
    fig.tight_layout()
    save(fig, "fig13_qualidade_agua.svg")


INFOAGUAS_PANELS = [
    ("Oxigênio Dissolvido", "Oxigenio dissolvido (mg/L)", False),
    ("DBO (5, 20)", "DBO (mg/L)", False),
    ("Fósforo Total", "Fosforo total (mg/L)", False),
    ("Turbidez", "Turbidez (NTU)", True),
]
INFOAGUAS_POINTS = {
    "TIET02900": ("Rio Tiete - TIET02900", "#C75D2C"),
    "TITR02100": ("Res. Tres Irmaos - TITR02100", "#1B75BB"),
}


def fig14_infoaguas_tiete() -> None:
    path = ANALYTIC_DIR / "jupia_infoaguas_monthly.csv"
    if not path.exists():
        return
    monthly = pd.read_csv(path, parse_dates=["year_month"])
    monthly = monthly[monthly["point_code"].isin(INFOAGUAS_POINTS)]
    if monthly.empty:
        return

    fig, axes = plt.subplots(2, 2, figsize=(13, 7.5), sharex=True)
    for ax, (param, label, log_scale) in zip(axes.flat, INFOAGUAS_PANELS):
        sub = monthly[monthly["parameter"] == param]
        for code, lines in sub.groupby("point_code"):
            name, color = INFOAGUAS_POINTS[code]
            series = lines.sort_values("year_month").set_index("year_month")["value"].asfreq("MS")
            ax.plot(series.index, series.rolling(12, min_periods=4).mean(), lw=1.8, color=color, label=name)
        if log_scale and not sub.empty and (sub["value"] > 0).any():
            ax.set_yscale("log")
        ax.set_title(label, fontsize=10)
        ax.grid(True, axis="y", alpha=0.25)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=2, loc="lower center", bbox_to_anchor=(0.5, -0.05), frameon=False, fontsize=10)
    fig.suptitle("CETESB InfoAguas - o Tiete que chega ao no de Jupia (media movel de 12 meses)", fontweight="bold")
    fig.text(
        0.01,
        -0.11,
        "Fonte: CETESB InfoAguas (sessao autenticada), amostras por coleta agregadas em medias mensais. TIET02900 = Rio Tiete em Pereira Barreto;\n"
        "TITR02100 = Reservatorio de Tres Irmaos. Coleta parcial: 7 pontos da UGRHI 19 Baixo Tiete, 2000-2026.",
        fontsize=9,
        color="#64748B",
    )
    fig.tight_layout()
    save(fig, "fig14_infoaguas_tiete_chegada.svg")


def fig10_correlation_readiness() -> None:
    rows = [
        "Comportamento dos rios",
        "Operacao de reservatorios",
        "Poluicao / qualidade da agua",
        "Sedimentos / turbidez",
        "Uso do solo / agro",
        "Clima / seca",
        "Pontos Jupia-Sucuriu",
    ]
    cols = ["Serie temporal", "Localizacao", "Variavel comparavel", "Fonte academica", "Pronto p/ correlacao"]
    data = np.array(
        [
            [3, 2, 3, 3, 3],
            [3, 2, 3, 2, 3],
            [3, 3, 3, 3, 2],
            [2, 3, 2, 3, 2],
            [3, 3, 2, 2, 2],
            [2, 2, 2, 3, 2],
            [2, 3, 2, 1, 2],
        ]
    )
    fig, ax = plt.subplots(figsize=(11, 6.8))
    im = ax.imshow(data, cmap="YlGnBu", vmin=0, vmax=3, aspect="auto")
    ax.set_xticks(np.arange(len(cols)), labels=cols, rotation=25, ha="right")
    ax.set_yticks(np.arange(len(rows)), labels=rows)
    ax.set_title("Prontidao das camadas para correlacao poluentes-rios-Jupia")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, str(data[i, j]), ha="center", va="center", fontsize=10, color="#0F172A")
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_ticks([0, 1, 2, 3])
    cbar.set_ticklabels(["ausente", "parcial", "boa", "pronta"])
    ax.text(
        0.0,
        -0.18,
        "Leitura: 3 = camada ja permite analise quantitativa; 1 = precisa extracao/normalizacao antes de correlacionar. Fonte: auditoria EDA ONS/ANA/OpenAlex.",
        transform=ax.transAxes,
        fontsize=9,
        color="#64748B",
    )
    save(fig, "fig10_correlation_readiness_matrix.svg")


def main() -> None:
    monthly, annual, coverage = load()
    fig0_data_origin_map()
    fig1_system_overview(monthly)
    fig2_monthly_inflow(monthly)
    fig3_jupia_node(monthly)
    fig4_annual_min_volume(annual)
    fig5_count_and_flow(monthly)
    fig6_coverage(coverage)
    fig7_station_collection_evidence()
    fig8_openalex_theme_coverage()
    fig9_openalex_timeline()
    fig10_correlation_readiness()
    fig11_ana_station_series()
    fig12_queimadas_pressao()
    fig13_qualidade_agua()
    fig14_infoaguas_tiete()


if __name__ == "__main__":
    main()
