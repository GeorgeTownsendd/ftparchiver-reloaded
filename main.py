import CoreUtils

CoreUtils.initialize_browser()
browser = CoreUtils.browser

import FTPUtils as FTPUtils
import PlayerDatabase as PlayerDatabase
import PresentData as PresentData
import os
import re

if __name__ == '__main__':
    #PlayerDatabase.download_database('market-archive')
    #PresentData.save_team_training_graphs(4791, 'teams-weekly')
    unique_database_list = list(set(['nzl-od-34', 'u16-weekly', 'market-archive', 'u21-national-squads', 'teams-weekly', 'nzl-t20-33', 'sa-od-42', 'PGT', 'u21-national-squads']))
    dbstack = PlayerDatabase.watch_database_list(unique_database_list)
    #for db in unique_database_list:
    #    PlayerDatabase.download_database(db)
    #db = PlayerDatabase.watch_database_list(unique_database_list)

    #database_name = 'teams-weekly'
    #training_data = FTPUtils.catagorise_training('all')

    #next_database_download = dbstack[0]
    #PlayerDatabase.download_database(next_database_download[1], download_teams_whitelist=next_database_download[2], age_override=next_database_download[3])
