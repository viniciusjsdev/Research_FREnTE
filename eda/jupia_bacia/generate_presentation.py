"""Render the Jupia basin HTML report from structured context."""

from __future__ import annotations

import json
import os
import shutil
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EDA_DIR = Path(__file__).resolve().parent
FIG_DIR = EDA_DIR / "figures"
CONTEXT_PATH = EDA_DIR / "report_context.json"
OUTPUT = ROOT / "docs" / "jupia" / "index.html"
DOC_FIG_DIR = OUTPUT.parent / "figures"
ASSETS = ROOT / "docs" / "assets"

TAG_COLORS = {
    "blue": ("rgba(27,117,187,.10)", "#1B75BB"),
    "green": ("rgba(15,123,95,.10)", "#0F7B5F"),
    "purple": ("rgba(107,72,168,.10)", "#6B48A8"),
    "orange": ("rgba(199,93,44,.10)", "#C75D2C"),
    "red": ("rgba(180,30,30,.10)", "#B41E1E"),
    "stone": ("rgba(120,113,108,.12)", "#57534E"),
}


def esc(value: Any) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def rel(path: Path) -> str:
    return os.path.relpath(path, OUTPUT.parent).replace("\\", "/")


def load_context() -> dict[str, Any]:
    return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))


def metric_card(metric: dict[str, Any]) -> str:
    return f"""
      <div class="rounded-xl px-4 py-3" style="background:rgba(255,255,255,.07)">
        <span class="material-symbols-outlined text-2xl" style="color:#C4A86C">{esc(metric.get("icon", "analytics"))}</span>
        <p class="text-white font-bold text-lg mt-1">{esc(metric["value"])}</p>
        <p class="text-white/50 text-xs">{esc(metric["label"])} · {esc(metric["detail"])}</p>
      </div>
    """


def figure_card(fig: dict[str, Any]) -> str:
    bg, color = TAG_COLORS.get(fig.get("tag_color", "blue"), TAG_COLORS["blue"])
    img_path = FIG_DIR / fig["file"]
    img_src = ""
    if img_path.exists():
        DOC_FIG_DIR.mkdir(parents=True, exist_ok=True)
        published = DOC_FIG_DIR / img_path.name
        shutil.copy2(img_path, published)
        img_src = rel(published)
    img_html = (
        f'<img src="{esc(img_src)}" alt="{esc(fig["title"])}" class="w-full rounded-lg border border-slate-200 shadow-sm bg-white">'
        if img_src
        else '<div class="w-full h-64 rounded-lg border border-dashed border-slate-300 flex items-center justify-center text-slate-400 text-sm">Figura nao encontrada</div>'
    )
    return f"""
<section class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden mb-10">
  <div class="px-8 pt-7 pb-4 flex items-start gap-4">
    <div class="mt-0.5 flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center" style="background:{bg}">
      <span class="material-symbols-outlined text-xl" style="color:{color}">{esc(fig.get("icon", "analytics"))}</span>
    </div>
    <div class="flex-1">
      <div class="flex flex-wrap items-center gap-2 mb-1">
        <span class="badge" style="background:{bg};color:{color}">{esc(fig["tag"])}</span>
        <span class="text-xs text-slate-400 font-mono">{esc(fig["id"].upper())}</span>
      </div>
      <h2 class="text-xl font-bold text-slate-800">{esc(fig["title"])}</h2>
    </div>
  </div>
  <div class="px-8 pb-2"><div class="gold-bar"></div></div>
  <div class="px-8 py-5">{img_html}</div>
  <div class="px-8 pb-8 grid lg:grid-cols-2 gap-6">
    <div>
      <p class="field-label mb-2"><span class="material-symbols-outlined text-sm mr-1">description</span>O QUE MOSTRA</p>
      <p class="text-sm text-slate-600 leading-relaxed">{esc(fig["summary"])}</p>
    </div>
    <div>
      <p class="field-label mb-2"><span class="material-symbols-outlined text-sm mr-1">lightbulb</span>INTERPRETACAO ANALITICA</p>
      <p class="text-sm text-slate-600 leading-relaxed">{esc(fig["interpretation"])}</p>
    </div>
    <div class="lg:col-span-2 rounded-lg px-5 py-3 flex items-start gap-3" style="background:{bg};border-left:3px solid {color}">
      <span class="material-symbols-outlined text-base flex-shrink-0 mt-0.5" style="color:{color}">star</span>
      <p class="text-sm font-semibold" style="color:{color}">{esc(fig["highlight"])}</p>
    </div>
  </div>
</section>
"""


def source_block(context: dict[str, Any]) -> str:
    outputs = context["data_outputs"]
    gaps = "".join(f"<li>{esc(item)}</li>" for item in context.get("known_gaps", []))
    summary = context.get("collection_summary", {})
    collection_run = context.get("collection_run_id", "")
    requested = context.get("requested_station_matches", [])
    requested_html = "".join(
        f"<li><strong>{esc(row.get('Codigo', ''))}</strong> - {esc(row.get('Nome', ''))} ({esc(row.get('RioNome', '') or 'sem rio no registro')})</li>"
        for row in requested[:3]
    )
    if not requested_html:
        requested_html = "<li>Nenhum match direto registrado.</li>"
    return f"""
<div class="max-w-6xl mx-auto px-6 mb-6">
  <div class="rounded-xl border border-slate-200 bg-white px-6 py-4 grid lg:grid-cols-3 gap-5">
    <div class="flex items-start gap-3">
      <span class="material-symbols-outlined text-xl flex-shrink-0 mt-0.5" style="color:#1B75BB">travel_explore</span>
      <div>
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Coleta e fontes</p>
        <p class="text-sm text-slate-700"><strong>ONS + ANA/Hidro + IBGE + CETESB/ANA</strong><br>Run: <span class="font-mono text-xs">{esc(collection_run)}</span><br>{esc(summary.get("collected", 0))} artefatos coletados de {esc(summary.get("targets_total", 0))} alvos tentados.</p>
      </div>
    </div>
    <div class="flex items-start gap-3">
      <span class="material-symbols-outlined text-xl flex-shrink-0 mt-0.5" style="color:#0F7B5F">pin_drop</span>
      <div>
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">UHE Jupia Sucuriu</p>
        <ul class="text-sm text-slate-700 list-disc pl-4 space-y-1">{requested_html}</ul>
      </div>
    </div>
    <div class="flex items-start gap-3">
      <span class="material-symbols-outlined text-xl flex-shrink-0 mt-0.5" style="color:#B41E1E">warning</span>
      <div>
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Lacunas preservadas</p>
        <ul class="text-sm text-slate-700 list-disc pl-4 space-y-1">{gaps}</ul>
      </div>
    </div>
  </div>
  <div class="rounded-xl border border-slate-200 bg-white px-6 py-3 mt-3">
    <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Artefatos derivados</p>
    <p class="text-xs text-slate-700 font-mono leading-relaxed">{esc(outputs["staging_daily"])}<br>{esc(outputs["monthly"])}<br>{esc(outputs["coverage"])}<br>{esc(outputs.get("station_inventory", ""))}<br>{esc(outputs.get("station_series_coverage", ""))}</p>
  </div>
</div>
"""


def render() -> str:
    context = load_context()
    metrics = "\n".join(metric_card(item) for item in context["metrics"])
    cards = "\n".join(figure_card(item) for item in context["figures"])
    logo_100k = rel(ASSETS / "100K.webp")
    logo_gsu = rel(ASSETS / "Georgia.png")
    logo_senai = rel(ASSETS / "SENAI.svg")
    source_html = source_block(context)
    subtitle = context["report_subtitle"]
    note = context["scope"]["available_station_note"]

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(context["report_title"])} - Projeto FREnTE</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Bitter:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
<style>
:root {{ --gsu-blue:#011E42; --gsu-gold:#87714D; --gsu-gold-light:#C4A86C; }}
body {{ font-family:'Inter',sans-serif; background:#f8fafc; color:#0f172a; }}
h1,h2,h3 {{ font-family:'Bitter',serif; }}
.material-symbols-outlined {{ font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 24; vertical-align:middle; }}
.gold-bar {{ height:3px; background:linear-gradient(90deg,#87714D,#C4A86C,#87714D); border-radius:999px; }}
.badge {{ display:inline-flex; align-items:center; font-size:10px; font-weight:700; padding:3px 9px; border-radius:999px; white-space:nowrap; text-transform:uppercase; letter-spacing:.06em; }}
.field-label {{ font-weight:700; font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:.06em; display:flex; align-items:center; }}
.logo-chip {{ background:white; border-radius:.75rem; padding:.35rem .6rem; display:flex; align-items:center; justify-content:center; }}
</style>
</head>
<body class="min-h-screen">

<header style="background:var(--gsu-blue)" class="sticky top-0 z-50 shadow-lg">
  <div class="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <img src="{esc(logo_100k)}" alt="Projeto 100K" class="h-9 object-contain">
      <div class="w-px h-7 bg-white/20"></div>
      <div class="logo-chip"><img src="{esc(logo_gsu)}" alt="Georgia State University" class="h-7 object-contain"></div>
      <div class="logo-chip"><img src="{esc(logo_senai)}" alt="SENAI" class="h-6 object-contain"></div>
    </div>
    <div class="flex items-center gap-3">
      <span class="hidden sm:inline-block text-white/40 text-xs">Projeto FREnTE - EDA</span>
      <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold" style="background:rgba(251,191,36,.15);color:#FCD34D;border:1px solid rgba(251,191,36,.25)">Novo recorte</span>
    </div>
  </div>
</header>

<section style="background:var(--gsu-blue)" class="pb-10 pt-8">
  <div class="max-w-6xl mx-auto px-6">
    <p class="text-xs font-semibold tracking-widest mb-2 uppercase" style="color:#87714D">Analise Exploratoria - Bacia Hidrografica de Jupia</p>
    <h1 class="text-3xl lg:text-4xl font-bold text-white leading-tight mb-3">
      Bacia Hidrografica de Jupia<br>
      <span style="color:#C4A86C">{esc(subtitle)}</span>
    </h1>
    <p class="text-white/75 text-sm lg:text-base max-w-4xl leading-relaxed mb-6">
      Este relatorio cria um novo link analitico para Jupia. A leitura deixa de tratar Jupia como simples extensao da cascata do Tiete e passa a considera-lo como no integrador do Alto Parana, reunindo os sinais operacionais dos rios Paranaiba, Grande e Tiete, alem do proprio trecho Parana/Jupia e do eixo Sucuriu. {esc(note)}
    </p>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">{metrics}</div>
  </div>
</section>

<div class="max-w-6xl mx-auto px-6 py-4"><div class="gold-bar"></div></div>
{source_html}
<main class="max-w-6xl mx-auto px-6 pb-16">{cards}</main>

<footer style="background:var(--gsu-blue)" class="py-8">
  <div class="max-w-6xl mx-auto px-6 text-center">
    <p class="text-white/40 text-xs">Projeto FREnTE - Bacia Hidrografica de Jupia - Dados: ONS, ANA/Hidro, ANA GitHub, IBGE, CETESB/ANA - Gerado automaticamente</p>
  </div>
</footer>
</body>
</html>
"""


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"HTML salvo: {OUTPUT}")


if __name__ == "__main__":
    main()
