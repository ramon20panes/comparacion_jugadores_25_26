# utils/fbref_lanus.py
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import pandas as pd
import LanusStats as ls

# -------------------------
# CONFIG
# -------------------------
COLS_ELEGIDAS = [
    'Player','stats_Nation','stats_Pos','stats_Squad','stats_Comp','stats_Age','stats_Born',
    'stats_MP','stats_Starts','stats_Min','stats_90s','playingtime_Min%','playingtime_+/-90',
    'stats_Gls','stats_G-PK','stats_Ast','stats_G+A','stats_xG','passing_xA','stats_xAG',
    'stats_npxG','stats_npxG+xAG','gca_SCA','gca_GCA','shooting_Sh','shooting_SoT',
    'shooting_SoT%','shooting_Sh/90','shooting_G/Sh','shooting_Dist','passing_Cmp%',
    'passing_TotDist','passing_PrgDist','passing_KP','passing_1/3','passing_PPA',
    'passing_types_TB','passing_types_Crs','passing_CrsPA','gca_SCA90','gca_GCA90',
    'stats_PrgC','stats_PrgP','stats_PrgR','possession_Touches','possession_Att',
    'possession_Succ%','possession_Succ','possession_TotDist','possession_PrgDist',
    'possession_Mis','possession_Dis','possession_Rec','possession_Mid 3rd',
    'possession_Att 3rd','possession_Att Pen','defense_Tkl','defense_Int',
    'defense_Tkl+Int','defense_Clr','defense_Err','defense_Blocks','defense_Mid 3rd',
    'defense_Att 3rd','misc_TklW','misc_Recov','misc_Won%','misc_CrdY','misc_CrdR',
    'misc_Fls','misc_Fld','misc_Off'
]

RENOMBRES = {
   'Player':'Jugador','stats_Nation':'Nacionalidad','stats_Pos':'Posicion','stats_Squad':'Equipo',
   'stats_Comp':'Competicion','stats_Age':'Edad','stats_Born':'Nacimiento','stats_MP':'Part_Jug',
   'stats_Starts':'Tit.','stats_Min':'Min','stats_90s':'Media_minXpart','playingtime_Min%':'%_min_respecto_equipo',
   'playingtime_+/-90':'Minutos_por_90','stats_Gls':'Gls','stats_G-PK':'Gls_sin_penal','stats_Ast':'Asis',
   'stats_G+A':'Gls+Asis','stats_xG':'xG','passing_xA':'xA','stats_xAG':'xAG','stats_npxG':'npxG',
   'stats_npxG+xAG':'npxG+xAG','gca_SCA':'Acc_tiro','gca_GCA':'Acc_gol','shooting_Sh':'Tiros',
   'shooting_SoT':'Tiros_puerta','shooting_SoT%':'Tiros_%_puerta','shooting_Sh/90':'Tiros_x_90',
   'shooting_G/Sh':'Goles_x_tiro','shooting_Dist':'Tiro_%_distancia','passing_Cmp%':'Pases_%_compl',
   'passing_TotDist':'Pases_dist_total','passing_PrgDist':'Pases_dist_Progr','passing_KP':'Pases_clave',
   'passing_1/3':'Pases_ult_tercio','passing_PPA':'Pases_area_penal','passing_types_TB':'Pases_espalda_df',
   'passing_types_Crs':'Pases_centros','passing_CrsPA':'Pases_centros_Area','gca_SCA90':'Acc_Tiro_90',
   'gca_GCA90':'Acc_Gol_90','stats_PrgC':'Conduc_Progresivas','stats_PrgP':'Pases_Progresivos',
   'stats_PrgR':'Recepciones_Progresivas','possession_Touches':'Pos_toques','possession_Att':'Pos_intento_regate',
   'possession_Succ%':'Pos_%_regate','possession_Succ':'Pos_regates_exit','possession_TotDist':'Pos_dist_tot_conduccion',
   'possession_PrgDist':'Pos_dist_progresiva_conduccion','possession_Mis':'Pos_ctrls_errados',
   'possession_Dis':'Pos_desposesion','possession_Rec':'Pos_recepcion','possession_Mid 3rd':'Pos_toques_primer_tercio',
   'possession_Att 3rd':'Pos_toques_ultimo_tercio','possession_Att Pen':'Pos_toques_area_rival',
   'defense_Tkl':'Df_entradas','defense_Int':'Df_intercepciones','defense_Tkl+Int':'Df_ent+inter',
   'defense_Clr':'Df_despejes','defense_Err':'Df_errores_tiro_rival','defense_Blocks':'Df_bloqueos',
   'defense_Mid 3rd':'Df_tackles_campo_propio','defense_Att 3rd':'Df_tackles_campo_rival',
   'misc_TklW':'Df_tackles_gan','misc_Recov':'Df_recup','misc_Won%':'Df_duelos_aereos_%',
   'misc_CrdY':'Amarillas','misc_CrdR':'Rojas','misc_Fls':'Faltas_Cometidas','misc_Fld':'Faltas_Recibidas',
   'misc_Off':'Fueras_Juego'
}

REEMPLAZOS_EQUIPOS = {
    'Atlético Madrid':'Atleti','Manchester City':'City','Newcastle Utd':'Newcastle','Paris S-G':'PSG',
    'Alavés':'Alaves','Bayern Munich':'Bayern',"Nott'ham Forest":'Forest','Saint-Étienne':'Saint-Etienne',
    'Rayo Vallecano':'Rayo'
}

CATEGORICAS = ['Jugador','Nacionalidad','Posicion','Equipo','Competicion']

# -------------------------
# ETL helpers
# -------------------------
def limpieza_inicial(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=['Player','stats_Nation','stats_Squad']).reset_index(drop=True)
    return df.fillna(0)

def transformar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['stats_Pos'] = df['stats_Pos'].astype(str).str.split(',').str[0].str[:2]
    df['stats_Nation'] = df['stats_Nation'].astype(str).str[-3:]
    df['stats_Comp'] = df['stats_Comp'].astype(str).str.split().str[1:].str.join(' ')
    df['stats_Age'] = df['stats_Age'].astype(str).str[:2]
    return df

def corregir_equipos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['stats_Squad'] = df['stats_Squad'].replace(REEMPLAZOS_EQUIPOS)
    return df

def seleccionar_y_renombrar(df: pd.DataFrame) -> pd.DataFrame:
    df = df[COLS_ELEGIDAS].copy()
    df = df.rename(columns=RENOMBRES)
    return df

def correcciones_puntuales(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Nacionalidades
    df.loc[df['Jugador']=='Atakan Karazor','Nacionalidad']='TUR'
    df.loc[df['Jugador']=='Plamedi Nsingi','Nacionalidad']='FRA'
    df.loc[df['Jugador']=='Fer López','Nacionalidad']='ESP'
    # Nacimiento
    df.loc[df['Jugador']=='Hannes Behrens','Nacimiento']='2005'
    df.loc[df['Jugador']=='Max Moerstedt','Nacimiento']='2006'
    df.loc[df['Jugador']=='Fer López','Nacimiento']='2004'
    df.loc[df['Jugador']=='Pape Daouda Diongue','Nacimiento']='2006'
    # Edad
    df.loc[df['Jugador']=='Hannes Behrens','Edad']='19'
    df.loc[df['Jugador']=='Max Moerstedt','Edad']='18'
    df.loc[df['Jugador']=='Fer López','Edad']='20'
    df.loc[df['Jugador']=='Pape Daouda Diongue','Edad']='18'
    return df

def tipificar_numericos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.loc[:, ~df.columns.duplicated()].copy()
    for col in df.columns:
        if col not in CATEGORICAS and col != 'Min':
            df[col] = pd.to_numeric(df[col], errors='coerce')
    # Min a float (quita comas si aparecen)
    df['Min'] = pd.to_numeric(df['Min'].astype(str).str.replace(',',''), errors='coerce')
    return df

# -------------------------
# Scrape
# -------------------------
def get_big5_latest_df(save_csv: bool = True, outdir: Path | None = None) -> pd.DataFrame:
    liga = 'Big 5 European Leagues'
    temporada = sorted(list(ls.get_available_season_for_leagues('Fbref', liga)['seasons']))[-1]
    fbref = ls.Fbref()
    df_big5 = fbref.get_all_player_season_stats(liga, temporada, save_csv=False)[0]
    df_big5['liga'] = liga
    df_big5['temporada'] = temporada

    # ETL
    df_big5 = (df_big5.pipe(limpieza_inicial)
                      .pipe(transformar_columnas)
                      .pipe(corregir_equipos)
                      .pipe(seleccionar_y_renombrar)
                      .pipe(correcciones_puntuales)
                      .pipe(tipificar_numericos))

    if save_csv:
        if outdir is None:
            outdir = Path.cwd().parent / "data" / "big5_fbref"
        outdir.mkdir(parents=True, exist_ok=True)
        outfile = outdir / "big5_24_25.csv"
        df_big5.to_csv(outfile, index=False, encoding="utf-8-sig")
        print(f"✅ Guardado: {outfile}")

    return df_big5

def extraer_y_guardar_big5(save_csv: bool = True, outdir: Path | None = None) -> pd.DataFrame:
    return get_big5_latest_df(save_csv=save_csv, outdir=outdir)
