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
    global franch_win_table
    gameids = FTPUtils.get_league_gameids(leagueid, round_n)
    result_strings = []

    for gameid in gameids:
        team_within_limits = verify_match_ratings(gameid, ratings_limit)
        team_names = [team for team in team_within_limits.keys()]
        team_ids = FTPUtils.get_game_teamids(gameid)
        game_result_string = FTPUtils.get_game_scorecard_table(gameid)[0][1][0]
        game_winner, game_loser = None, None
        game_adjusted, game_tied = None, None
        if team_names[0] in game_result_string:
            game_tied = False
            if 'adjusted' in game_result_string:
                game_adjusted = True
                game_winner = (team_names[1], team_ids[1])
                game_loser = (team_names[0], team_ids[0])
            else:
                game_adjusted = False
                game_winner = (team_names[0], team_ids[0])
                game_loser = (team_names[1], team_ids[1])
        elif team_names[1] in game_result_string:
            game_tied = False
            if 'adjusted' in game_result_string:
                game_adjusted = True
                game_winner = (team_names[0], team_ids[0])
                game_loser = (team_names[1], team_ids[1])
            else:
                game_adjusted = False
                game_winner = (team_names[1], team_ids[1])
                game_loser = (team_names[0], team_ids[0])
        elif 'Match tied' in game_result_string:
            game_tied = True
            game_winner = (team_names[1], team_ids[1]) #game winner/loser is just a placeholder name for tied matches
            game_loser = (team_names[0], team_ids[0])

        if game_adjusted:
            formatted_result_string = game_result_string + '. (result already overturned)'
            winning_franchise = team_franches[game_winner[0]]
            losing_franchise = team_franches[game_loser[0]]
        elif game_tied:
            formatted_result_string = game_result_string
            if not team_within_limits[game_winner[0]] and not team_within_limits[game_loser[0]]:
                formatted_result_string += ', and the result will stand due to an overrating by both teams.'
                winning_franchise, losing_franchise = team_franches[game_winner[0]], team_franches[game_loser[0]]
            elif not team_within_limits[game_winner[0]]:
                formatted_result_string += ', but the result will be overturned to a win for {} due to an overrating.'.format(game_loser[0])
                game_tied = False
                game_winner, game_loser = game_loser, game_winner
                winning_franchise, losing_franchise = team_franches[game_winner[0]], team_franches[game_loser[0]]
            elif not team_within_limits[game_loser[0]]:
                formatted_result_string += ', but the result will be overturned to a win for {} due to an overrating'.format(game_winner[0])
                game_tied = False
                winning_franchise, losing_franchise = team_franches[game_winner[0]], team_franches[game_loser[0]]
            else:
                formatted_result_string += '. Both teams fell within the rating limits.'
                winning_franchise, losing_franchise = team_franches[game_winner[0]], team_franches[game_loser[0]]
        else:
            formatted_result_string = game_result_string
            if not team_within_limits[game_winner[0]]:
                if team_within_limits[game_loser[0]]:
                    formatted_result_string += ', but the result will be overturned to a win for {} due to overrating.'.format(game_loser[0])
                    winning_franchise = team_franches[game_loser[0]]
                    losing_franchise = team_franches[game_winner[0]]
                else:
                    formatted_result_string += ', and the result will stand due to an overrating by both teams.'
                    winning_franchise = team_franches[game_winner[0]]
                    losing_franchise = team_franches[game_loser[0]]
            else:
                if team_within_limits[game_loser[0]]:
                    formatted_result_string += '. Both teams fell within the rating limits.'
                    winning_franchise = team_franches[game_winner[0]]
                    losing_franchise = team_franches[game_loser[0]]
                else:
                    formatted_result_string += ' despite an overrating by {}.'.format(game_loser[0])
                    winning_franchise = team_franches[game_loser[0]]
                    losing_franchise = team_franches[game_winner[0]]

        if not game_tied:
            franch_win_table[winning_franchise][losing_franchise][0] += 2
            franch_win_table[winning_franchise][losing_franchise][1].append(gameid)
            franch_win_table[losing_franchise][winning_franchise][1].append(gameid)
        else:
            franch_win_table[winning_franchise][losing_franchise][0] += 1 #winning/losing franchise names are not actually winners/losers
            franch_win_table[losing_franchise][winning_franchise][0] += 1
            franch_win_table[winning_franchise][losing_franchise][1].append(gameid)
            franch_win_table[losing_franchise][winning_franchise][1].append(gameid)

        for team in [game_winner[0], game_loser[0]]:
            if team in formatted_result_string:
                formatted_result_string = formatted_result_string.replace(team, '{} ({})'.format(team, team_franches[team]))

        game_title = '[{}] {} ({}) v {} ({}): '.format(gameid, team_names[0], team_ids[0], team_names[1], team_ids[1])
        result_strings.append(game_title + formatted_result_string)

    return result_strings

def print_results(franch_win_table):
    for franch1 in franch_win_table.keys():
        print('Points breakdown for {}:'.format(franch1))
        points_sum = 0
        for franch2 in franch_win_table[franch1].keys():
            if franch1 != franch2:
                franch1_points = franch_win_table[franch1][franch2][0]
                franch2_points = franch_win_table[franch2][franch1][0]
                pointdif = franch1_points - franch2_points
                franch1_score = pointdif if pointdif > 0 else 0
                points_sum += franch1_score

                print('\tvs. {}'.format(franch2))
                print('\t\tGames included: {}'.format(','.join(franch_win_table[franch1][franch2][1])))
                print('\t\tHead to Head: {} - {}'.format(franch1_points, franch2_points))
                print('\t\tResult: {} points for {}'.format(franch1_score, franch1))
        print('\n\t{} total: {} points'.format(franch1, points_sum))
        print('---')

if __name__ == '__main__':
    '''franch_win_table = {}
    for franch_team in franchise_name_list:
        game_results = {}
        for verses_team in franchise_name_list:
            if verses_team == franch_team:
                game_results[verses_team] = ['-', []]
            else:
                game_results[verses_team] = [0, []]
        franch_win_table[franch_team] = game_results

    round_results = {}
    for round_n in [1, 2, 3, 4, 5]:
        league_round_result_strings = {}
        for league_name in league_ids.keys():
            league_id = league_ids[league_name]
            league_rating_limit = league_rating_limits[league_name]
            league_results = verify_league_round_ratings(league_id, round_n, league_rating_limit)
            league_round_result_strings[league_name] = league_results
        round_results[round_n] = league_round_result_strings'''

    PSL5_franch_win_table = {'IU': {'IU': ['-', []], 'KK': [4, ['5615965', '5615957', '5615990', '5616024', '5616002', '5616270']], 'LCF': [10, ['5616263', '5616009', '5615991', '5615968', '5615950', '5616016']], 'QG': [8, ['5615989', '5616021', '5616273', '5615997', '5615974', '5615955']], 'MS': [6, ['5615996', '5615964', '5616017', '5616269', '5615992', '5615972']], 'PZ': [6, ['5615971', '5616008', '5615986', '5615951', '5616262', '5616022']]}, 'KK': {'IU': [8, ['5615965', '5615957', '5615990', '5616024', '5616002', '5616270']], 'KK': ['-', []], 'LCF': [4, ['5615999', '5615953', '5616015', '5616271', '5615983', '5615966']], 'QG': [2, ['5615979', '5615998', '5615959', '5615994', '5616010', '5616274']], 'MS': [6, ['5615993', '5616261', '5616003', '5615973', '5615956', '5616014']], 'PZ': [4, ['5616268', '5616005', '5615984', '5616013', '5615976', '5615961']]}, 'LCF': {'IU': [2, ['5616263', '5616009', '5615991', '5615968', '5615950', '5616016']], 'KK': [8, ['5615999', '5615953', '5616015', '5616271', '5615983', '5615966']], 'LCF': ['-', []], 'QG': [7, ['5615977', '5615982', '5615960', '5616007', '5616011', '5616264']], 'MS': [8, ['5615975', '5616023', '5616004', '5615981', '5616272', '5615954']], 'PZ': [8, ['5615985', '5615962', '5616020', '5616266', '5615995', '5615978']]}, 'QG': {'IU': [4, ['5615989', '5616021', '5616273', '5615997', '5615974', '5615955']], 'KK': [10, ['5615979', '5615998', '5615959', '5615994', '5616010', '5616274']], 'LCF': [5, ['5615977', '5615982', '5615960', '5616007', '5616011', '5616264']], 'QG': ['-', []], 'MS': [6, ['5616260', '5616000', '5615980', '5615952', '5615970', '5616012']], 'PZ': [6, ['5616001', '5615958', '5616019', '5616265', '5615988', '5615967']]}, 'MS': {'IU': [6, ['5615996', '5615964', '5616017', '5616269', '5615992', '5615972']], 'KK': [6, ['5615993', '5616261', '5616003', '5615973', '5615956', '5616014']], 'LCF': [4, ['5615975', '5616023', '5616004', '5615981', '5616272', '5615954']], 'QG': [6, ['5616260', '5616000', '5615980', '5615952', '5615970', '5616012']], 'MS': ['-', []], 'PZ': [10, ['5615969', '5615987', '5615963', '5616018', '5616006', '5616267']]}, 'PZ': {'IU': [6, ['5615971', '5616008', '5615986', '5615951', '5616262', '5616022']], 'KK': [8, ['5616268', '5616005', '5615984', '5616013', '5615976', '5615961']], 'LCF': [4, ['5615985', '5615962', '5616020', '5616266', '5615995', '5615978']], 'QG': [6, ['5616001', '5615958', '5616019', '5616265', '5615988', '5615967']], 'MS': [2, ['5615969', '5615987', '5615963', '5616018', '5616006', '5616267']], 'PZ': ['-', []]}}
    #format_win_table(PSL5_franch_win_table)

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
