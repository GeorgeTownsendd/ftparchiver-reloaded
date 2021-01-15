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

if __name__ == '__main__':
    #PresentData.save_team_training_graphs(4791, 'teams-weekly')
    #unique_database_list = list(set(['market-archive', 'nzl-od-34', 'u16-weekly', 'u21-national-squads', 'teams-weekly', 'nzl-t20-33', 'sa-od-42', 'PGT', 'u21-national-squads']))
    #for db in unique_database_list:
    #    PlayerDatabase.download_database(db)
    #db = PlayerDatabase.watch_database_list(unique_database_list)

    #database_name = 'teams-weekly'
    #training_data = FTPUtils.catagorise_training('all')


    current_round = 2
    league_ids = {'Youth' : 97605, 'Silver' : 97603, 'Platinum' : 97607, 'Gold' : 97602, 'Diamond' : 97606, 'Bronze' : 97604}

    leaguegames = {}
    for leaguename in league_ids.keys():
        if leaguename == 'Platinum':
            current_round -= 1
        leaguegames[leaguename] = [FTPUtils.get_league_gameids(league_ids[leaguename], round_n=n) for n in range(1, current_round+1)]
        if leaguename == 'Platinum':
            current_round += 1

    big_gameid_list = []
    for leaguename in leaguegames.keys():
        for round_list in leaguegames[leaguename]:
            for game in round_list:
                big_gameid_list.append(game)

    game_data = []
    for gameid in big_gameid_list:
        game = FTPUtils.get_game_scorecard_table(gameid)

        home_team_id = int(game[5][1][0])
        away_team_id = int(game[5][1][1])

        inn1_team_name = [x for x in game[1].iloc[0].index][0]
        inn2_team_name = [x for x in game[3].iloc[0].index][0]

        inn1_team_franch = team_franches[inn1_team_name]
        inn2_team_franch = team_franches[inn2_team_name]

        inn1_wicket_over_string = game[1].iloc[12][1]
        inn1_wickets, inn1_overs = [''.join([c for c in sideofcomma if c.isdigit() or c == '.']) for sideofcomma in inn1_wicket_over_string.split(',')]

        inn2_wicket_over_string = game[3].iloc[12][1]
        inn2_wickets, inn2_overs = [''.join([c for c in sideofcomma if c.isdigit() or c == '.']) for sideofcomma in inn2_wicket_over_string.split(',')]

        inn1_wickets, inn2_wickets = int(inn1_wickets), int(inn2_wickets)

        inn1_runs = int(game[1].iloc[12][3])
        inn2_runs = int(game[3].iloc[12][3])

        home_bats = FTPUtils.get_team_name(home_team_id) == inn1_team_name

        if home_bats:
            teamorder = [home_team_id, away_team_id]
        else:
            teamorder = [away_team_id, home_team_id]

        game = [gameid, teamorder, [inn1_team_name, inn2_team_name], [inn1_runs, inn2_runs], [inn1_wickets, inn2_wickets], [inn1_overs, inn2_overs], [inn1_team_franch, inn2_team_franch]]

        if not home_bats: #reverse so home team is first
            game = [game[0]] + [d[::-1] for d in game[1:]]

        game_data.append(game)

    franchise_data = []
    for franchise in franchise_name_list:
        games = 0
        wins = 0
        ties = 0
        points = 0

        runs = 0
        runs_against = 0

        wickets = 0
        wickets_against = 0

        balls = 0
        balls_against = 0
        for game in game_data:
            if franchise in game[-1]:
                games += 1
                franch_team_ind = game[-1].index(franchise)
                other_team_ind = (franch_team_ind-1)%2

                tie = game[3][franch_team_ind] == game[3][other_team_ind]
                scorecard = FTPUtils.get_game_scorecard_table(game[0])

                won_game = game[2][franch_team_ind] in scorecard[0][1][0]

                tie = False

                if won_game:
                    wins += 1
                    points += 4
                elif tie:
                    ties += 1
                    points += 2

                runs += game[3][franch_team_ind]
                runs_against += game[3][other_team_ind]

                game_wickets = game[4][franch_team_ind]
                game_wickets_against = game[4][other_team_ind]

                wickets += game_wickets
                wickets_against += game_wickets_against

                overs = game[5][franch_team_ind]
                against_overs = game[5][other_team_ind]

                if game_wickets == 10:
                    if scorecard[5].iloc[3][1] == 'PSL Youth':
                        overs = '40'
                    else:
                        overs = '50'
                if game_wickets_against == 10:
                    if scorecard[5].iloc[3][1] == 'PSL Youth':
                        against_overs = '40'
                    else:
                        against_overs = '50'

                balls += int(overs.split('.')[0]) * 6 + int(overs.split('.')[1]) if '.' in str(overs) else int(overs) * 6
                balls_against += int(against_overs.split('.')[0]) * 6 + int(against_overs.split('.')[1]) if '.' in str(against_overs) else int(against_overs) * 6


        balls_in_overs = float(balls // 6) + ((balls % 6) / 6)
        against_balls_in_overs = float(balls_against // 6) + (((balls_against) % 6) / 6)
        print(balls_in_overs, against_balls_in_overs)
        run_rate = (runs / balls)
        NRR = round((runs / balls_in_overs) - (runs_against / against_balls_in_overs), 4)

        full_bio = str(balls_in_overs).split('.')[0] + '.' + str(int(float('0.' + str(balls_in_overs).split('.')[1]) / (1/6)))
        full_bioa = str(against_balls_in_overs).split('.')[0] + '.' + str(int(float('0.' + str(against_balls_in_overs).split('.')[1]) / (1/6)))

        for_str = '{} / {}'.format(runs, full_bio)
        against_str = '{} / {}'.format(runs_against, full_bioa)

        franchise_data.append([franchise, games, wins, ties, points, NRR, for_str, against_str, runs, wickets, balls, runs_against, wickets_against, balls_against])

    column_names = ['Franchise', 'Games', 'Wins', 'Ties', 'Points', 'NRR', 'For', 'Against', 'Runs', 'Wickets', 'Balls', 'Runs Against', 'Wickets Against', 'Balls Against']
    col_dic = {}
    for n, cname in enumerate(column_names):
        col_dic[cname] = [row[n] for row in franchise_data]

    p = pd.DataFrame(col_dic)
    p.sort_values(['Points', 'NRR'], inplace=True, ascending=False)
    o = p.copy()
    for c in ['Runs', 'Wickets', 'Balls', 'Runs Against', 'Wickets Against', 'Balls Against']:
        o.drop(columns=c, inplace=True)

