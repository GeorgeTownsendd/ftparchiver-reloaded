import CoreUtils

CoreUtils.initialize_browser()
browser = CoreUtils.browser

import FTPUtils as FTPUtils
import PlayerDatabase as PlayerDatabase
import PresentData as PresentData
import os
import re
import pandas as pd

team_franches = {'Allmänna Idrottsklubben': 'QG', 'Hasraz': 'PZ', 'Pakshaheen': 'MS', 'Dead Stroker': 'MS', 'Caterham Crusaders': 'KK', 'Shahzaday11': 'LCF', 'London Spirit': 'KK', 'TRAL TIGERS': 'IU', 'Better Late Than Pregnant': 'LCF', 'Maiden Over CC': 'IU', 'The Hybrid Dolphins': 'PZ', "South London's Number One CC": 'PZ', 'Al Khobar Falcons': 'IU', 'ST 96': 'PZ', 'Jacksons Barbers': 'IU', 'Nepali Gaints': 'IU', 'The Humpty Elephants': 'MS', 'Legend Super Chicken Samurai': 'MS', 'Blade Brakers': 'LCF', 'Harrow CC': 'PZ', 'Afghan=Good': 'QG', 'ChePu 206': 'QG', 'United XI': 'QG', 'Afridi XI': 'KK', 'Bottybotbots': 'QG', "Lachlan's Tigers": 'MS', 'Mohun Bagan': 'KK', 'Young Snipers': 'KK', 'SBClub': 'MS', 'Jhelum Lions': 'KK', 'Wolfberries Too': 'LCF', 'Cover point': 'LCF', 'blackcat': 'QG', 'Hasraz A': 'PZ', 'Shorkot Stallions': 'IU', 'Indian Capers': 'LCF'}
franchise_name_list = list(set([team_franches[f] for f in team_franches.keys()]))
league_ids = {'Youth': 97605, 'Bronze': 97604, 'Silver': 97603, 'Gold': 97602, 'Diamond': 97606, 'Platinum': 97607}
league_rating_limits = {'Youth': 1000000, 'Bronze': 160000, 'Silver': 180000, 'Gold': 200000, 'Diamond': 220000, 'Platinum': 1000000}

def fantasy_point_analysis():
    '''cupId = 874
     group1_lsId = 97616
     group2_lsId = 97617
     group1 = [3009, 3007, 3003, 3018, 3015, 3008]
     group2 = [3017, 3004, 3001, 3011, 3013, 3002]'''  # Current World Cup

    cupId = 853
    group1_lsId = 92646
    group2_lsId = 92647
    group1_teams = [3017, 3013, 3005, 3003, 3008, 3006]
    group2_teams = [3015, 3018, 3001, 3007, 3002, 3009]  # s45 world cup

    group1_players = FTPUtils.get_touring_players(group1_lsId, group1_teams)
    group2_players = FTPUtils.get_touring_players(group2_lsId, group2_teams)

    group1_games, group2_games, finals_games = FTPUtils.get_cup_gameids(cupId)

    allplayers = pd.concat([group1_players, group2_players])
    allplayer_ids = pd.concat([group1_players['PlayerID'], group2_players['PlayerID']])
    allgames = group1_games + group2_games + finals_games

    fantasy_points_tables = [FTPUtils.get_game_ratings_fantasy_tables(gameid, 'fantasy') for gameid in allgames]
    player_fantasy_points = {}

    for fantasy_pt in fantasy_points_tables:
        player_ids, player_points = fantasy_pt['PlayerID'], fantasy_pt['Fantasy Points']
        for pid, fpoints in zip(player_ids, player_points):
            if pid in player_fantasy_points.keys():
                player_fantasy_points[pid] += fpoints
            else:
                player_fantasy_points[pid] = fpoints

    allplayers_ordered_fantasy_points = []
    for n, player_id in allplayer_ids.iteritems():
        allplayers_ordered_fantasy_points.append(player_fantasy_points[player_id])

    allplayers['Age'] = FTPUtils.normalize_age_list(FTPUtils.normalize_age_list(allplayers['Age']), reverse=True)
    allplayers.insert(len(allplayers.columns), 'Total Fantasy Points', allplayers_ordered_fantasy_points)


def verify_match_ratings(gameid, ratings_limit):
    match_ratings = FTPUtils.get_game_ratings_fantasy_tables(gameid, 'ratings')
    team_names = [team for team in match_ratings.columns[1:3]]
    overall_ratings = [int(overall_rating) for overall_rating in match_ratings.iloc[6][1:3]]
    within_limits = {}

    for n, team in enumerate(team_names):
        if overall_ratings[n] > ratings_limit:
            within_limits[team] = False
        else:
            within_limits[team] = True

    return within_limits


def verify_league_round_ratings(leagueid, round_n, ratings_limit):
    gameids = FTPUtils.get_league_gameids(leagueid, round_n)
    result_strings = []


    for gameid in gameids:
        team_within_limits = verify_match_ratings(gameid, ratings_limit)
        team_names = [team for team in team_within_limits.keys()]
        team_ids = FTPUtils.get_game_teamids(gameid)
        game_result_string = FTPUtils.get_game_scorecard_table(gameid)[0][1][0]
        game_winner, game_loser = None, None
        game_adjusted = None
        if team_names[0] in game_result_string:
            if 'adjusted' in game_result_string:
                game_adjusted = True
                game_winner = (team_names[1], team_ids[1])
                game_loser = (team_names[0], team_ids[0])
            else:
                game_adjusted = False
                game_winner = (team_names[0], team_ids[0])
                game_loser = (team_names[1], team_ids[1])
        elif team_names[1] in game_result_string:
            if 'adjusted' in game_result_string:
                game_adjusted = True
                game_winner = (team_names[0], team_ids[0])
                game_loser = (team_names[1], team_ids[1])
            else:
                game_adjusted = False
                game_winner = (team_names[1], team_ids[1])
                game_loser = (team_names[0], team_ids[0])

        if game_adjusted:
            formatted_result_string = game_result_string + '. (result already overturned)'
            winning_franchise = team_franches[game_winner[0]]
            losing_franchise = team_franches[game_winner[0]]
        else:
            formatted_result_string = game_result_string
            if not team_within_limits[game_winner[0]]:
                if team_within_limits[game_loser[0]]:
                    formatted_result_string += ', but the result will be overturned to a win for {} due to overrating.'.format(game_loser[0])
                    winning_franchise = team_franches[game_loser[0]]
                    losing_franchise = team_franches[game_loser[0]]
                else:
                    formatted_result_string += ', and the result will stand due to an overrating by both teams.'
                    winning_franchise = team_franches[game_winner[0]]
            else:
                if team_within_limits[game_loser[0]]:
                    formatted_result_string += '. Both teams fell within the rating limits.'
                    winning_franchise = team_franches[game_winner[0]]
                    losing_franchise = team_franches[game_loser[0]]
                else:
                    formatted_result_string += ' despite an overrating by {}.'.format(game_loser[0])
                    winning_franchise = team_franches[game_loser[0]]
                    losing_franchise = team_franches[game_winner[0]]

        for team in [game_winner[0], game_loser[0]]:
            if team in formatted_result_string:
                formatted_result_string = formatted_result_string.replace(team, '{} ({})'.format(team, team_franches[team]))

        game_title = '[{}] {} ({}) v {} ({}): '.format(gameid, team_names[0], team_ids[0], team_names[1], team_ids[1])
        result_strings.append(game_title + formatted_result_string)

    return result_strings


if __name__ == '__main__':
    round_n = 1
    league_result_strings = {}
    for league_name in league_ids.keys():
        league_id = league_ids[league_name]
        league_rating_limit = league_rating_limits[league_name]
        league_results = verify_league_round_ratings(league_id, round_n, league_rating_limit)
        league_result_strings[league_name] = league_results



    #PlayerDatabase.download_database('market-archive')
    #PresentData.save_team_training_graphs(4791, 'teams-weekly')
    #unique_database_list = list(set(['nzl-od-34', 'u16-weekly', 'market-archive', 'u21-national-squads', 'teams-weekly', 'nzl-t20-33', 'sa-od-42', 'PGT', 'u21-national-squads']))
    #PlayerDatabase.watch_database_list(unique_database_list)
    #for db in unique_database_list:
    #    PlayerDatabase.download_database(db)
    #db = PlayerDatabase.watch_database_list(unique_database_list)
    pass
    #database_name = 'teams-weekly'
    #training_data = FTPUtils.catagorise_training('all')

    #next_database_download = dbstack[0]
    #PlayerDatabase.download_database(next_database_download[1], download_teams_whitelist=next_database_download[2], age_override=next_database_download[3])
