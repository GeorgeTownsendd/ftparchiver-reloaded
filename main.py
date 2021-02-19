import CoreUtils

CoreUtils.initialize_browser()
browser = CoreUtils.browser.rbrowser

import FTPUtils as FTPUtils
import PlayerDatabase as PlayerDatabase
import PresentData as PresentData
import os
import re
import pandas as pd

BATTERS = ['Gideon Wettenhall', 'Shontayne John', 'Hallam Corbie', 'Andrew Kibet', 'Colin Eugene', 'Crackers Breust', 'Anomen Delryn', 'Mahfuz Khan', 'Motu Jellick', 'Callum Sewart', 'Sharrod Hay', 'Gagan Khoda', 'Tanwir McInnes', 'Ajitesh Rangachari', 'Frank Elliott', 'Lisle Sicily', 'Dilum Nandana', 'Jurriaan Uytdehaage', 'Dermot Sweeney', 'Luuk van Eijsinga', 'Gabriel Greene', 'Aled Field', 'Vaughan Brennan', 'Ambathi Binny', 'Hakeem wa Mathai', 'Abhiramana Mukund', 'Barlow Charlwood', 'John Molony', 'Neomal Irfahan', 'Zaccheus Kinyua', 'Lawrie Silva', 'Ciaran Dempsey', 'Karl Langley', 'Dion King', 'Ismail Menk', 'FitzChivalry Farseer', 'Adam Finnegan', 'Karson Acosta', 'Imtiaz Whybrew', 'Jaap Mijnke', 'Richard Hibbert', 'Silida Warnapura', 'Wouter Teeven', 'Samson Blackwell', 'Imogen de Groen', 'Raymond Fernandez', 'Audrey Anthony', 'Mandeep Dadawala', 'Lyndon Luatua', 'Ashish Sharma', 'Alexander De Valera', 'Justus Mwangi', 'Dinny Murphy', 'Laurel McTrusty', 'Tilan Kobbekaduwa', 'Warran Yearwood', 'Parimal Shrestha', 'Rajavarothiam Kuruppuarachchi', 'Floyd Doctrove', 'Earl Douglas', 'Jomo Kibaki', 'Bennedict Maina', 'Dollar Sixer', 'Sanjog Ubriani', 'Lodewijk van Amsterdam', 'Nathaniel Cochran', 'Victor van Nierop', 'Sandip Kuruvilla', 'Indika Kumaratunga', 'Ahuja Patankar', 'Nelson Ninelives', 'Selwyn Hubble', 'Lloyd Phillips', 'Len Thomas', 'Talha Matin', 'Danny Astruc', 'Homer Simpson', 'Mervin Carew', 'Mark Waugh', 'Amit Uthappa', 'James McKew', 'Oliver Kelly']
INIT_BATTERS = ['G. Wettenhall', 'S. John', 'H. Corbie', 'A. Kibet', 'C. Eugene', 'C. Breust', 'A. Delryn', 'M. Khan', 'M. Jellick', 'C. Sewart', 'S. Hay', 'G. Khoda', 'T. McInnes', 'A. Rangachari', 'F. Elliott', 'L. Sicily', 'D. Nandana', 'J. Uytdehaage', 'D. Sweeney', 'L. van Eijsinga', 'G. Greene', 'A. Field', 'V. Brennan', 'A. Binny', 'H. wa Mathai', 'A. Mukund', 'B. Charlwood', 'J. Molony', 'N. Irfahan', 'Z. Kinyua', 'L. Silva', 'C. Dempsey', 'K. Langley', 'D. King', 'I. Menk', 'F. Farseer', 'A. Finnegan', 'K. Acosta', 'I. Whybrew', 'J. Mijnke', 'R. Hibbert', 'S. Warnapura', 'W. Teeven', 'S. Blackwell', 'I. de Groen', 'R. Fernandez', 'A. Anthony', 'M. Dadawala', 'L. Luatua', 'A. Sharma', 'A. De Valera', 'J. Mwangi', 'D. Murphy', 'L. McTrusty', 'T. Kobbekaduwa', 'W. Yearwood', 'P. Shrestha', 'R. Kuruppuarachchi', 'F. Doctrove', 'E. Douglas', 'J. Kibaki', 'B. Maina', 'D. Sixer', 'S. Ubriani', 'L. van Amsterdam', 'N. Cochran', 'V. van Nierop', 'S. Kuruvilla', 'I. Kumaratunga', 'A. Patankar', 'N. Ninelives', 'S. Hubble', 'L. Phillips', 'L. Thomas', 'T. Matin', 'D. Astruc', 'H. Simpson', 'M. Carew', 'M. Waugh', 'A. Uthappa', 'J. McKew', 'O. Kelly']

if __name__ == '__main__':
    cupId = 874
    group1_lsId = 97616
    group2_lsId = 97617
    group1_teams = [3009, 3007, 3003, 3018, 3015, 3008]
    group2_teams = [3017, 3004, 3001, 3011, 3013, 3002]  # Current World Cup

    group1_players = FTPUtils.get_touring_players(group1_lsId, group1_teams)
    group2_players = FTPUtils.get_touring_players(group2_lsId, group2_teams)
    allplayers = pd.concat([group1_players, group2_players])

    group1_games, group2_games, finals_games = FTPUtils.get_cup_gameids(cupId)
    allgames = group1_games + group2_games + finals_games

    game_data = []

    for game in allgames:
        browser.open('https://www.fromthepavilion.org/scorecard.htm?gameId={}'.format(game))
        page = str(browser.parsed)
        data = pd.read_html(page)
        home_xi = data[1][list(data[1].columns)[0]][:10]
        home_runs = data[1].Runs[:10]
        away_xi = data[3][list(data[3].columns)[0]][:10]
        away_runs = data[3].Runs[:10]

        game_data.append([home_xi, home_runs, away_xi, away_runs])

    batter_scores = {batter_name: [] for batter_name in INIT_BATTERS}
    for game in game_data:
        players, runs = pd.concat([game[0], game[2]]), pd.concat([game[1], game[3]])
        for player, runs in zip(players, runs):
            if player in INIT_BATTERS:
                batter_scores[player].append(runs)

    scores_by_thousand_wage = {w : [] for w in list(range(15, 31))}
    for player in batter_scores.keys():
        player_ind = INIT_BATTERS.index(player)
        player_fullname = BATTERS[player_ind]
        player_wage_str = allplayers[allplayers['Player'] == player_fullname].Wage.iloc[0]
        player_wage = int(''.join([x for x in player_wage_str if x.isdigit()]))
        player_wage_k = player_wage // 1000
        for score in batter_scores[player]:
            if isinstance(score, float):
                pass
            else:
                score = int(score)
                scores_by_thousand_wage[player_wage_k].append(score)

    averages = [sum(scores_by_thousand_wage[wage]) / len(scores_by_thousand_wage[wage]) if len(scores_by_thousand_wage[wage]) > 0 else 0 for wage in scores_by_thousand_wage.keys()]







