# utils/visualizaciones.py
from mplsoccer import Pitch
import numpy as np
import pandas as pd

# Función llamada terreno de juego
def draw_opta_pitch(
    ax=None,
    pitch_color="#1A1730",   # fondo del campo (oscuro/morado)
    line_color="#00E5FF",    # líneas claras (cian suave)
    linewidth=0.9,
    corner_arcs=True,
):
    """
    Dibuja un campo tipo Opta en el eje dado y devuelve (pitch, ax).
    Pensado para eventos WhoScored (x,y en 0-100).
    """
    pitch = Pitch(
        pitch_type="opta",
        pitch_color=pitch_color,
        line_color=line_color,
        linewidth=linewidth,
        corner_arcs=corner_arcs,
    )
    if ax is None:
        fig, ax = pitch.draw()
        return pitch, ax
    pitch.draw(ax=ax)
    return pitch, ax

# --- Utilidades comunes para paneles ------------------------------------------
def tidy_axes(ax, with_frame=True, spine_color="#3A3F4B", lw=1):
    """Oculta ticks y controla la visibilidad/estilo del marco."""
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(with_frame)
        sp.set_color(spine_color)
        sp.set_linewidth(lw)

def draw_pitch_panel(
    ax, 
    title=None, 
    pitch_color="#1A1730", 
    line_color="#00E5FF", 
    linewidth=0.9, 
    title_color="#9AA0A6"
):
    """Dibuja el campo estilo Opta, añade un título opcional y limpia ejes."""
    draw_opta_pitch(ax=ax, pitch_color=pitch_color, line_color=line_color, linewidth=linewidth)
    if title:
        ax.set_title(title, fontsize=12, fontweight="bold", color=title_color, pad=6)
    tidy_axes(ax, with_frame=False)

# ---------------------------------------------------------------- #
# Función para red de pases
def plot_pass_network_for_player(
    ax,
    df_events,
    df_players=None,
    *,
    player_id=None,
    team_id=None,
    team_color="#00E5FF",
    show_all=True,                
    min_edge_count=1,
    emphasised_alpha=0.95,
    deemphasised_alpha=0.18,
    node_base=90,
    node_scale=260,
    draw_titles=False,
    highlight_label=None,
    highlight_text_color=None
):
    """
    Pinta la red de pases del equipo del jugador indicado, sobre un campo Opta (0-100).
    - Requiere que el pitch ya esté dibujado (usa tu draw_pitch_panel).
    - Etiquetas: nombre para el jugador destacado, dorsal para el resto (si disponible).
    - df_events: WhoScored lg_eventos del partido.
    - df_players: WhoScored lg_jugadores del mismo partido (opcional pero recomendado).
    """

    if df_events is None or len(df_events) == 0 or player_id is None:
        return  # nada que hacer

    # --- Helpers internos ------------------------------------------------------
    def _pick(df, opts):
        for c in opts:
            if c in df.columns:
                return c
        return None

    def _to_num(s):
        return pd.to_numeric(s, errors="coerce")

    def _short_name(n):
        if not isinstance(n, str): 
            return ""
        parts = n.strip().split()
        return parts[-1] if parts else n

    # --- Normalización de columnas de eventos ---------------------------------
    cols = {
        "type":   _pick(df_events, ["type","type_display_name"]),
        "outc":   _pick(df_events, ["outcomeType","outcome_type_display_name"]),
        "pid":    _pick(df_events, ["playerId","player_id"]),
        "tid":    _pick(df_events, ["teamId","team_id"]),
        "rel":    _pick(df_events, ["relatedPlayerId","related_player_id"]),
        "x":      _pick(df_events, ["x","startX","start_x"]),
        "y":      _pick(df_events, ["y","startY","start_y"]),
        "endX":   _pick(df_events, ["endX","end_x"]),
        "endY":   _pick(df_events, ["endY","end_y"]),
        "minute": _pick(df_events, ["expandedMinute","minute"]),
        "second": _pick(df_events, ["second"]),
    }

    d = pd.DataFrame({
        "type":   df_events[cols["type"]]   if cols["type"]   else np.nan,
        "outc":   df_events[cols["outc"]]   if cols["outc"]   else np.nan,
        "pid":    df_events[cols["pid"]]    if cols["pid"]    else np.nan,
        "tid":    df_events[cols["tid"]]    if cols["tid"]    else np.nan,
        "rel":    df_events[cols["rel"]]    if cols["rel"]    else np.nan,
        "x":      _to_num(df_events[cols["x"]])      if cols["x"]    else np.nan,
        "y":      _to_num(df_events[cols["y"]])      if cols["y"]    else np.nan,
        "endX":   _to_num(df_events[cols["endX"]])   if cols["endX"] else np.nan,
        "endY":   _to_num(df_events[cols["endY"]])   if cols["endY"] else np.nan,
        "minute": _to_num(df_events[cols["minute"]]) if cols["minute"] else 0,
        "second": _to_num(df_events[cols["second"]]) if cols["second"] else 0,
    }).copy()

    # IDs canónicos (enteros "limpios")
    d["pid"] = _to_num(d["pid"]).astype("Int64")
    d["rel"] = _to_num(d["rel"]).astype("Int64")
    d["tid"] = _to_num(d["tid"]).astype("Int64")

    try:
        pid = int(float(player_id))
    except Exception:
        return

    # --- Determinar team_id si no se pasa -------------------------------------
    if team_id is None:
        cand = d.loc[d["pid"] == pid, "tid"].dropna()
        if not cand.empty:
            team_id = int(cand.mode().iloc[0])
        elif df_players is not None and "teamId" in df_players.columns and "playerId" in df_players.columns:
            c2 = _to_num(df_players.loc[_to_num(df_players["playerId"]) == pid, "teamId"]).dropna()
            if not c2.empty:
                team_id = int(c2.iloc[0])
    if team_id is None:
        all_t = d["tid"].dropna()
        team_id = int(all_t.mode().iloc[0]) if not all_t.empty else None
    if team_id is None:
        return

    # --- Filtro: solo pases exitosos del equipo --------------------------------
    type_pass = d["type"].astype(str).str.lower().str.contains("pass", na=False)
    out_ok = d["outc"].astype(str).str.lower().isin(
        {"successful", "success", "succesful", "successfull"}  # tolerante a typos
    )
    passes = d[type_pass & out_ok & (d["tid"] == team_id)].copy()
    if passes.empty:
        return

    # --- Receptor: usar relatedPlayerId + pequeña heurística -------------------
    passes["receiver"] = passes["rel"]

    # tiempo en segundos para heurística
    passes["t"] = passes["minute"].fillna(0)*60 + passes["second"].fillna(0)

    same_team = d[d["tid"] == team_id].copy()
    same_team["t"] = same_team["minute"].fillna(0)*60 + same_team["second"].fillna(0)
    same_team = same_team.sort_values("t").reset_index(drop=True)

    tol_time = 10.0   # seg.
    tol_dist = 12.0   # unidades en escala 0-100

    miss_idx = passes[passes["receiver"].isna()].index
    for idx in miss_idx:
        row = passes.loc[idx]
        t0 = row["t"]; xe, ye = row["endX"], row["endY"]
        if pd.isna(xe) or pd.isna(ye):
            continue
        cand = same_team[(same_team["t"] > t0) & (same_team["t"] <= t0 + tol_time)]
        cand = cand[cand["pid"] != row["pid"]]
        if cand.empty:
            continue
        dd = np.hypot(cand["x"] - xe, cand["y"] - ye)
        good = dd[dd <= tol_dist]
        if not good.empty:
            pick = good.index[0]
            passes.at[idx, "receiver"] = same_team.loc[pick, "pid"]
        else:
            # fallback: primero de la ventana temporal
            passes.at[idx, "receiver"] = cand.iloc[0]["pid"]

    passes = passes.dropna(subset=["receiver"]).copy()
    passes["receiver"] = passes["receiver"].astype("Int64")

    # --- Aristas (pares no dirigidos) -----------------------------------------
    edges = passes.groupby(["pid","receiver"]).size().reset_index(name="count")
    edges["a"] = edges[["pid","receiver"]].min(axis=1)
    edges["b"] = edges[["pid","receiver"]].max(axis=1)
    edges_u = edges.groupby(["a","b"])["count"].sum().reset_index()
    edges_u = edges_u[edges_u["count"] >= min_edge_count]

    if not show_all:
        # conserva solo aristas que involucren al jugador objetivo
        edges_u = edges_u[(edges_u["a"] == pid) | (edges_u["b"] == pid)]

    # --- Posiciones medias: inicio pasador + fin receptor ----------------------
    pos_start = passes[["pid","x","y"]].rename(columns={"pid":"playerId","x":"px","y":"py"})
    pos_end   = passes[["receiver","endX","endY"]].rename(columns={"receiver":"playerId","endX":"px","endY":"py"})
    pos_all   = pd.concat([pos_start, pos_end], ignore_index=True).dropna(subset=["playerId","px","py"])

    avg_pos = pos_all.groupby("playerId").agg(x=("px","median"), y=("py","median")).reset_index()

    # Conteo de pases recibidos → tamaño del nodo
    recv = passes["receiver"].value_counts().rename_axis("playerId").reset_index(name="received")
    avg_pos = avg_pos.merge(recv, on="playerId", how="left").fillna({"received":0})

    # --- Info de jugadores: nombre, dorsal, titular ----------------------------
    name_map, shirt_map, starter_map = {}, {}, {}
    if df_players is not None and not df_players.empty:
        dfp = df_players.copy()
        dfp["playerId"] = _to_num(dfp["playerId"]).astype("Int64")
        if "name" in dfp.columns:
            name_map = dfp.set_index("playerId")["name"].to_dict()
        if "shirtNo" in dfp.columns:
            shirt_map = dfp.set_index("playerId")["shirtNo"].to_dict()
        if "isFirstEleven" in dfp.columns:
            starter_map = dfp.set_index("playerId")["isFirstEleven"].to_dict()

    # --- Dibujo ----------------------------------------------------------------    
    try:
        tidy_axes(ax, with_frame=False)
    except Exception:
        pass

    # color base (resto de la red, tenue)
    base_edge_color = (1, 1, 1, deemphasised_alpha)
    highlight_color = team_color or "#00E5FF"

    pos_map = avg_pos.set_index("playerId")[["x","y"]].to_dict("index")
    max_count = max(1, int(edges_u["count"].max())) if not edges_u.empty else 1

    # Aristas
    for _, e in edges_u.iterrows():
        a, b, c = int(e["a"]), int(e["b"]), int(e["count"])
        if a not in pos_map or b not in pos_map:
            continue
        xa, ya = pos_map[a]["x"], pos_map[a]["y"]
        xb, yb = pos_map[b]["x"], pos_map[b]["y"]
        lw = 1.0 + 7.0 * (c / max_count)
        involves = (a == pid) or (b == pid)
        col = highlight_color if involves else base_edge_color
        alp = emphasised_alpha if involves else deemphasised_alpha
        ax.plot([xa, xb], [ya, yb], linewidth=lw, color=col, alpha=alp,
                solid_capstyle="round", zorder=1, clip_on=True)

    # Nodos
    max_recv = max(1, int(avg_pos["received"].max())) if not avg_pos.empty else 1
    for _, r in avg_pos.iterrows():
        p = int(r["playerId"]); x, y = r["x"], r["y"]
        received = int(r["received"])

        # NUEVO: tamaño = base + escala * (recibidos/max)^0.8  (suaviza diferencias)
        frac = (received / max_recv) ** 0.8
        size = node_base + node_scale * frac

        is_starter = bool(starter_map.get(p, True))
        marker = "o" if is_starter else "s"
        edge_col = highlight_color if p == pid else (1,1,1,0.75)
        face_col = (0,0,0,0)  # hueco
        lw_node = 2.4 if p == pid else 1.6

        ax.scatter([x], [y], s=size, marker=marker,
                facecolors=face_col, edgecolors=edge_col,
                linewidths=lw_node, zorder=2, clip_on=True)  # <- clip_off

        # Etiquetas: nombre para el jugador destacado; dorsal para el resto
        if p == pid:
            # Si hay un nick explícito (nick_name), se usa, si no, el nombre que haya
            full = name_map.get(p, str(p))
            label = highlight_label if (highlight_label is not None) else (
                str(full).split()[0] if isinstance(full, str) else str(full)  # nombre de pila como fallback
            )
            # Color del texto del destacado: gris claro, si no el color de equipo
            tcol  = highlight_text_color if (highlight_text_color is not None) else highlight_color
            fz    = 14
        else:
            label = shirt_map.get(p, None)
            if label is None or (isinstance(label, float) and np.isnan(label)):
                label = _short_name(name_map.get(p, str(p)))
            tcol = (1,1,1,0.9)
            fz   = 10

        # Jugar con tamaño del nombre del jugador
        ax.text(x, y, str(label), ha="center", va="center",
                fontsize=fz, fontweight="bold", color=tcol, zorder=3, clip_on=False)  # <- clip_off

        if draw_titles:
            ax.set_title("Red de pases · equipo del jugador", fontsize=11, color=highlight_color)

# Ayuda para hacerlo genérico

# --- Lector flexible (auto ; o ,) ---------------------------------------------
def _auto_csv_vis(path):

    with open(path, "r", encoding="utf-8") as f:
        first = f.readline()
    sep = ";" if (";" in first and "," not in first) else ","
    df = pd.read_csv(path, sep=sep, encoding="utf-8")
    df.columns = [c.strip() for c in df.columns]
    return df

# --- Buscar el partido de un jugador y devolver (eventos, jugadores) ----------
def get_match_data_for_player(player_id, players_files, events_files):
    """
    Recorre la lista de *_lg_jugadores.csv y encuentra en cuál está player_id.
    Devuelve (df_eventos, df_jugadores) del partido correspondiente.
    """
    pid = int(float(player_id))

    # Aseguramos que listas tienen misma longitud
    if len(players_files) != len(events_files):
        raise ValueError("players_files y events_files deben tener la misma longitud y orden.")

    for p_path, e_path in zip(players_files, events_files):
        try:
            dfp = _auto_csv_vis(p_path)
        except Exception:
            continue
        if "playerId" not in dfp.columns:
            continue
        # normaliza a int
        pid_series = pd.to_numeric(dfp["playerId"], errors="coerce").astype("Int64")
        if int(pid) in set(pid_series.dropna().astype(int)):
            dfe = _auto_csv_vis(e_path)
            return dfe, dfp

    # Si no lo encuentra:
    return None, None

# --- Resolver color del equipo desde master_equipos ---------------------------
def resolve_team_color(team_id, master_teams_df=None, master_teams_path=None, default="#00E5FF"):
    """
    Devuelve el color (hex) del team_id buscando en master_equipos.
    Puedes pasar el DF ya cargado o la ruta al CSV.
    """
    if master_teams_df is None:
        if master_teams_path is None:
            return default
        try:
            mt = _auto_csv_vis(master_teams_path)
        except Exception:
            return default
    else:
        mt = master_teams_df

    # Detecta columnas candidatas
    def _pick(df, opts):
        for c in opts:
            if c in df.columns:
                return c
        return None

    col_id  = _pick(mt, ["teamId","id","team_id"])
    col_hex = _pick(mt, ["color_primario","primary_color","team_color_hex"])

    if col_id is None or col_hex is None:
        return default

    try:
        tid = int(float(team_id))
    except Exception:
        return default

    row = mt[pd.to_numeric(mt[col_id], errors="coerce").astype("Int64") == tid]
    if row.empty:
        return default
    val = str(row.iloc[0][col_hex]).strip()
    return val if val.startswith("#") and len(val) in (4,7) else default

# --- Versión comodín: todo automático con rutas -------------------------------
def plot_pass_network_for_player_auto(
    ax,
    player_id,
    players_files,
    events_files,
    master_teams_path=None,
    team_color=None,
    **kwargs
):
    """
    Helper para no preparar nada en el notebook.
    - Busca el partido del jugador en players_files/events_files.
    - Si no pasas team_color, lo intenta resolver desde master_teams_path.
    - Llama a plot_pass_network_for_player con lo encontrado.
    """
    dfe, dfp = get_match_data_for_player(player_id, players_files, events_files)
    if dfe is None or dfp is None:
        return

    # Si no pasan color: resolver por teamId del propio jugador
    if team_color is None:
        # teamId desde dfp
        try:
            pid = int(float(player_id))
            row = dfp[pd.to_numeric(dfp["playerId"], errors="coerce").astype("Int64") == pid]
            team_id = int(float(row.iloc[0]["teamId"])) if not row.empty else None
        except Exception:
            team_id = None
        team_color = resolve_team_color(team_id, master_teams_path=master_teams_path, default="#00E5FF")

    # Dibuja (usa el pitch ya dibujado por tu draw_pitch_panel)
    plot_pass_network_for_player(
        ax=ax,
        df_events=dfe,
        df_players=dfp,
        player_id=player_id,
        team_color=team_color,
        **kwargs
    )

# --------- Visualización de evento comun de la posición ---------

# === Paleta unificada para "Acción técnica por posición" ======================

EVENT_COLORS = {
    # tiros / gol
    "goal":        {"edge": "#1500FF"},   
    "shot_ot":     {"edge": "#58FD0C"},   
    "shot_off":    {"edge": "#FC050D"},   
    "shot_post":   {"edge": "#23F2B0"},   

    # pases
    "assist":      {"edge": "#E8F810"},   
    "key_pass":    {"edge": "#FD7D06"},
    "cross":       {"edge": "#196ACD"},   

    # acciones varias
    "dribble_ok":  {"edge": "#31FDF9"},   
    "dribble_ng":  {"edge": "#CD3C03E7"},   
    "recover":     {"edge": "#F34CD1"},   
}

# Función para dibujar la leyenda de extremos
def draw_winger_legend(
    ax,
    *,
    x=7, y0=25, dy=6, fz=10, L=10,
    sym_s=42, sym_lw=1.8, head=14,
    lw_goal=2.6, lw_ot=1.6, lw_off=1.6, lw_ast=2.2, lw_kp=1.6, lw_cross=1.2,
    use_glow=True  # ← NUEVO: para sincronizar con el panel
):
    col = lambda k: EVENT_COLORS[k]["edge"]

    x0, x1 = x, x + L
    xmid   = x0 + L/2
    tx     = x1 + 3
    y      = y0

    # --- helpers de glow ------------------------------------------------------
    def _glow_line(x0, y0, x1, y1, color, lw_core, lw_glow=6.0, alpha_glow=0.22, z=10):
        # cola suave
        ax.plot([x0, x1], [y0, y1],
                lw=lw_glow, alpha=alpha_glow, color=color,
                solid_capstyle="round", zorder=z)
        # núcleo
        ax.plot([x0, x1], [y0, y1],
                lw=lw_core, alpha=0.95, color=color,
                solid_capstyle="round", zorder=z+0.1)

    def _glow_arrow(x0, y0, x1, y1, color, lw_core, lw_glow=6.0, alpha_glow=0.22, z=10):
        # replica visual de glow_arrow() pero breve
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(arrowstyle="->", lw=lw_glow, color=color,
                            alpha=alpha_glow, mutation_scale=18,
                            joinstyle="round", capstyle="round",
                            shrinkA=0, shrinkB=0),
            zorder=z)
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(arrowstyle="->", lw=lw_core, color=color,
                            mutation_scale=14, joinstyle="round", capstyle="round",
                            shrinkA=0, shrinkB=0),
            zorder=z+0.1)

    # --- flecha “normal” (para tiros/gol) ------------------------------------
    def _flecha(label, key, lw, m=head):
        nonlocal y
        c = col(key)
        if use_glow:
            _glow_arrow(x0, y, x1, y, c, lw_core=lw, lw_glow=lw+4)
        else:
            ax.annotate("", xy=(x1, y), xytext=(x0, y),
                        arrowprops=dict(arrowstyle="->", lw=lw, color=c,
                                        mutation_scale=m),
                        zorder=11)
        ax.text(tx, y, label, va="center", ha="left", fontsize=fz)
        y += dy

    # --- “cometa” (cola + punto final) para asist/kp/centros ------------------
    def _flecha_comet(label, key, lw):
        nonlocal y
        c = col(key)
        if use_glow:
            _glow_line(x0, y, x1, y, c, lw_core=lw, lw_glow=lw+4)
        else:
            ax.plot([x0, x1], [y, y],
                    lw=lw, alpha=0.95, color=c, solid_capstyle="round", zorder=11)
        # “dot” de llegada (end_mark)
        ax.scatter([x1], [y], s=28, edgecolor=c, facecolor="#0C0D0E",
                   linewidths=1.0, zorder=12)
        ax.text(tx, y, label, va="center", ha="left", fontsize=fz)
        y += dy

    # --- TIROS / GOL ----------------------------------------------------------
    _flecha("Gol",           "goal",     lw_goal, m=head+2)
    _flecha("Tiro a puerta", "shot_ot",  lw_ot)
    _flecha("Tiro fuera",    "shot_off", lw_off)

    # --- PASES con estilo comet ----------------------------------------------
    _flecha_comet("Asistencia", "assist",   lw_ast)
    _flecha_comet("Pase clave", "key_pass", lw_kp)
    _flecha_comet("Centros",    "cross",    lw_cross)

    # --- REGATES --------------------------------------------------------------
    ax.scatter([xmid], [y], s=sym_s, facecolors="none",
               edgecolors=col("dribble_ok"), linewidths=sym_lw, zorder=12)
    ax.text(tx, y, "Regate ganado", va="center", ha="left", fontsize=fz); y += dy

    ax.text(xmid, y, "×", ha="center", va="center",
            fontsize=fz+1, color=col("dribble_ng"), zorder=12)
    ax.text(tx, y, "Regate perdido", va="center", ha="left", fontsize=fz); y += dy

    # --- RECUPERACIONES -------------------------------------------------------
    ax.scatter([xmid], [y], s=sym_s, marker="D", facecolors="none",
               edgecolors=col("recover"), linewidths=sym_lw, zorder=12)
    ax.text(tx, y, "Recuperaciones", va="center", ha="left", fontsize=fz)

# Función para mejorar tiros y goles
def glow_arrow(ax, xy0, xy1, color, lw_core=1.6, lw_glow=6.0, alpha_glow=0.18, z=3):
    """
    Dibuja una flecha con efecto glow: una capa gruesa semitransparente y otra nítida encima.
    """
    # capa glow
    ax.annotate("", xy=xy1, xytext=xy0,
        arrowprops=dict(arrowstyle="->", lw=lw_glow, color=color,
                        alpha=alpha_glow, mutation_scale=18,
                        joinstyle="round", capstyle="round",
                        shrinkA=0, shrinkB=0),
        zorder=z)
    # capa nítida
    ax.annotate("", xy=xy1, xytext=xy0,
        arrowprops=dict(arrowstyle="->", lw=lw_core, color=color,
                        mutation_scale=14, joinstyle="round", capstyle="round",
                        shrinkA=0, shrinkB=0),
        zorder=z+0.1)

# Función colocación de eventos en campo
def plot_winger_actions_for_player(
    ax,
    df_events,
    *,
    player_id,
    df_players=None,   # opcional para deducir teamId si hace falta
    show_legend=True,
    use_glow=True    
):
    """
    Pinta acciones clave (goles, tiros, asistencias/pases clave, centros, regates,
    recuperaciones) del JUGADOR en CAMPO RIVAL, con paleta unificada.
    Requiere campo Opta (0..100) ya dibujado.
    """
    if df_events is None or len(df_events) == 0:
        return

    # ---- helpers
    def to_num(s): return pd.to_numeric(s, errors="coerce")

    def norm_type(s):
        return (s.astype(str).str.lower()
                .str.replace(r"[\s_\-]+", "", regex=True))

    def truthy(col):
        if col not in df_events.columns: 
            return pd.Series([0]*len(df_events))
        x = df_events[col]
        if x.dtype == bool: 
            return x.astype(int)
        return to_num(x).fillna(0).astype(int)  # maneja "1.00", "0", "", etc.

    # ---- normaliza columnas básicas
    d = pd.DataFrame({
        "type":   norm_type(df_events.get("type", pd.Series(dtype=object))),
        "pid":    to_num(df_events.get("playerId", np.nan)).astype("Int64"),
        "tid":    to_num(df_events.get("teamId",  np.nan)).astype("Int64"),
        "x":      to_num(df_events.get("x",   np.nan)),
        "y":      to_num(df_events.get("y",   np.nan)),
        "ex":     to_num(df_events.get("endX",np.nan)),
        "ey":     to_num(df_events.get("endY",np.nan)),
        "outc":   df_events.get("outcomeType", "").astype(str).str.lower(),
        "isgoal": truthy("isGoal"),
    }).copy()

    # columnas de portería: Opta suele dar goalMouthY/Z (0..100)
    d["gmy"] = to_num(df_events.get("goalMouthY", df_events.get("qNone_GoalMouthY", np.nan)))
    d["gmz"] = to_num(df_events.get("goalMouthZ", df_events.get("qNone_GoalMouthZ", np.nan)))  # por si sirve para más adelante

    d["eid"] =   to_num(df_events.get("id", np.nan)).astype("Int64")

    for c in ("x","y","ex","ey"):
        d[c] = pd.to_numeric(d[c], errors="coerce")

    pid = int(float(player_id))

    # teamId (por si alguna vez hiciera falta usarlo)
    team_id = None
    cand = d.loc[d["pid"] == pid, "tid"].dropna()
    if not cand.empty:
        team_id = int(cand.mode().iloc[0])
    elif df_players is not None and "teamId" in df_players.columns:
        row = df_players[pd.to_numeric(df_players["playerId"], errors="coerce").astype("Int64") == pid]
        if not row.empty:
            team_id = int(float(row.iloc[0]["teamId"]))

    # ---- subset del jugador en campo rival
    me = d[(d["pid"] == pid) & (d["x"] > 50)].copy()  # campo rival

    # ---- filtros por tipo
    G_GOAL      = me[(me["type"] == "goal") & (me["isgoal"] > 0)]

    SH_OT_TYPES = {"savedshot", "attemptsaved", "goal", "shotonpost"}  # ← incluye post
    SH_OFF_TYPES = {"missedshots"}

    SH_OT  = me[me["type"].isin(SH_OT_TYPES)]
    SH_OFF = me[me["type"].isin(SH_OFF_TYPES)]

    # regates
    DRIBBLE_OK = me[(me["type"] == "takeon") & (me["outc"].str.startswith("succ"))]
    DRIBBLE_NG = me[(me["type"] == "takeon") & (~me["outc"].str.startswith("succ"))]

    # centros: TODOS los centros (da igual bloqueado/no)
    CROSS_ANY = me[(truthy("qNone_Cross") > 0)]

    # pases clave / asistencias
    KEY_PASS = me[(truthy("qNone_KeyPass") > 0) | (truthy("qNone_ShotAssist") > 0)]
    ASSIST   = me[(truthy("qNone_Assisted") > 0) | (truthy("qNone_IntentionalAssist") > 0)
                  | (truthy("qNone_IntentionalGoalAssist") > 0)]

    # recuperaciones defensivas en campo rival
    REC_TYPES = {"ballrecovery", "interception", "tackle"}
    RECOVER   = me[me["type"].isin(REC_TYPES) & (me["outc"].str.startswith("succ"))]

    # --- PRIORIDADES / DESOLAPES -----------------------------------------------
    # 1) GOL manda sobre cualquier TIRO
    if "eid" in d.columns:
        goal_ids = set(G_GOAL["eid"].dropna().astype(int))
        SH_OT  = SH_OT [~SH_OT ["eid"].isin(goal_ids)]
        SH_OFF = SH_OFF[~SH_OFF["eid"].isin(goal_ids)]
        # (Si en el feed existe un "shot" separado del "goal" conectado por relatedEventId,
        #  esto ya evita pintar doble. En la muestra, el gol viene como fila propia con endX/Y.)

    # 2) ASISTENCIA manda sobre PASE CLAVE y sobre CENTRO
    assist_ids = set(ASSIST.get("eid", pd.Series(dtype="Int64")).dropna().astype(int)) if "eid" in ASSIST.columns else set()
    KEY_PASS  = KEY_PASS [~KEY_PASS .get("eid", pd.Series(dtype="Int64")).isin(assist_ids)]
    CROSS_ANY = CROSS_ANY[~CROSS_ANY.get("eid", pd.Series(dtype="Int64")).isin(assist_ids)]

    # 3) PASE CLAVE manda sobre CENTRO (si coincidieran)
    kp_ids    = set(KEY_PASS.get("eid", pd.Series(dtype="Int64")).dropna().astype(int)) if "eid" in KEY_PASS.columns else set()
    CROSS_ANY = CROSS_ANY[~CROSS_ANY.get("eid", pd.Series(dtype="Int64")).isin(kp_ids)]

    # ---- DIBUJO --------------------------------------------------------------
    def draw_arrows(df, lw=1.0, ls="-", col="#E6EDF3"):
        for _, r in df.dropna(subset=["x","y","ex","ey"]).iterrows():
            ax.annotate("", xy=(float(r["ex"]), float(r["ey"])),
                        xytext=(float(r["x"]),  float(r["y"])),
                        arrowprops=dict(arrowstyle="->", lw=lw, linestyle=ls, color=col),
                        zorder=3)

    # --- NUEVO estilo con comet --------------------------------------
    from mplsoccer import Pitch
    _pitch = Pitch(pitch_type="opta")  # solo para usar .lines() y .scatter()

    def draw_pass_set(df, *, col_key, lw=1.2, comet=False, alpha=0.7, end_mark=False):
        if df is None or df.empty:
            return
        d2 = df.dropna(subset=["x","y","ex","ey"])
        if d2.empty:
            return
        col = EVENT_COLORS[col_key]["edge"]

        if comet:
            _pitch.lines(
                d2["x"], d2["y"], d2["ex"], d2["ey"],
                lw=lw, comet=True, color=col, alpha=alpha, ax=ax, zorder=3
            )
        else:
            for _, r in d2.iterrows():
                ax.annotate("", xy=(float(r["ex"]), float(r["ey"])),
                            xytext=(float(r["x"]), float(r["y"])),
                            arrowprops=dict(arrowstyle="->", lw=lw, color=col),
                            zorder=3)

        if end_mark:
            _pitch.scatter(
                d2["ex"], d2["ey"],
                s=28, edgecolor=col, linewidth=1.0,
                facecolor="#0C0D0E", zorder=4, ax=ax
            )

    # Llamadas específicas
    draw_pass_set(ASSIST,    col_key="assist",   lw=2.0, comet=True, alpha=0.55, end_mark=True)
    draw_pass_set(KEY_PASS,  col_key="key_pass", lw=1.5, comet=True, alpha=0.50, end_mark=True)
    draw_pass_set(CROSS_ANY, col_key="cross",    lw=1.3, comet=True, alpha=0.45, end_mark=True)


    # Tiros: flecha + marcador inicial distinto
    # ----------- tiros como flechas (con endpoint robusto) ------------------------
    def _endpoint_for_shot(r):
        """
        Devuelve (ex, ey) para dibujar la flecha de un tiro.
        Prioridad:
        1) endX/endY válidos (0..100)
        2) (100, goalMouthY) si existe goalMouthY
        3) proyección hasta x=100 usando el vector (x,y)->(ex,ey) o un
            vector genérico hacia portería si no hay ex/ey.
        """
        x, y = float(r["x"]), float(r["y"])
        ex, ey = r.get("ex"), r.get("ey")
        # a) endX/endY válidos
        if pd.notna(ex) and pd.notna(ey):
            exf, eyf = float(ex), float(ey)
            if 0.0 <= exf <= 100.0 and 0.0 <= eyf <= 100.0:
                return exf, eyf
        # b) goal mouth (a la derecha)
        if pd.notna(r.get("gmy")):
            return 100.0, float(r["gmy"])
        # c) proyección lineal hacia x=100 (si hay ey/endY parcial)
        if pd.notna(ex) and pd.notna(ey):
            # ya cubierto arriba, pero por si llega algo fuera de rango
            return min(100.0, max(0.0, float(ex))), min(100.0, max(0.0, float(ey)))
        # d) fallback: flecha recta hacia la portería manteniendo la misma y
        return 100.0, y

    def draw_shot_set(df, *, col_key, lw=1.2, start_marker=None, start_text=None, head=14):
        col = EVENT_COLORS[col_key]["edge"]
        for _, r in df.dropna(subset=["x","y"]).iterrows():
            x, y = float(r["x"]), float(r["y"])
            ex, ey = _endpoint_for_shot(r)
            
            # flecha del tiro
            if use_glow:
                glow_arrow(ax, (x, y), (ex, ey), col, lw_core=lw, lw_glow=6.0, alpha_glow=0.18, z=4)
            else:
                ax.annotate(
                    "", xy=(ex, ey), xytext=(x, y),
                    arrowprops=dict(
                        arrowstyle="->",
                        lw=lw,
                        color=col,
                        mutation_scale=head,
                        shrinkA=0, shrinkB=0,
                        joinstyle="round", capstyle="round"
                    ),
                    zorder=4
                )

            # marcador de inicio (si procede)
            if start_marker is not None:
                ax.scatter([x], [y], s=70, marker=start_marker,
                        facecolors="none", edgecolors=col, linewidths=1.1, zorder=5)
            if start_text is not None:
                ax.text(x, y, start_text, ha="center", va="center",
                        fontsize=11, color=col, zorder=5)

    # Tiros a puerta 
    draw_shot_set(SH_OT,  col_key="shot_ot",  lw=0.8, head=13, start_marker=None, start_text=None)
    # Tiros fuera 
    draw_shot_set(SH_OFF, col_key="shot_off", lw=0.8,  head=13, start_marker=None, start_text=None)

    # GOL: flecha más gruesa
    for _, r in G_GOAL.dropna(subset=["x","y"]).iterrows():
        x, y = float(r["x"]), float(r["y"])
        ex, ey = _endpoint_for_shot(r)
        if use_glow:
            glow_arrow(ax, (x, y), (ex, ey), EVENT_COLORS["goal"]["edge"],
                    lw_core=3.0, lw_glow=8.0, alpha_glow=0.22, z=6)
        else:
            ax.annotate(
                "", xy=(ex, ey), xytext=(x, y),
                arrowprops=dict(
                    arrowstyle="->",
                    lw=3.0,
                    color=EVENT_COLORS["goal"]["edge"],
                    mutation_scale=18,
                    shrinkA=0, shrinkB=0,
                    joinstyle="round", capstyle="round"
                ),
                zorder=6
            )

    # Regates
    ax.scatter(DRIBBLE_OK["x"], DRIBBLE_OK["y"], s=30, facecolors="none",
            edgecolors=EVENT_COLORS["dribble_ok"]["edge"], linewidths=1.2, zorder=4)
    for _, r in DRIBBLE_NG.dropna(subset=["x","y"]).iterrows():
        x, y = float(r["x"]), float(r["y"])
        dx = 1.0   # largo de cada trazo
        lw = 1.6   # más gruesa
        col = EVENT_COLORS["dribble_ng"]["edge"]
        ax.plot([x-dx, x+dx], [y-dx, y+dx], color=col, lw=lw, zorder=4)
        ax.plot([x-dx, x+dx], [y+dx, y-dx], color=col, lw=lw, zorder=4)

    # Recuperaciones (rombo pequeño)
    ax.scatter(RECOVER["x"], RECOVER["y"], s=25, marker="D", facecolors="none",
            edgecolors=EVENT_COLORS["recover"]["edge"], linewidths=1.8, zorder=4)

    # Leyenda
    if show_legend:
        draw_winger_legend(ax)

# Busca los jugadores, csv y demás
def plot_winger_actions_for_player_auto(
    ax,
    player_id,
    players_files,
    events_files,
    show_legend=True,
):
    """
    Wrapper automático:
    busca el partido en los CSV *_lg_jugadores y *_lg_eventos
    y llama a plot_winger_actions_for_player.
    """
    # este helper ya está definido en el flujo
    dfe, dfp = get_match_data_for_player(player_id, players_files, events_files)
    if dfe is None:
        return
    plot_winger_actions_for_player(
        ax, dfe,
        player_id=int(float(player_id)),
        df_players=dfp,
        show_legend=show_legend,
    )
