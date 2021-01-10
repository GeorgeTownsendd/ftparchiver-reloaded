import ftputils as FTPUtils
import ftppresentation as PresentData

import os
import time
import datetime
import re
import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
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

GLOBAL_SETTINGS = ['name', 'description', 'database_type', 'w_directory', 'archive_days', 'scrape_time', 'additional_columns']
ORDERED_SKILLS = [['ID', 'Player', 'Nat', 'Deadline', 'Current Bid'], ['Rating', 'Exp', 'Talents', 'BT'], ['Bat', 'Bowl', 'Keep', 'Field'], ['End', 'Tech', 'Pow']]

def generate_config_file(database_settings, additional_settings):
    if database_settings['w_directory'][-1] != '/':
        database_settings['w_directory'] += '/'
    conf_file = database_settings['w_directory'] + database_settings['name'] + '.config'

    if not os.path.exists(database_settings['w_directory']):
        os.makedirs(database_settings['w_directory'])
        FTPUtils.FTPUtils.log_event('Creating directory {}'.format(database_settings['w_directory']), logfile=['default', database_settings['w_directory'] + database_settings['name'] + '.log'])

    if os.path.isfile(conf_file):
        shutil.copy(conf_file, conf_file + '.old')
        FTPUtils.FTPUtils.log_event('Config file {} already exisits, copying to {} and creating new file'.format(conf_file, conf_file + '.old'), logfile=['default', database_settings['w_directory'] + database_settings['name'] + '.log'])

    with open(conf_file, 'w') as f:
        for setting in GLOBAL_SETTINGS:
            try:
                f.write('{}:{}\n'.format(setting, database_settings[setting]))
            except KeyError:
                if setting in ['archive_days', 'scrape_time'] and database_settings['database_type'] == 'transfer_market_search':
                    pass
                else:
                    raise KeyError

        for setting in additional_settings.keys():
            if setting == 'teamids':
                f.write('{}:{}\n'.format(setting, ','.join([str(teamid) for teamid in additional_settings[setting]])))
            else:
                f.write('{}:{}\n'.format(setting, additional_settings[setting]))

    FTPUtils.log_event('Successfully created config file {}'.format(conf_file), logfile=['default', database_settings['w_directory'] + database_settings['name'] + '.log'])


def load_config_file(config_file_directory):
    if '/' not in config_file_directory:
        config_file_directory = config_file_directory + '/' + config_file_directory + '.config'

    database_settings = {}
    additional_settings = {}
    all_file_values = {}
    with open(config_file_directory, 'r') as f:
        config_file_lines = [line.rstrip() for line in f.readlines()]
        for n, line in enumerate(config_file_lines):
            setting_name, value = line.split(':', 1)
            if setting_name in ['additional_columns', 'archive_days', 'teamids']:
                all_file_values[setting_name]= value.split(',')
            elif setting_name in ['scrape_time']:
                all_file_values[setting_name] = value.split(':')
            else:
                all_file_values[setting_name] = value

    for setting_name in all_file_values.keys():
        if setting_name in GLOBAL_SETTINGS:
            database_settings[setting_name] = all_file_values[setting_name]
        else:
            additional_settings[setting_name] = all_file_values[setting_name]

    return database_settings, additional_settings


def player_search(search_settings={}, to_file=False, search_type='transfer_market', normalize_age=False, additional_columns=False, return_sort_column=False, ind_level=0, use_browser=False):
    global browser
    if use_browser:
        browser = use_browser
    browser = FTPUtils.check_login(browser, return_browser=True)

    if search_type != 'all':
        FTPUtils.log_event('Searching {} for players with parameters {}'.format(search_type, search_settings), ind_level=ind_level)
        url = 'https://www.fromthepavilion.org/{}.htm'
        if search_type == 'transfer_market':
            url = url.format('transfer')
        elif search_type == 'nat_search':
            url = url.format('natsearch')
        browser.open(url)
        search_settings_form = browser.get_form()

        for setting in search_settings.keys():
            search_settings_form[setting] = str(search_settings[setting])

        browser.submit_form(search_settings_form)
        players_df = pd.read_html(str(browser.parsed))[0]

    if search_type == 'transfer_market':
        del players_df['Nat']
        player_ids = [x[9:] for x in re.findall('playerId=[0-9]+', str(browser.parsed))][::2]
        region_ids = [x[9:] for x in re.findall('regionId=[0-9]+', str(browser.parsed))][9:]
        players_df.insert(loc=3, column='Nat', value=region_ids)
        players_df.insert(loc=1, column='PlayerID', value=player_ids)
        players_df['Deadline'] = [deadline[:-5] + ' ' + deadline[-5:] for deadline in players_df['Deadline']]
        cur_bids_full = [bid for bid in players_df['Current Bid']]
        split_bids = [b.split(' ', 1) for b in cur_bids_full]
        bids = [b[0] for b in split_bids]
        team_names = pd.Series([b[1] for b in split_bids])
        bid_ints = [int(''.join([x for x in b if x.isdigit()])) for b in bids]
        players_df['Current Bid'] = pd.Series(bid_ints)
        players_df.insert(loc=3, column='Bidding Team', value=team_names)

    elif search_type == 'nat_search':
        del players_df['Unnamed: 13']
        player_ids = [x[9:] for x in re.findall('playerId=[0-9]+', str(browser.parsed))][::2]
        players_df.insert(loc=1, column='PlayerID', value=player_ids)

    elif search_type == 'all':
        if 'pages' not in search_settings.keys():
            search_settings['pages'] = 1

        browser.open('https://www.fromthepavilion.org/playerranks.htm?regionId=1')
        search_settings_form = browser.get_forms()[0]

        for search_setting in ['nation', 'region', 'age', 'wagesort']:
            if search_setting in search_settings.keys():
                if search_setting == 'nation':
                    search_settings_form['country'].value = str(search_settings[search_setting])
                elif search_setting == 'region':
                    search_settings_form['region'].value = str(search_settings[search_setting])
                elif search_setting == 'wagesort':
                    search_settings_form['sortByWage'].value = str(search_settings[search_setting])
                else:
                    search_settings_form[search_setting].value = str(search_settings[search_setting])

        player_ids = []
        region_ids = []
        players_df = pd.DataFrame()

        FTPUtils.log_event('Searching for best players with parameters {}'.format(search_settings), ind_level=ind_level)
        for page in range(int(search_settings['pages'])):
            search_settings_form['page'].value = str(page)
            browser.submit_form(search_settings_form)

            pageplayers_df = pd.read_html(str(browser.parsed))[1]
            players_df = players_df.append(pageplayers_df)

            page_player_ids = [x[9:] for x in re.findall('playerId=[0-9]+', str(browser.parsed))][::2]
            page_region_ids = [x[9:] for x in re.findall('regionId=[0-9]+', str(browser.parsed))][20:]

            player_ids += page_player_ids
            region_ids += page_region_ids

                # FTPUtils.log_event('Downloaded page {}/{}...'.format(page + 1, int(search_settings['pages'])), logtype='console', ind_level=1)

        del players_df['Nat']
        players_df.insert(loc=3, column='Nat', value=region_ids)
        players_df.insert(loc=1, column='PlayerID', value=player_ids)
        players_df['Wage'] = players_df['Wage'].str.replace('\D+', '')

    if normalize_age:
        players_df['Age'] = normalize_age(players_df['Age'])

    if additional_columns:
        players_df = add_player_columns(players_df, additional_columns, ind_level=ind_level+1, use_browser=browser)
        sorted_columns = ['Player', 'PlayerID', 'Age', 'NatSquad', 'Touring', 'Wage', 'Rating' 'BT', 'End', 'Bat', 'Bowl', 'Tech', 'Pow', 'Keep', 'Field', 'Exp', 'Talents', 'SpareRat']
        players_df = players_df.reindex(columns=sorted_columns)

    players_df.drop(columns=[x for x in ['#', 'Unnamed: 18'] if x in players_df.columns], inplace=True)

    if return_sort_column:
        players_df.sort_values(return_sort_column, inplace=True, ascending=False)

    if to_file:
        pd.DataFrame.to_csv(players_df, to_file, index=False, float_format='%.2f')

    print(players_df)

    return players_df


def download_database(config_file_directory, preserve_exisiting=False, return_next_runtime=False, ind_level=0, use_browser=False):
    global browser
    if use_browser:
        browser = use_browser
    browser = FTPUtils.check_login(browser, return_browser=True)
    FTPUtils.log_event('Downloading database {}'.format(config_file_directory.split('/')[-1]), ind_level=ind_level)

    if '/' not in config_file_directory:
        config_file_directory = config_file_directory + '/' + config_file_directory + '.config'

    database_settings, additional_settings = load_config_file(config_file_directory)
    if 'additional_columns' not in database_settings.keys():
        database_settings['additional_columns'] = False

    browser.open('https://www.fromthepavilion.org/club.htm?teamId=4791')
    timestr = re.findall('Week [0-9]+, Season [0-9]+', str(browser.parsed))[0]
    week, season = timestr.split(',')[0].split(' ')[-1], timestr.split(',')[1].split(' ')[-1]

    if database_settings['database_type'] != 'transfer_market_search':
        season_dir = database_settings['w_directory'] + 's{}/w{}/'.format(season, week)
    else:
        season_dir = database_settings['w_directory'] + '/s{}/w{}/'.format(season, week)

    if not os.path.exists(season_dir):
        os.makedirs(season_dir)
        FTPUtils.log_event('Creating directory {}'.format(season_dir), logfile=['default', database_settings['w_directory'] + database_settings['name'] + '.log'], ind_level=ind_level)

    player_df = pd.DataFrame()
    if database_settings['database_type'] in ['domestic_team', 'national_team']:
        for teamid in additional_settings['teamids']:
            player_df.append(FTPUtils.get_team_players(teamid, age_group=additional_settings['age'], to_file=database_settings['w_directory'] + 's{}/w{}/{}.csv'.format(season, week, teamid), ind_level=ind_level+1, additional_columns=database_settings['additional_columns']))
    elif database_settings['database_type'] == 'best_player_search':
        for nationality_id in additional_settings['teamids']:
            additional_settings['nation'] = nationality_id
            player_df.append(player_search(additional_settings, search_type='all', to_file=database_settings['w_directory'] + 's{}/w{}/{}.csv'.format(season, week, nationality_id), additional_columns=database_settings['additional_columns'], ind_level=ind_level+1))
    elif database_settings['database_type'] == 'transfer_market_search':
        player_df = player_search(search_settings=additional_settings, search_type='transfer_market', additional_columns=database_settings['additional_columns'], ind_level=ind_level+1, use_browser=browser)
        player_df.to_csv(database_settings['w_directory'] + '/s{}/w{}/{}.csv'.format(season, week, player_df['Deadline'][0] + ' - ' + player_df['Deadline'][len(player_df['Deadline'])-1]))

    #FTPUtils.log_event('Successfully saved {} players from database {}'.format(len(player_df.PlayerID), database_settings['name']), logfile=['default', database_settings['w_directory'] + database_settings['name'] + '.log'])
    if return_next_runtime:
        if database_settings['database_type'] != 'transfer_market_search':
            return next_run_time([database_settings, additional_settings])
        else:
            return datetime.datetime.strptime(player_df['Deadline'][len(player_df['Deadline'])-1] + ' +0000', '%d %b %Y %H:%M %z')


def load_entry(database, season, week, groupid, normalize_age=True, ind_level=0):
    if database[-1] != '/':
        database += '/'

    predicted_log_file = database + database.split('/')[-2] + '.log' #if name of database is the name of it's working directory
    if os.path.exists(predicted_log_file):
        log_files = ['default', predicted_log_file]
    else:
        log_files = ['default']

    data_file = database + 's{}/w{}/{}.csv'.format(season, week, groupid)
    if os.path.isfile(data_file):
        players = pd.read_csv(data_file, float_precision='2')
        if normalize_age:
            players['Age'] = pd.Series(normalize_age(players['Age']))
        return players
    else:
        FTPUtils.log_event('Error loading database entry (file not found): {}'.format(data_file), logtype='full', logfile=log_files, ind_level=ind_level)


def add_player_columns(player_df, column_types, normalize_wages=True, returnsortcolumn=None, ind_level=0, use_browser=False):
    if column_types != ['SpareRat']: #no need to log in
        global browser
        if use_browser:
            browser = use_browser
        browser = FTPUtils.check_login(browser, return_browser=True)
    FTPUtils.log_event('Creating additional columns ({}) for {} players'.format(column_types, len(player_df['Rating'])), ind_level=ind_level)

    all_player_data = []
    hidden_training_n = 0
    for player_id in player_df['PlayerID']:
        player_data = []
        if 'Training' in column_types:
            browser.open('https://www.fromthepavilion.org/playerpopup.htm?playerId={}'.format(player_id))
            popup_page_info = pd.read_html(str(browser.parsed))
            try:
                training_selection = popup_page_info[0][3][9]
            except KeyError: #player training not visible to manager
                training_selection = 'Hidden'
                hidden_training_n += 1

        if column_types != ['Training'] and column_types != ['SpareRat']:
            browser.open('https://www.fromthepavilion.org/player.htm?playerId={}'.format(player_id))
            player_page = str(browser.parsed)

        for column_name in column_types:
            if column_name == 'Training':
                player_data.append(training_selection)

            elif column_name == 'Wage':
                player_wage = FTPUtils.get_player_wage(player_id, player_page, normalize_wages)
                player_data.append(player_wage)

            elif column_name == 'Nat':
                player_nationality_id = FTPUtils.get_player_nationality(player_id, player_page)
                player_data.append(player_nationality_id)

            elif column_name == 'NatSquad':
                if 'This player is a member of the national squad' in player_page:
                    player_data.append(True)
                else:
                    player_data.append(False)

            elif column_name == 'Touring':
                if 'This player is on tour with the national team' in player_page:
                    player_data.append(True)
                else:
                    player_data.append(False)

            elif column_name == 'TeamID':
                player_teamid = FTPUtils.get_player_teamid(player_id, player_page)
                player_data.append(player_teamid)

            elif column_name == 'SpareRat':
                player_data.append(FTPUtils.get_player_spare_ratings(player_df[player_df['PlayerID'] == player_id].iloc[0]))

            elif column_name == 'SkillShift':
                skillshifts = FTPUtils.get_player_skillshifts(player_id, page=player_page)
                player_data.append('-'.join(skillshifts.keys()) if len(skillshifts.keys()) >= 1 else None)

            else:
                player_data.append('UnknownColumn')

        all_player_data.append(player_data)

    if hidden_training_n > 0:
        FTPUtils.log_event('Training not visible for {}/{} players - marked "Hidden" in dataframe'.format(hidden_training_n, len(player_df['PlayerID'])), ind_level=ind_level+1)

    for n, column_name in enumerate(column_types):
        values = [v[n] for v in all_player_data]
        player_df.insert(3, column_name, values)

    if returnsortcolumn in player_df.columns:
        player_df.sort_values(returnsortcolumn, inplace=True, ignore_index=True, ascending=False)

    return player_df


def match_pg_ids(pg1, pg2, returnsortcolumn='Player'):
    shared_ids = [x for x in pg1['PlayerID'] if x in [y for y in pg2['PlayerID']]]

    pg1_shared = pg1[(pg1['PlayerID'].isin(shared_ids))].copy()
    pg2_shared = pg2[(pg2['PlayerID'].isin(shared_ids))].copy()

    pg1_shared.sort_values('PlayerID', inplace=True, ignore_index=True, ascending=False)
    pg2_shared.sort_values('PlayerID', inplace=True, ignore_index=True, ascending=False)

    add_columns = ['Ratdif', 'Wagedif', 'SkillShift']
    pg2_shared = calculate_additional_columns(pg1_shared, pg2_shared, add_columns)

    pg1_shared.sort_values(returnsortcolumn, inplace=True, ignore_index=True, ascending=False)
    pg2_shared.sort_values(returnsortcolumn, inplace=True, ignore_index=True, ascending=False)

    return pg1_shared, pg2_shared


def calculate_additional_columns(pg1, pg2, columns):
    for c in columns:
        if c == 'Ratdif':
            rating_differences = pg2['Rating'] - pg1['Rating']
            pg2.insert(len(pg2.columns), 'Ratdif', rating_differences)
        elif c == 'Wagedif':
            wage_differences = pg2['Wage'] - pg1['Wage']
            pg2.insert(len(pg2.columns), 'Wagedif', wage_differences)
        elif c == 'SkillShift':
            popped_skills = [calculate_player_skillshifts(playert_1, playert_2) for playert_1, playert_2 in zip(pg1, pg2)]
            pg2.insert(len(pg2.columns), 'SkillShift', '-'.join(popped_skills))

    return pg2


def calculate_player_skillshifts(player_data1, player_data2):
    long_names = ['Batting', 'Endurance', 'Bowling', 'Technique', 'Keeping', 'Power', 'Fielding']
    short_names = ['Bat', 'End', 'Bowl', 'Tech', 'Keep', 'Power', 'Field']
    saved_columns = [t for t in player_data1.axes[0].values]
    shifts = []

    if 'Bat' in saved_columns:
        col_names = short_names
    elif 'Batting' in saved_columns:
        col_names = long_names

    for c in col_names:
        if player_data1[c] != player_data2[c]:
            skill_ind = col_names.index(c)
            shifts.append(long_names[skill_ind])

    return shifts


def next_run_time(db_config_file):
    current_datetime = datetime.datetime.now(datetime.timezone.utc)# - datetime.timedelta(days=1)
    db_scrape_hour, db_scrape_minute = db_config_file[0]['scrape_time']

    db_days = db_config_file[0]['archive_days']

    weekly_runtimes = []
    for day in db_days:
        day = int(day)
        days_ahead = day - current_datetime.weekday()
        if days_ahead < 0:  # Target day already happened this week
            days_ahead += 7
        next_run_datetime = current_datetime + datetime.timedelta(days_ahead)
        next_run_datetime = next_run_datetime.replace(hour=int(db_scrape_hour), minute=int(db_scrape_minute), second=0, microsecond=0)
        weekly_runtimes.append(next_run_datetime)

    weekly_runtimes.sort()
    for runtime in weekly_runtimes:
        if runtime > current_datetime:
            return runtime
    else:
        return weekly_runtimes[0] + datetime.timedelta(days=7)


def watch_database_list(database_list, ind_level=0, use_browser=False):
    global browser
    if use_browser:
        browser = use_browser
    browser = FTPUtils.check_login(browser, return_browser=True)

    loaded_database_dict = {}
    database_stack = []
    for database_name in database_list:
        conf_data = load_config_file(database_name)
        if conf_data[0]['database_type'] != 'transfer_market_search':
            db_next_runtime = next_run_time(conf_data)
            loaded_database_dict[database_name] = [conf_data, db_next_runtime]
            database_stack.append([database_name, db_next_runtime])
        else:
            current_datetime = datetime.datetime.now(datetime.timezone.utc)
            loaded_database_dict[database_name] = [conf_data, current_datetime]
            database_stack.append([database_name, current_datetime])

    while True:
        current_datetime = datetime.datetime.now(datetime.timezone.utc)
        seconds_until_next_run = int((database_stack[0][1] - current_datetime).total_seconds())
        if seconds_until_next_run > 0:
            FTPUtils.log_event('Sleeping {} seconds until {} runtime at {}'.format(seconds_until_next_run, database_stack[0][0], database_stack[0][1]), ind_level=ind_level)
            time.sleep(seconds_until_next_run)

        attempts_before_exiting = 10
        current_attempt = 0
        seconds_between_attempts = 60

        db_next_runtime = download_database(database_stack[0][0], return_next_runtime=True, use_browser=browser)

        while current_attempt <= attempts_before_exiting:
            try:
                db_next_runtime = download_database(database_stack[0][0], return_next_runtime=True, use_browser=browser)
                if current_attempt > 0:
                    FTPUtils.log_event('Completed successfully after {} failed attempts'.format(current_attempt), ind_level=ind_level)
                break
            except:
                FTPUtils.log_event('Error downloading database. {}/{} attempts, {}s between attempts...'.format(current_attempt, attempts_before_exiting, seconds_between_attempts), ind_level=ind_level+1)
                time.sleep(seconds_between_attempts)

        FTPUtils.log_event('Database {} will be downloaded again at {}'.format(database_stack[0][0], db_next_runtime), ind_level=ind_level)
        database_stack[0][1] = db_next_runtime
        database_stack = sorted(database_stack, key=lambda x: x[1])

    return database_stack