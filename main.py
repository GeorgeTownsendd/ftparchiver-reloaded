import CoreUtils

CoreUtils.initialize_browser()
browser = CoreUtils.browser

import FTPUtils as FTPUtils
import PlayerDatabase as PlayerDatabase
import PresentData as PresentData



unique_database_list = list(set(['market-archive', 'nzl-od-34', 'u16-weekly', 'u21-national-squads', 'teams-weekly', 'nzl-t20-33', 'sa-od-42', 'PGT', 'u21-national-squads']))
db = PlayerDatabase.watch_database_list(unique_database_list)
