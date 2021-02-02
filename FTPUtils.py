import PlayerDatabase
import PresentData

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
SKILL_LEVELS = ['atrocious', 'dreadful', 'poor', 'ordinary', 'average', 'reasonable', 'capable', 'reliable', 'accomplished', 'expert', 'outstanding', 'spectacular', 'exceptional', 'world class', 'elite', 'legendary']

def log_event(logtext, logtype='full', logfile='default', ind_level=0):
    current_time = datetime.datetime.now()
    if type(logfile) == str:
        logfile = [logfile]

    for logf in logfile:
        if logf == 'default':
            logf = 'ftp_archiver_output_history.log'
        if logtype in ['full', 'console']:
            print('[{}] '.format(current_time.strftime('%d/%m/%Y-%H:%M:%S')) + '\t' * ind_level + logtext)
        if logtype in ['full', 'file']:
            with open(logf, 'a') as f:
                f.write('[{}] '.format(current_time.strftime('%d/%m/%Y-%H:%M:%S')) + logtext + '\n')

        logtype = 'file' # to prevent repeated console outputs when multiple logfiles are specified


def check_login(use_browser=False, return_browser=False, reload_homepage=False):
    global browser
    if use_browser:
        browser = use_browser

    if isinstance(browser, type(None)) or not browser:
        with open('credentials.txt', 'r') as f:
            credentials = f.readline().split(',')
        browser = login(credentials)
        if return_browser:
            return browser
        else:
            return True
    else:
        last_page_load = datetime.datetime.strptime(str(browser.response.headers['Date'])[:-4]+'+0000', '%a, %d %b %Y %H:%M:%S%z')
        if reload_homepage:
            browser.open('https://www.fromthepavilion.org/club.htm?teamId=4791')
        browser_page = str(browser.parsed)
        if (datetime.datetime.now(datetime.timezone.utc) - last_page_load) > datetime.timedelta(minutes=10) or 'Watch the commentary or scorecard of your' in browser_page:
            log_event('Browser timed out...')
            with open('credentials.txt', 'r') as f:
                credentials = f.readline().split(',')
            browser = login(credentials)
            browser.open('https://www.fromthepavilion.org/club.htm?teamId=4791')
            if return_browser:
                return browser
            else:
                return True
        else:
            if return_browser:
                return browser
            else:
                return True


def login(credentials, logtype='full', logfile='default', use_browser=False):
    global browser
    if use_browser:
        browser = use_browser

    browser = RoboBrowser(history=True)
    browser.open('http://www.fromthepavilion.org/')
    form = browser.get_form(action='securityCheck.htm')

    form['j_username'] = credentials[0]
    form['j_password'] = credentials[1]

    browser.submit_form(form)
    if check_login(browser, return_browser=False):
        logtext = 'Successfully logged in as user {}.'.format(credentials[0])
        log_event(logtext, logtype=logtype, logfile=logfile)
        return browser
    else:
        logtext = 'Failed to log in as user {}'.format(credentials[0])
        log_event(logtext, logtype=logtype, logfile=logfile)
        return None

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


def get_player_page(player_id, use_browser=False):
    global browser
    if use_browser:
        browser = use_browser
    browser = check_login(browser, return_browser=True)

    browser.open('https://www.fromthepavilion.org/player.htm?playerId={}'.format(player_id))
    page = str(browser.parsed)

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

def get_team_players(teamid, age_group='all', squad_type='domestic_team', to_file = False, normalize_age=False, additional_columns=False, ind_level=0, use_browser=False):
    global browser
    if use_browser:
        browser = use_browser
    browser = check_login(browser, return_browser=True)

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
    browser.open(squad_url)
    page_tmp = str(browser.parsed)
    page_tmp = page_tmp[page_tmp.index('middle-noright'):]
    team_name = page_tmp[page_tmp.index('teamId={}">'.format(teamid)):page_tmp.index('teamId={}">'.format(teamid))+30]
    team_name = team_name.split('>')[1].split('<')[0]

    playerids = []
    team_players = pd.DataFrame()

    try:
        log_event('Downloading players from teamid {}'.format(teamid, squad_url), ind_level=ind_level)
        team_players = pd.read_html(str(browser.parsed))[0]
        playerids = [x[9:] for x in re.findall('playerId=[0-9]+', str(browser.parsed))][::2]
    except ValueError:
        log_event('Error saving teamid: {}. No dataframe found in url'.format(teamid), ind_level=ind_level)
        raise ValueError

    team_players.insert(loc=0, column='TeamID', value=teamid)
    team_players.insert(loc=2, column='Team', value=team_name)
    team_players.insert(loc=0, column='PlayerID', value=playerids)
    team_players['Wage'] = team_players['Wage'].str.replace('\D+', '')

    if squad_type == 'domestic_team':
        player_nationalities = [x[-2:].replace('=', '') for x in re.findall('regionId=[0-9]+', str(browser.parsed))][-len(playerids):]
        team_players['Nat'] = player_nationalities

        #log_event('Saved {} players to {}'.format(len(playerids), to_file), ind_level=1)

    if normalize_age:
        team_players['Age'] = normalize_age_list(team_players['Age'])

    if additional_columns:
        team_players = PlayerDatabase.add_player_columns(team_players, additional_columns, ind_level=ind_level+1)

    team_players.drop(columns=[x for x in ['#', 'Unnamed: 18'] if x in team_players.columns], inplace=True)

    if to_file:
        pd.DataFrame.to_csv(team_players, to_file, index=False, float_format='%.2f')

    return team_players

def get_current_ftp_time(return_type='inttuple'):
    current_time = datetime.datetime.utcnow()
    if return_type == 'datetime':
        return current_time
    elif return_type == 'inttuple':
        return (int(current_time.weekday()), int(current_time.hour), (current_time.minute))


def get_event_runtime_from_country(country_name, event, return_type='datetime', use_browser=False):
    global browser
    if use_browser:
        browser = use_browser
    browser = check_login(browser, return_browser=True)

    country_offsets = [('Australia', [0, 0]), ('Bangladesh', [2, 0]), ('India', [4, 30]), ('Pakistan', [5, 0]), ('Sri Lanka', [5, 30]), ('South Africa', [8, 0]), ('Scotland', [9, 0]), ('England', [10, 0]), ('Ireland', [11, 30]), ('Netherlands', [12, 0]), ('Zimbabwe', [13, 0]), ('West Indies', [15, 0]), ('Canada', [16, 0]), ('New Zealand', [22, 0])]

    selected_offset = country_offsets[[x[0] for x in country_offsets].index(country_name)]
    current_time = get_current_ftp_time('inttuple')








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


def get_league_teamids(leagueid, league_format='league', knockout_round=None, ind_level=0, use_browser=False):
    global browser
    if use_browser:
        browser = check_login(browser, return_browser=True)

    if league_format == 'knockout':
        if not isinstance(knockout_round, None):
            round_n = knockout_round
        else:
            round_n = 1
    else:
        round_n = 1

    log_event('Searching for teamids in leagueid {} - round {}'.format(leagueid, round_n, ind_level=ind_level))
    gameids = get_league_gameids(leagueid, round_n=round_n, league_format=league_format)
    teamids = []
    for gameid in gameids:
        team1, team2 = get_game_teamids(gameid, ind_level=ind_level+1)
        teamids.append(team1)
        teamids.append(team2)

    log_event('Successfully found {} teams.'.format(len(teamids)), ind_level=ind_level)

    return teamids


def get_league_gameids(leagueid, round_n='latest', league_format='league', use_browser=False):
    global browser
    if use_browser:
        browser = use_browser
    browser = check_login(browser, return_browser=True)

    if round_n == 'latest':
        round_n = 1

    if league_format == 'league':
        browser.open('https://www.fromthepavilion.org/leaguefixtures.htm?lsId={}'.format(leagueid))
        league_page = str(browser.parsed)
        league_rounds = int(max([int(r[6:]) for r in re.findall('Round [0-9]+', league_page)]))
        gameids = [g[7:] for g in re.findall('gameId=[0-9]+', league_page)]

        unique_gameids = []
        for g in gameids:
            if g not in unique_gameids:
                unique_gameids.append(g)

        games_per_round = len(unique_gameids) // league_rounds

        round_start_ind = games_per_round*(round_n-1)
        round_end_ind = round_start_ind + games_per_round

        return unique_gameids[round_start_ind:round_end_ind]

    elif league_format == 'knockout':
        browser.open('https://www.fromthepavilion.org/cupfixtures.htm?cupId={}&currentRound=true'.format(leagueid))
        fixtures = pd.read_html(str(browser.parsed))[0]
        for n, roundname in enumerate(fixtures.columns):
            if roundname[:7] == 'Round {}'.format(round_n):
                round_column_name = roundname
                break

        games_on_page = re.findall('gameId=.{0,150}', str(browser.parsed))
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

        return requested_game_ids



def get_game_scorecard_table(gameid, ind_level=0, use_browser=False):
    global browser
    if use_browser:
        browser = use_browser
    browser = check_login(browser, return_browser=True)

    browser.open('https://www.fromthepavilion.org/scorecard.htm?gameId={}'.format(gameid))
    scorecard_tables = pd.read_html(str(browser.parsed))
    page_teamids = [''.join([c for c in x if c.isdigit()]) for x in re.findall('teamId=[0-9]+', str(browser.parsed))]
    home_team_id, away_team_id = page_teamids[21], page_teamids[22]
    scorecard_tables[-2].iloc[0][1] = home_team_id
    scorecard_tables[-2].iloc[1][1] = away_team_id

    log_event('Downloaded scorecard for game {}'.format(gameid), ind_level=ind_level)

    return scorecard_tables


def get_game_teamids(gameid, ind_level=0, use_browser=False):
    global browser
    if use_browser:
        browser = use_browser
    browser = check_login(browser, return_browser=True)

    browser.open('https://www.fromthepavilion.org/gamedetails.htm?gameId={}'.format(gameid))
    page_teamids = [''.join([c for c in x if c.isdigit()]) for x in re.findall('teamId=[0-9]+', str(browser.parsed))]
    home_team_id, away_team_id = page_teamids[22], page_teamids[23]

    log_event('Found teams for game {} - {} vs {}'.format(gameid, home_team_id, away_team_id), ind_level=ind_level)

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

def catagorise_training(db_time_pairs, min_data_include=1, std_highlight_limit=1, max_weeks_between_training=0):
    '''
    Catagorises a set of players from database/week pairs into a dictionary of
    lists sorted by training/age. Used to view e.g. The average ratdif of all
    22 year old players trained in Fielding

        db_time_pair_element = (db_name, dbt1, dbt2)
        dbt1 = (season, week)

        min_data_include = minimum points of data to plot for an age
        std_highlight_label = how wide the highlighted section should be for an age, by std
    '''
    training_data_collection = []
    for dbtpair in db_time_pairs:
        training_data_week = ratdif_from_weeks(dbtpair[0], dbtpair[1], dbtpair[2])
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