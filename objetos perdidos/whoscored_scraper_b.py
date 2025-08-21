import os
import json
import time
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup

def extract_json_from_whoscored(match_id):
    url = f'https://es.whoscored.com/Matches/{match_id}/Live'
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    scripts = soup.find_all("script")

    for script in scripts:
        if script.string and "matchCentreData" in script.string:
            data_string = script.string.split('require.config.params["args"] = ')[1].split("};")[0] + "}"
            data_string = data_string.replace('matchId', '"matchId"')
            data_string = data_string.replace('matchCentreData', '"matchCentreData"')
            data_string = data_string.replace('formationIdNameMappings', '"formationIdNameMappings"')
            data_string = data_string.replace('matchCentreEventTypeJson', '"matchCentreEventTypeJson"')
            return json.loads(data_string)

    raise ValueError("No se pudo extraer JSON del partido")

def process_events_json(data):
    events = data["matchCentreData"]["events"]
    df = pd.DataFrame(events)
    df['type'] = df['type'].astype(str).str.extract(r"'displayName': '([^']+)'")
    df['outcomeType'] = df['outcomeType'].astype(str).str.extract(r"'displayName': '([^']+)'")
    df['period'] = df['period'].astype(str).str.extract(r"'displayName': '([^']+)'")
    return df

def process_players_json(data):
    players_home = pd.DataFrame(data["matchCentreData"]["home"]["players"])
    players_home["teamId"] = data["matchCentreData"]["home"]["teamId"]
    players_away = pd.DataFrame(data["matchCentreData"]["away"]["players"])
    players_away["teamId"] = data["matchCentreData"]["away"]["teamId"]
    return pd.concat([players_home, players_away], ignore_index=True)

def guardar_csvs(eventos_df, jugadores_df, jornada, equipo1, equipo2, output_folder="data/partidos"):
    nombre_base = f"{jornada}J_{equipo1}_{equipo2}"
    os.makedirs(output_folder, exist_ok=True)
    eventos_df.to_csv(os.path.join(output_folder, f"{nombre_base}_eventos.csv"), index=False, encoding='utf-8-sig')
    jugadores_df.to_csv(os.path.join(output_folder, f"{nombre_base}_jugadores.csv"), index=False, encoding='utf-8-sig')
    print(f"✅ Guardado: {nombre_base}_eventos.csv")
    print(f"✅ Guardado: {nombre_base}_jugadores.csv")

def extraer_datos_partido(match_id, jornada, equipo1, equipo2, output_folder="../data/partidos"):
    print(f"🔄 Procesando partido {jornada}J: {equipo1} vs {equipo2} (match_id={match_id})")
    data = extract_json_from_whoscored(match_id)
    eventos_df = process_events_json(data)
    jugadores_df = process_players_json(data)
    guardar_csvs(eventos_df, jugadores_df, jornada, equipo1, equipo2, output_folder)
