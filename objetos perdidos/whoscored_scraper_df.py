import os
import json
import time
import numpy as np
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup

# =========================================================
# Utilidades numéricas (para evitar errores con dicts/listas)
# =========================================================

# Métricas que tienen sentido como MEDIA al colapsar minuto a minuto
AGG_MEAN_STATS = {
    "ratings", "possession", "aerialSuccess", "dribbleSuccess",
    "tackleSuccess", "throwInAccuracy", "passSuccess"
}

def _collapse_stat_value(val, how="sum"):
    # val puede ser dict {minuto: valor}, lista o ya un escalar
    if isinstance(val, dict):
        nums = [v for v in val.values() if isinstance(v, (int, float, np.integer, np.floating))]
    elif isinstance(val, (list, tuple)):
        nums = [v for v in val if isinstance(v, (int, float, np.integer, np.floating))]
    else:
        return val
    if not nums:
        return np.nan
    return float(np.mean(nums)) if how == "mean" else float(np.sum(nums))

def _to_numeric_safe(s):
    return pd.to_numeric(s, errors="coerce")

# =========================================================
# Extracción WhoScored (mantenemos tu flujo)
# =========================================================

def extract_json_from_whoscored(match_id):
    url = f'https://es.whoscored.com/Matches/{match_id}/Live'
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    scripts = soup.find_all("script")
    for script in scripts:
        if script.string and "matchCentreData" in script.string and 'require.config.params["args"]' in script.string:
            data_string = script.string.split('require.config.params["args"] = ')[1].split("};")[0] + "}"
            data_string = (data_string
                           .replace('matchId', '"matchId"')
                           .replace('matchCentreData', '"matchCentreData"')
                           .replace('formationIdNameMappings', '"formationIdNameMappings"')
                           .replace('matchCentreEventTypeJson', '"matchCentreEventTypeJson"'))
            return json.loads(data_string)

    raise ValueError("No se pudo extraer JSON del partido")

# =========================================================
# Procesado de eventos
# =========================================================

def process_events_json(data):
    events = data["matchCentreData"]["events"]
    df = pd.DataFrame(events)

    # Campos de texto legibles
    df['type'] = df['type'].astype(str).str.extract(r"'displayName': '([^']+)'")
    df['outcomeType'] = df['outcomeType'].astype(str).str.extract(r"'displayName': '([^']+)'")
    df['period'] = df['period'].astype(str).str.extract(r"'displayName': '([^']+)'")

    # Expandir qualifiers -> columnas q{ID}_{Nombre}
    qualifiers_expanded = []
    for _, row in df.iterrows():
        qdict = {}
        quals = row.get('qualifiers')
        if isinstance(quals, list):
            for q in quals:
                qid = q.get('qualifierId')
                qname = q.get('type', {}).get('displayName', f"qual_{qid}").replace(" ", "_")
                col = f"q{qid}_{qname}"
                qdict[col] = q.get('value', 1)  # 1 si no trae valor
        qualifiers_expanded.append(qdict)

    qdf = pd.DataFrame(qualifiers_expanded)
    df = pd.concat([df.drop(columns=['qualifiers'], errors='ignore'), qdf], axis=1)

    # Normalizar numéricos frecuentes
    for col in ["expandedMinute", "minute", "second", "x", "y", "endX", "endY"]:
        if col in df.columns:
            df[col] = _to_numeric_safe(df[col])

    return df

# =========================================================
# Procesado de jugadores (colapsa dicts/listas a números)
# =========================================================

def process_players_json(data):
    def expand_player_stats(player_list):
        raw = pd.DataFrame(player_list)
        out_rows = []
        for _, player in raw.iterrows():
            stats = player.get("stats", {})
            flat = {}
            for stat_name, stat_val in stats.items():
                base = stat_name.replace(" ", "_")
                how = "mean" if stat_name in AGG_MEAN_STATS else "sum"
                flat[f"s_{base}"] = _collapse_stat_value(stat_val, how=how)
            base_df = pd.DataFrame([player]).drop(columns=["stats"], errors="ignore")
            out_rows.append(pd.concat([base_df.reset_index(drop=True),
                                       pd.DataFrame([flat]).reset_index(drop=True)], axis=1))
        return pd.concat(out_rows, ignore_index=True)

    # 1) expandir por equipo
    home = expand_player_stats(data["matchCentreData"]["home"]["players"])
    home["teamId"] = data["matchCentreData"]["home"]["teamId"]

    away = expand_player_stats(data["matchCentreData"]["away"]["players"])
    away["teamId"] = data["matchCentreData"]["away"]["teamId"]

    # 2) combinar y trabajar SIEMPRE sobre 'df'
    df = pd.concat([home, away], ignore_index=True)

    # 3) forzar numérico en todo s_* y en los minutos de cambios
    for c in [c for c in df.columns if c.startswith("s_")] + ["subbedInExpandedMinute","subbedOutExpandedMinute"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # 4) eliminar % “crudos” (por si WhoScored los trae agregados raro)
    df = df.drop(columns=[
        "s_passSuccess", "s_dribbleSuccess", "s_tackleSuccess",
        "s_aerialSuccess", "s_throwInAccuracy"
    ], errors="ignore")

    # 5) recalcular SIEMPRE desde conteos (solo si existen)
    if {"s_passesAccurate","s_passesTotal"}.issubset(df.columns):
        df["s_passSuccess"] = (df["s_passesAccurate"] / df["s_passesTotal"].replace(0, np.nan)) * 100

    if {"s_dribblesWon","s_dribblesAttempted"}.issubset(df.columns):
        df["s_dribbleSuccess"] = (df["s_dribblesWon"] / df["s_dribblesAttempted"].replace(0, np.nan)) * 100

    if {"s_tackleSuccessful","s_tacklesTotal"}.issubset(df.columns):
        df["s_tackleSuccess"] = (df["s_tackleSuccessful"] / df["s_tacklesTotal"].replace(0, np.nan)) * 100

    if {"s_aerialsWon","s_aerialsTotal"}.issubset(df.columns):
        df["s_aerialSuccess"] = (df["s_aerialsWon"] / df["s_aerialsTotal"].replace(0, np.nan)) * 100

    if {"s_throwInsAccurate","s_throwInsTotal"}.issubset(df.columns):
        df["s_throwInAccuracy"] = (df["s_throwInsAccurate"] / df["s_throwInsTotal"].replace(0, np.nan)) * 100

    return df

# =========================================================
# Features de jugadores (per90 y ratios)
# =========================================================

def safe_div(n, d):
    n = pd.to_numeric(n, errors="coerce")
    d = pd.to_numeric(d, errors="coerce").replace(0, np.nan)
    return n / d

def infer_match_length(eventos_df, default_len=90):
    if "expandedMinute" in eventos_df.columns and eventos_df["expandedMinute"].notna().any():
        return int(np.nanmax(eventos_df["expandedMinute"]))
    if "minute" in eventos_df.columns and eventos_df["minute"].notna().any():
        return int(np.nanmax(eventos_df["minute"]))
    return default_len

def build_features_jugadores(lg_players_df, match_minutes=90):
    df = lg_players_df.copy()

    # Minutos jugados
    in_min  = df.get("subbedInExpandedMinute")
    out_min = df.get("subbedOutExpandedMinute")
    in_min  = _to_numeric_safe(in_min).fillna(0) if in_min is not None else pd.Series(0, index=df.index, dtype="float")
    out_min = _to_numeric_safe(out_min).fillna(match_minutes) if out_min is not None else pd.Series(match_minutes, index=df.index, dtype="float")
    minutes = (out_min - in_min).clip(lower=0, upper=match_minutes)

    if "isFirstEleven" in df.columns and "subbedInPeriod" in df.columns:
        never_played = (~df["isFirstEleven"].astype(bool)) & (df["subbedInPeriod"].isna())
        minutes = minutes.mask(never_played, 0)

    df["minutes"] = minutes

    # Conteos para per90
    per90_cols = [
        "s_touches","s_passesTotal","s_passesAccurate","s_passesKey",
        "s_shotsTotal","s_shotsOnTarget","s_dribblesAttempted","s_dribblesWon",
        "s_tacklesTotal","s_tackleSuccessful","s_tackleUnsuccesful",
        "s_interceptions","s_clearances","s_aerialsTotal","s_aerialsWon",
        "s_offsidesCaught","s_dispossessed","s_foulsCommited",
        "s_cornersTotal","s_cornersAccurate","s_throwInsTotal","s_throwInsAccurate",
        "s_totalSaves","s_parriedSafe","s_parriedDanger","s_errors"
    ]
    for c in per90_cols:
        if c in df.columns:
            df[c] = _to_numeric_safe(df[c])
            df[f"{c}_per90"] = safe_div(df[c], df["minutes"]) * 90.0

    # Ratios/porcentajes
    for num, den, out in [
        ("s_passesAccurate","s_passesTotal","pass_acc_pct"),
        ("s_dribblesWon","s_dribblesAttempted","dribble_succ_pct"),
        ("s_aerialsWon","s_aerialsTotal","aerial_win_pct"),
        ("s_tackleSuccessful","s_tacklesTotal","tackle_succ_pct"),
        ("s_cornersAccurate","s_cornersTotal","corner_acc_pct"),
        ("s_throwInsAccurate","s_throwInsTotal","throwin_acc_pct"),
    ]:
        if num in df.columns and den in df.columns:
            df[out] = safe_div(df[num], df[den]) * 100.0

    cols_per90 = [c for c in df.columns if c.endswith("_per90")]
    cols_pct = [
        "pass_acc_pct", "dribble_succ_pct", "aerial_win_pct",
        "tackle_succ_pct", "corner_acc_pct", "throwin_acc_pct"
    ]
    for c in cols_per90:
        if c in df.columns:
            df[c] = df[c].round(2)
    for c in cols_pct:
        if c in df.columns:
            df[c] = df[c].round(2)

    return df

# =========================================================
# Guardado de CSVs
# =========================================================

def _to_csv(df, path_base, name):
    # CSV estándar (para código)
    df.to_csv(os.path.join(path_base, f"{name}.csv"),
              index=False, encoding="utf-8-sig")
    # CSV para Excel (coma decimal, separador ;)
    df.to_csv(os.path.join(path_base, f"{name}_excel.csv"),
              index=False, encoding="utf-8-sig",
              sep=";", decimal=",", float_format="%.2f")

def guardar_csvs(eventos_df, jugadores_df, jornada, equipo1, equipo2, output_folder="data/partidos"):
    nombre_base = f"{jornada}J_{equipo1}_{equipo2}"
    os.makedirs(output_folder, exist_ok=True)

    # 1) largos
    _to_csv(eventos_df,   output_folder, f"{nombre_base}_lg_eventos")
    _to_csv(jugadores_df, output_folder, f"{nombre_base}_lg_jugadores")

    # 2) agregado eventos
    agr_eventos = eventos_df.groupby(["playerId","type"]).size().unstack(fill_value=0).reset_index()
    _to_csv(agr_eventos,  output_folder, f"{nombre_base}_agr_eventos")

    # 3) features jugadores
    match_len = infer_match_length(eventos_df)
    features = build_features_jugadores(jugadores_df, match_minutes=match_len)
    _to_csv(features,      output_folder, f"{nombre_base}_features_jugadores")

    print("✅ Guardados CSV estándar y *_excel.csv para cada uno")

# =========================================================
# Orquestador
# =========================================================

def extraer_datos_partido(match_id, jornada, equipo1, equipo2, output_folder="../data/partidos"):
    print(f"🔄 Procesando partido {jornada}J: {equipo1} vs {equipo2} (match_id={match_id})")
    data = extract_json_from_whoscored(match_id)
    eventos_df = process_events_json(data)
    jugadores_df = process_players_json(data)
    guardar_csvs(eventos_df, jugadores_df, jornada, equipo1, equipo2, output_folder)
