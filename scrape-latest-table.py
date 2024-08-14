import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO

def construct_url(competition, game_date):
    game_date = pd.to_datetime(game_date)
    day = game_date.day
    month = game_date.month_name().lower()
    year = game_date.year
    division = competition.lower().replace(" ", "-").replace("(", "").replace(")", "")

    if day < 10:
        day = f'0{day}'
    url = f"https://www.11v11.com/league-tables/{division}/{day}-{month}-{year}/"
    
    return url

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
}

tabs_df = pd.read_csv("./data/lge_tables.csv", parse_dates=["game_date"])
latest_tab = tabs_df.game_date.max()

results_df = pd.read_csv("https://raw.githubusercontent.com/petebrown/data-updater/main/data/results.csv", parse_dates=["game_date"])
lge_df = results_df[results_df.game_type == "League"][["season", "game_date", "ssn_comp_game_no", "competition"]].rename(columns = {"ssn_comp_game_no": "game_no"})

latest_game = lge_df.game_date.max()

if latest_game > latest_tab:
    print("New games found")
    
    new_games = lge_df[lge_df.game_date > latest_tab].copy()
    
    new_games['url'] = new_games.apply(lambda x: construct_url(x.competition, x.game_date), axis = 1)

    urls = new_games['url'].to_list()

    new_tables = []

    for url in urls:
        # r = requests.get(url, headers = headers)
        # doc = BeautifulSoup(r.text, 'html.parser')
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        page_source = driver.page_source
        doc = BeautifulSoup(page_source, 'html.parser')

        table = pd.read_html(StringIO(str(doc)))[0]

        table["pos"] = table.index + 1
        table["url"] = url
        
        table = table[['pos', 'Team', 'Pld', 'W', 'D', 'L', 'GF', 'GA', 'Pts', 'url']]
        
        new_tables.append(table)
    
    new_tables = pd.concat(new_tables)
    new_tables = new_tables.merge(new_games, on = "url", how = "left")
    new_tables = new_tables[["season", "game_no", "game_date", "pos", "Team", "Pld", "W", "D", "L", "GF", "GA", "Pts", "url"]]

    tabs_df = pd.concat([tabs_df, new_tables]).sort_values(["game_date", "pos"], ascending = [0, 1]).reset_index(drop = True)

    tabs_df.to_csv("./data/lge_tables.csv", index = False)    
else:
    print("No new games found")
