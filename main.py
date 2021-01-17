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
gameid_scorecard = {}


def get_round_franch_table(to_round):
    global gameid_scorecard
    league_ids = {'Youth': 97605, 'Silver': 97603, 'Platinum': 97607, 'Gold': 97602, 'Diamond': 97606, 'Bronze': 97604}

    franchise_points = {f: 0 for f in franchise_name_list}

    leaguegames = {}
    for leaguename in league_ids.keys():
        if leaguename == 'Platinum':
            current_round = to_round - 1
        else:
            current_round = to_round

        if current_round > 0:

            browser.rbrowser.open(
                'https://www.fromthepavilion.org/leaguepositions.htm?lsId={}'.format(league_ids[leaguename]))
            parameter_form = browser.rbrowser.get_form()
            parameter_form['graph'].value = 'false'  # false is table view
            browser.rbrowser.submit_form(parameter_form)
            page = str(browser.rbrowser.parsed)
            table_positions = pd.read_html(page)[2]
            team_standings = [[n for n in table_positions.iloc[team]] for team in range(len(table_positions))]
            team_standings = sorted(team_standings, key=lambda x: x[current_round])

            team_sorted_list = [team_franches[t[0]] for t in team_standings]
            points = [x for x in range(0, len(team_sorted_list))][::-1]
            for points, franch in zip(points, team_sorted_list):
                franchise_points[franch] += points

            leaguegames[leaguename] = [FTPUtils.get_league_gameids(league_ids[leaguename], round_n=n) for n in range(1, current_round + 1)]

    big_gameid_list = []
    for leaguename in leaguegames.keys():
        for round_list in leaguegames[leaguename]:
            for game in round_list:
                big_gameid_list.append(game)

    game_data = []
    for gameid in big_gameid_list:
        if gameid in gameid_scorecard.keys():
            game = gameid_scorecard[gameid]
        else:
            game = FTPUtils.get_game_scorecard_table(gameid)
            gameid_scorecard[gameid] = game

        home_team_id = int(game[5][1][0])
        away_team_id = int(game[5][1][1])

        inn1_team_name = [x for x in game[1].iloc[0].index][0]
        inn2_team_name = [x for x in game[3].iloc[0].index][0]

        inn1_team_franch = team_franches[inn1_team_name]
        inn2_team_franch = team_franches[inn2_team_name]

        inn1_wicket_over_string = game[1].iloc[12][1]
        inn1_wickets, inn1_overs = [''.join([c for c in sideofcomma if c.isdigit() or c == '.']) for sideofcomma in
                                    inn1_wicket_over_string.split(',')]

        inn2_wicket_over_string = game[3].iloc[12][1]
        inn2_wickets, inn2_overs = [''.join([c for c in sideofcomma if c.isdigit() or c == '.']) for sideofcomma in
                                    inn2_wicket_over_string.split(',')]

        inn1_wickets, inn2_wickets = int(inn1_wickets), int(inn2_wickets)

        inn1_runs = int(game[1].iloc[12][3])
        inn2_runs = int(game[3].iloc[12][3])

        home_bats = FTPUtils.get_team_name(home_team_id) == inn1_team_name

        if home_bats:
            teamorder = [home_team_id, away_team_id]
        else:
            teamorder = [away_team_id, home_team_id]

        game = [gameid, teamorder, [inn1_team_name, inn2_team_name], [inn1_runs, inn2_runs],
                [inn1_wickets, inn2_wickets], [inn1_overs, inn2_overs], [inn1_team_franch, inn2_team_franch]]

        if not home_bats:  # reverse so home team is first
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
                other_team_ind = (franch_team_ind - 1) % 2

                tie = game[3][franch_team_ind] == game[3][other_team_ind]
                scorecard = gameid_scorecard[game[0]]

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

                balls += int(overs.split('.')[0]) * 6 + int(overs.split('.')[1]) if '.' in str(overs) else int(
                    overs) * 6
                balls_against += int(against_overs.split('.')[0]) * 6 + int(against_overs.split('.')[1]) if '.' in str(
                    against_overs) else int(against_overs) * 6

        balls_in_overs = float(balls // 6) + ((balls % 6) / 6)
        against_balls_in_overs = float(balls_against // 6) + (((balls_against) % 6) / 6)
        run_rate = (runs / balls)
        NRR = round((runs / balls_in_overs) - (runs_against / against_balls_in_overs), 4)

        full_bio = str(balls_in_overs).split('.')[0] + '.' + str(
            int(float('0.' + str(balls_in_overs).split('.')[1]) / (1 / 6)))
        full_bioa = str(against_balls_in_overs).split('.')[0] + '.' + str(
            int(float('0.' + str(against_balls_in_overs).split('.')[1]) / (1 / 6)))

        for_str = '{} / {}'.format(runs, full_bio)
        against_str = '{} / {}'.format(runs_against, full_bioa)

        franchise_data.append(
            [franchise, franchise_points[franchise], games, wins, ties, points, NRR, for_str, against_str, runs,
             wickets, balls, runs_against, wickets_against, balls_against])

    column_names = ['Franchise', 'PSL Points', 'Games', 'Wins', 'Ties', 'Game Points', 'NRR', 'For', 'Against', 'Runs',
                    'Wickets', 'Balls', 'Runs Against', 'Wickets Against', 'Balls Against']
    col_dic = {}
    for n, cname in enumerate(column_names):
        col_dic[cname] = [row[n] for row in franchise_data]

    table = pd.DataFrame(col_dic)
    table.sort_values(['PSL Points'], inplace=True, ascending=False)
    table['Franchise'] = ['Islambad United', 'Multan Sultans', 'Peshawar Zalmi', 'Quetta Gladiators', 'Karachi Kings', 'Lahore Capra Falconeri']
    for c in ['Runs', 'Wickets', 'Balls', 'Runs Against', 'Wickets Against', 'Balls Against']:
        table.drop(columns=c, inplace=True)
    table.reset_index(drop=True)
    table['Pos.'] = [n+1 for n in range(len(table))]
    return table

def create_advanced_table(round_n):
    prev_round = round_n-1
    curr_round = round_n

    prev_round_table = get_round_franch_table(prev_round)
    curr_round_table = get_round_franch_table(curr_round)

    position_shifts = ['-' for change in range(len(curr_round_table))]
    for curr_position, franch in enumerate(curr_round_table.Franchise):
        curr_position += 1
        prev_position = [f for f in prev_round_table['Franchise']].index(franch) + 1
        if curr_position - prev_position > 0:
            position_shifts[curr_position] = '↓'
        elif curr_position - prev_position < 0:
            position_shifts[curr_position] = '↑'

    curr_round_table['Position Change'] = position_shifts

    prev_round_table = prev_round_table.sort_values(['Franchise'])
    curr_round_table = curr_round_table.sort_values(['Franchise'])

    curr_round_table['PSL Points Dif'] = curr_round_table['PSL Points'] - prev_round_table['PSL Points']
    points_shifts = ['-' for change in range(len(curr_round_table))]
    for pos_n, points_dif in enumerate(curr_round_table['PSL Points Dif']):
        if points_dif > 0:
            points_shifts[pos_n] = '↑'
        elif points_dif < 0:
            points_shifts[pos_n] = '↓'
    curr_round_table['PSL Points Change'] = points_shifts
    curr_round_table = curr_round_table.sort_values(['PSL Points'], ascending=False)

    new_psl_points = []
    for point, dif, shift in zip(curr_round_table['PSL Points'], curr_round_table['PSL Points Change'], curr_round_table['PSL Points Dif']):
        new_psl_points.append('{} ({} {})'.format(point, abs(shift), dif))
    curr_round_table['PSL Points Str'] = new_psl_points

    return curr_round_table

if __name__ == '__main__':
    #PresentData.save_team_training_graphs(4791, 'teams-weekly')
    #unique_database_list = list(set(['market-archive', 'nzl-od-34', 'u16-weekly', 'u21-national-squads', 'teams-weekly', 'nzl-t20-33', 'sa-od-42', 'PGT', 'u21-national-squads']))
    #for db in unique_database_list:
    #    PlayerDatabase.download_database(db)
    #db = PlayerDatabase.watch_database_list(unique_database_list)

    #database_name = 'teams-weekly'
    #training_data = FTPUtils.catagorise_training('all')

    curr_round_table = create_advanced_table(2)

