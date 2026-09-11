"""English localization helpers for the Jupia report and its figures.

The numeric data and plotting logic remain in the Portuguese generators.  This
module only replaces presentation text so both published reports are built from
the same analytical inputs.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any


FIGURE_EXACT = {
    "Bacia contribuinte ate Jupia": "Jupia contributing basin",
    "Recorte geografico: bacia contribuinte do Alto Parana ate a UHE Jupia": "Geographic scope: Upper Parana contributing basin to the Jupia HPP",
    "Leitura: area vermelha = bacia contribuinte ate Jupia (~480.000 km2 no delineamento de referencia); linhas = rios estruturantes; pontos = estacoes/locais de evidencia. Fonte: ANA/Hidro, ONS, OpenAlex e delineamento de referencia informado pelo usuario. Mapa esquematico, nao cartografia oficial.": "How to read: red area = contributing basin to Jupia (~480,000 km2 in the reference delineation); lines = main rivers; points = monitoring/evidence locations. Source: ANA/Hidro, ONS, OpenAlex, and the user-provided reference delineation. Schematic map, not official cartography.",
    "area academica": "academic area",
    "area contribuinte": "contributing area",
    "estacao ANA/Hidro": "ANA/Hidro station",
    "no receptor": "receiving node",
    "Outlet Jupia\n-20.868, -51.628": "Jupia outlet\n-20.868, -51.628",
    "UHE JUPIA\nno integrador do Alto Parana": "JUPIA HPP\nUpper Parana integration node",
    "Sistema contribuinte de Jupia - leitura operacional ONS (2000-2025)": "Jupia contributing system - ONS operational view (2000-2025)",
    "Fonte: ONS Dados Hidrologicos de Reservatorios. Sucuriu nao aparece como identificador proprio na base local.": "Source: ONS Reservoir Hydrological Data. Sucuriu does not appear as a separate identifier in the local dataset.",
    "Vazao afluente mensal por contribuinte - media movel de 12 meses": "Monthly inflow by contributing basin - 12-month moving average",
    "Vazao afluente media (m3/s)": "Average inflow (m3/s)",
    "Faixa laranja: crise hidrica 2014-2015. Fonte: ONS Dados Abertos.": "Orange band: 2014-2015 water crisis. Source: ONS Open Data.",
    "UHE Jupia - afluencia, defluencia e volume util": "Jupia HPP - inflow, outflow, and useful storage",
    "Vazao (m3/s)": "Flow (m3/s)",
    "Volume util (%)": "Useful storage (%)",
    "Serie ONS identificada como JUPIA na bacia PARANA. Sucuriu requer coleta complementar.": "ONS series identified as JUPIA in the PARANA basin. Sucuriu requires complementary data collection.",
    "Volume util minimo anual por reservatorio selecionado": "Annual minimum useful storage by selected reservoir",
    "Volume util minimo anual (%)": "Annual minimum useful storage (%)",
    "Fonte: ONS Dados Abertos. Cores vermelhas indicam anos de menor armazenamento relativo.": "Source: ONS Open Data. Red colors indicate years with lower relative storage.",
    "Cota local (cm)": "Local gauge height (cm)",
    "Sem serie de cota coletada": "No gauge-height series collected",
    "Cota media mensal por regua ANA - paineis independentes em ordem montante-jusante": "Monthly average gauge height at ANA stations - independent panels ordered upstream to downstream",
    "Fonte: ANA GitHub hidro-dados-estacoes-convencionais (run operational-collect-jupia). Cada painel usa escala vertical propria. As cotas sao leituras locais de regua e nao sao amarradas altialtimetricamente; portanto, nao comparar valores absolutos entre estacoes. A leitura correta e comparar a variacao temporal dentro de cada regua e a sequencia espacial montante -> jusante.": "Source: ANA GitHub hidro-dados-estacoes-convencionais (run operational-collect-jupia). Each panel uses its own vertical scale. Gauge heights are local readings without a shared elevation datum; therefore, absolute values must not be compared across stations. The correct interpretation is to compare temporal variation within each gauge and the spatial sequence from upstream to downstream.",
    "Focos de calor por ano (escala log)": "Active fire detections per year (log scale)",
    "Focos de calor INPE dentro da bacia contribuinte, por estado": "INPE active fire detections within the contributing basin, by state",
    "Fonte: INPE/BDQueimadas via WFS TerraBrasilis, coleta com envelope da bacia e filtro point-in-polygon no contorno esquematico do recorte.\nMato Grosso do Sul em vermelho cobre o entorno Tres Lagoas/Jupia e o eixo Sucuriu; Goias/MG cobrem as cabeceiras do Paranaiba e do Grande.": "Source: INPE/BDQueimadas via WFS TerraBrasilis, collected using the basin envelope and a point-in-polygon filter against the schematic boundary.\nMato Grosso do Sul in red covers the Tres Lagoas/Jupia surroundings and the Sucuriu corridor; Goias/MG cover the headwaters of the Paranaiba and Grande rivers.",
    "Oxigenio dissolvido (mg/L)": "Dissolved oxygen (mg/L)",
    "DBO (mg/L)": "BOD (mg/L)",
    "Fosforo total (mg/L)": "Total phosphorus (mg/L)",
    "Nitrato (mg/L)": "Nitrate (mg/L)",
    "Condutividade (uS/cm)": "Specific conductance (uS/cm)",
    "Turbidez (NTU)": "Turbidity (NTU)",
    "IQA": "WQI",
    "Qualidade da agua na bacia contribuinte - media anual das estacoes ANA/RNQA": "Water quality in the contributing basin - annual average across ANA/RNQA stations",
    "Fonte: ANA SNIRH ArcGIS, Indicadores de Qualidade (series historicas ate 2021). Media simples das medias anuais por estacao dentro do contorno da bacia;\nvermelho = estacoes em Mato Grosso do Sul (entorno Jupia/Sucuriu), azul = contribuintes a montante. Numero de estacoes varia por ano e parametro.": "Source: ANA SNIRH ArcGIS, Quality Indicators (historical series through 2021). Simple average of annual station means within the basin boundary;\nred = stations in Mato Grosso do Sul (Jupia/Sucuriu surroundings), blue = upstream contributors. The number of stations varies by year and parameter.",
    "MS / entorno Jupia": "MS / Jupia surroundings",
    "Montante (SP, MG, GO, DF)": "Upstream (SP, MG, GO, DF)",
    "Poluentes e nutrientes no no de Jupia - CETESB InfoAguas (media movel de 12 meses)": "Pollutants and nutrients at the Jupia node - CETESB InfoAguas (12-month moving average)",
    "Fonte: CETESB InfoAguas, amostras por coleta agregadas em medias mensais. TIET02900 = Rio Tiete (afluente que chega); TITR02100 = Res. Tres Irmaos;\nPARN02100 = sobre a barragem de Jupia (no receptor). Fosforo e turbidez em escala log para acomodar picos.": "Source: CETESB InfoAguas, sampling results aggregated into monthly averages. TIET02900 = Tiete River (incoming tributary); TITR02100 = Tres Irmaos Reservoir;\nPARN02100 = on the Jupia dam (receiving node). Phosphorus and turbidity use a log scale to accommodate peaks.",
    "Metais no no de Jupia - ponto CETESB PARN02100 (media movel de 12 meses sobre as coletas)": "Metals at the Jupia node - CETESB PARN02100 (12-month moving average of samples)",
    "Fonte: CETESB InfoAguas, ponto PARN02100 sobre a barragem de Jupia. Pontos claros = coletas individuais; linha = media movel de 12 meses.\nFerro acompanha a fracao mineral/sedimento; cobre, chumbo e zinco sinalizam aporte antropico do trecho a montante. Escala log para acomodar a variabilidade.": "Source: CETESB InfoAguas, PARN02100 on the Jupia dam. Light points = individual samples; line = 12-month moving average.\nIron tracks the mineral/sediment fraction; copper, lead, and zinc indicate anthropogenic inputs from the upstream reach. Log scale accommodates variability.",
    "Ferro total (mg/L)": "Total iron (mg/L)",
    "Cobre total (mg/L)": "Total copper (mg/L)",
    "Chumbo total (mg/L)": "Total lead (mg/L)",
    "Zinco total (mg/L)": "Total zinc (mg/L)",
    "Correlação de Spearman no nó de Jupiá (PARN02100)": "Spearman correlation at the Jupia node (PARN02100)",
    "Coeficiente de Spearman (rho)": "Spearman coefficient (rho)",
    "Correlação no nó de Jupiá: vazão x poluentes e sedimentos": "Correlation at the Jupia node: flow vs. pollutants and sediments",
    "Fonte: vazão afluente e volume útil do nó (ONS) cruzados mês a mês com poluentes/sedimentos do ponto CETESB PARN02100 (sobre a barragem). Spearman mede associação monotônica; vermelho = positiva, azul = negativa. Vazão x turbidez/sólidos positiva indica transporte de sedimento; vazão x condutividade negativa indica diluição.": "Source: node inflow and useful storage (ONS) matched month by month with pollutants/sediments at CETESB PARN02100 (on the dam). Spearman measures monotonic association; red = positive, blue = negative. Positive flow vs. turbidity/solids indicates sediment transport; negative flow vs. conductance indicates dilution.",
}


FIGURE_REPLACEMENTS = [
    ("Informação não disponível", "Information unavailable"),
    ("INFORMAÇÃO NÃO DISPONÍVEL", "INFORMATION UNAVAILABLE"),
    ("Porto Primavera (jusante do nó)", "Porto Primavera (downstream of the node)"),
    ("Reservatório de Três Irmãos", "Tres Irmaos Reservoir"),
    ("sobre a barragem de Jupiá", "on the Jupia dam"),
    ("UHE JUPIÁ", "JUPIA HPP"),
    ("UHE Jupia", "Jupia HPP"),
    ("RIO PARANÁ", "PARANA RIVER"),
    ("RIO PARANAÍBA", "PARANAIBA RIVER"),
    ("RIO SUCURIÚ", "SUCURIU RIVER"),
    ("RIO TIETÊ", "TIETE RIVER"),
    ("Rio Paraná", "Parana River"),
    ("Rio Paranaíba", "Paranaiba River"),
    ("Rio Sucuriú", "Sucuriu River"),
    ("Rio Tietê", "Tiete River"),
    ("Rio Parana / Jupia", "Parana River / Jupia"),
    ("Alto Parana / La Plata", "Upper Parana / La Plata"),
    ("Rio Paranaiba", "Paranaiba River"),
    ("Rio Sucuriu", "Sucuriu River"),
    ("Rio Tiete", "Tiete River"),
    ("Rio Parana", "Parana River"),
    ("Rio Grande", "Grande River"),
    ("UHE Jupia Jusante", "Jupia HPP Downstream"),
    ("UHE Jupia Barramento", "Jupia HPP Dam"),
    ("Barragem de Jupia", "Jupia Dam"),
    ("Res. Tres Irmaos", "Tres Irmaos Res."),
    ("Jupia - Ponte", "Jupia - Bridge"),
    (" BARRAMENTO", " DAM"),
    (" RESERVATÓRIO", " RESERVOIR"),
    (" MONTANTE", " UPSTREAM"),
    (" JUSANTE", " DOWNSTREAM"),
    ("Barragem ", "Dam "),
    ("Reservatório ", "Reservoir "),
    ("Montante", "Upstream"),
    ("Jusante", "Downstream"),
    ("Vazao afluente", "Inflow"),
    ("Volume util", "Useful storage"),
    ("Solidos totais", "Total solids"),
    ("Fosforo total", "Total phosphorus"),
    ("Ferro total", "Total iron"),
    ("Condutividade", "Specific conductance"),
    ("Turbidez", "Turbidity"),
    ("Nitrato", "Nitrate"),
    ("OD", "DO"),
    ("Afluencia", "Inflow"),
    ("Defluencia", "Outflow"),
    ("reservatorios", "reservoirs"),
    ("m3/s medio", "m3/s average"),
    ("escala propria", "individual scale"),
    ("Ano", "Year"),
    ("Distrito Federal", "Federal District"),
]


def translate_figure_text(value: str) -> str:
    """Translate Matplotlib-visible text while preserving numbers and codes."""
    if value in FIGURE_EXACT:
        return FIGURE_EXACT[value]
    translated = value
    translated = re.sub(r"^(\d+) reservatorios$", r"\1 reservoirs", translated)
    translated = re.sub(r"^(\d+) m3/s medio$", r"\1 m3/s average", translated)
    translated = re.sub(r"^escala propria\n", "individual scale\n", translated)
    for source, target in FIGURE_REPLACEMENTS:
        translated = translated.replace(source, target)
    return translated


def _set_fields(target: dict[str, Any], values: dict[str, Any]) -> None:
    for key, value in values.items():
        target[key] = value


def english_context(context: dict[str, Any]) -> dict[str, Any]:
    """Return the report context with prose localized and numeric values intact."""
    out = deepcopy(context)
    out["report_title"] = "Jupia Watershed"
    out["report_subtitle"] = "Paranaiba, Grande, Tiete, and Parana/Jupia contributing system"
    _set_fields(
        out["scope"],
        {
            "primary_node": "Jupia HPP",
            "requested_station": "JUPIA HPP SUCURIU",
            "available_station_note": "The ANA collection found direct matches for JUPIA HPP RIO SUCURIU and JUPIA HPP SUCURIU in the Hidro inventory; in the local ONS data, the operational series remains identified as JUPIA in the PARANA basin.",
            "source": "ONS Reservoir Hydrological Data, ANA Hidro/SOAP, ANA GitHub hidro-dados-estacoes-convencionais, IBGE BHB250, and CETESB/ANA documents.",
            "academic_source": "OpenAlex API /works, Jupia academic round without Perplexity, with raw JSON preserved.",
            "geographic_scope": "Jupia HPP and the Tres Lagoas/Castilho surroundings; Sucuriu River; Parana River; and the Tiete, Grande, and Paranaiba contributing rivers in the Upper Parana.",
        },
    )
    _set_fields(
        out["spatial_recorte"],
        {
            "title": "Analyzed geographic scope",
            "short_name": "Upper Parana contributing basin to the Jupia HPP",
            "outlet": "Analytical outlet on the Parana River, near the Jupia HPP / Eng. Souza Dias, between Tres Lagoas-MS and Castilho/Andradina-SP.",
            "watershed_area_note": "Area delineated on the global watershed site: approximately 480,000 km2 upstream of the outlet.",
            "definition": "This report analyzes the area draining to Jupia before the outlet on the Parana River. The scope is neither the Tiete basin alone nor only the Jupia Reservoir; it is the Upper Parana contributing system that combines the Paranaiba, Grande, Tiete, and Parana rivers at the Jupia receiving node.",
            "main_basin": "Upper Parana to Jupia",
            "structuring_rivers": ["Paranaiba River", "Grande River", "Tiete River", "Parana River"],
            "local_focus": ["Jupia HPP / Eng. Souza Dias", "Sucuriu River", "ANA/Hidro stations JUPIA HPP SUCURIU", "Tres Lagoas-Castilho-Andradina surroundings"],
            "analysis_question": "How do the Paranaiba, Grande, Tiete, and Parana rivers, together with reservoir operations, pollution, land use, climate, and sediments, shape the Jupia receiving node?",
        },
    )

    metric_text = [
        ("ONS flow", "27 reservoirs · 26 years"),
        ("Streamflow stations", "ANA series 1924-01-01-2014-12-01"),
        ("ANA/RNQA quality", "stations in the basin · 1978-2021"),
        ("InfoAguas samples", "226 parameters · 14 sites"),
        ("Node correlation", "months of flow vs. pollutants (PARN02100)"),
        ("Articles (sources)", "100 with PDF/DOI"),
    ]
    for metric, (label, detail) in zip(out["metrics"], metric_text):
        metric["label"] = label
        metric["detail"] = detail
        if label == "InfoAguas samples":
            metric["value"] = metric["value"].replace(".", ",")

    out["known_gaps"] = [
        "ANA/RNQA quality indicators (fig13) extend through 2021; the monthly CETESB InfoAguas series (fig14/fig15) covers 2000-2026 at Lower Tiete and Parana River sites, including PARN02100 on the Jupia dam. Sites in UGRHIs 18, 15, and 12 are outside this round.",
        "The node correlation (fig10) uses CETESB site PARN02100, on the dam; it measures the signature at the node itself, not the isolated contribution of each upstream tributary.",
        "Porto Primavera is downstream of the Jupia node; it appears as context for the Parana reach, not as a contributor within the scope.",
        "The basin boundary is schematic; refinement with official ANA/IBGE ottobasins may move stations and fire detections near the boundary.",
    ]

    figure_overrides = {
        "fig0": {
            "title": "Geographic scope: contributing basin to Jupia",
            "tag": "Map",
            "summary": "Schematic map of the Upper Parana contributing basin to the Jupia outlet, with the Paranaiba, Grande, Tiete, and Parana rivers as the main axes and Sucuriu/Jupia as the local focus.",
            "interpretation": "The red area represents the system that can deliver water, sediments, nutrients, and pollutants to Jupia. ANA/Hidro points are local measurements; colored areas indicate the sub-basins and evidence regions used in the analysis.",
            "highlight": "The unit of analysis is the contributing system to Jupia: river behavior first, pollution and pressures next, and correlation at the receiving node at the end.",
        },
        "fig1": {
            "title": "Jupia contributing system",
            "tag": "Structure",
            "summary": "Diagram of the four operational blocks used in this first analysis: Grande, Paranaiba, Tiete, and Parana/Jupia.",
            "interpretation": "Jupia should be read as the Upper Parana integration node. The Tiete remains relevant but now appears alongside the Grande, Paranaiba, and Sucuriu/Jupia corridor confirmed in the ANA inventory.",
            "highlight": "The analytical unit shifts from the Tiete cascade alone to the integrated Jupia contributing basin.",
        },
        "fig2": {
            "title": "Monthly inflow by major contributing basin",
            "tag": "Hydrology",
            "summary": "Average monthly inflow series by ONS operational basin, aggregating the selected reservoirs in each contributing basin.",
            "interpretation": "The comparison shows the relative scale of the contributors that shape Jupia. The Grande and Paranaiba substantially broaden the hydrological context compared with a Tiete-only interpretation.",
            "highlight": "The Jupia report must bring together the three major rivers instead of reusing only the Tiete narrative.",
        },
        "fig3": {
            "title": "Jupia node: inflow, outflow, and useful storage",
            "tag": "Jupia",
            "summary": "Monthly ONS series for the Jupia HPP, with average inflow, outflow, and useful storage.",
            "interpretation": "The series positions Jupia as the system's operational receiver. Complementary collection has already identified ANA codes associated with the Jupia HPP/Sucuriu, enabling a later bridge to conventional series and water quality.",
            "highlight": "In ONS data, the auditable point is JUPIA; in the ANA inventory, JUPIA HPP SUCURIU appears under code 63003300.",
        },
        "fig11": {
            "title": "Local ANA gauge heights along the Sucuriu/Jupia corridor",
            "tag": "Local rivers",
            "summary": "Average monthly gauge height at the four requested conventional ANA gauges, shown on independent vertical panels ordered upstream to downstream: Upper Sucuriu, Sao Jose do Sucuriu, Jupia-Bridge, and Jupia HPP Downstream.",
            "interpretation": "Gauge heights are local readings without a shared elevation datum across stations. The figure therefore does not compare absolute elevation between gauges; it compares temporal variation within each gauge and the spatial sequence of the system.",
            "highlight": "Revised figure: each gauge uses its own vertical scale to prevent the incorrect inference that one station is meters above another.",
        },
        "fig4": {
            "title": "Critical years by reservoir",
            "tag": "Water stress",
            "summary": "Heatmap of annual minimum useful storage for the selected reservoirs.",
            "interpretation": "The panel identifies years of synchronized stress and distinguishes responses at headwaters, contributing basins, and the receiving node.",
            "highlight": "Dry events should be evaluated as system-wide signals, not as isolated anomalies in a single cascade.",
        },
        "fig12": {
            "title": "Territorial pressure: active fire detections within the contributing basin",
            "tag": "Pressures",
            "summary": "INPE/BDQueimadas active fire detections by state and year, collected via WFS using the full basin envelope and filtered by the contributing-basin boundary (point-in-polygon). Coverage includes Mato Grosso do Sul, Sao Paulo, Minas Gerais, Goias/DF, and boundary areas.",
            "interpretation": "This is the report's quantitative pressure layer: an annual geolocated series that now also covers the Grande and Paranaiba headwaters, which the prior Tiete-corridor collection did not reach. Mato Grosso do Sul contains the Tres Lagoas/Jupia surroundings and the Sucuriu corridor.",
            "highlight": "2,305,936 detections within the basin in 2000-2025; the pressure layer now covers the full scope, not only the Tiete corridor.",
        },
        "fig13": {
            "title": "Water quality in the basin: DO, BOD, phosphorus, turbidity, and WQI",
            "tag": "Pollutants",
            "summary": "Annual water-quality indicators from the ANA/RNQA network (station averages, 1978-2021) for stations within the contributing basin, separating the Mato Grosso do Sul/Jupia surroundings from upstream contributors (SP/MG/GO/DF).",
            "interpretation": "The pollutant analysis no longer depends only on PDFs and literature: DO, BOD, total phosphorus, turbidity, E. coli, and WQI are now available as annual tabular series with coordinates, ready to be matched with flow and useful storage at the receiving node.",
            "highlight": "906 quality stations within the basin (12 in MS), covering 1978-2021; source: ANA SNIRH ArcGIS Quality Indicators.",
        },
        "fig14": {
            "title": "Pollutants and nutrients at the Jupia node (CETESB InfoAguas, monthly)",
            "tag": "Pollutants",
            "summary": "Monthly sampling series (2000-2026) at three sites: TIET02900 (Tiete River, the incoming polluted tributary), TITR02100 (Tres Irmaos Reservoir), and PARN02100 (on the Jupia dam, the receiving node). Six variables: dissolved oxygen, BOD, total phosphorus, nitrate nitrogen, specific conductance, and turbidity.",
            "interpretation": "Here the pollutant analysis gains monthly resolution and includes nutrients (phosphorus and nitrate, linked to agricultural land use) and proxies for dissolved and sediment loads (specific conductance and turbidity). Comparing the incoming Tiete with the Parana at the dam shows how much of the tributary signature persists at the node.",
            "highlight": "32,071 samples · 226 parameters · 14 sites (Lower Tiete + Parana River corridor) · 2000-02-09 to 2026-05-19.",
        },
        "fig15": {
            "title": "Metals at the Jupia node: iron, copper, lead, and zinc",
            "tag": "Pollutants",
            "summary": "Monthly series of metals measured by CETESB at PARN02100, on the Jupia dam: total iron, copper, lead, and zinc (mg/L), with the CONAMA class reference where applicable.",
            "interpretation": "Metals are associated with sediments and suspended material reaching the reservoir and are therefore relevant to the node's geomorphological interpretation. Iron tracks the mineral fraction; copper, lead, and zinc indicate anthropogenic and industrial contributions from the upstream reach.",
            "highlight": "The metals layer connects the sediment load (turbidity/solids) to mineral and anthropogenic inputs measured directly at the receiving node.",
        },
        "fig10": {
            "title": "Correlation at the Jupia node: flow vs. pollutants and sediments",
            "tag": "Correlation",
            "summary": "Monthly Spearman correlation matrix between node hydrology (inflow and useful storage, ONS) and pollutants/sediments measured at the node itself (CETESB PARN02100): turbidity, total solids, dissolved oxygen, phosphorus, nitrate, specific conductance, and iron. The strongest flow-pollutant pairs appear as scatter plots alongside the matrix.",
            "interpretation": "This closes the premise: rivers -> pollutants -> correlation becomes a coefficient rather than a claim. Positive flow-turbidity/solids coefficients indicate flow-driven sediment transport; negative flow-conductance/nutrient correlations indicate dilution during high-flow events. Useful storage adds the reservoir-effect perspective.",
            "highlight": "Strongest correlation: inflow vs. turbidity (rho = +0.29), calculated over 140 months at the PARN02100 node.",
        },
    }
    for figure in out["figures"]:
        _set_fields(figure, figure_overrides[figure["id"]])
    return out


HTML_REPLACEMENTS = {
    '<html lang="pt-BR">': '<html lang="en">',
    "Projeto 100K": "100K Project",
    " - Projeto FREnTE": " - FREnTE Project",
    "Projeto FREnTE - EDA": "FREnTE Project - EDA",
    "Em desenvolvimento": "In development",
    "Análise Exploratória - Bacia Hidrográfica de Jupiá": "Exploratory Analysis - Jupia Watershed",
    "Bacia Hidrográfica de Jupiá": "Jupia Watershed",
    "Este relatório cria um novo link analítico para Jupiá. A leitura deixa de tratar Jupiá como simples extensão da cascata do Tietê e passa a considerá-lo como nó integrador do Alto Paraná, reunindo os sinais operacionais dos rios Paranaíba, Grande e Tietê, além do próprio trecho Paraná/Jupiá e do eixo Sucuriú.": "This report provides a dedicated analytical view of Jupia. It no longer treats Jupia as a simple extension of the Tiete cascade; instead, it considers Jupia as the Upper Parana integration node, combining operational signals from the Paranaiba, Grande, and Tiete rivers with the Parana/Jupia reach and the Sucuriu corridor.",
    "O QUE MOSTRA": "WHAT IT SHOWS",
    "INTERPRETACAO ANALITICA": "ANALYTICAL INTERPRETATION",
    "Figura nao encontrada": "Figure not found",
    "Localização": "Location",
    "Mapa interativo": "Interactive map",
    "Onde os dados foram coletados - bacia contribuinte até Jupiá": "Where the data were collected - contributing basin to Jupia",
    "O contorno vermelho indica a bacia contribuinte (~480.000 km2, traçado esquemático); cada ponto é um local real de medição ou um reservatório ONS usado na análise.": "The red boundary indicates the contributing basin (~480,000 km2, schematic delineation); each point is an actual monitoring location or an ONS reservoir used in the analysis.",
    "Estação ANA - match UHE Jupiá Sucuriú": "ANA station - Jupia HPP Sucuriu match",
    "Estação ANA com série CSV coletada": "ANA station with collected CSV series",
    "Estação ANA inventariada": "Inventoried ANA station",
    "Reservatório ONS (cor por bacia)": "ONS reservoir (color by basin)",
    "Estação de qualidade ANA/RNQA (camada opcional)": "ANA/RNQA quality station (optional layer)",
    "Ponto CETESB InfoÁguas (camada opcional; estrela = nó PARN02100)": "CETESB InfoAguas site (optional layer; star = PARN02100 node)",
    "Bacia contribuinte (esquemática)": "Contributing basin (schematic)",
    "Mapa interativo - clique nos marcadores para detalhes. Estações ANA com coordenadas oficiais do inventário Hidro; barragens ONS em posição aproximada; contorno da bacia e rios em traçado esquemático.": "Interactive map - click markers for details. ANA stations use official Hidro inventory coordinates; ONS dams use approximate positions; the basin boundary and rivers are schematic.",
    "Bacia contribuinte até Jupiá": "Contributing basin to Jupia",
    "~480.000 km2 a montante do ponto de fechamento. Traçado esquemático, não cartografia oficial.": "~480,000 km2 upstream of the outlet. Schematic delineation, not official cartography.",
    "Traçado esquemático do eixo do rio.": "Schematic river centerline.",
    "reservatório ONS (2000-2025)": "ONS reservoir (2000-2025)",
    "Posição aproximada da barragem.": "Approximate dam position.",
    "Match direto da demanda UHE JUPIA SUCURIU": "Direct match for the JUPIA HPP SUCURIU request",
    "Série histórica CSV coletada (cotas/vazões)": "Collected historical CSV series (gauge height/flow)",
    "Inventário ANA/Hidro": "ANA/Hidro inventory",
    "Código ": "Code ",
    "Codigo ": "Code ",
    " parâmetros - série ": " parameters - series ",
    " parâmetros - ": " parameters - ",
    "Indicadores anuais ANA/RNQA (OD, DBO, fósforo, turbidez, E.coli, IQA)": "Annual ANA/RNQA indicators (DO, BOD, phosphorus, turbidity, E. coli, WQI)",
    "Qualidade ": "Quality ",
    "Sistema hidrico": "Water system",
    " amostras - série ": " samples - series ",
    "CETESB InfoÁguas (amostras mensais por coleta)": "CETESB InfoAguas (monthly sampling results)",
    "Nó receptor: ponto sobre a barragem de Jupiá": "Receiving node: site on the Jupia dam",
    " - nó de Jupiá": " - Jupia node",
    "Estacoes de qualidade ANA/RNQA": "ANA/RNQA quality stations",
    "Pontos CETESB InfoAguas": "CETESB InfoAguas sites",
    "Ponto de fechamento Jupiá": "Jupia outlet",
    "Rio Paraná, entre Três Lagoas-MS e Castilho/Andradina-SP.": "Parana River, between Tres Lagoas-MS and Castilho/Andradina-SP.",
    "Recorte": "Scope",
    "Recorte geografico": "Geographic scope",
    ">BACIA<": ">BASIN<",
    ">PONTO<": ">OUTLET<",
    ">RIOS<": ">RIVERS<",
    ">FOCO LOCAL<": ">LOCAL FOCUS<",
    "Coordenadas:": "Coordinates:",
    "Fontes de dados": "Data sources",
    "Fontes bibliográficas": "Bibliographic sources",
    " artigos": " articles",
    " levantados em bases bibliográficas, ": " retrieved from bibliographic databases, ",
    " com PDF/DOI, como apoio para a discussão de mecanismos e referências das conclusões.": " with PDF/DOI, supporting the discussion of mechanisms and the references behind the conclusions.",
    "Limites dos dados": "Data limitations",
    "Vazão afluente/defluente e volume útil dos reservatórios (2000-2025)": "Reservoir inflow/outflow and useful storage (2000-2025)",
    "ONS Dados Abertos": "ONS Open Data",
    "ANA SNIRH ArcGIS - Indicadores de Qualidade": "ANA SNIRH ArcGIS - Quality Indicators",
    "Séries fluviométricas convencionais (vazão e cota) no eixo Sucuriú/Jupiá": "Conventional streamflow and gauge-height series along the Sucuriu/Jupia corridor",
    "OD, DBO, fósforo, turbidez, E.coli e IQA anuais por estação (até 2021)": "Annual DO, BOD, phosphorus, turbidity, E. coli, and WQI by station (through 2021)",
    "Amostras mensais por coleta no Baixo Tietê e no eixo Rio Paraná (2000-2026)": "Monthly sampling results in the Lower Tiete and Parana River corridor (2000-2026)",
    "Focos de calor anuais dentro do contorno da bacia": "Annual active fire detections within the basin boundary",
    "Limites de bacia e referência territorial": "Basin boundaries and territorial reference",
    "Síntese": "Overview",
    "O que esta tela está contando": "What this report shows",
    "O relatório lê Jupiá como nó receptor do Alto Paraná. A tela começa pelo recorte contribuinte e pelos pontos de medição, passa pela escala de vazão dos rios Grande, Paranaíba, Tietê, Paraná e Sucuriú, incorpora pressões territoriais e qualidade da água, e termina testando se a vazão afluente aparece associada a poluentes, turbidez, sólidos e sedimentos no ponto PARN02100.": "The report interprets Jupia as the receiving node of the Upper Parana. It begins with the contributing area and monitoring locations, moves through the flow scale of the Grande, Paranaiba, Tiete, Parana, and Sucuriu rivers, incorporates territorial pressures and water quality, and ends by testing whether inflow is associated with pollutants, turbidity, solids, and sediments at PARN02100.",
    ">FONTES<": ">SOURCES<",
    ">LITERATURA<": ">LITERATURE<",
    ">HISTÓRIA ANALÍTICA<": ">ANALYTICAL STORY<",
    "A síntese cruza séries e camadas consultadas em ONS, ANA/Hidro, ANA SNIRH/RNQA, CETESB InfoÁguas, INPE/BDQueimadas e IBGE, mantendo separadas a coleta operacional, a camada analítica e a interpretação dos gráficos.": "The synthesis combines series and layers from ONS, ANA/Hidro, ANA SNIRH/RNQA, CETESB InfoAguas, INPE/BDQueimadas, and IBGE while keeping operational collection, the analytical layer, and chart interpretation separate.",
    "Foram levados em consideração 130 artigos de apoio, incluindo 100 registros com PDF/DOI, como contexto para mecanismos de transporte de sedimentos, nutrientes, qualidade da água e dinâmica de reservatórios.": "The analysis considered 130 supporting articles, including 100 records with PDF/DOI, as context for sediment transport, nutrients, water quality, and reservoir dynamics.",
    "A sequência das figuras constrói a história: primeiro quem contribui para Jupiá, depois onde medir, quais pressões entram na bacia e, por fim, quais variáveis ambientais respondem junto com a vazão.": "The figure sequence builds the story: first, what contributes to Jupia; then, where measurements are available; next, which pressures enter the basin; and finally, which environmental variables respond with flow.",
    "Conclusão": "Conclusion",
    "O que os dados e gráficos sustentam": "What the data and figures support",
    "Os dados e figuras sustentam que Jupiá deve ser interpretado como ponto de integração: os gráficos de vazão mostram a escala dos grandes contribuintes, os mapas de estações localizam medições próximas ao barramento e ao Sucuriú, as queimadas indicam pressão territorial distribuída na área contribuinte, e as séries ANA/RNQA e CETESB InfoÁguas confirmam disponibilidade de observações para nutrientes, oxigênio, turbidez, sólidos e metais no entorno do nó.": "The data and figures support interpreting Jupia as an integration point: flow charts show the scale of the major contributors, station maps locate measurements near the dam and Sucuriu, fire detections indicate distributed territorial pressure across the contributing area, and ANA/RNQA and CETESB InfoAguas series confirm observations of nutrients, oxygen, turbidity, solids, and metals around the node.",
    "O fechamento quantitativo está na FIG10: no ponto PARN02100, a correlação mais forte é vazão afluente x turbidez (rho = +0,29; 140 meses). Isso indica que meses de maior vazão tendem a carregar mais sinal de material em suspensão, enquanto as associações negativas com condutividade e nutrientes sugerem diluição durante cheias.": "The quantitative conclusion is in FIG10: at PARN02100, the strongest correlation is inflow vs. turbidity (rho = +0.29; 140 months). This indicates that higher-flow months tend to carry a stronger suspended-material signal, while negative associations with conductance and nutrients suggest dilution during high-flow events.",
    "Projeto FREnTE - Bacia Hidrográfica de Jupiá - Dados:": "FREnTE Project - Jupia Watershed - Data:",
    "ANA SNIRH ArcGIS (qualidade)": "ANA SNIRH ArcGIS (quality)",
    "IBGE e CETESB/ANA": "IBGE and CETESB/ANA",
    "Gerado automaticamente": "Generated automatically",
}


def translate_report_html(html: str) -> str:
    """Translate fixed template copy and JavaScript popup labels."""
    for source, target in sorted(HTML_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True):
        html = html.replace(source, target)
    return html


def translate_payload(value: Any) -> Any:
    """Translate strings in the interactive-map payload recursively."""
    if isinstance(value, str):
        return translate_figure_text(value)
    if isinstance(value, list):
        return [translate_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: translate_payload(item) for key, item in value.items()}
    return value
