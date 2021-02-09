import CoreUtils

CoreUtils.initialize_browser()
browser = CoreUtils.browser

import FTPUtils as FTPUtils
import PlayerDatabase as PlayerDatabase
import PresentData as PresentData
import os
import re

if __name__ == '__main__':
    '''cupId = 874
    group1_lsId = 97616
    group2_lsId = 97617
    group1 = [3009, 3007, 3003, 3018, 3015, 3008]
    group2 = [3017, 3004, 3001, 3011, 3013, 3002]''' #Current World Cup
    import pandas as pd

    cupId = 853
    group1_lsId = 92646
    group2_lsId = 92647
    group1_teams = [3017, 3013, 3005, 3003, 3008, 3006]
    group2_teams = [3015, 3018, 3001, 3007, 3002, 3009] #s45 world cup

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
