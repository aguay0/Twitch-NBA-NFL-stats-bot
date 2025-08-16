import twitchio
from twitchio.ext import commands
from datetime import datetime
import re
from thefuzz import fuzz
from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.live.nba.endpoints.boxscore import BoxScore

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
        player_name = ctx.message.text.split("!nba ")
        player_name_final = player_name[1]
        try:
            player_name_final = players.find_players_by_full_name(player_name_final)[0]['full_name']
            player_id = players.find_players_by_full_name(player_name_final)[0]['id']
            games = leaguegamefinder.LeagueGameFinder(season_nullable='2024-25',league_id_nullable='00', player_id_nullable=player_id)
            games = games.get_data_frames()[0]
            latest_game_id = games.to_dict()['GAME_ID']
            boxscore = BoxScore(game_id=str(latest_game_id[0]))
            boxscore2 = boxscore.get_dict()
            boxscoreboth = boxscore.away_team_player_stats.get_dict(
            ) + boxscore.home_team_player_stats.get_dict()
            for personId in boxscoreboth:
                try:
                    if personId['personId'] == int(player_id):
                        stats = boxscore.away_team_player_stats.get_dict()[
                            boxscore.away_team_player_stats.get_dict().index(personId)]
                        break
                    else:
                        continue
                except:
                    if personId['personId'] == int(player_id):
                        stats = boxscore.home_team_player_stats.get_dict()[
                            boxscore.home_team_player_stats.get_dict().index(personId)]
                        break
                    else:
                        continue
            FGA = (stats['statistics']['fieldGoalsAttempted'])
            FGM = (stats['statistics']['fieldGoalsMade'])
            MIN = (stats['statistics']['minutes']).replace("PT", "")
            THREEPA = (stats['statistics']['threePointersAttempted'])
            THREEPM = (stats['statistics']['threePointersMade'])
            MIN = MIN.replace("M", "")
            MIN = MIN[:2]
            FTA = (stats['statistics']['freeThrowsAttempted'])
            FTM = (stats['statistics']['freeThrowsMade'])
            stats_list = [
                "%s" % MIN, 'MIN,', stats['statistics']['points'], 'PTS,',
                stats['statistics']['reboundsTotal'], 'REB,',
                stats['statistics']['assists'], 'AST,', stats['statistics']['steals'],
                'STL,', stats['statistics']['blocks'], 'BLK,',
                stats['statistics']['turnovers'], 'TO,',
                stats['statistics']['foulsPersonal'], 'FLS,',
                "%s/%s" % (FTM, FTA), 'FT,',
                "(%s/%s" % (THREEPM, THREEPA), '3P,',
                round(stats['statistics']['threePointersPercentage'] * 100,
                    1), '3P%),',
                "(%s/%s" % (FGM, FGA), 'FG,',
                round(stats['statistics']['fieldGoalsPercentage'] * 100, 1), 'FG%)'
            ]
            message = " ".join(str(x) for x in stats_list)
            name = player_name_final.split(" ", 1)
            for i in range(len(name)):
                name[i] = name[i].capitalize()
            name_final = " ".join(str(x) for x in name)
            game_date = games.to_dict()['GAME_DATE']
            game_date = game_date[0]
            game_date_final = datetime.strptime(game_date, '%Y-%m-%d').strftime('%m-%d-%Y')
            if boxscore2['game']['gameStatus'] == 3:
                await ctx.send(
                f"@{ctx.author.name}, No live stats found for {name_final}. Last played game {game_date_final}: {message}"
            )
            elif boxscore2['game']['gameStatus'] == 2:
                await ctx.send(
          f"@{ctx.author.name}, Live stats for {name_final}: {message}"
            )
            else:
                await ctx.send(
            f"@{ctx.author.name}, Error finding live or last nba game stats for {name_final}. It might be because a game is close to starting, try again in a bit."
            )
        except:
            await ctx.send(f'@{ctx.author.name}, Player not found. Check spelling or type: "!nba <player full name>"')