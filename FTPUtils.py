import PlayerDatabase
import PresentData
import CoreUtils

browser = CoreUtils.browser

import os
import re
import pandas as pd
import numpy as np
import matplotlib
from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})
import seaborn as sns; sns.set_theme(color_codes=True)
from math import floor, isnan
pd.options.mode.chained_assignment = None  # default='warn'

SKILL_LEVELS = ['atrocious', 'dreadful', 'poor', 'ordinary', 'average', 'reasonable', 'capable', 'reliable', 'accomplished', 'expert', 'outstanding', 'spectacular', 'exceptional', 'world class', 'elite', 'legendary']


def nationality_id_to_rgba_color(natid):
    nat_colors = ['darkblue', 'red', 'forestgreen', 'black', 'mediumseagreen', 'darkkhaki', 'maroon', 'firebrick', 'darkgreen', 'firebrick', 'tomato', 'royalblue', 'brown', 'darkolivegreen', 'olivedrab', 'purple', 'lightcoral', 'darkorange']

    return matplotlib.colors.to_rgba(nat_colors[natid-1])


def nationality_id_to_name_str(natid, full_name=False):
    natid = int(natid)
    nat_name_short = ['AUS', 'ENG', 'IND', 'NZL', 'PAK', 'SA', 'WI', 'SRI', 'BAN', 'ZWE', 'CAN', 'USA', 'KEN', 'SCO', 'IRE', 'UAE', 'BER', 'NL']
    nat_name_long = ['Australia', 'England', 'India', 'New Zealand', 'Pakistan', 'South Africa', 'West Indies', 'Sri Lanka', 'Bangladesh', 'Zimbabwe', 'Canada', 'USA', 'Kenya', 'Scotland', 'Ireland', 'UAE', 'Bermuda', 'Netherlands']

    return nat_name_long[natid-1] if full_name else nat_name_short[natid-1]


def skill_word_to_index(skill_w, skill_word_type='full'):
    SKILL_LEVELS_FULL = ['atrocious', 'dreadful', 'poor', 'ordinary', 'average', 'reasonable', 'capable', 'reliable', 'accomplished', 'expert', 'outstanding', 'spectacular', 'exceptional', 'world class', 'elite', 'legendary']
    SKILL_LEVELS_SHORT = ['atroc', 'dread', 'poor', 'ordin', 'avg', 'reas', 'capab', 'reli', 'accom', 'exprt', 'outs', 'spect', 'excep', 'wclas', 'elite', 'legen']

    if str(skill_w) == 'nan':
        return -1

    if skill_word_type == 'full':
        skill_n = SKILL_LEVELS_FULL.index(skill_w)
    elif skill_word_type == 'short':
        skill_n = SKILL_LEVELS_SHORT.index(skill_w)
    else:
        skill_n = -1

    return skill_n


def get_player_page(player_id):
    browser.rbrowser.open('https://www.fromthepavilion.org/player.htm?playerId={}'.format(player_id))
    page = str(browser.rbrowser.parsed)

    return page


def get_player_spare_ratings(player_df, col_name_len='full'):
    skill_rating_sum = 0
    for skill in ['Bat', 'Bowl', 'Keep', 'Field', 'End', 'Tech', 'Pow' if 'Pow\'' in [str(x) for x in player_df.axes][0] else 'Power']:
        player_level = player_df[skill]
        if str(player_level) == 'nan':
            return 'Unknown'
        skill_n = skill_word_to_index(player_level, col_name_len)
        skill_rating_sum += 500 if skill_n == 0 else 1000 * skill_n

    return player_df['Rating'] - skill_rating_sum

def get_team_players(teamid, age_group='all', squad_type='domestic_team', to_file = False, normalize_age=False, additional_columns=False, overwrite_method='append', ind_level=0):
    if int(teamid) in range(3001, 3019) or int(teamid) in range(3021, 3039) and squad_type == 'domestic_team':
        squad_type = 'national_team'

    if age_group == 'all':
        age_group = 0
    elif age_group == 'seniors':
        age_group = 1
    elif age_group == 'youths':
        age_group = 2

    if squad_type == 'domestic_team':
        squad_url = 'https://www.fromthepavilion.org/seniors.htm?squadViewId=2&orderBy=&teamId={}&playerType={}'
    elif squad_type == 'national_team':
        squad_url = 'https://www.fromthepavilion.org/natsquad.htm?squadViewId=2&orderBy=15&teamId={}&playerType={}'

    squad_url = squad_url.format(teamid, age_group)
    browser.rbrowser.open(squad_url)
    page_tmp = str(browser.rbrowser.parsed)
    page_tmp = page_tmp[page_tmp.index('middle-noright'):]
    team_name = page_tmp[page_tmp.index('teamId={}">'.format(teamid)):page_tmp.index('teamId={}">'.format(teamid))+30]
    team_name = team_name.split('>')[1].split('<')[0]

    playerids = []
    team_players = pd.DataFrame()

    try:
        CoreUtils.log_event('Downloading players from teamid {}'.format(teamid, squad_url), ind_level=ind_level)
        team_players = pd.read_html(str(browser.rbrowser.parsed))[0]
        playerids = [x[9:] for x in re.findall('playerId=[0-9]+', str(browser.rbrowser.parsed))][::2]
    except ValueError:
        CoreUtils.log_event('Error saving teamid: {}. No dataframe found in url'.format(teamid), ind_level=ind_level)
        raise ValueError

    team_players.insert(loc=0, column='TeamID', value=teamid)
    team_players.insert(loc=2, column='Team', value=team_name)
    team_players.insert(loc=0, column='PlayerID', value=playerids)
    team_players['Wage'] = team_players['Wage'].str.replace('\D+', '')

    if squad_type == 'domestic_team':
        player_nationalities = [x[-2:].replace('=', '') for x in re.findall('regionId=[0-9]+', str(browser.rbrowser.parsed))][-len(playerids):]
        team_players['Nat'] = player_nationalities

        #CoreUtils.log_event('Saved {} players to {}'.format(len(playerids), to_file), ind_level=1)

    if normalize_age:
        team_players['Age'] = normalize_age_list(team_players['Age'])

    if additional_columns:
        team_players = PlayerDatabase.add_player_columns(team_players, additional_columns, ind_level=ind_level+1)

    team_players.drop(columns=[x for x in ['#', 'Unnamed: 18'] if x in team_players.columns], inplace=True)

    if to_file:
        if os.path.exists(to_file):
            old_file = pd.read_csv(to_file, float_precision=2)
        else:
            old_file = pd.DataFrame()
        if overwrite_method == 'append':
            file_data = pd.concat([old_file, team_players])
            file_data = file_data.sort_values(['PlayerID', 'Rating'], ascending=True).drop_duplicates(['PlayerID', 'Rating'], keep='first')
        elif overwrite_method == 'overwrite':
            file_data = team_players

        pd.DataFrame.to_csv(file_data, to_file, index=False, float_format='%.2f')

    return team_players

def get_team_page(teamid):
    browser.rbrowser.open('https://www.fromthepavilion.org/club.htm?teamId={}'.format(teamid))
    page = str(browser.rbrowser.parsed)

    return page

def get_team_name(teamid, page=False):
    if not page:
        page = get_team_page(teamid)

    page = page[page.index('Add this team to your bookmarks'):]
    name_start_str = str(teamid) + '">'
    name_end_str = '</a> &gt;&gt; Club'
    team_name = page[page.index(name_start_str) + len(name_start_str):page.index(name_end_str)]

    return team_name

def get_team_region(teamid, return_type='regionid', page=False):
    if not page:
        browser.rbrowser.open('https://www.fromthepavilion.org/club.htm?teamId={}'.format(teamid))
        page = str(browser.rbrowser.parsed)

    country_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 18]
    senior_country_ids = [id + 3000 for id in country_ids]
    youth_country_ids = [id + 3020 for id in country_ids]

    if teamid in senior_country_ids + youth_country_ids:
        return teamid

    truncated_page = page[page.index('<th>Country</th>'):][:200]
    country_id = int(''.join([x for x in re.findall('regionId=[0-9]+', truncated_page)[0] if x.isdigit()]))

    if return_type == 'regionid':
        return country_id
    elif return_type == 'name':
        return nationality_id_to_name_str(country_id, True)

def country_game_start_time(region_id):
    region_names = ['Australia', 'England', 'India', 'New Zealand', 'Pakistan', 'South Africa', 'West Indies', 'Sri Lanka', 'Bangladesh', 'Zimbabwe', 'Canada', 'Scotland', 'Ireland', 'Netherlands']
    country_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 18]
    region_starttimes = ['00:00', '10:00', '04:30', '22:00', '05:00', '08:00', '15:00', '05:30', '02:00', '13:00', '16:00', '09:00', '11:30', '12:00']

    if isinstance(type(region_id), type(int)):
        return region_starttimes[country_ids.index(region_id)]
    elif isinstance(type(region_id), type(str)):
        return region_starttimes[region_names.index(region_id)]

def get_player_wage(player_id, page=False, normalize_wage=False):
    if not page:
        page = get_player_page(player_id)

    player_discounted_wage = int(''.join([x for x in re.findall('[0-9]+,[0-9]+ wage' if bool(re.search('[0-9]+,[0-9]+ wage', page)) else '[0-9]+ wage', page)[0] if x.isdigit()]))
    try:
        player_discount = float(re.findall('[0-9]+\% discount', page)[0][:-10]) / 100
    except: #Discount is by .5
        player_discount = float(re.findall('[0-9]+\.[0-9]+\% discount', page)[0][:-10]) / 100
    player_real_wage = int(player_discounted_wage / (1-player_discount))

    if normalize_wage:
        return player_real_wage
    else:
        return player_discounted_wage

def get_player_teamid(player_id, page=False):
    if not page:
        page = get_player_page(player_id)

    team_id = re.findall('teamId=[0-9]+', page)[-2]

    return team_id

def get_player_nationality(player_id, page=False):
    if not page:
        page = get_player_page(player_id)

    player_nationality_id = re.findall('regionId=[0-9]+', page)[-1][9:]

    return player_nationality_id


def get_player_skillshifts(player_id, page=False):
    if not page:
        page = get_player_page(player_id)

    skill_names = ['Experience', 'Captaincy', 'Batting', 'Endurance', 'Bowling', 'Technique', 'Keeping', 'Power', 'Fielding']
    skills = re.findall('class="skills".{0,200}', page)
    skills = skills[:2] + skills[-7:]
    skillshifts = {}
    for skill_str, skill_name in zip(skills, skill_names):
        skill_level = None
        for possible_skill in SKILL_LEVELS:
            if possible_skill in skill_str:
                skill_level = possible_skill
                break

        if 'skillup' in skill_str:
            skillshifts[skill_name] = 1
        elif 'skilldown' in skill_str:
            skillshifts[skill_name] = -1

    return skillshifts


def get_player_summary(player_id, page=False):
    if not page:
        page = get_player_page(player_id)

    summary_names = ['BattingSum', 'BowlingSum', 'KeepingSum', 'AllrounderSum']
    skills = re.findall('class="skills".{0,200}', page)
    skills = skills[2:-7]
    summary_dir = {}
    for skill_str, summary_name in zip(skills, summary_names):
        skill_level = None
        for possible_skill in SKILL_LEVELS:
            if possible_skill in skill_str:
                skill_level = possible_skill
                break

        summary_dir[summary_name] = skill_level

    return summary_dir


def get_league_teamids(leagueid, league_format='league', knockout_round=None, ind_level=0):
    if league_format == 'knockout':
        if not isinstance(knockout_round, None):
            round_n = knockout_round
        else:
            round_n = 1
    else:
        round_n = 1

    CoreUtils.log_event('Searching for teamids in leagueid {} - round {}'.format(leagueid, round_n, ind_level=ind_level))
    gameids = get_league_gameids(leagueid, round_n=round_n, league_format=league_format)
    teamids = []
    for gameid in gameids:
        team1, team2 = get_game_teamids(gameid, ind_level=ind_level+1)
        teamids.append(team1)
        teamids.append(team2)

    CoreUtils.log_event('Successfully found {} teams.'.format(len(teamids)), ind_level=ind_level)

    return teamids


def get_league_gameids(leagueid, round_n='latest', league_format='league'):
    if round_n == 'latest':
        round_n = 1

    if league_format == 'league':
        browser.rbrowser.open('https://www.fromthepavilion.org/leaguefixtures.htm?lsId={}'.format(leagueid))
        league_page = str(browser.rbrowser.parsed)
        league_rounds = int(max([int(r[6:]) for r in re.findall('Round [0-9]+', league_page)]))
        gameids = [g[7:] for g in re.findall('gameId=[0-9]+', league_page)]

        unique_gameids = []
        for g in gameids:
            if g not in unique_gameids:
                unique_gameids.append(g)

        games_per_round = len(unique_gameids) // league_rounds

        round_start_ind = games_per_round*(round_n-1)
        round_end_ind = round_start_ind + games_per_round

        game_ids = unique_gameids[round_start_ind:round_end_ind]

    elif league_format == 'knockout':
        browser.rbrowser.open('https://www.fromthepavilion.org/cupfixtures.htm?cupId={}&currentRound=true'.format(leagueid))
        fixtures = pd.read_html(str(browser.rbrowser.parsed))[0]
        for n, roundname in enumerate(fixtures.columns):
            if roundname[:7] == 'Round {}'.format(round_n):
                round_column_name = roundname
                break

        games_on_page = re.findall('gameId=.{0,150}', str(browser.rbrowser.parsed))
        requested_games = []
        for game in fixtures[round_column_name][::2 ** (round_n - 1)]:
            team1, team2 = game.split('vs')
            if bool(re.match('.* \([0-9]+\)', team1)):
                team1 = team1[:team1.index(' (')]
            if bool(re.match('.* \([0-9]+\)', team2)):
                team2 = team2[:team2.index(' (')]

            requested_games.append([team1, team2])

        requested_game_ids = []
        for game in games_on_page:
            game = game.replace(' &amp; ', ' & ')
            for team1, team2 in requested_games:
                if team1 in game and team2 in game:
                    requested_game_ids.append(''.join([c for c in game[:game.index('>')] if c.isdigit()]))

        game_ids = requested_game_ids

    CoreUtils.log_event('Found {} games in round {} of {}'.format(len(game_ids), round_n, leagueid))

    return game_ids


def get_game_scorecard_table(gameid, ind_level=0):
    browser.rbrowser.open('https://www.fromthepavilion.org/scorecard.htm?gameId={}'.format(gameid))
    scorecard_tables = pd.read_html(str(browser.rbrowser.parsed))
    page_teamids = [''.join([c for c in x if c.isdigit()]) for x in re.findall('teamId=[0-9]+', str(browser.rbrowser.parsed))]
    home_team_id, away_team_id = page_teamids[21], page_teamids[22]
    scorecard_tables[-2].iloc[0][1] = home_team_id
    scorecard_tables[-2].iloc[1][1] = away_team_id

    CoreUtils.log_event('Downloaded scorecard for game {}'.format(gameid), ind_level=ind_level)

    return scorecard_tables


def get_game_teamids(gameid, ind_level=0):
    browser.rbrowser.open('https://www.fromthepavilion.org/gamedetails.htm?gameId={}'.format(gameid))
    page_teamids = [''.join([c for c in x if c.isdigit()]) for x in re.findall('teamId=[0-9]+', str(browser.rbrowser.parsed))]
    home_team_id, away_team_id = page_teamids[22], page_teamids[23]

    CoreUtils.log_event('Found teams for game {} - {} vs {}'.format(gameid, home_team_id, away_team_id), ind_level=ind_level)

    return (home_team_id, away_team_id)


def normalize_age_list(player_ages, reverse=False):
    min_year = min([int(str(age).split('.')[0]) for age in player_ages])
    max_year = max([int(str(age).split('.')[0]) for age in player_ages]) + 1
    year_list = [year for year in range(min_year, max_year)]

    nor_agelist = [] #normalized
    rea_agelist = [] #real / string / 00

    for year in year_list:
        for week in range(0, 15):
            frac_end = str(week / 15).split('.')[1]
            normalized_age = str(year) + '.' + frac_end[:5]

            if week < 10:
                if week == 0:
                    real_age = str(year) + '.00'
                else:
                    real_age = str(year) + '.0' + str(week)
            else:
                real_age = str(year) + '.' + str(week)

            nor_agelist.append(normalized_age)
            rea_agelist.append(real_age)

    new_ages = []
    for p_age in player_ages:
        if reverse:
            try:
                age_ind = nor_agelist.index(str(p_age).split('.')[0] + '.' + str(p_age).split('.')[1][:5])
                new_age = rea_agelist[age_ind]
                new_ages.append(new_age)
            except ValueError:
                new_ages.append('AgeError:Unexpected')
        else:
            if str(p_age).split('.')[1] == '1':
                p_age = str(p_age).split('.')[0] + '.10'
            if str(p_age).split('.')[1] == '0':
                p_age = str(p_age).split('.')[0] + '.00'
            new_ages.append(nor_agelist[rea_agelist.index(str(p_age))])

    return [str(age) if reverse else float(age) for age in new_ages]

def generate_db_time_pairs(database_entries='all'):
    if database_entries == 'all':
        database_entries = PlayerDatabase.database_entries_from_directory('working_directory')

    dbt_pairs = []
    for database_name in database_entries.keys():
        sequential_entries = []
        for season in database_entries[database_name].keys():
            for week in database_entries[database_name][season]:
                sequential_entries.append(season + '.' + week)

        for entry in range(len(sequential_entries)-1):
            entryminus1 = [int(''.join([n for n in x if n.isdigit()])) for x in sequential_entries[entry-1].split('.')]
            entry = [int(''.join([n for n in x if n.isdigit()])) for x in sequential_entries[entry].split('.')]
            dbt_pairs.append((database_name, entryminus1, entry))

    return dbt_pairs

def catagorise_training(db_time_pairs='all', min_data_include=5, std_highlight_limit=1, max_weeks_between_training=1):
    '''
    Catagorises a set of players from database/week pairs into a dictionary of
    lists sorted by training/age. Used to view e.g. The average ratdif of all
    22 year old players trained in Fielding

        db_time_pair_element = (db_name, dbt1, dbt2)
        dbt1 = (season, week)

        min_data_include = minimum points of data to plot for an age
        std_highlight_label = how wide the highlighted section should be for an age, by std
    '''
    if db_time_pairs == 'all':
        db_time_pairs = generate_db_time_pairs(database_entries='all')

    db_time_pairs = [dbt for dbt in db_time_pairs if (abs((dbt[2][0] * 15) + dbt[2][1]) - ((dbt[1][0] * 15) + dbt[1][1])) <= max_weeks_between_training]

    training_data_collection = []
    for dbtpair in db_time_pairs:
        training_data_week = ratdif_from_weeks(dbtpair[0], dbtpair[1], dbtpair[2])
        if 'Training' in training_data_week.columns:
            training_data_week = training_data_week[(training_data_week['Training'] != 'Rest') & (training_data_week['Ratdif'] > 0)]
            non_hidden_training = training_data_week[training_data_week['Training'] != 'Hidden']

            training_data_collection.append(non_hidden_training)

    all_training_data = pd.concat(training_data_collection)
    all_training_data.drop_duplicates(['PlayerID', 'Rating'], inplace=True)
    training_type_dict = {}
    for trainingtype in ['Batting', 'Bowling', 'Keeping', 'Keeper-Batsman', 'All-rounder', 'Fielding', 'Fitness',
                             'Batting Technique', 'Bowling Technique', 'Strength', 'Rest']:
        training_type_data = all_training_data[all_training_data['Training'] == trainingtype]
        training_type_data['Age'] = [int(floor(a)) for a in list(training_type_data['Age'])]
        training_type_age_dict = {}
        for age in range(
                int(min(np.append(training_type_data.Age, int(max(np.append(training_type_data.Age, 16)))))),
                int(max(np.append(training_type_data.Age, 16)))):
            data = training_type_data[training_type_data['Age'] == age]
            if len(data) >= min_data_include:
                data = data[np.abs(data.Ratdif - data.Ratdif.mean()) <= (
                            std_highlight_limit * training_data_week.Ratdif.std())]
                    # keep only values within +- 3 std of ratdif

                training_type_age_dict[age] = data

        training_type_dict[trainingtype] = training_type_age_dict

    return training_type_dict

def ratdif_from_weeks(db_name, dbt1, dbt2, average_ratdif=True):
    db_config = PlayerDatabase.load_config_file(db_name)
    db_team_ids = db_config[1]['teamids']
    w2p = []
    w1p = []
    for region_id in db_team_ids:
        team_w1p = PlayerDatabase.load_entry(db_name, dbt1[0], dbt1[1], region_id, normalize_age=True)  # pd.concat(w13players)
        team_w2p = PlayerDatabase.load_entry(db_name, dbt2[0], dbt2[1], region_id, normalize_age=True)  # pd.concat(w10players)
        x1, x2 = PlayerDatabase.match_pg_ids(team_w1p, team_w2p, returnsortcolumn='Ratdif')
        w1p.append(x1)
        w2p.append(x2)

    allplayers = pd.concat(w2p, ignore_index=True).T.drop_duplicates().T
    weeks_of_training = dbt2[1] - dbt1[1]

    allplayers['TrainingWeeks'] = weeks_of_training
    allplayers['DataTime'] = 's{}w{}'.format(dbt2[0], dbt2[1])
    if average_ratdif:
        if weeks_of_training > 1:
            allplayers['Ratdif'] = np.divide(allplayers['Ratdif'], weeks_of_training)

    return allplayers
