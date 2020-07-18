import os
import time
import datetime
import pickle
import re
from robobrowser import RoboBrowser
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as datacolors
import matplotlib.patches as mpatches
import matplotlib
import openpyxl
from colour import Color
from pytz import timezone
import pause
import imageio
import calendar

ORDERED_SKILLS = [['ID', 'Player', 'Nat', 'Deadline', 'Current Bid'], ['Rating', 'Exp', 'Talents', 'BT'], ['Bat', 'Bowl', 'Keep', 'Field'], ['End', 'Tech', 'Pow']]
SKILL_LEVELS = ['atrocious', 'dreadful', 'poor', 'ordinary', 'average', 'reasonable', 'capable', 'reliable', 'accomplished', 'expert', 'outstanding', 'spectacular', 'exceptional', 'world class', 'elite', 'legendary']
browser = None


with open('credentials.txt', 'r') as f:
    CREDENTIALS = f.readline().split(',')

class Player():
    def __init__(self, ID, market_info=None):
        self.class_version = '1.5'
        self.ID = ID
        self.instancetime = str(int(time.time()))

        player_page = pages_from_id(self.ID, t = 'player')
        stats = self.player_stats_from_page(player_page)
        stats['Age'] = stats['Age'][:2] + '.' + stats['Age'][9:11]
        self.stats = stats

        if market_info != None:
            bid, team_bid = market_info['Current Bid'].split(' ', 1)
            deadline = datetime.datetime.strptime(market_info['Deadline'], '%d %b %Y%H:%M')

            self.stats['Name'] = market_info['Player']
            self.stats['Current Bid'] = bid
            self.stats['Current Buyer'] = team_bid
            self.stats['Deadline'] = deadline
            self.stats['Price'] = -1

    def print_self(self):
        if 'Price' not in self.stats.keys():
            self.stats['Price'] = - 1
        cata_skills = ['Bat.', 'Bowl.', 'Tech.', 'Field.', 'Power', 'End.', 'Keep.', 'Capt.', 'Exp.']
        named_skills = ['Bats', 'Bowls', 'Nat.', 'Talents']
        num_skills = ['Price', 'Age', 'Rating', 'Wage']

        print('--- PLAYER ID: {} ---\n'.format(self.ID))
        for skill in num_skills + named_skills + cata_skills:
            if skill == cata_skills[0] or skill == named_skills[0]:
                print('\n\n')
            print('{} : {}'.format(skill, self.stats[skill]))

        print('\n--- end of {} ---\n'.format(self.ID))

    def player_stats_from_page(self, page):
        info = pd.read_html(page)
        infodic = {}
        for x in range(0, len(info[0]), 2):
            try:
                for stat in zip(info[0][x], info[0][x + 1]):
                    infodic[stat[0]] = stat[1]
            except:
                pass
        return infodic

    def calculate_spare_ratings(self, r=False):
        skill_rating_sum = 0
        for skill in ['Bat.', 'Bowl.', 'Keep.', 'Field.', 'End.', 'Tech.', 'Power']:
            if SKILL_LEVELS.index(self.stats[skill]) == 0:
                skill_rating_sum += 500
            else:
                skill_rating_sum += (SKILL_LEVELS.index(self.stats[skill]) * 1000)

        spare_ratings = int(self.stats['Rating']) - skill_rating_sum
        print('{} spare rating for player {}'.format(spare_ratings, self.ID))

        if r:
            return spare_ratings

def log_event(logtext, logtype, logfile):
    current_time = datetime.datetime.now()
    if logfile == 'default':
        logfile = 'ftp_archiver_output_history.txt'
    if logtype in ['full', 'console']:
        print('[{}] '.format(current_time.strftime('%m/%d/%Y-%H:%M:%S')) + logtext)
    if logtype in ['full', 'file']:
        with open(logfile, 'a') as f:
            f.write('[{}] '.format(current_time.strftime('%m/%d/%Y-%H:%M:%S')) + logtext + '\n')

def load_transfer_history(ID, database_dir='players/'):
    transferdir = database_dir + str(ID) + '/' + 'transfer.txt'
    sales = []
    with open(transferdir, 'r') as playerfile:
        for sale in playerfile.readlines():
            sale = sale[:-1]
            sale = sale.split(',')
            sales.append(sale)

    return sales[0] if time == 'recent' and len(sales) > 0 else sales

def save_player_instance(player, database_dir='players/'):
    if not os.path.exists(database_dir):
        os.mkdir(database_dir)

    playerdir = database_dir + str(player.ID) + '/'
    if not os.path.exists(playerdir):
        os.mkdir(playerdir)

    filename = database_dir + str(player.ID) + '/' + str(player.instancetime)
    with open(filename, 'wb') as playerfile:
        pickle.dump(player, playerfile)

def load_player_instance(ID, instancetime, database_dir='players/'):
    playerdir = database_dir + str(ID) + '/'
    if isinstance(instancetime, type(list)):
        instancetime = instancetime[0][0]

    filename = playerdir + str(instancetime)
    with open(filename, 'rb') as playerfile:
        player = pickle.load(playerfile)
    if os.path.exists(database_dir + '/{}/transfer.txt'.format(ID)):
        transfer_history = load_transfer_history(ID, database_dir=database_dir)
        #print(ID, transfer_history)
        for sale in transfer_history:
            offset = abs((datetime.datetime.strptime(sale[0], '%d %b %y %H %M') - player.stats['Deadline']))
            if offset.total_seconds() < 14400:
                player.sale_type = 'Completed'
                player.stats['Deadline'] = datetime.datetime.strptime(sale[0], '%d %b %y %H %M')
                player.stats['Price'] = sale[3]
                player.stats['Winning Bid'] = sale[2]
                break
        else:
            player.sale_type = 'Incomplete'
            player.stats['Winning Bid'] = None

        return player
    else:
        print('Transfer history not saved for {}'.format(ID))
        player.sale_type = 'Unknown'
        return player

def load_player_instances(ID, instancetimes='all', duplicates=False, database_dir='players/'):
    sold_instances = []
    unsold_instances = []
    player_instancetimes = []

    if instancetimes == 'all':
        player_instancetimes = [x for x in os.listdir(database_dir + str(ID) + '/') if x.isdigit()]

    if instancetimes == 'recent':
        player_instancetimes = sorted([x for x in os.listdir(database_dir + str(ID) + '/') if x.isdigit()], key = lambda x : int(x))

    for t in player_instancetimes:
        try:
            p = load_player_instance(ID, instancetime=t, database_dir=database_dir)
            if p.sale_type == 'Completed':
                if not duplicates:
                    if not p.stats['Deadline'] in [t.stats['Deadline'] for t in sold_instances]:
                        sold_instances.append(p)
                else:
                    sold_instances.append(p)
            elif p.sale_type == 'Incomplete':
                if not duplicates:
                    if not p.stats['Deadline'] in [t.stats['Deadline'] for t in unsold_instances]:
                        unsold_instances.append(p)
                else:
                    unsold_instances.append(p)
        except ModuleNotFoundError:
            print('Module not found: ftparchiver (ID: {})'.format(ID))

        except EOFError:
            print('Pickle end of file error (ID: {})'.format(ID))

    if instancetimes == 'all':
        return sorted(sold_instances + unsold_instances, key = lambda x : x.instancetime)

    elif instancetimes == 'recent':
        return sorted(sold_instances + unsold_instances, key = lambda x : x.instancetime)[-1:]

def load_players(players, instancetimes, database_dir='players/'):
    if (type(players) == str or type(players) == int) and players != 'all':
        players = [players]
    loaded_instances = []
    if players == 'all':
        players = [x for x in os.listdir(database_dir) if x.isdigit()]

    for p in players:
        player_instances = load_player_instances(p, instancetimes=instancetimes, database_dir=database_dir)
        for t in player_instances:
            loaded_instances.append(t)

    return loaded_instances


def transfer_history_from_page(page):
    page = page[page.index('Player Transfers'):]

    prices = [re.sub("\D", "", p) for p in re.findall('\$[0-9]{0,3}[,0-9{3}]+', page)]
    dates = [' '.join(x) for x in re.findall('(\d{2}) (\w{3}) (\d{2})<br/>(\d{2}):(\d{2})', page)] #time.strptime(' '.join(t[0]), '%d %b %y %H %M')
    teams = [x[7:] for x in re.findall('teamId=\d+', page)]
    ratings = [re.sub(',', '', x) for x in re.findall('\d{1,2},\d{3}', page)[1::2]] #only every 2nd item returned by findall is a rating

    return [(dates[i], teams[i*2], teams[(i*2) + 1], prices[i], ratings[i]) for i in range(len(prices))]

def save_transfer_history(players, database_dir = 'players/'):
    for n, player in enumerate([str(x) for x in players]):
        print(player)
        transfer_data = transfer_history_from_page(pages_from_id(player, t='playertransfer'))
        print(transfer_data)

        playerdir = database_dir + (str(player.ID) if not (type(player) == int or type(player) == str) else player) + '/'
        print(playerdir)
        if not os.path.exists(playerdir):
            os.mkdir(playerdir)

        transferdir = playerdir + 'transfer.txt'

        with open(transferdir, 'w') as f:
            for line in transfer_data:
                f.write(str(','.join(line)) + '\n')

def scrape_transfer_market(pages=-1, database_dir = 'players/', logtype ='full', logfile = 'default'):
    global browser, CREDENTIALS
    while pages != 0:
        current_page = get_current_transfers(logtype=logtype, logfile=logfile)

        current_players = [Player(t['ID'], market_info=t) for t in current_page]
        for player in current_players:
            save_player_instance(player, database_dir=database_dir)

        log_event('Successfully saved players to disk.', logtype=logtype, logfile=logfile)

        next_refresh = current_players[-1].stats['Deadline'] - datetime.timedelta(minutes=1)

        next_refresh_local = next_refresh + datetime.timedelta(hours=10) #for SYDNEY NSW (DAYLIGHT SAVINGS!)
        log_event('Pausing program until current page is complete. Restarting at {} UTC ({} local time)'.format(next_refresh.strftime('%m/%d/%Y-%H:%M:%S'), next_refresh_local.strftime('%m/%d/%Y-%H:%M:%S')), logtype=logtype, logfile=logfile)
        pause.until(next_refresh_local)
        log_event('\tProgram execution successfully resumed.' + ' {} pages remaining.'.format(pages) if pages > 1 else '\tProgram execution successfully resumed.', logtype=logtype, logfile=logfile)
        pages -= 1

def pages_from_id(ID, t='player'):
    global browser
    if t == 'player':
        #print('Downloading player ' + str(ID))
        browser.open('http://www.fromthepavilion.org/playerpopup.htm?playerId={}&amp;showExtraSkills=true&amp;club=true'.format(ID))
        pages_data = str(browser.parsed)
    elif t == 'playertransfer':
        print('Downloading transfer history for ' + str(ID))
        browser.open('http://www.fromthepavilion.org/playertransfers.htm?playerId={}'.format(ID))
        pages_data = str(browser.parsed)
    elif t == 'match':
        print('Downloading match ' + str(ID))
        browser.open('https://www.fromthepavilion.org/commentary.htm?gameId={}'.format(ID))
        commentary_data = str(browser.parsed)
        browser.open('https://www.fromthepavilion.org/scorecard.htm?gameId={}'.format(ID))
        scorecard_data = str(browser.parsed)
        browser.open('https://www.fromthepavilion.org/ratings.htm?gameId={}'.format(ID))
        matchratings_data = str(browser.parsed)

        pages_data = [commentary_data, scorecard_data, matchratings_data]

    return pages_data


def playername_from_id(player_id, download_name=False, age_thres=2419200, playernames_file = 'players/player_names.txt', b = '', player_page=None):
    if b == '':
        global browser

    else:
        browser = b

    player_exists_locally = False
    loaded_players = []
    with open(playernames_file, 'r') as f:
        for player in f.readlines():
            loaded_players.append(player[:-1].split(','))

    for player in loaded_players:
        if int(player[0]) == int(player_id):
            if int(player[2]) - int(time.time()) < age_thres:
                print('Player {} found!\n\t{}: {}'.format(player_id, player_id, player[1]))
                return player[1]
            else:
                player_exists_locally = True
                print('Player {} found, but name is beyond threshold age...'.format(player_id))
                break

    if download_name or player_page != None:
        if download_name:
            print('Downloading player {}...'.format(player_id))
            browser.open('http://www.fromthepavilion.org/player.htm?playerId={}'.format(player_id))
            page = str(browser.parsed)
        else:
            page = player_page
        try:
            name = re.findall('<title>From the Pavilion \- [a-zA-Z \']+</title>', page)[0][27:-8]
        except IndexError:
            #print('{} name contains strange characters...')
            return player_id

        print('\t{}: {}'.format(player_id, name))

        with open(playernames_file, 'a') as f:
            f.write('{},{},{}\n'.format(player_id, name, int(time.time())))

        return name

    else:
        if not player_exists_locally:
            print('Player {} not found locally... (and download_new is False)'.format(player_id))
        return player_id

def get_current_transfers(logtype='full', logfile='default'):
    global browser, CREDENTIALS
    if not isinstance(browser, type(None)):
        browser.open('http://www.fromthepavilion.org/transfer.htm')
    if isinstance(browser, type(None)) or 'Play the game your way' in str(browser.parsed):
        logtext = 'User {} session expired. Restarting browser...'.format( CREDENTIALS[0])
        log_event(logtext, logtype=logtype, logfile=logfile)
        browser = login(CREDENTIALS)
        browser.open('http://www.fromthepavilion.org/transfer.htm')
    try:
        form = browser.get_form(action='/transfer.htm')
        browser.submit_form(form)
        raw_player_info = pd.read_html(str(browser.parsed))[0]
        print(raw_player_info)
        player_data = []
        player_ids = re.findall('playerId=\d+&', str(browser.parsed))
        player_ids = [t[9:-1] for t in player_ids]
        for player in range(len(raw_player_info)):
            playerdic = {}
            playerdic['ID'] = player_ids[player]
            for item in raw_player_info.keys():
                playerdic[item] = raw_player_info[item][player]
            player_data.append(playerdic)

        if len(player_data) == 20:
            logtext = 'Successfully fetched first page of transfer market.'
            log_event(logtext, logtype=logtype, logfile=logfile)
            return player_data
        else:
            logtext = 'Error error downloading current transfers - no players found'
            log_event(logtext, logtype=logtype, logfile=logfile)
            return []
    except:
        logtext = 'Critical error downloading current transfers - python error'
        log_event(logtext, logtype=logtype, logfile=logfile)
        return []

def check_login(browser):
    if isinstance(browser, type(None)):
        return False

    browser.open('https://www.fromthepavilion.org/club.htm?teamId=4791')
    if 'Player the game your way' in str(browser.parsed):
        return False
    elif 'Bottybotbots' in str(browser.parsed):
        return True

def login(credentials, logtype='full', logfile='default'):
    browser = RoboBrowser(history=True)
    browser.open('http://www.fromthepavilion.org/')
    form = browser.get_form(action='securityCheck.htm')

    form['j_username'] = credentials[0]
    form['j_password'] = credentials[1]

    browser.submit_form(form)
    if check_login(browser):
        logtext = 'Successfully logged in as user {}.'.format(CREDENTIALS[0])
        log_event(logtext, logtype=logtype, logfile=logfile)
        return browser
    else:
        logtext = 'Failed to log in as user {}'.format(CREDENTIALS[0])
        log_event(logtext, logtype=logtype, logfile=logfile)
        return None

def get_season_day(dateobj, season_start = datetime.datetime(2019, 4, 3)): #season 43
    return (dateobj - season_start).days

def sale_day_graph(players, time_start = datetime.datetime(2020, 4, 3), time_end = datetime.datetime.now()): #season 43
    fig = plt.figure()

    players = [p for p in players if time_end > p.stats['Deadline'] > time_start]
    day = []
    day_cum = {}
    for player in players:
        day_of_season = get_season_day(player.stats['Deadline'], season_start=time_start)

        if time_start < player.stats['Deadline'] < time_end and 'Price' in [x for x in player.stats.keys()]:
            day.append(day_of_season)
            if day_of_season in [x for x in day_cum.keys()]:
                day_cum[day_of_season] += int(player.stats['Price'])
            else:
                day_cum[day_of_season] = int(player.stats['Price'])


    day_range = max(day) + 1
    daynums = [[0, 0] for day in range(day_range)]
    offset = min([x for x in day_cum.keys()])

    for d in range(day_range):
        daynums[d][0] = day.count(d)
        if daynums[d][0] == 0 or d + offset not in [x for x in day_cum.keys()]:
            daynums[d][1] = 0
        else:
            daynums[d][1] = int(day_cum[d + offset]) / daynums[d][0]


    print(len([x for x in range(max(day)+1)]), len([x[0] for x in daynums]))

    plt.bar([x for x in range(max(day)+1)][1:], [x[0] for x in daynums][1:])
    plt.title('Season 44 sales by day')
    plt.xticks([x+1 for x in range(0, day_range, 7) if x % 7 == 0], [(x//7)-1 for x in range(7, day_range+7, 7)])
    plt.xlabel('Week (since Day 1, Week 0, Season 44)')
    plt.ylabel('Total sales')
    plt.show()

def player_sales_by_age_table(players, start_time=datetime.datetime(2020, 4, 6), end_time = datetime.datetime.now()):
    weeks = int(abs((end_time - start_time).total_seconds()) / (60 * 60 * 24 * 7)) + 1
    table = {str(a) : {str(w) : 0 for w in range(weeks+1)} for a in range(16, 33)}

    for playerinstance in players:
        week = str(int(get_season_day(playerinstance.stats['Deadline'], season_start=start_time) // 7))
        age = str(playerinstance.stats['Age'])
        if age in table.keys():
            if week in table[age].keys():
                table[age][week] += int(playerinstance.stats['Price'])
            else:
                print(age, week)
        else:
            print(age, week)
    return table

def save_team_weekly_ratings(teamID, database = 'teamratings/'):
    global browser
    browser.open('https://www.fromthepavilion.org/seniors.htm?teamId={}'.format(teamID))
    page = str(browser.parsed)

    print(teamID)
    timestr = re.findall('Week [0-9]+, Season [0-9]+', page)[0]
    week, season = timestr.split(',')[0].split(' ')[-1], timestr.split(',')[1].split(' ')[-1]
    players = set([x[9:] for x in re.findall('playerId=[0-9]+', page)])
    ratings = [x.split(' ')[0] for x in re.findall('[0-9]+,[0-9]+ rating', page)]

    if not os.path.exists(database + str(teamID) + '/'):
        os.mkdir(database + str(teamID) + '/')
    if not os.path.exists(database + str(teamID) + '/s{}/'.format(season)):
        os.mkdir(database + str(teamID) + '/s{}/'.format(season))

    with open(database + str(teamID) + '/s{}/w{}.txt'.format(season, week), 'w') as f:
        f.write(str(int(time.time())) + '\n')
        for n, p in enumerate(players):
            f.write('{},{}\n'.format(p, ''.join([x for x in ratings[n] if x.isdigit()])))

def rating_over_time(players):
    players = [p for p in players if p.stats['Deadline'] > datetime.datetime(2020, 1, 6)]
    unique_player_dic = {}
    for p in players:
        if p.ID in unique_player_dic.keys():
            unique_player_dic[p.ID].append(p)
        else:
            unique_player_dic[p.ID] = [p]

    playergroups = []

    for pid in unique_player_dic.keys():
        if len(unique_player_dic[pid]) >= 2:
            playergroups.append(unique_player_dic[pid])

    fig, ax = plt.subplots()
    ax.set_title('Player ratings over time')
    ax.set_xlabel('Date (FTP S44)')
    ax.set_ylabel('Rating')
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator())
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%B'))
    #ax.xaxis.set_minor_locator(matplotlib.dates.DayLocator(interval=14))
    #ax.xaxis.set_minor_formatter(matplotlib.dates.DateFormatter('%d'))
    for player in playergroups:
        dates = [pinstance.stats['Deadline'] for pinstance in player]
        dates = matplotlib.dates.date2num(dates)
        ratings = [int(pinstance.stats['Rating']) for pinstance in player]

        ax.plot(dates, ratings)
    fig.autofmt_xdate()

def age_rating_increase(allplayers, out_dir='temp/', season_start = datetime.datetime(2020, 1, 6), histtype='standard', highlighted_countries=False):
    for a in range(16, 33):
        players = [p for p in allplayers if int(p.stats['Age']) == a and p.stats['Deadline'] > season_start]
        #print(len(players))
        unique_player_dic = {}
        for p in players:
            if p.ID in unique_player_dic.keys():
                unique_player_dic[p.ID].append(p)
            else:
                unique_player_dic[p.ID] = [p]

        playergroups = []

        for pid in unique_player_dic.keys():
            if len(unique_player_dic[pid]) >= 2:
                playergroups.append(unique_player_dic[pid])

        added_ratings = []
        added_ratings_by_country = {}
        youth_training, senior_training = 'Monday', 'Wednesday'

        for group in playergroups:
            for n, player in enumerate(sorted([x for x in group], key=lambda x: x.stats['Deadline'])):
                if (n + 1) < len(group):
                    start_date = player.stats['Deadline']
                    end_date = group[n+1].stats['Deadline']

                    weekday_counts = {}
                    for i in range((end_date - start_date).days):
                        day = calendar.day_name[(start_date + datetime.timedelta(days=i + 1)).weekday()]
                        weekday_counts[day] = weekday_counts[day] + 1 if day in weekday_counts else 1

                    try:
                        training_weeks = weekday_counts[youth_training if a <= 21 else senior_training]
                    except KeyError:
                        training_weeks = 0

                    if training_weeks >= 1:
                        ratingchange = int(group[n + 1].stats['Rating']) - int(player.stats['Rating'])
                        average_change = ratingchange / training_weeks
                        if ratingchange/training_weeks > 500 and training_weeks == 1:
                            print(p.ID, a, average_change, group[n+1].stats['Deadline'], player.stats['Deadline'])
                        added_ratings.append(average_change)
                        if highlighted_countries:
                            if player.stats['Nat.'] in highlighted_countries or highlighted_countries == 'all':
                                if player.stats['Nat.'] in added_ratings_by_country.keys():
                                    added_ratings_by_country[player.stats['Nat.']].append(average_change)
                                else:
                                    added_ratings_by_country[player.stats['Nat.']] = [average_change]
                            else:
                                if 'Other' in added_ratings_by_country.keys():
                                    added_ratings_by_country['Other'].append(average_change)
                                else:
                                    added_ratings_by_country['Other'] = [average_change]


        if histtype == 'standard':
            plt.hist(added_ratings, bins=100, range=(-200, 700))

        if histtype == 'stacked':
            histcolors = ['tab:orange', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray', 'tab:olive', 'tab:cyan']
            selectedcolors = histcolors[:len(highlighted_countries)] + ['tab:blue']
            selecteddata = [added_ratings_by_country[c] if c in added_ratings_by_country.keys() else [] for c in sorted(highlighted_countries)] + [added_ratings_by_country['Other']]
            plt.hist(selecteddata, stacked=True, bins=100, range=(-200, 700), color=selectedcolors)
            plt.legend(handles = [mpatches.Patch(color = selectedcolors[n], label = c) for n, c in enumerate(sorted(highlighted_countries))])


        plt.xlabel('Rating increase per week')
        plt.ylabel('Points of data')
        plt.title('Rating increase per week (age = {})'.format(a))
        axes = plt.gca()
        axes.set_ylim([0, 40])

        added_ratings = np.array(added_ratings)
        p90 = np.percentile(added_ratings, 90)
        p50 = np.percentile(added_ratings, 50)
        p50l = plt.axvline(p50, color='b', linestyle='dashed', linewidth=1)
        p90l = plt.axvline(p90, color='r', linestyle='dashed', linewidth=1)

        percentile_legend = plt.legend([p50l, p90l], ['50th percentile', '90th percentile'], loc=1)
        plt.gca().add_artist(percentile_legend)

        if histtype == 'stacked':
            country_legend = plt.legend(handles=[mpatches.Patch(color=selectedcolors[n], label=c) for n, c in enumerate(sorted(highlighted_countries) + ['Other'])], loc=2)
            plt.gca().add_artist(country_legend)

        plt.savefig(out_dir + '{}y.png'.format(a))
        plt.close()

    images = []
    for filename in os.listdir(out_dir):
        if '.png' in filename:
            images.append(imageio.imread(out_dir + filename))
    imageio.mimsave(out_dir + 'timeline.gif', images, duration=1)

def migrate_ages(playerinstances):
    pass

if __name__ == '__main__':
    browser = login(CREDENTIALS)
    #allplayers = load_players('all', 'all', database_dir='players-old/')
    #recentplayers = load_players('all', 'recent', database_dir='players-old/')

    #age_rating_increase(allplayers)
    #rating_over_time(allplayers)

    #with open('teamratings/trainingsurvey-1', 'r') as f:
    #    for line in [x[:-1] for x in f.readlines()]:
    #        print(line)
    #        save_team_weekly_ratings(line)
    #players = load_players(['2236846'], instancetimes='all')
    #rating_over_time(players)
