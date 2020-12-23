import os
import time
import datetime
import re
from robobrowser import RoboBrowser
import pandas as pd
import shutil
import ast
import itertools
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns; sns.set_theme(color_codes=True)
import mplcursors
from math import floor

ORDERED_SKILLS = [['ID', 'Player', 'Nat', 'Deadline', 'Current Bid'], ['Rating', 'Exp', 'Talents', 'BT'], ['Bat', 'Bowl', 'Keep', 'Field'], ['End', 'Tech', 'Pow']]
SKILL_LEVELS = ['atrocious', 'dreadful', 'poor', 'ordinary', 'average', 'reasonable', 'capable', 'reliable', 'accomplished', 'expert', 'outstanding', 'spectacular', 'exceptional', 'world class', 'elite', 'legendary']
browser = None

with open('credentials.txt', 'r') as f:
    CREDENTIALS = f.readline().split(',')


class PlayerDatabase():
    global_settings = ['name', 'description', 'database_type', 'w_directory', 'archive_days', 'scrape_time', 'additional_columns']

    @staticmethod
    def generate_config_file(database_settings, additional_settings):
        if database_settings['w_directory'][-1] != '/':
            database_settings['w_directory'] += '/'
        conf_file = database_settings['w_directory'] + database_settings['name'] + '.config'

        if not os.path.exists(database_settings['w_directory']):
            os.makedirs(database_settings['w_directory'])
            log_event('Creating directory {}'.format(database_settings['w_directory']), logfile=['default', database_settings['w_directory'] + database_settings['name'] + '.log'])

        if os.path.isfile(conf_file):
            shutil.copy(conf_file, conf_file + '.old')
            log_event('Config file {} already exisits, copying to {} and creating new file'.format(conf_file, conf_file + '.old'), logfile=['default', database_settings['w_directory'] + database_settings['name'] + '.log'])

        with open(conf_file, 'w') as f:
            for setting in PlayerDatabase.global_settings:
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

        log_event('Successfully created config file {}'.format(conf_file), logfile=['default', database_settings['w_directory'] + database_settings['name'] + '.log'])

    @staticmethod
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
            if setting_name in PlayerDatabase.global_settings:
                database_settings[setting_name] = all_file_values[setting_name]
            else:
                additional_settings[setting_name] = all_file_values[setting_name]

        return database_settings, additional_settings

    @staticmethod
    def player_search(search_settings={}, to_file=False, search_type='transfer_market', extra_columns=False, normalize_age=False, additional_columns=False, ind_level=0):
        global browser
        check_login()

        if search_type != 'all':
            log_event('Searching {} for players with parameters {}'.format(search_type, search_settings), ind_level=ind_level)
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
                    elif search_setting == 'wagesort':
                        search_settings_form['sortByWage'].value = str(search_settings[search_setting])
                    else:
                        search_settings_form[search_setting].value = str(search_settings[search_setting])

            player_ids = []
            region_ids = []
            players_df = pd.DataFrame()

            log_event('Searching for best players with parameters {}'.format(search_settings), ind_level=ind_level)
            for page in range(int(search_settings['pages'])):
                search_settings_form['page'].value = str(page)
                browser.submit_form(search_settings_form)

                pageplayers_df = pd.read_html(str(browser.parsed))[1]
                players_df = players_df.append(pageplayers_df)

                page_player_ids = [x[9:] for x in re.findall('playerId=[0-9]+', str(browser.parsed))][::2]
                page_region_ids = [x[9:] for x in re.findall('regionId=[0-9]+', str(browser.parsed))][20:]

                player_ids += page_player_ids
                region_ids += page_region_ids

                # log_event('Downloaded page {}/{}...'.format(page + 1, int(search_settings['pages'])), logtype='console', ind_level=1)

            del players_df['Nat']
            players_df.insert(loc=3, column='Nat', value=region_ids)
            players_df.insert(loc=1, column='PlayerID', value=player_ids)
            players_df['Wage'] = players_df['Wage'].str.replace('\D+', '')

        if normalize_age:
            players_df['Age'] = FTPUtils.normalize_age(players_df['Age'])

        if additional_columns:
            players_df = PlayerDatabase.add_player_columns(players_df, additional_columns, ind_level=ind_level+1)

        players_df.drop(columns=[x for x in ['#', 'Unnamed: 18'] if x in players_df.columns], inplace=True)

        if to_file:
            pd.DataFrame.to_csv(players_df, to_file, index=False, float_format='%.2f')

        return players_df

    @staticmethod
    def download_database(config_file_directory, preserve_exisiting=False, return_next_runtime=False, ind_level=0):
        global browser
        check_login()
        log_event('Downloading database {}'.format(config_file_directory.split('/')[-1]), ind_level=ind_level)

        if '/' not in config_file_directory:
            config_file_directory = config_file_directory + '/' + config_file_directory + '.config'

        database_settings, additional_settings = PlayerDatabase.load_config_file(config_file_directory)
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
            log_event('Creating directory {}'.format(season_dir), logfile=['default', database_settings['w_directory'] + database_settings['name'] + '.log'], ind_level=ind_level)

        player_df = pd.DataFrame()
        if database_settings['database_type'] in ['domestic_team', 'national_team']:
            for teamid in additional_settings['teamids']:
                player_df.append(FTPUtils.get_team_players(teamid, age_group=additional_settings['age'], to_file=database_settings['w_directory'] + 's{}/w{}/{}.csv'.format(season, week, teamid), ind_level=ind_level+1, additional_columns=database_settings['additional_columns']))
        elif database_settings['database_type'] == 'best_player_search':
            for nationality_id in additional_settings['teamids']:
                additional_settings['nation'] = nationality_id
                player_df.append(PlayerDatabase.player_search(additional_settings, search_type='all', to_file=database_settings['w_directory'] + 's{}/w{}/{}.csv'.format(season, week, nationality_id), ind_level=ind_level+1), additional_columns=database_settings['additional_columns'])
        elif database_settings['database_type'] == 'transfer_market_search':
            player_df = PlayerDatabase.player_search(search_settings=additional_settings, search_type='transfer_market', additional_columns=database_settings['additional_columns'], ind_level=ind_level+1)
            player_df.to_csv(database_settings['w_directory'] + '/s{}/w{}/{}.csv'.format(season, week, player_df['Deadline'][0] + ' - ' + player_df['Deadline'][len(player_df['Deadline'])-1]))

        #log_event('Successfully saved {} players from database {}'.format(len(player_df.PlayerID), database_settings['name']), logfile=['default', database_settings['w_directory'] + database_settings['name'] + '.log'])
        if return_next_runtime:
            if database_settings['database_type'] != 'transfer_market_search':
                return PlayerDatabase.next_run_time([database_settings, additional_settings])
            else:
                return datetime.datetime.strptime(player_df['Deadline'][len(player_df['Deadline'])-1] + ' +0000', '%d %b %Y %H:%M %z')


    @staticmethod
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
            players = pd.read_csv(data_file, float_precision=2)
            if normalize_age:
                players['Age'] = pd.Series(FTPUtils.normalize_age(players['Age']))
            return players
        else:
            log_event('Error loading database entry (file not found): {}'.format(data_file), logtype='full', logfile=log_files, ind_level=ind_level)

    @staticmethod
    def add_player_columns(player_df, column_types, normalize_wages=True, returnsortcolumn=None, ind_level=0):
        check_login()
        log_event('Saving additional columns ({}) for {} players'.format(column_types, len(player_df['Rating'])), ind_level=ind_level)

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

            if column_types != ['Training']:
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
            log_event('Training not visible for {}/{} players - marked "Hidden" in dataframe'.format(hidden_training_n, len(player_df['PlayerID'])), ind_level=ind_level+1)

        for n, column_name in enumerate(column_types):
            values = [v[n] for v in all_player_data]
            player_df.insert(3, column_name, values)

        if returnsortcolumn in player_df.columns:
            player_df.sort_values(returnsortcolumn, inplace=True, ignore_index=True, ascending=False)

        return player_df

    @staticmethod
    def match_pg_ids(pg1, pg2, returnsortcolumn='Player'):
        shared_ids = [x for x in pg1['PlayerID'] if x in [y for y in pg2['PlayerID']]]

        pg1_shared = pg1[(pg1['PlayerID'].isin(shared_ids))].copy()
        pg2_shared = pg2[(pg2['PlayerID'].isin(shared_ids))].copy()

        pg1_shared.sort_values('PlayerID', inplace=True, ignore_index=True, ascending=False)
        pg2_shared.sort_values('PlayerID', inplace=True, ignore_index=True, ascending=False)

        rating_differences = pg2_shared['Rating'] - pg1_shared['Rating']
        wage_differences = pg2_shared['Wage'] - pg1_shared['Wage']
        pg1_shared.insert(len(pg1_shared.columns), 'Ratdif', rating_differences)
        pg2_shared.insert(len(pg2_shared.columns), 'Ratdif', rating_differences)
        pg1_shared.insert(len(pg1_shared.columns), 'Wagedif', wage_differences)
        pg2_shared.insert(len(pg2_shared.columns), 'Wagedif', wage_differences)

        pg1_shared.sort_values(returnsortcolumn, inplace=True, ignore_index=True, ascending=False)
        pg2_shared.sort_values(returnsortcolumn, inplace=True, ignore_index=True, ascending=False)

        return pg1_shared, pg2_shared

    @staticmethod
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

    @staticmethod
    def watch_database_list(database_list, ind_level = 0):
        loaded_database_dict = {}
        database_stack = []
        for database_name in database_list:
            conf_data = PlayerDatabase.load_config_file(database_name)
            if conf_data[0]['database_type'] != 'transfer_market_search':
                db_next_runtime = PlayerDatabase.next_run_time(conf_data)
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
                log_event('Sleeping {} seconds until {} runtime at {}'.format(seconds_until_next_run, database_stack[0][0], database_stack[0][1]), ind_level=ind_level)
                time.sleep(seconds_until_next_run)

            db_next_runtime = PlayerDatabase.download_database(database_stack[0][0], return_next_runtime=True)
            log_event('Database {} will be downloaded again at {}'.format(database_stack[0][0], db_next_runtime), ind_level=ind_level)
            database_stack[0][1] = db_next_runtime
            database_stack = sorted(database_stack, key=lambda x: x[1])

        return database_stack

    def __init__(self, config_file_directory):
        self.database_settings, self.additional_settings = self.load_config_file(config_file_directory)


class FTPUtils():
    @staticmethod
    def nationality_id_to_rgba_color(natid):
        nat_colors = ['darkblue', 'red', 'forestgreen', 'black', 'mediumseagreen', 'darkkhaki', 'maroon', 'firebrick', 'darkgreen', 'firebrick', 'tomato', 'royalblue', 'brown', 'darkolivegreen', 'olivedrab', 'purple', 'lightcoral', 'darkorange']

        return matplotlib.colors.to_rgba(nat_colors[natid-1])

    @staticmethod
    def nationality_id_to_name_str(natid, full_name=False):
        natid = int(natid)
        nat_name_short = ['AUS', 'ENG', 'IND', 'NZL', 'PAK', 'SA', 'WI', 'SRI', 'BAN', 'ZWE', 'CAN', 'USA', 'KEN', 'SCO', 'IRE', 'UAE', 'BER', 'NL']
        nat_name_long = ['Australia', 'England', 'India', 'New Zealand', 'Pakistan', 'South Africa', 'West Indies', 'Sri Lanka', 'Bangladesh', 'Zimbabwe', 'Canada', 'USA', 'Kenya', 'Scotland', 'Ireland', 'UAE', 'Bermuda', 'Netherlands']

        return nat_name_long[natid-1] if full_name else nat_name_short[natid-1]

    @staticmethod
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

    @staticmethod
    def get_player_page(player_id):
        check_login()

        browser.open('https://www.fromthepavilion.org/player.htm?playerId={}'.format(player_id))
        page = str(browser.parsed)

        return page

    @staticmethod
    def get_player_spare_ratings(player_df, col_name_len='full'):
        skill_rating_sum = 0
        for skill in ['Bat', 'Bowl', 'Keep', 'Field', 'End', 'Tech', 'Pow' if 'Pow\'' in [str(x) for x in player_df.axes][0] else 'Power']:
            player_level = player_df[skill]
            if str(player_level) == 'nan':
                return 'Unknown'
            skill_n = FTPUtils.skill_word_to_index(player_level, col_name_len)
            skill_rating_sum += 500 if skill_n == 0 else 1000 * skill_n

        return player_df['Rating'] - skill_rating_sum

    @staticmethod
    def get_team_players(teamid, age_group='all', squad_type='domestic_team', to_file = False, normalize_age=False, additional_columns=False, ind_level=0):
        global browser
        check_login()

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
            team_players['Age'] = FTPUtils.normalize_age(team_players['Age'])

        if additional_columns:
            team_players = PlayerDatabase.add_player_columns(team_players, additional_columns, ind_level=ind_level+1)

        team_players.drop(columns=[x for x in ['#', 'Unnamed: 18'] if x in team_players.columns], inplace=True)

        if to_file:
            pd.DataFrame.to_csv(team_players, to_file, index=False, float_format='%.2f')

        return team_players

    @staticmethod
    def get_player_wage(player_id, page=False, normalize_wage=False):
        if not page:
            page = FTPUtils.get_player_page(player_id)

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

    @staticmethod
    def get_player_teamid(player_id, page=False):
        if not page:
            page = FTPUtils.get_player_page(player_id)

        team_id = re.findall('teamId=[0-9]+', page)[-2]

        return team_id

    @staticmethod
    def get_player_nationality(player_id, page=False):
        if not page:
            page = FTPUtils.get_player_page(player_id)

        player_nationality_id = re.findall('regionId=[0-9]+', page)[-1][9:]

        return player_nationality_id

    @staticmethod
    def get_player_skillshifts(player_id, page=False):
        if not page:
            page = FTPUtils.get_player_page(player_id)

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

    @staticmethod
    def get_player_summary(player_id, page=False):
        if not page:
            page = FTPUtils.get_player_page(player_id)

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


    @staticmethod
    def get_league_gameids(leagueid, round_n='latest', league_format='league'):
        global browser
        check_login()

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


    @staticmethod
    def game_scordcard_table(gameid, ind_level=0):
        global browser
        check_login()

        browser.open('https://www.fromthepavilion.org/scorecard.htm?gameId={}'.format(gameid))
        scorecard_tables = pd.read_html(str(browser.parsed))
        page_teamids = [''.join([c for c in x if c.isdigit()]) for x in re.findall('teamId=[0-9]+', str(browser.parsed))]
        home_team_id, away_team_id = page_teamids[21], page_teamids[22]
        scorecard_tables[-2].iloc[0][1] = home_team_id
        scorecard_tables[-2].iloc[1][1] = away_team_id

        log_event('Downloaded scorecard for game {}'.format(gameid), ind_level=ind_level)

        return scorecard_tables

    @staticmethod
    def get_game_teamids(gameid, ind_level=0):
        check_login()

        browser.open('https://www.fromthepavilion.org/gamedetails.htm?gameId={}'.format(gameid))
        page_teamids = [''.join([c for c in x if c.isdigit()]) for x in re.findall('teamId=[0-9]+', str(browser.parsed))]
        home_team_id, away_team_id = page_teamids[22], page_teamids[23]

        log_event('Found teams for game {} - {} vs {}'.format(gameid, home_team_id, away_team_id), ind_level=ind_level)

        return (home_team_id, away_team_id)

    @staticmethod
    def normalize_age(player_ages, reverse=False):
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


class PresentData():
    @staticmethod
    def youth_pull_league_round_overview(leagueid, normalize_age=False, league_format='league', round_n='latest', ind_level=0, weeks_since_game='default'):
        requested_games = FTPUtils.get_league_gameids(leagueid, league_format=league_format, round_n=round_n)
        browser.open('https://www.fromthepavilion.org/commentary.htm?gameId={}'.format(requested_games[0]))
        if weeks_since_game == 'default':
            player_match_age = FTPUtils.normalize_age(['16.00'])[0]
        else:
            valid_age = 16 + (weeks_since_game / 15)
            valid_age = '16.' + str(valid_age).split('.')[1][:5]
            player_match_age = float(valid_age)

        if 'Membership Features' in str(browser.parsed):
            games_finished = False
        else:
            games_finished = True

        log_event('League {} - Round {}: {}'.format(leagueid, round_n, 'Played' if games_finished else 'Not Played'), ind_level=ind_level)

        round_teams = []
        if not games_finished:
            for game in [FTPUtils.get_game_teamids(game) for game in requested_games]:
                round_teams.append(game[0]) #home
                round_teams.append(game[1]) #away
        else:
            scorecard_tables = [FTPUtils.game_scordcard_table(gameid) for gameid in requested_games]
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
            log_event('Requested round (League {} - Round {}) has not been played, so no stats could be collected. {} players found.'.format(leagueid, round_n, len(new_players)), ind_level=ind_level)

        try:
            new_players.sort_values('Rating', ascending=False, inplace=True, ignore_index=True)
            del new_players['Fatg']
            del new_players['Initial']
            del new_players['BT']
            # del new_player_overview['Age']
            # del new_player_overview['Nat']

            if not normalize_age:
                new_players['Age'] = FTPUtils.normalize_age(new_players['Age'], reverse=True)

            new_players['Nat'] = [FTPUtils.nationality_id_to_name_str(natid) for natid in new_players['Nat']]

        except KeyError:
            log_event('No new players found in round ({}) in league {}'.format(round_n, leagueid), ind_level=ind_level)

        return new_players

    @staticmethod
    def database_rating_increase_scatter(db_name, group1_db_entry=[46, 2], group2_db_entry=[46, 3], return_w2=False, include_hidden_training=False):
        db_config = PlayerDatabase.load_config_file(db_name)
        db_team_ids = db_config[1]['teamids']
        w2p = []
        w1p = []
        for region_id in db_team_ids:
            team_w1p = PlayerDatabase.load_entry(db_name, group1_db_entry[0], group1_db_entry[1], region_id, normalize_age=True)  # pd.concat(w13players)
            team_w2p = PlayerDatabase.load_entry(db_name, group2_db_entry[0], group2_db_entry[1], region_id, normalize_age=True)  # pd.concat(w10players)
            x1, x2 = PlayerDatabase.match_pg_ids(team_w1p, team_w2p, returnsortcolumn='Ratdif')
            w1p.append(x1)
            w2p.append(x2)

        allplayers = pd.concat(w2p, ignore_index=True).T.drop_duplicates().T
        if return_w2:
            return w2p
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
            age = FTPUtils.normalize_age([allplayers.iloc[pn]['Age']], True)[0]
            p_data = [allplayers.iloc[pn]['Player'], allplayers.iloc[pn]['PlayerID'], allplayers.iloc[pn]['Team'], allplayers.iloc[pn]['TeamID'], age, allplayers.iloc[pn]['Ratdif']]
            if 'Training' in allplayers.columns:
                p_data.append(allplayers.iloc[pn]['Training'])
            else:
                p_data.append('Not in table')
            labeldata.append(p_data)

        labels = [
            'Player: {} ({})\nTeam: {} ({})\nAge: {}\nRatdif: +{}\nTraining: {}'.format(player[0], player[1], player[2], player[3],
                                                                          player[4], player[5], player[6]) for player in labeldata]
        cursor = mplcursors.cursor(ax, hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(labels[sel.target.index]))
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(20, integer=True))
        plt.grid(axis='x', linestyle='--', c='k', linewidth=1, alpha=0.4)
        plt.ylim([0, max(allplayers['Ratdif']) + 100])
        plt.show()

        #sns.lmplot(x='Age', y='Ratdif', data=allplayers, hue='TeamID')

    @staticmethod
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
            x1, x2 = PlayerDatabase.match_pg_ids(group1_team, group2_team, returnsortcolumn='Ratdif')
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


def log_event(logtext, logtype='full', logfile='default', ind_level = 0):
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


def check_login():
    global browser, CREDENTIALS
    if isinstance(browser, type(None)):
        browser = login(CREDENTIALS)
        return True
    else:
        last_page_load = datetime.datetime.strptime(str(browser.response.headers['Date'])[:-4]+'+0000', '%a, %d %b %Y %H:%M:%S%z')
        if (datetime.datetime.now(datetime.timezone.utc) - last_page_load) > datetime.timedelta(minutes=10):
            log_event('Browser timed out...')
            browser = login(CREDENTIALS)
            browser.open('https://www.fromthepavilion.org/club.htm?teamId=4791')
            return True

    return True


def login(credentials, logtype='full', logfile='default'):
    global browser
    browser = RoboBrowser(history=True)
    browser.open('http://www.fromthepavilion.org/')
    form = browser.get_form(action='securityCheck.htm')

    form['j_username'] = credentials[0]
    form['j_password'] = credentials[1]

    browser.submit_form(form)
    if check_login():
        logtext = 'Successfully logged in as user {}.'.format(CREDENTIALS[0])
        log_event(logtext, logtype=logtype, logfile=logfile)
        return browser
    else:
        logtext = 'Failed to log in as user {}'.format(CREDENTIALS[0])
        log_event(logtext, logtype=logtype, logfile=logfile)
        return None

def catagorise_training(db_time_pairs):
    training_data_collection = []
    for dbtpair in db_time_pairs:
        training_data_week = pd.concat(PresentData.database_rating_increase_scatter(dbtpair[0], dbtpair[1], dbtpair[2], True))
        non_hidden_training = training_data_week[training_data_week['Training'] != 'Hidden']
        if dbtpair[2][1] - dbtpair[1][1] > 1:
            non_hidden_training['Ratdif'] = np.divide(non_hidden_training['Ratdif'], dbtpair[2][1] - dbtpair[1][1])
        training_data_collection.append(non_hidden_training)

    all_training_data = pd.concat(training_data_collection)
    training_type_dict = {}
    for trainingtype in ['Batting', 'Bowling', 'Keeping', 'Keeper-Batsman', 'All-rounder', 'Fielding', 'Fitness', 'Batting Technique', 'Bowling Technique', 'Strength', 'Rest']:
        training_type_data = all_training_data[all_training_data['Training'] == trainingtype]
        training_type_data['Age'] = [int(floor(a)) for a in list(training_type_data['Age'])]
        training_type_age_dict = {}
        for age in range(int(min(np.append(training_type_data.Age, int(max(np.append(training_type_data.Age, 16)))))), int(max(np.append(training_type_data.Age, 16)))):
            data = training_type_data[training_type_data['Age'] == age]
            if len(data) > 0:
                training_type_age_dict[age] = data

        training_type_dict[trainingtype] = training_type_age_dict

    return training_type_dict

if __name__ == '__main__':
    db_pairs = [['u21-national-squads', (46, 6), (46, 7)],
                ['u21-national-squads', (46, 5), (46, 6)],
                ['u21-national-squads', (46, 2), (46, 3)],
                ['teams-weekly', (46, 2), (46, 3)],
                ['teams-weekly', (46, 3), (46, 5)],
                ['teams-weekly', (46, 5), (46, 7)],
                ['nzl-od-34', (46, 5), (46, 7)],
                ['nzl-t20-33', (46, 5), (46, 7)],
                ['sa-od-42', (46, 5), (46, 7)]]
    x = catagorise_training(db_pairs)

    for k in x.keys():
        print(k, len(pd.concat(x[k])) if len(x[k]) != 0 else 0)

    training_names = x.keys()

    for training in training_names:
        plt.plot([t for t in x[training].keys()], [sum(x[training][age]['Ratdif']) / len(x[training][age]) for age in x[training].keys()])

    plt.legend(training_names)
    #league_id = 97290
    #current_round = 7
    #round_dic = {}
    #for round in [6, 7]:
    #    round_dic[round] = PresentData.youth_pull_league_round_overview(league_id, round_n=round, league_format='league', weeks_since_game=current_round-round)

    #week_pak_recruits = pd.concat(pyc_round_2, pgt_round_3)
    #unique_pak_recruits = week_pak_recruits.drop_duplicates(['PlayerID'])

    #print(pyc_round_2_markdown_text)
    #PlayerDatabase.download_database('u21-national-squads')
    #player_databases = ['market-archive', 'PGT', 'senior-national-squads', 'teams-weekly', 'u16-weekly', 'u21-national-squads', 'nzl-t20-33', 'nzl-od-34', 'sa-od-42']
    #PlayerDatabase.watch_database_list(player_databases)

    #p = PlayerDatabase.player_search(search_settings={'skill1': '8', 'fromSkill1': '9', 'skill2': '7', 'fromSkill2': '7', 'fromAge': '20', 'toAge': '20', 'toAgeWeeks': '11', 'skill3': '1', 'fromSkill3': '5'}, search_type='nat_search', extra_columns=['Wage', 'Nat', 'NatSquad', 'SpareRat'], normalize_age=False)
    #p19 = PlayerDatabase.player_search(search_settings={'skill1': '8', 'fromSkill1': '9', 'skill2': '7', 'fromSkill2': '7', 'toAge': '19', 'skill3': '1', 'fromSkill3': '5'}, search_type='nat_search', extra_columns=['Wage', 'Nat', 'NatSquad', 'SpareRat'], normalize_age=False)
    #allp = pd.concat([p, p19])
    #allp.sort_values('Wage', inplace=True, ascending=False)
    pass
