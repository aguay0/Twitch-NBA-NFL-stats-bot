from twitchio.ext import commands
from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.live.nba.endpoints.boxscore import BoxScore
import requests
import json
from datetime import datetime
import re
from thefuzz import fuzz
from dotenv import load_dotenv
import os



class Bot(commands.Bot):

  def __init__(self):
    load_dotenv()
    super().__init__(token=os.getenv("TOKEN"),
                     prefix='!',
                     initial_channels=['aifredo'],
                     nick='Albotzo',
                     user_id=os.getenv("USER_ID"))
    self.editors = ['aifredo']

  async def event_ready(self):
    print(f'{self.nick} online')
    #print(f'User id is | {self.user_id}')

  async def event_message(self, message):
    if message.echo:
      return
    await self.handle_commands(message)

  @commands.command()
  async def stats(self, ctx: commands.Context):
    await ctx.send(f'@{ctx.author.name}, The commands for stats are: !nba, !nfl')

  @commands.command()
  async def nba(self, ctx: commands.Context):
    player_name = ctx.message.content.split("!nba ")
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

  @commands.command()
  async def nfl(self, ctx: commands.Context):
    player_name = ctx.message.content.split("!nfl ")
    player_name_final = player_name[1]
    name = player_name_final.split(" ", 1)
    for i in range(len(name)):
      name[i] = name[i].capitalize()
    name_final = " ".join(str(x) for x in name)
    try:
      with open('nfl_ids.json') as f:
        data = json.load(f)
      for i in range(len(data)):
        if (fuzz.ratio(data[i]['fullName'].lower(), name_final.lower()) > 85):
          player_id = data[i]['id']
          name_final = data[i]['fullName']
          break
        else:
          continue
      current_year = 2024
      current_date = datetime.today().strftime('%Y-%m-%d')
      if current_date <= f'{current_year+1}-1-10':
        url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{current_year}/athletes/{player_id}/eventlog"
        response = requests.get(url)
        if response.status_code == 200:
          dataalt = response.json()
        else:
          await ctx.send(f'@{ctx.author.name}, Player was not found. Check spelling or type: "!nfl <player full name>"')
        team_id = dataalt['events']['items'][0]['teamId']
        
        urlteam = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{current_year}/teams/{team_id}/events"
        
        responseteam = requests.get(urlteam)
        if responseteam.status_code == 200:
          datateam = responseteam.json()
        else:
          await ctx.send(f'@{ctx.author.name}, Team games were not found. Check spelling or type: "!nfl <player full name>"')
        
        last_item = datateam["items"][len(datateam["items"])-1]["$ref"]
        urlteam2 = last_item
        responseteam2 = requests.get(urlteam2)
        if responseteam2.status_code == 200:
          datateam2 = responseteam2.json()
        else:
          await ctx.send(f'@{ctx.author.name}, Team games were not found. Check spelling or type: "!nfl <player full name>"')
        if datateam2["date"].split('T')[0] >= current_date:
          last_item = datateam["items"][len(datateam["items"])-2]["$ref"]
          urlteam2 = last_item
        pattern = r'/events/(\d+)'
        match = re.search(pattern, last_item)
        matchgameid = match.group(1)
            
        url2 = f"http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{matchgameid}/competitions/{matchgameid}/competitors/{team_id}/roster/{player_id}/statistics/0?lang=en&region=us"
        urlDate = f"http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{matchgameid}/competitions/{matchgameid}?lang=en&region=us"
      else:
        url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{current_year}/athletes/{player_id}/eventlog"
        response = requests.get(url)
        if response.status_code == 200:
          data2 = response.json()
        else:
          await ctx.send(f'@{ctx.author.name}, Player was not found. Check spelling or type: "!nfl <player full name>"')

        for i in range(len(data2['events']['items'])):
          if data2['events']['items'][len(data2['events']['items'])-1-i]['played'] == True:
            url2 = data2['events']['items'][len(data2['events']['items'])-1-i]['statistics']['$ref']
            urlDate = data2['events']['items'][len(data2['events']['items'])-1-i]['competition']['$ref']
            url_parts = url2.split('/')
            game_id = url_parts[9]
            break
          else:
            continue

      response2 = requests.get(url2)
      if response2.status_code == 200:
        data3 = response2.json()
      else:
        await ctx.send(f'@{ctx.author.name}, Error finding game stats for {name_final}.')
      
      url3 = f"http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{current_year}/athletes/{player_id}?lang=en&region=us"
      response3 = requests.get(url3)
      if response3.status_code == 200:
        data4 = response3.json()
      else:
        await ctx.send(f'@{ctx.author.name}, Error finding position for {name_final}.')

      position = data4['position']['abbreviation']
      stats = []
      with open('stats_abbreviations.json') as f:
        data5 = json.load(f)
      
      for i in range(len(data5['categories'])):
        for j in range(len(data5['categories'][i]['positions'])):
          if data5['categories'][i]['positions'][j] == position:
            for k in range(len(data5['categories'][i]['stats'])):
              for l in range(len(data3['splits']['categories'])):
                for m in range(len(data3['splits']['categories'][l]['stats'])):
                  if data3['splits']['categories'][l]['name'] == data5['categories'][i]['name']:
                    if data3['splits']['categories'][l]['stats'][m]['abbreviation'] == data5['categories'][i]['stats'][k]:
                      stats.append(data3['splits']['categories'][l]['stats'][m]['value'])
                      stats.append(data5['categories'][i]['stats'][k])
                      break
                else:
                  continue
            break
          else:
            continue
      
      response4 = requests.get(urlDate)
      if response4.status_code == 200:
        data6 = response4.json()
      else:
        await ctx.send(f'@{ctx.author.name}, Error finding game date for {name_final}.')
      
      game_date = data6['date'].split('T', 1)[0]
      game_date = datetime.strptime(game_date, '%Y-%m-%d').strftime('%m-%d-%Y')

      stats_msg = " ".join(str(x) for x in stats)
      formatted_stats_temp1 = re.sub(r'(\d+\.\d+ [A-Z]+(?: [A-Z]+)?)', r'\1,', stats_msg)
      formatted_stats_temp2 = formatted_stats_temp1.rstrip(',')
      if position == 'QB':
        pass_stats = formatted_stats_temp2.split(", ")[:5]  # First five stats for passing
        carry_stats = formatted_stats_temp2.split(", ")[5:8]  # Next three stats for carries
        fumble = formatted_stats_temp2.split(", ")[8]  # Last stat for fumbles
        formatted_stats_final = f"Pass: ({', '.join(pass_stats)}), Carry: ({', '.join(carry_stats)}), {fumble}"
      elif position == 'RB' or position == 'WR' or position == 'TE' or position == 'FB' or position == 'HB':
        rec_stats = formatted_stats_temp2.split(", ")[:4]  # First four stats for receptions
        carry_stats = formatted_stats_temp2.split(", ")[4:7]  # Next three stats for carries
        fumble = formatted_stats_temp2.split(", ")[7]  # Last stat for fumbles
        formatted_stats_final = f"Rec: ({', '.join(rec_stats)}), Carry: ({', '.join(carry_stats)}), {fumble}"
      else:
        formatted_stats_final = formatted_stats_temp2
        

      if data6['liveAvailable'] == True:
        await ctx.send(f"@{ctx.author.name}, Live stats for {name_final}: {formatted_stats_final}")
      else:
        await ctx.send(f"@{ctx.author.name}, No live stats found for {name_final}. Last played game {game_date}: {formatted_stats_final}")
        
      
    except Exception as e:
      await ctx.send(f'@{ctx.author.name}, Player not found. Check spelling or type: "!nfl <player full name>"')
      print (e)
  
  @commands.command()
  async def updatenflids(self, ctx: commands.Context):
    url = "https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=20000&active=true"
    response = requests.get(url)
    if response.status_code == 200:
      data = response.json()
    else:
      await ctx.send(f'@{ctx.author.name}, Error updating NFL player ids.')
    json_list = []
    for i in range(18739):
      if data['items'][i]['active'] == True:
        json_list.append({
          'id': data['items'][i]['id'],
          'fullName': data['items'][i]['fullName']
        })
    with open('nfl_ids.json', 'w') as f:
      json.dump(json_list, f)
    await ctx.send(f'@{ctx.author.name}, NFL player ids updated.')




bot = Bot()
bot.run()