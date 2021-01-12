import FTPUtils as FTPUtils
import PlayerDatabase as PlayerDatabase
import PresentData as PresentData

browser = None
with open('credentials.txt', 'r') as f:
    CREDENTIALS = f.readline().split(',')
browser = FTPUtils.login(CREDENTIALS)

