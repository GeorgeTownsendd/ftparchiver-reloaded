import FTPUtils
import PlayerDatabase

import os
import time
import datetime
import re
import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
from robobrowser import RoboBrowser
import pandas as pd
import shutil
import numpy as np
import matplotlib
#matplotlib.use('Agg')
from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})
import matplotlib.pyplot as plt
import seaborn as sns; sns.set_theme(color_codes=True)
import mplcursors
from math import floor, isnan
pd.options.mode.chained_assignment = None  # default='warn'

browser = False

def youth_pull_league_round_overview(leagueid, normalize_age=False, league_format='league', round_n='latest', ind_level=0, weeks_since_game='default', use_browser=False):
    global browser
    if use_browser:
        browser = use_browser
    FTPUtils.check_login(browser)
    
    requested_games = FTPUtils.get_league_gameids(leagueid, league_format=league_format, round_n=round_n, use_browser=browser)
    browser.open('https://www.fromthepavilion.org/commentary.htm?gameId={}'.format(requested_games[0]))
    if weeks_since_game == 'default':
        player_match_age = FTPUtils.normalize_age_list(['16.00'])[0]
    else:
        valid_age = 16 + (weeks_since_game / 15)
        valid_age = '16.' + str(valid_age).split('.')[1][:5]
        player_match_age = float(valid_age)

    if 'Membership Features' in str(browser.parsed):
        games_finished = False
    else:
        games_finished = True

    FTPUtils.log_event('League {} - Round {}: {}'.format(leagueid, round_n, 'Played' if games_finished else 'Not Played'), ind_level=ind_level)

    round_teams = []
    if not games_finished:
        for game in [FTPUtils.get_game_teamids(game) for game in requested_games]:
            round_teams.append(game[0]) #home
            round_teams.append(game[1]) #away
    else:
        scorecard_tables = [FTPUtils.get_game_scoredcard_table(gameid) for gameid in requested_games]
        for game in [g[-2] for g in scorecard_tables]:
            round_teams.append(game[1][0]) #home
            round_teams.append(game[1][1]) #away

    team_youthsquads = pd.concat([FTPUtils.get_team_players(teamid, age_group='youths', normalize_age=True) for teamid in round_teams])
    new_players = team_youthsquads[team_youthsquads['Age'] == float(player_match_age)]
    new_players['Age'] = [str(x) for x in new_players['Age']]
    new_players.insert(3, 'Initial', [playername.split(' ', 1)[0][0] + '. ' + playername.split(' ', 1)[1] for playername in new_players['Player']])

    if games_finished:
        players = []
        players_in_round = []
        for player_initial in new_players['Initial']:
            player = new_players.iloc[[str(x) for x in new_players['Initial']].index(player_initial)]
            player['Batting'] = None
            player['Bowling'] = None
            player_bat, player_bowl = None, None

            for game_scorecard in scorecard_tables:
                home_batting, home_bowling = game_scorecard[1], game_scorecard[4]
                away_batting, away_bowling = game_scorecard[3], game_scorecard[2]

                home_team_name, away_team_name = home_batting.columns[0], away_batting.columns[0]
                home_lineup = [str(x).replace(' (c)', '').replace(' (wk)', '') for x in home_batting[home_team_name] if '.' in x]
                away_lineup = [str(x).replace(' (c)', '').replace(' (wk)', '') for x in away_batting[away_team_name] if '.' in x]

                home_lineup_initials = [playername.split(' ', 1)[0][0] + '. ' + playername.split(' ', 1)[1] for playername in home_lineup]
                away_lineup_initials = [playername.split(' ', 1)[0][0] + '. ' + playername.split(' ', 1)[1] for playername in away_lineup]

                players_in_round.append(home_lineup)
                players_in_round.append(away_lineup)


                if player_initial in [str(x) for x in home_lineup_initials]:
                    player_bat = home_batting.iloc[[str(x.replace(' (c)', '').replace(' (wk)', '')) for x in home_batting[home_team_name]].index(player_initial)]
                    if player_bowl is None:
                        player_bowl = '-'

                    print('Player {} found in {}'.format(player_initial, home_team_name + ' - ' + away_team_name))
                elif player_initial in [str(x) for x in away_lineup_initials]:
                    player_bat = away_batting.iloc[[str(x).replace(' (c)', '').replace(' (wk)', '') for x in away_batting[away_team_name]].index(player_initial)]
                    if player_bowl is None:
                        player_bowl = '-'

                    print('Player {} found in {}'.format(player_initial, home_team_name + ' - ' + away_team_name))

                home_bowling['Name'] = [str(player.split('(')[0][:-1]) for player in home_bowling['Bowling']]
                away_bowling['Name'] = [str(player.split('(')[0][:-1]) for player in away_bowling['Bowling']]

                if player_initial in [str(x) for x in home_bowling['Name']]:
                    player_bowl = home_bowling.iloc[[str(x) for x in home_bowling['Name']].index(player_initial)]
                    print('Player {} found in {}'.format(player_initial, home_team_name + ' - ' + away_team_name))

                if player_initial in [str(x) for x in away_bowling['Name']]:
                    player_bowl = away_bowling.iloc[[str(x) for x in away_bowling['Name']].index(player_initial)]
                    print('Player {} found in {}'.format(player_initial, home_team_name + ' - ' + away_team_name))

                if player_bat is not None and player_bowl is not None:
                    break

            if player_bat is not None:
                player['Batting'] = player_bat['Runs']
            elif player_bat != '-':
                player['Batting'] = 'DNP'
            if isinstance(player_bowl, pd.Series):
                player['Bowling'] = str(player_bowl['Wickets']) + '-' + str(player_bowl['Runs'])
            elif player_bowl is None:
                player['Bowling'] = 'DNP'

            if isinstance(player['Batting'], type(None)):
                player['Batting'] = '-'
            if isinstance(player['Batting'], float):
                player['Batting'] = '-'
            if isinstance(player['Bowling'], type(None)):
                player['Bowling'] = '-'

            players.append([player, player_bat, player_bowl])

        new_player_overview = pd.DataFrame([player[0] for player in players])

        new_players = new_player_overview
    else:
        FTPUtils.log_event('Requested round (League {} - Round {}) has not been played, so no stats could be collected. {} players found.'.format(leagueid, round_n, len(new_players)), ind_level=ind_level)

    try:
        new_players.sort_values('Rating', ascending=False, inplace=True, ignore_index=True)
        del new_players['Fatg']
        del new_players['Initial']
        del new_players['BT']

        if not normalize_age:
            new_players['Age'] = FTPUtils.normalize_age_list(new_players['Age'], reverse=True)

        new_players['Nat'] = [FTPUtils.nationality_id_to_name_str(natid) for natid in new_players['Nat']]

    except KeyError:
        FTPUtils.log_event('No new players found in round ({}) in league {}'.format(round_n, leagueid), ind_level=ind_level)

    return new_players

    
def database_rating_increase_scatter(db_name, group1_db_entry=[46, 2], group2_db_entry=[46, 3], include_hidden_training=False):
    allplayers = FTPUtils.ratdif_from_weeks(db_name, group1_db_entry, group2_db_entry
                                                   )
    fig, ax = plt.subplots()
    if 'Training' in allplayers.columns and not include_hidden_training:
        allplayers = allplayers[allplayers['Training'] != 'Hidden']
    else:
        allplayers['Training'] = 'Not in table'
    unique_teams = list(set(allplayers['TeamID']))
    if len(unique_teams) < 10:
        colors = [plt.get_cmap('tab10').colors[n % 10] for n in range(len(unique_teams))]
    else:
        colors = [plt.get_cmap('tab20').colors[n % 20] for n in range(len(unique_teams))]
    scatter_colors = [colors[unique_teams.index(team)] for team in allplayers['TeamID']]
    legend_color_rects = [matplotlib.patches.Rectangle((0, 0),1,1,fc=color) for color in colors]
    ax.scatter(allplayers['Age'], allplayers['Ratdif'], c=scatter_colors)
    ax.legend(legend_color_rects, unique_teams)
    labeldata = []
    for pn in range(len(allplayers['PlayerID'])):
        age = FTPUtils.normalize_age_list([allplayers.iloc[pn]['Age']], True)[0]
        p_data = [allplayers.iloc[pn]['Player'], allplayers.iloc[pn]['PlayerID'], allplayers.iloc[pn]['Team'], allplayers.iloc[pn]['TeamID'], age, allplayers.iloc[pn]['Ratdif']]
        if 'Training' in allplayers.columns:
            p_data.append(allplayers.iloc[pn]['Training'])
        else:
            p_data.append('Not in table')
        labeldata.append(p_data)

    labels = ['Player: {} ({})\nTeam: {} ({})\nAge: {}\nRatdif: +{}\nTraining: {}'.format(player[0], player[1], player[2], player[3],
                                                                          player[4], player[5], player[6]) for player in labeldata]

    cursor = mplcursors.cursor(ax, hover=True)
    cursor.connect("add", lambda sel: sel.annotation.set_text(labels[sel.target.index]))
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(20, integer=True))
    plt.grid(axis='x', linestyle='--', c='k', linewidth=1, alpha=0.4)
    plt.ylim([0, max(allplayers['Ratdif']) + 100])
    plt.show()
    
def team_increase_quiver(db_name, group1_entry, group2_entry):
    db_config = PlayerDatabase.load_config_file(db_name)
    db_team_ids = db_config[1]['teamids']
    group1_p = []
    group2_p = []
    g1s, g1w = group2_entry
    g2s, g2w = group2_entry
    for team_id in db_team_ids:
        group1_team = PlayerDatabase.load_entry(db_name, g1s, g1w, team_id, normalize_age=True)  # pd.concat(w13players)
        group2_team = PlayerDatabase.load_entry(db_name, g2s, g2w, team_id, normalize_age=True)  # pd.concat(w10players)
        x1, x2 = FTPUtils.match_pg_ids(group1_team, group2_team, returnsortcolumn='Ratdif')
        group1_p.append(x1)
        group2_p.append(x2)

    average_a, average_r, average_rd = [], [], []

    for region in group2_p:
        region_players = np.array([len(region) for player in range(len(region))])
        average_a.append(sum(region['Age']) / len(region))
        average_r.append(sum(region['Rating']) / len(region))
        average_rd.append(sum(region['Ratdif']) / len(region))

    age_range = max(average_a) - min(average_a)
    rating_range = max(average_r) - min(average_r)
    aspect_ratio = rating_range / age_range

    fig, ax = plt.subplots()
    qp = ax.quiver(average_a, average_r, average_rd, [aspect_ratio for x in range(len(average_a))], pivot='tail', color=[FTPUtils.nationality_id_to_rgba_color(natid) for natid in range(1, 19)])
    for n, data in enumerate(zip(average_a, average_r)):
        age, wage = data[0], data[1]
        ax.quiverkey(qp, age, wage, 1, color=FTPUtils.nationality_id_to_rgba_color(n+1), label='{} ({})'.format(FTPUtils.nationality_id_to_name_str((n+1), full_name=True), len(group2_p[n])), labelpos='S', coordinates='data')

    ax.set_title('{} Rating / Age of Long Term Players'.format(db_name))
    ax.set_xlabel('Average Age')
    ax.set_ylabel('Average Rating')
    fig.show()

    
def training_age_increase_plot(training_data, training_names):
    for k in training_data.keys():
        print(k, len(pd.concat(training_data[k])) if len(training_data[k]) != 0 else 0)

    for training in training_names:
        training_ages = [t for t in training_data[training].keys()]
        training_average_increase = np.empty(len(training_data[training]))
        training_average_increase_max = np.empty(len(training_data[training]))
        training_average_increase_min = np.empty(len(training_data[training]))

        for n, age in enumerate(training_data[training].keys()):
            avg_increase = sum(training_data[training][age]['Ratdif']) / len(training_data[training][age]['Ratdif'])

            training_average_increase[n] = avg_increase
            training_average_increase_min[n] = min(training_data[training][age]['Ratdif'])
            training_average_increase_max[n] = max(training_data[training][age]['Ratdif'])

        plt.plot(training_ages, training_average_increase)

        plt.fill_between(training_ages, training_average_increase_max, training_average_increase_min, alpha=0.5)


    plt.legend(training_names)
    plt.axis([15, 33, 0, 500])
    plt.xticks(range(16, 33), range(16, 33))
    plt.show()