from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


def finite(value):
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def records(frame: pd.DataFrame):
    return [
        {str(k): finite(v) for k, v in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def main() -> None:
    ons = pd.read_parquet(
        ROOT / "data/staging/operacao_reservatorio/operacao_reservatorio_dia.parquet"
    )
    ons["data"] = pd.to_datetime(ons["data"])
    ons["ano_mes"] = ons["data"].dt.to_period("M")

    monthly = (
        ons.groupby(["nom_reservatorio", "ano_mes"], observed=True)
        .agg(
            vol_util_pct=("vol_util_pct", "mean"),
            vazao_afluente_m3s=("val_vazaoafluente", "mean"),
            tr_dias=("tempo_residencia_dias", "median"),
        )
        .reset_index()
    )
    monthly["data"] = monthly["ano_mes"].dt.to_timestamp()
    valid_tr = monthly[monthly["tr_dias"].between(1, 1000)].copy()

    reservoir_rows = []
    for reservoir, sub in monthly.groupby("nom_reservatorio", observed=True):
        valid_pair = sub[
            sub["vol_util_pct"].between(0, 100)
            & sub["tr_dias"].between(1, 1000)
        ][["vol_util_pct", "tr_dias"]].dropna()
        crisis = sub[sub["data"].between("2014-01-01", "2015-12-31")]
        all_vol = sub["vol_util_pct"].dropna()
        all_flow = sub["vazao_afluente_m3s"].dropna()
        all_tr = sub.loc[sub["tr_dias"].between(1, 1000), "tr_dias"].dropna()
        daily_sub = ons[ons["nom_reservatorio"] == reservoir]
        daily_pair = daily_sub[
            daily_sub["vol_util_pct"].between(0, 100)
            & daily_sub["tempo_residencia_dias"].between(1, 1000)
        ][["vol_util_pct", "tempo_residencia_dias"]].dropna()
        min_idx = all_vol.idxmin() if not all_vol.empty else None
        reservoir_rows.append(
            {
                "reservatorio": reservoir,
                "meses": int(len(sub)),
                "volume_medio_pct": finite(all_vol.mean()),
                "volume_mediana_pct": finite(all_vol.median()),
                "volume_min_pct": finite(all_vol.min()),
                "volume_min_mes": finite(sub.loc[min_idx, "data"]) if min_idx is not None else None,
                "volume_primeiro_mes_valido": finite(
                    sub.loc[sub["vol_util_pct"].first_valid_index(), "data"]
                ) if sub["vol_util_pct"].first_valid_index() is not None else None,
                "volume_ultimo_mes_valido": finite(
                    sub.loc[sub["vol_util_pct"].last_valid_index(), "data"]
                ) if sub["vol_util_pct"].last_valid_index() is not None else None,
                "volume_meses_validos": int(all_vol.count()),
                "volume_crise_2014_2015_medio_pct": finite(crisis["vol_util_pct"].mean()),
                "vazao_media_m3s": finite(all_flow.mean()),
                "vazao_mediana_m3s": finite(all_flow.median()),
                "vazao_cv": finite(all_flow.std() / all_flow.mean()),
                "tr_mediana_dias": finite(all_tr.median()),
                "tr_p90_dias": finite(all_tr.quantile(0.90)),
                "tr_max_dias": finite(all_tr.max()),
                "correlacao_pearson_vol_tr": finite(valid_pair.corr().iloc[0, 1])
                if len(valid_pair) >= 2
                else None,
                "correlacao_pearson_diaria_vol_tr": finite(daily_pair.corr().iloc[0, 1])
                if len(daily_pair) >= 2
                else None,
            }
        )

    fire = pd.read_parquet(
        ROOT / "data/staging/queimadas/focos_calor_evento.parquet"
    )
    fire["data"] = pd.to_datetime(fire["data"])
    fire_annual = (
        fire.groupby("ano", observed=True).size().rename("n_focos").reset_index()
    )
    fire_biome = (
        fire.groupby("bioma", observed=True).size().rename("n_focos").reset_index()
    )
    fire_peak = fire_annual.loc[fire_annual["n_focos"].idxmax()]

    snis = pd.read_parquet(ROOT / "data/staging/snis/snis_municipios_serie.parquet")
    snis_annual = (
        snis.groupby("ano", observed=True)
        .agg(
            municipios=("municipio", "nunique"),
            in015_mediana=("in015", "median"),
            in046_mediana=("in046", "median"),
        )
        .reset_index()
    )
    snis_annual["gap_pp"] = snis_annual["in015_mediana"] - snis_annual["in046_mediana"]

    waste = pd.read_parquet(
        ROOT / "data/staging/residuos/residuos_municipio_ano.parquet"
    )
    waste_annual = (
        waste.groupby(["ano", "tiete"], observed=True)
        .agg(municipios=("municipio", "nunique"), iqr_mediana=("iqr", "median"))
        .reset_index()
    )

    out = {
        "ons": {
            "columns": list(ons.columns),
            "rows": int(len(ons)),
            "date_min": finite(ons["data"].min()),
            "date_max": finite(ons["data"].max()),
            "reservoir_count": int(ons["nom_reservatorio"].nunique()),
            "per_reservoir": reservoir_rows,
        },
        "fire": {
            "rows": int(len(fire)),
            "date_min": finite(fire["data"].min()),
            "date_max": finite(fire["data"].max()),
            "year_min": int(fire["ano"].min()),
            "year_max": int(fire["ano"].max()),
            "peak_year": int(fire_peak["ano"]),
            "peak_count": int(fire_peak["n_focos"]),
            "latitude_min": finite(pd.to_numeric(fire["latitude"], errors="coerce").min()),
            "latitude_max": finite(pd.to_numeric(fire["latitude"], errors="coerce").max()),
            "longitude_min": finite(pd.to_numeric(fire["longitude"], errors="coerce").min()),
            "longitude_max": finite(pd.to_numeric(fire["longitude"], errors="coerce").max()),
            "states": sorted(str(x) for x in fire["estado"].dropna().unique()),
            "municipality_count": int(fire["municipio"].nunique()),
            "annual": records(fire_annual),
            "by_biome": records(fire_biome.sort_values("n_focos", ascending=False)),
        },
        "snis": {
            "rows": int(len(snis)),
            "year_min": int(snis["ano"].min()),
            "year_max": int(snis["ano"].max()),
            "annual": records(snis_annual),
        },
        "waste": {
            "rows": int(len(waste)),
            "year_min": int(waste["ano"].min()),
            "year_max": int(waste["ano"].max()),
            "annual": records(waste_annual),
        },
    }
    output = Path(__file__).with_name("audit_results.json")
    output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
