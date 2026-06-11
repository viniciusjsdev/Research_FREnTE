"""Render the Jupia basin HTML report from structured context."""

from __future__ import annotations

import csv
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
STAGING_DIR = ROOT / "data" / "staging" / "jupia_bacia"

# Estacoes com serie CSV historica coletada no run operacional.
SERIES_STATIONS = {63001500, 63002000, 63005000, 63010000}
# Matches diretos da demanda UHE JUPIA SUCURIU.
REQUESTED_STATIONS = {1952023, 63001850, 63003300}
# Falsos positivos de busca fora do recorte (bacia do Sao Francisco).
OUT_OF_SCOPE_STATIONS = {40890000}

# Coordenadas aproximadas das barragens dos reservatorios ONS usados no relatorio
# (localizacao do eixo da barragem; suficiente para contexto, nao para cartografia).
ONS_RESERVOIRS = [
    ("Furnas", "Rio Grande", -20.669, -46.318),
    ("Luis Carlos Barreto", "Rio Grande", -20.150, -47.277),
    ("Igarapava", "Rio Grande", -20.039, -47.758),
    ("Volta Grande", "Rio Grande", -20.033, -48.221),
    ("Porto Colombia", "Rio Grande", -20.123, -48.570),
    ("Marimbondo", "Rio Grande", -20.303, -49.198),
    ("Agua Vermelha", "Rio Grande", -19.866, -50.346),
    ("Nova Ponte", "Rio Paranaíba", -19.135, -47.689),
    ("Miranda", "Rio Paranaíba", -18.910, -48.043),
    ("Corumbá", "Rio Paranaíba", -17.987, -48.530),
    ("Corumbá-3", "Rio Paranaíba", -16.770, -48.030),
    ("Corumbá-4", "Rio Paranaíba", -16.323, -48.183),
    ("Batalha", "Rio Paranaíba", -17.350, -47.510),
    ("Emborcação", "Rio Paranaíba", -18.452, -47.987),
    ("Itumbiara", "Rio Paranaíba", -18.407, -49.097),
    ("Cachoeira Dourada", "Rio Paranaíba", -18.500, -49.490),
    ("São Simão", "Rio Paranaíba", -19.018, -50.499),
    ("Barra Bonita", "Rio Tietê", -22.519, -48.534),
    ("Bariri", "Rio Tietê", -22.152, -48.754),
    ("Ibitinga", "Rio Tietê", -21.758, -48.989),
    ("Promissão", "Rio Tietê", -21.296, -49.783),
    ("Nova Avanhandava", "Rio Tietê", -21.119, -50.200),
    ("Três Irmãos", "Rio Tietê", -20.672, -51.302),
    ("Ilha Solteira", "Rio Paraná", -20.382, -51.363),
    ("Jupiá / Eng. Souza Dias", "Rio Paraná", -20.778, -51.629),
    ("Porto Primavera (jusante do nó)", "Rio Paraná", -22.481, -52.959),
]

BASIN_COLORS = {
    "Rio Grande": "#1B75BB",
    "Rio Paranaíba": "#0F7B5F",
    "Rio Tietê": "#C75D2C",
    "Rio Paraná": "#87714D",
}

# Contorno esquematico da bacia: fonte unica em process_context_sources.BASIN_OUTLINE.
from process_context_sources import BASIN_OUTLINE  # noqa: E402

# Tracados esquematicos dos rios estruturantes (mesmos da fig0).
RIVER_LINES = [
    ("Rio Tietê", "#C75D2C", [[-23.5, -46.7], [-22.6, -48.4], [-21.8, -50.0], [-20.8, -51.45]]),
    ("Rio Grande", "#1B75BB", [[-20.3, -46.8], [-20.0, -48.4], [-20.2, -50.1], [-20.8, -51.45]]),
    ("Rio Paranaíba", "#0F7B5F", [[-18.1, -47.8], [-18.8, -49.2], [-19.7, -50.5], [-20.8, -51.45]]),
    ("Rio Paraná", "#011E42", [[-20.8, -51.45], [-21.0, -51.6], [-21.7, -51.7]]),
    ("Rio Sucuriú", "#6B48A8", [[-20.0, -52.6], [-20.35, -52.1], [-20.65, -51.65]]),
]

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


def load_quality_stations() -> list[dict[str, Any]]:
    path = ROOT / "data" / "analytic" / "jupia_bacia" / "jupia_quality_stations.csv"
    if not path.exists():
        return []
    stations: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
            except (TypeError, ValueError):
                continue
            stations.append(
                {
                    "code": row.get("station_code", ""),
                    "entity": row.get("entity", ""),
                    "water_body": row.get("water_body", ""),
                    "uf": row.get("uf", ""),
                    "lat": lat,
                    "lon": lon,
                    "parameters": row.get("parameters", ""),
                    "period": f"{row.get('first_year', '')}-{row.get('last_year', '')}",
                }
            )
    return stations


def load_infoaguas_points() -> list[dict[str, Any]]:
    path = ROOT / "data" / "analytic" / "jupia_bacia" / "jupia_infoaguas_points.csv"
    if not path.exists():
        return []
    points: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
            except (TypeError, ValueError):
                continue
            points.append(
                {
                    "code": row.get("point_code", ""),
                    "system": row.get("hydric_system", ""),
                    "municipality": row.get("municipality", ""),
                    "lat": lat,
                    "lon": lon,
                    "parameters": row.get("parameters", ""),
                    "samples": row.get("samples", ""),
                    "period": f"{row.get('first_year', '')}-{row.get('last_year', '')}",
                    "is_node": row.get("point_code", "") == "PARN02100",
                }
            )
    return points


def load_ana_stations() -> list[dict[str, Any]]:
    path = STAGING_DIR / "ana_jupia_station_inventory_matches.csv"
    if not path.exists():
        return []
    stations: list[dict[str, Any]] = []
    seen: set[int] = set()
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                code = int(float(row["Codigo"]))
                lat = float(row["Latitude"])
                lon = float(row["Longitude"])
            except (TypeError, ValueError):
                continue
            if code in seen or code in OUT_OF_SCOPE_STATIONS:
                continue
            seen.add(code)
            if code in REQUESTED_STATIONS:
                category = "requested"
            elif code in SERIES_STATIONS:
                category = "series"
            else:
                category = "inventory"
            stations.append(
                {
                    "code": code,
                    "name": row.get("Nome", "") or "",
                    "river": row.get("RioNome", "") or "",
                    "municipality": f"{row.get('nmMunicipio', '') or ''} - {row.get('nmEstado', '') or ''}".strip(" -"),
                    "lat": lat,
                    "lon": lon,
                    "category": category,
                }
            )
    return stations


def map_block(context: dict[str, Any]) -> str:
    stations = load_ana_stations()
    quality_stations = load_quality_stations()
    infoaguas_points = load_infoaguas_points()
    reservoirs = [
        {"name": name, "basin": basin, "lat": lat, "lon": lon, "color": BASIN_COLORS.get(basin, "#64748B")}
        for name, basin, lat, lon in ONS_RESERVOIRS
    ]
    rivers = [{"name": name, "color": color, "coords": coords} for name, color, coords in RIVER_LINES]
    recorte = context.get("spatial_recorte", {})
    outlet_label = esc(recorte.get("outlet", "Ponto de fechamento de Jupiá"))
    payload = json.dumps(
        {
            "stations": stations,
            "quality": quality_stations,
            "infoaguas": infoaguas_points,
            "reservoirs": reservoirs,
            "rivers": rivers,
            "outline": BASIN_OUTLINE,
            "outlet": {"lat": -20.868, "lon": -51.628},
        }
    )
    return f"""
<section class="max-w-6xl mx-auto px-6 pb-6">
  <div class="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
    <div class="px-8 pt-7 pb-4 flex items-start gap-4">
      <div class="mt-0.5 flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center" style="background:rgba(1,30,66,.08)">
        <span class="material-symbols-outlined text-xl" style="color:var(--gsu-blue)">map</span>
      </div>
      <div class="flex-1">
        <div class="flex flex-wrap items-center gap-2 mb-1">
          <span class="badge" style="background:rgba(1,30,66,.08);color:var(--gsu-blue)">Localização</span>
          <span class="text-xs text-slate-400 font-mono">Mapa interativo</span>
        </div>
        <h2 class="text-xl font-bold text-slate-800">Onde os dados foram coletados - bacia contribuinte até Jupiá</h2>
        <p class="text-sm text-slate-600 leading-relaxed mt-2">{outlet_label} O contorno vermelho indica a bacia contribuinte (~480.000 km2, traçado esquemático); cada ponto é um local real de medição ou um reservatório ONS usado na análise.</p>
      </div>
    </div>
    <div class="px-8 pb-3"><div class="gold-bar"></div></div>
    <div class="px-8 pb-3 flex flex-wrap gap-4 text-xs font-semibold">
      <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-full" style="background:#B41E1E"></span>Estação ANA - match UHE Jupiá Sucuriú</span>
      <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-full" style="background:#0F7B5F"></span>Estação ANA com série CSV coletada</span>
      <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-full" style="background:#0B5CAD"></span>Estação ANA inventariada</span>
      <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-full" style="background:#87714D"></span>Reservatório ONS (cor por bacia)</span>
      <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-full" style="background:#6B48A8"></span>Estação de qualidade ANA/RNQA (camada opcional)</span>
      <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-full" style="background:#C75D2C"></span>Ponto CETESB InfoÁguas (camada opcional; estrela = nó PARN02100)</span>
      <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-full border-2" style="border-color:#DC2626;background:rgba(220,38,38,.15)"></span>Bacia contribuinte (esquemática)</span>
    </div>
    <div id="jupia-map" style="height:600px;width:100%"></div>
    <div class="px-8 py-4 text-xs text-slate-400 border-t border-slate-100">
      Mapa interativo - clique nos marcadores para detalhes. Estações ANA com coordenadas oficiais do inventário Hidro; barragens ONS em posição aproximada; contorno da bacia e rios em traçado esquemático. Tiles: OpenStreetMap &copy; contributors.
    </div>
  </div>
</section>

<script>
(function() {{
  var data = {payload};
  var map = L.map('jupia-map', {{ zoomControl: true, scrollWheelZoom: false }}).setView([-20.6, -49.6], 6);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 18
  }}).addTo(map);

  L.polygon(data.outline, {{ color: '#DC2626', weight: 2, opacity: 0.65, fillColor: '#DC2626', fillOpacity: 0.05, dashArray: '8,6' }})
    .bindPopup('<b style="color:#DC2626">Bacia contribuinte até Jupiá</b><br><span style="font-size:12px;color:#64748b">~480.000 km2 a montante do ponto de fechamento. Traçado esquemático, não cartografia oficial.</span>')
    .addTo(map);

  data.rivers.forEach(function(r) {{
    L.polyline(r.coords, {{ color: r.color, weight: 2.5, opacity: 0.5, dashArray: '6,4' }})
      .bindPopup('<b style="color:' + r.color + '">' + r.name + '</b><br><span style="font-size:12px;color:#64748b">Traçado esquemático do eixo do rio.</span>')
      .addTo(map);
  }});

  var canvasRenderer = L.canvas({{ padding: 0.3 }});
  function marker(lat, lon, color, radius, label, detail, useCanvas) {{
    return L.circleMarker([lat, lon], {{
      radius: radius, fillColor: color, color: '#fff', weight: 2, opacity: 1, fillOpacity: 0.88,
      renderer: useCanvas ? canvasRenderer : undefined
    }}).bindPopup('<b style="color:' + color + '">' + label + '</b>' + (detail ? '<br><span style="font-size:12px;color:#64748b">' + detail + '</span>' : ''));
  }}

  data.reservoirs.forEach(function(r) {{
    marker(r.lat, r.lon, r.color, 9, r.name, r.basin + ' - reservatório ONS (2000-2025)<br>Posição aproximada da barragem.').addTo(map);
  }});

  var styles = {{
    requested: {{ color: '#B41E1E', radius: 11, note: 'Match direto da demanda UHE JUPIA SUCURIU' }},
    series: {{ color: '#0F7B5F', radius: 10, note: 'Série histórica CSV coletada (cotas/vazões)' }},
    inventory: {{ color: '#0B5CAD', radius: 7, note: 'Inventário ANA/Hidro' }}
  }};
  data.stations.forEach(function(s) {{
    var st = styles[s.category];
    var detail = 'Código ' + s.code + (s.river ? ' - ' + s.river : '') + '<br>' + s.municipality + '<br>' + st.note;
    marker(s.lat, s.lon, st.color, st.radius, s.name, detail).addTo(map);
  }});

  var qualityLayer = L.layerGroup();
  data.quality.forEach(function(q) {{
    var detail = 'Codigo ' + q.code + ' - ' + q.water_body + '<br>' + q.entity + ' (' + q.uf + ')<br>' +
      q.parameters + ' parâmetros - série ' + q.period + '<br>Indicadores anuais ANA/RNQA (OD, DBO, fósforo, turbidez, E.coli, IQA)';
    marker(q.lat, q.lon, '#6B48A8', 5, 'Qualidade ' + q.code, detail, true).addTo(qualityLayer);
  }});

  var infoLayer = L.layerGroup();
  data.infoaguas.forEach(function(p) {{
    var detail = (p.system || 'Sistema hidrico') + '<br>' + (p.municipality || '') + '<br>' +
      p.parameters + ' parâmetros - ' + p.samples + ' amostras - série ' + p.period +
      '<br>CETESB InfoÁguas (amostras mensais por coleta)' + (p.is_node ? '<br><b>Nó receptor: ponto sobre a barragem de Jupiá</b>' : '');
    if (p.is_node) {{
      L.marker([p.lat, p.lon], {{
        icon: L.divIcon({{ className: '', html: '<div style="font-size:22px;line-height:22px;color:#C75D2C;text-shadow:0 0 3px #fff">&#9733;</div>', iconSize: [22, 22], iconAnchor: [11, 11] }})
      }}).bindPopup('<b style="color:#C75D2C">' + p.code + ' - nó de Jupiá</b><br><span style="font-size:12px;color:#64748b">' + detail + '</span>').addTo(infoLayer);
    }} else {{
      marker(p.lat, p.lon, '#C75D2C', 6, 'InfoAguas ' + p.code, detail, true).addTo(infoLayer);
    }}
  }});

  var overlays = {{}};
  if (data.quality.length) {{ overlays['Estacoes de qualidade ANA/RNQA'] = qualityLayer; }}
  if (data.infoaguas.length) {{ overlays['Pontos CETESB InfoAguas'] = infoLayer; infoLayer.addTo(map); }}
  if (Object.keys(overlays).length) {{
    L.control.layers(null, overlays, {{ collapsed: false }}).addTo(map);
  }}

  L.marker([data.outlet.lat, data.outlet.lon], {{
    icon: L.divIcon({{ className: '', html: '<div style="font-size:26px;line-height:26px;color:#DC2626;text-shadow:0 0 3px #fff">&#9733;</div>', iconSize: [26, 26], iconAnchor: [13, 13] }})
  }}).bindPopup('<b style="color:#DC2626">Ponto de fechamento Jupiá</b><br><span style="font-size:12px;color:#64748b">-20.868, -51.628 - Rio Paraná, entre Três Lagoas-MS e Castilho/Andradina-SP.</span>').addTo(map);
}})();
</script>
"""


def recorte_block(context: dict[str, Any]) -> str:
    recorte = context.get("spatial_recorte", {})
    rivers = "".join(f"<li>{esc(item)}</li>" for item in recorte.get("structuring_rivers", []))
    focus = "".join(f"<li>{esc(item)}</li>" for item in recorte.get("local_focus", []))
    return f"""
<section class="max-w-6xl mx-auto px-6 pb-6">
  <div class="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
    <div class="px-8 pt-7 pb-4 flex items-start gap-4">
      <div class="mt-0.5 flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center" style="background:rgba(27,117,187,.10)">
        <span class="material-symbols-outlined text-xl" style="color:#1B75BB">map</span>
      </div>
      <div>
        <span class="badge" style="background:rgba(27,117,187,.10);color:#1B75BB">Recorte</span>
        <h2 class="text-xl font-bold text-slate-800 mt-2">{esc(recorte.get("short_name", "Recorte geografico"))}</h2>
        <p class="text-sm text-slate-600 leading-relaxed mt-2">{esc(recorte.get("definition", ""))}</p>
      </div>
    </div>
    <div class="px-8 pb-2"><div class="gold-bar"></div></div>
    <div class="px-8 py-5 grid lg:grid-cols-4 gap-5">
      <div class="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
        <p class="field-label mb-2"><span class="material-symbols-outlined text-sm mr-1">account_tree</span>BACIA</p>
        <p class="text-sm font-semibold text-slate-800">{esc(recorte.get("main_basin", ""))}</p>
        <p class="text-xs text-slate-500 mt-2">{esc(recorte.get("watershed_area_note", ""))}</p>
      </div>
      <div class="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
        <p class="field-label mb-2"><span class="material-symbols-outlined text-sm mr-1">place</span>PONTO</p>
        <p class="text-sm font-semibold text-slate-800">{esc(recorte.get("outlet", ""))}</p>
        <p class="text-xs text-slate-500 mt-2">Coordenadas: {esc(recorte.get("outlet_coordinates", ""))}</p>
      </div>
      <div class="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
        <p class="field-label mb-2"><span class="material-symbols-outlined text-sm mr-1">water</span>RIOS</p>
        <ul class="text-sm text-slate-700 list-disc pl-4 space-y-1">{rivers}</ul>
      </div>
      <div class="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
        <p class="field-label mb-2"><span class="material-symbols-outlined text-sm mr-1">my_location</span>FOCO LOCAL</p>
        <ul class="text-sm text-slate-700 list-disc pl-4 space-y-1">{focus}</ul>
      </div>
    </div>
    <div class="mx-8 mb-7 rounded-lg px-5 py-3 flex items-start gap-3" style="background:rgba(135,113,77,.10);border-left:3px solid #87714D">
      <span class="material-symbols-outlined text-base flex-shrink-0 mt-0.5" style="color:#87714D">hub</span>
      <p class="text-sm font-semibold" style="color:#6F5D3F">{esc(recorte.get("analysis_question", ""))}</p>
    </div>
  </div>
</section>
"""


DATA_SOURCES = [
    ("ONS Dados Abertos", "Vazão afluente/defluente e volume útil dos reservatórios (2000-2025)"),
    ("ANA Hidro / SOAP HidroSerieHistorica", "Séries fluviométricas convencionais (vazão e cota) no eixo Sucuriú/Jupiá"),
    ("ANA SNIRH ArcGIS - Indicadores de Qualidade", "OD, DBO, fósforo, turbidez, E.coli e IQA anuais por estação (até 2021)"),
    ("CETESB InfoÁguas", "Amostras mensais por coleta no Baixo Tietê e no eixo Rio Paraná (2000-2026)"),
    ("INPE / BDQueimadas (WFS TerraBrasilis)", "Focos de calor anuais dentro do contorno da bacia"),
    ("IBGE BHB250", "Limites de bacia e referência territorial"),
]


def source_block(context: dict[str, Any]) -> str:
    gaps = "".join(f"<li>{esc(item)}</li>" for item in context.get("known_gaps", []))
    openalex_summary = context.get("openalex_summary", {})
    sources_html = "".join(
        f'<li><strong>{esc(name)}</strong> - {esc(desc)}</li>' for name, desc in DATA_SOURCES
    )
    return f"""
<div class="max-w-6xl mx-auto px-6 mb-6">
  <div class="rounded-xl border border-slate-200 bg-white px-6 py-4 grid lg:grid-cols-3 gap-5">
    <div class="flex items-start gap-3 lg:col-span-2">
      <span class="material-symbols-outlined text-xl flex-shrink-0 mt-0.5" style="color:#1B75BB">database</span>
      <div>
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Fontes de dados</p>
        <ul class="text-sm text-slate-700 list-disc pl-4 space-y-1">{sources_html}</ul>
      </div>
    </div>
    <div class="flex items-start gap-3">
      <span class="material-symbols-outlined text-xl flex-shrink-0 mt-0.5" style="color:#6B48A8">article</span>
      <div>
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Fontes bibliográficas</p>
        <p class="text-sm text-slate-700"><strong>{esc(openalex_summary.get("works", 0))} artigos</strong> levantados em bases bibliográficas, {esc(openalex_summary.get("with_pdf", 0))} com PDF/DOI, como apoio para a discussão de mecanismos e referências das conclusões.</p>
      </div>
    </div>
  </div>
  <div class="rounded-xl border border-slate-200 bg-white px-6 py-4 mt-3 flex items-start gap-3">
    <span class="material-symbols-outlined text-xl flex-shrink-0 mt-0.5" style="color:#B41E1E">warning</span>
    <div>
      <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Limites dos dados</p>
      <ul class="text-sm text-slate-700 list-disc pl-4 space-y-1">{gaps}</ul>
    </div>
  </div>
</div>
"""


def executive_summary_block() -> str:
    return """
<section class="max-w-6xl mx-auto px-6 pb-6">
  <div class="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
    <div class="px-8 pt-7 pb-4 flex items-start gap-4">
      <div class="mt-0.5 flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center" style="background:rgba(135,113,77,.12)">
        <span class="material-symbols-outlined text-xl" style="color:#87714D">summarize</span>
      </div>
      <div>
        <span class="badge" style="background:rgba(135,113,77,.12);color:#6F5D3F">Síntese</span>
        <h2 class="text-xl font-bold text-slate-800 mt-2">O que esta tela está contando</h2>
        <p class="text-sm text-slate-600 leading-relaxed mt-2">O relatório lê Jupiá como nó receptor do Alto Paraná. A tela começa pelo recorte contribuinte e pelos pontos de medição, passa pela escala de vazão dos rios Grande, Paranaíba, Tietê, Paraná e Sucuriú, incorpora pressões territoriais e qualidade da água, e termina testando se a vazão afluente aparece associada a poluentes, turbidez, sólidos e sedimentos no ponto PARN02100.</p>
      </div>
    </div>
    <div class="px-8 pb-2"><div class="gold-bar"></div></div>
    <div class="px-8 pb-8 grid lg:grid-cols-3 gap-5">
      <div class="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
        <p class="field-label mb-2"><span class="material-symbols-outlined text-sm mr-1">database</span>FONTES</p>
        <p class="text-sm text-slate-700 leading-relaxed">A síntese cruza séries e camadas consultadas em ONS, ANA/Hidro, ANA SNIRH/RNQA, CETESB InfoÁguas, INPE/BDQueimadas e IBGE, mantendo separadas a coleta operacional, a camada analítica e a interpretação dos gráficos.</p>
      </div>
      <div class="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
        <p class="field-label mb-2"><span class="material-symbols-outlined text-sm mr-1">article</span>LITERATURA</p>
        <p class="text-sm text-slate-700 leading-relaxed">Foram levados em consideração 130 artigos de apoio, incluindo 100 registros com PDF/DOI, como contexto para mecanismos de transporte de sedimentos, nutrientes, qualidade da água e dinâmica de reservatórios.</p>
      </div>
      <div class="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3">
        <p class="field-label mb-2"><span class="material-symbols-outlined text-sm mr-1">hub</span>HISTÓRIA ANALÍTICA</p>
        <p class="text-sm text-slate-700 leading-relaxed">A sequência das figuras constrói a história: primeiro quem contribui para Jupiá, depois onde medir, quais pressões entram na bacia e, por fim, quais variáveis ambientais respondem junto com a vazão.</p>
      </div>
    </div>
  </div>
</section>
"""


def conclusion_block() -> str:
    return """
<section class="max-w-6xl mx-auto px-6 pb-14">
  <div class="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
    <div class="px-8 pt-7 pb-4 flex items-start gap-4">
      <div class="mt-0.5 flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center" style="background:rgba(1,30,66,.08)">
        <span class="material-symbols-outlined text-xl" style="color:var(--gsu-blue)">flag</span>
      </div>
      <div>
        <span class="badge" style="background:rgba(1,30,66,.08);color:var(--gsu-blue)">Conclusão</span>
        <h2 class="text-xl font-bold text-slate-800 mt-2">O que os dados e gráficos sustentam</h2>
        <p class="text-sm text-slate-600 leading-relaxed mt-2">Os dados e figuras sustentam que Jupiá deve ser interpretado como ponto de integração: os gráficos de vazão mostram a escala dos grandes contribuintes, os mapas de estações localizam medições próximas ao barramento e ao Sucuriú, as queimadas indicam pressão territorial distribuída na área contribuinte, e as séries ANA/RNQA e CETESB InfoÁguas confirmam disponibilidade de observações para nutrientes, oxigênio, turbidez, sólidos e metais no entorno do nó.</p>
      </div>
    </div>
    <div class="px-8 pb-8">
      <div class="rounded-lg px-5 py-3 flex items-start gap-3" style="background:rgba(15,123,95,.10);border-left:3px solid #0F7B5F">
        <span class="material-symbols-outlined text-base flex-shrink-0 mt-0.5" style="color:#0F7B5F">query_stats</span>
        <p class="text-sm font-semibold" style="color:#0F7B5F">O fechamento quantitativo está na FIG10: no ponto PARN02100, a correlação mais forte é vazão afluente x turbidez (rho = +0,29; 140 meses). Isso indica que meses de maior vazão tendem a carregar mais sinal de material em suspensão, enquanto as associações negativas com condutividade e nutrientes sugerem diluição durante cheias.</p>
      </div>
    </div>
  </div>
</section>
"""


def render() -> str:
    context = load_context()
    metrics = "\n".join(metric_card(item) for item in context["metrics"])
    figures = [item for item in context["figures"] if item.get("id") != "fig0"]
    cards = "\n".join(figure_card(item) for item in figures)
    recorte_html = recorte_block(context)
    interactive_map_html = map_block(context)
    logo_100k = rel(ASSETS / "100K.webp")
    logo_gsu = rel(ASSETS / "Georgia.png")
    logo_senai = rel(ASSETS / "SENAI.svg")
    source_html = source_block(context)
    executive_summary_html = executive_summary_block()
    conclusion_html = conclusion_block()
    subtitle = context["report_subtitle"]
    note = context["scope"]["available_station_note"]

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(context["report_title"])} - Projeto FREnTE</title>
<link rel="icon" href="data:,">
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Bitter:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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
      <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold" style="background:rgba(251,191,36,.15);color:#FCD34D;border:1px solid rgba(251,191,36,.25)">Em desenvolvimento</span>
    </div>
  </div>
</header>

<section style="background:var(--gsu-blue)" class="pb-10 pt-8">
  <div class="max-w-6xl mx-auto px-6">
    <p class="text-xs font-semibold tracking-widest mb-2 uppercase" style="color:#87714D">Análise Exploratória - Bacia Hidrográfica de Jupiá</p>
    <h1 class="text-3xl lg:text-4xl font-bold text-white leading-tight mb-3">
      Bacia Hidrográfica de Jupiá<br>
      <span style="color:#C4A86C">{esc(subtitle)}</span>
    </h1>
    <p class="text-white/75 text-sm lg:text-base max-w-4xl leading-relaxed mb-6">
      Este relatório cria um novo link analítico para Jupiá. A leitura deixa de tratar Jupiá como simples extensão da cascata do Tietê e passa a considerá-lo como nó integrador do Alto Paraná, reunindo os sinais operacionais dos rios Paranaíba, Grande e Tietê, além do próprio trecho Paraná/Jupiá e do eixo Sucuriú. {esc(note)}
    </p>
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">{metrics}</div>
  </div>
</section>

<div class="max-w-6xl mx-auto px-6 py-4"><div class="gold-bar"></div></div>
{executive_summary_html}
{recorte_html}
{interactive_map_html}
{source_html}
<main class="max-w-6xl mx-auto px-6 pb-16">{cards}</main>
{conclusion_html}

<footer style="background:var(--gsu-blue)" class="py-8">
  <div class="max-w-6xl mx-auto px-6 text-center">
    <p class="text-white/40 text-xs">Projeto FREnTE - Bacia Hidrográfica de Jupiá - Dados: ONS, ANA/Hidro, ANA GitHub, ANA SNIRH ArcGIS (qualidade), INPE/BDQueimadas, IBGE e CETESB/ANA - Gerado automaticamente</p>
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
