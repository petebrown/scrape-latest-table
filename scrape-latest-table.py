import requests
import pandas as pd
import datetime
from typing import Dict

def construct_11v11_url(competition, game_date):
    game_date = pd.to_datetime(game_date)
    day = game_date.day
    month = game_date.month_name().lower()
    year = game_date.year
    division = competition.lower().replace(" ", "-").replace("(", "").replace(")", "")

    if day < 10:
        day = f'0{day}'
    url = f"https://www.11v11.com/league-tables/{division}/{day}-{month}-{year}/"
    
    return url

def date_today():
    return datetime.datetime.now().strftime('%Y-%m-%d')

def request_json(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/90.0.4430.212 Safari/537.36'
    }
    r = requests.get(url, headers=headers)
    return r.json()

def get_fixtures(start_date, end_date=None):
    if not end_date:
        end_date = start_date
    fixtures = f'https://web-cdn.api.bbci.co.uk/wc-poll-data/container/sport-data-scores-fixtures?selectedEndDate={end_date}&selectedStartDate={start_date}&todayDate={date_today()}&urn=urn%3Abbc%3Asportsdata%3Afootball%3Ateam%3Atranmere-rovers&useSdApi=false'
    print(fixtures)
    return request_json(fixtures)['eventGroups']


def get_resource_id(fixture_info):
    return fixture_info['secondaryGroups'][0]['events'][0]['tipoTopicId']

def get_match_id(fixture_info):
    return fixture_info['secondaryGroups'][0]['events'][0]['id']

def get_table(match_id, date = date_today()):
    table = f'https://web-cdn.api.bbci.co.uk/wc-poll-data/container/football-table?globalContainerPolling=true&matchDate={date}&matchUrn=urn%3Abbc%3Asportsdata%3Afootball%3Aevent%3A{match_id}'
    return request_json(table)

def get_league_name(data: Dict) -> str:
    """ 
        Extract the league name.
    """
    return data['tournaments'][0]['name']

def get_league_df(div: Dict) -> pd.DataFrame:
    """ 
        Normalize the JSON participants data into a pandas DataFrame. 
    """
    return pd.json_normalize(div['participants'])

def process_league_table_df(df: pd.DataFrame, game_date: str, tab_url: str) -> pd.DataFrame:

    df['season'] = '2024/25'
    
    df['game_no'] = df[df.name=='Tranmere Rovers'].matchesPlayed.values[0]

    df['game_date'] = pd.to_datetime(game_date)

    df['url'] = tab_url

    df = df[['season', 'game_no', 'game_date', 'rank', 'name', 'matchesPlayed', 'wins', 'draws', 'losses', 'goalsScoredFor', 'goalsScoredAgainst', 'points', 'url']].rename(columns={
        'rank': 'pos',
        'name': 'Team',
        'matchesPlayed': 'Pld',
        'wins': 'W',
        'draws': 'D',
        'losses': 'L',
        'goalsScoredFor': 'GF',
        'goalsScoredAgainst': 'GA',
        'points': 'Pts'
    })

    return df

def get_league_table(game_date = date_today()):

    f = get_fixtures(game_date)

    match_id = get_match_id(f[0])

    t = get_table(match_id)

    league_name = get_league_name(t)

    tab_url = construct_11v11_url(league_name, game_date)

    df = get_league_df(t['tournaments'][0]['stages'][0]['rounds'][0])

    df = process_league_table_df(df, game_date=game_date, tab_url=tab_url)

    return df

tabs_df = pd.read_csv("./data/lge_tables.csv", parse_dates=["game_date"])
latest_tab = tabs_df.game_date.max()

results_df = pd.read_csv("https://raw.githubusercontent.com/petebrown/data-updater/main/data/results.csv", parse_dates=["game_date"])
lge_df = results_df[results_df.game_type == "League"][["season", "game_date", "ssn_comp_game_no", "competition"]].rename(columns = {"ssn_comp_game_no": "game_no"})

latest_game = lge_df.game_date.max()

if latest_game > latest_tab:
    print("New games found")
    
    new_games = lge_df[lge_df.game_date > latest_tab].copy()
    
    game_dates = new_games['game_date'].to_list()

    new_tables = []

    for game_date in game_dates:
        table = get_league_table(game_date)
        
        new_tables.append(table)
    
    new_tables = pd.concat(new_tables)

    tabs_df = pd.concat([tabs_df, new_tables]).sort_values(["game_date", "pos"], ascending = [0, 1]).reset_index(drop = True)

    tabs_df.to_csv("./data/lge_tables.csv", index = False)    
else:
    print("No new games found")
