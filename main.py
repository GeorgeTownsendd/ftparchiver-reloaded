import FTPUtils as FTPUtils
import PlayerDatabase as PlayerDatabase
import PresentData as PresentData

with open('credentials.txt', 'r') as f:
    CREDENTIALS = f.readline().split(',')

browser = FTPUtils.login(CREDENTIALS)
x = PlayerDatabase.player_search(search_type='transfer_market', use_browser=browser)
