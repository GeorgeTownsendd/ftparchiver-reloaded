import ftputils as FTPUtils
import ftpdatabase as PlayerDatabase
import ftppresentation as PresentData

with open('credentials.txt', 'r') as f:
    CREDENTIALS = f.readline().split(',')
browser = FTPUtils.login(CREDENTIALS)

