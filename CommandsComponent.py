import twitchio
from twitchio.ext import commands
import datetime
from datetime import datetime
import datetime
import re
import asyncio
from thefuzz import fuzz
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.live.nba.endpoints import scoreboard, boxscore
import json
import requests
from dateutil import parser

#CURRENT_YEAR = datetime.datetime.now().year
current_date = datetime.datetime.now()
CURRENT_YEAR = current_date.year

class CommandsComponent(commands.Component):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    async def hi(self, ctx: commands.Context) -> None:
        """Command that replys to the invoker with Hi <name>!

        !hi
        """
        await ctx.reply(f"Hi {ctx.chatter}!")

    @commands.command()
    async def nba(self, ctx: commands.Context) -> None:
        name = ctx.message.text.split("!nba")
        name_lower = name[1].lower()
        player_dict = players.find_players_by_full_name(name_lower.strip())
        if not player_dict:
            await ctx.reply("Player not found. Check spelling and type !nba <player_name>.")

        games = scoreboard.ScoreBoard().get_dict()["scoreboard"]["games"]

        for game in games:
            game_id = game["gameId"]
            box = boxscore.BoxScore(
                game_id=game_id).get_dict()["game"]
            for side in ("homeTeam", "awayTeam"):
                for player in box[side]["players"]:
                    if player["name"].lower() != name_lower:
                        continue
                    stats = player.get("statistics")
                    if not stats:
                        continue

                    pts = stats["points"]
                    reb = stats["reboundsTotal"]
                    ast = stats["assists"]
                    stl = stats["steals"]
                    blk = stats["blocks"]
                    tov = stats["turnovers"]
                    mins = int(stats["minutes"].split("PT")[1].split("M")[0])

                    fg_m = stats["fieldGoalsMade"]
                    fg_a = stats["fieldGoalsAttempted"]
                    tp_m = stats["threePointersMade"]
                    tp_a = stats["threePointersAttempted"]
                    ft_m = stats["freeThrowsMade"]
                    ft_a = stats["freeThrowsAttempted"]

                    await ctx.reply (
                        f"{player['name']}: {pts} PTS "
                        f"({fg_m}/{fg_a} FG, {tp_m}/{tp_a} 3PT, {ft_m}/{ft_a} FT), "
                        f"{reb} REB, {ast} AST, {stl} STL, {blk} BLK, {tov} TO "
                        f"in {mins} MIN"
                    )

        await ctx.send(f"No live stats found for {name_lower}")
    
    @commands.command()
    async def nfl(self, ctx: commands.Context):
        try:
            player_name = self.extract_player_name(ctx.message.text)
            player_data = self.get_player_data(player_name)

            if not player_data:
                await ctx.reply(f'@{ctx.author.name}, player not found. Check spelling.')
                return

            player_id = player_data['id']
            full_name = player_data['fullName']

            is_in_season = self.is_in_season()
            if is_in_season:
                game_stats_url, game_date_url = self.get_live_or_recent_game_urls(player_id)
            else:
                game_stats_url, game_date_url = self.get_last_played_game_urls(player_id)

            stats_data = self.get_json(game_stats_url)
            if not stats_data:
                await ctx.reply(f'error finding stats for {full_name}.')
                return

            position = self.get_player_position(player_id)
            if not position:
                await ctx.reply(f'error finding position for {full_name}.')
                return

            formatted_stats = self.format_stats(position, stats_data)

            game_date_data = self.get_json(game_date_url)
            if not game_date_data:
                await ctx.reply(f'error finding game date.')
                return

            game_date = datetime.strptime(game_date_data['date'].split('T')[0], '%Y-%m-%d').strftime('%m-%d-%Y')

            if game_date_data.get('liveAvailable', False):
                await ctx.reply(f"Live stats for {full_name}: {formatted_stats}")
            else:
                await ctx.reply(f"Last game on {game_date}: {formatted_stats}")

        except Exception as e:
            await ctx.reply(f'error occurred. Try again.')
            print(e)

    def extract_player_name(self, message):
        return " ".join(word.capitalize() for word in message.split("!nfl ")[1].split())

    def get_player_data(self, name):
        with open('nfl_ids.json') as f:
            players = json.load(f)
        return next((p for p in players if fuzz.ratio(p['fullName'].lower(), name.lower()) > 80), None)

    def is_in_season(self):
        today = datetime.today().strftime('%m-%d-%Y')
        return today <= f'{CURRENT_YEAR+1}-01-10'

    def get_live_or_recent_game_urls(self, player_id):
        current_date = datetime.today().strftime('%m-%d-%Y')

        eventlog_url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{CURRENT_YEAR}/athletes/{player_id}/eventlog"
        eventlog_data = self.get_json(eventlog_url)
        team_id = eventlog_data['events']['items'][0]['teamId']

        team_events_url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{CURRENT_YEAR}/teams/{team_id}/events"
        team_events = self.get_json(team_events_url)['items']

        last_game_url = team_events[-1]["$ref"]
        last_game_data = self.get_json(last_game_url)

        ##
        # Parse full datetime of the last game
        last_game_datetime = parser.parse(last_game_data["date"])
        now = datetime.now(last_game_datetime.tzinfo)

        # Only skip if the game is in the future
        if last_game_datetime > now:
            last_game_url = team_events[-2]["$ref"]

        match = re.search(r'/events/(\d+)', last_game_url)
        game_id = match.group(1)

        stats_url = f"http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{game_id}/competitions/{game_id}/competitors/{team_id}/roster/{player_id}/statistics/0?lang=en&region=us"
        date_url = f"http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{game_id}/competitions/{game_id}?lang=en&region=us"
        return stats_url, date_url

    def get_last_played_game_urls(self, player_id):
        eventlog_url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{CURRENT_YEAR}/athletes/{player_id}/eventlog"
        events = self.get_json(eventlog_url)['events']['items']
        for event in reversed(events):
            if event['played']:
                return event['statistics']['$ref'], event['competition']['$ref']
        return None, None

    def get_player_position(self, player_id):
        url = f"http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{CURRENT_YEAR}/athletes/{player_id}?lang=en&region=us"
        data = self.get_json(url)
        return data.get('position', {}).get('abbreviation')

    def format_stats(self, position, stats_data):
        with open('stats_abbreviations.json') as f:
            abbrev_data = json.load(f)

        output_sections = []

        for category in abbrev_data['categories']:
            if position not in category['positions']:
                continue

            cat_name = category['name']
            expected_stats = category['stats']

            # Find corresponding category in the actual game data
            stat_category = next(
                (c for c in stats_data['splits']['categories'] if c['name'].lower() == cat_name.lower()),
                None
            )

            if not stat_category:
                continue

            collected_stats = []
            for stat in stat_category['stats']:
                if stat['abbreviation'] in expected_stats:
                    collected_stats.append(f"{stat['abbreviation']} {stat['value']}")

            if collected_stats:
                section_title = self.get_section_label(cat_name)
                output_sections.append(f"{section_title}: ({', '.join(collected_stats)})")

        return " | ".join(output_sections)

    def get_section_label(self, cat_name):
        labels = {
            "passing": "Pass",
            "rushing": "Rush",
            "receiving": "Rec",
            "fumbles": "Fum",
            "defensive": "Def",
            "interceptions": "INT",
            "defensiveInterceptions": "INT",
            "kicking": "Kick",
            "punting": "Punt",
            "general": "Gen"
        }
        return labels.get(cat_name.lower(), cat_name.capitalize())


    def get_json(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None

    @commands.command()
    async def updatenflids(self, ctx: commands.Context):
        try:
            url = "https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=20000&active=true"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if not items:
                await ctx.reply(f"no players found in response.")
                return

            json_list = [
                {
                    "id": player["id"],
                    "fullName": player["fullName"]
                }
                for player in items
                if player.get("active")
            ]

            with open("nfl_ids.json", "w") as f:
                json.dump(json_list, f, indent=2)

            await ctx.reply(f"NFL player IDs updated: {len(json_list)} players saved.")

        except requests.RequestException as e:
            await ctx.reply(f"error updating NFL player IDs (network issue).")
            print("Request error:", e)

        except Exception as e:
            await ctx.reply(f"unexpected error occurred while updating NFL player IDs.")
            print("Unexpected error:", e)
