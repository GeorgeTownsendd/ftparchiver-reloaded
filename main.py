import FTPUtils as FTPUtils
import PlayerDatabase as PlayerDatabase
import PresentData as PresentData

browser = None
with open('credentials.txt', 'r') as f:
    CREDENTIALS = f.readline().split(',')
#browser = FTPUtils.login(CREDENTIALS)


#database_list = ['teams-weekly', 'market-archive', 'nzl-od-34', 'u16-weekly', 'u21-national-squads', 'teams-weekly', 'nzl-t20-33', 'sa-od-42', 'PGT', 'u21-national-squads']
#db = PlayerDatabase.watch_database_list(database_list, browser=browser)
