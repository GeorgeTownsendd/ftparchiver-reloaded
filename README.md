Archiving / Player Tracking / Visualization Tool for From the Pavilion (FTP - fromthepavilion.org)

Provides tools to download team data and player searches to .csv files in structured databases.
Additionally provides functionality to configure user defined 'databases' (groups of teams, a transfer market search, or a player search) and auotmate their weekly download.

Databases of players can be tracked over time and viewed interactively in predefined matplotlib plots. 

Example usage (with exisiting database 'senior-national-squads'):


>>> PlayerDatabase.download_database('senior-national-squads')
#Downloads database based on config file senior-national-squads/senior-national-squads.config

>>> PresentData.database_rating_increase_scatter('senior-national-squads', group1_db_entry=[46, 2], group2_db_entry=[46, 3])
#graphs rating increase per week/age of all players in senior-national-squads, colored by team and interactive tooltip with the mouse. 
#db_entry format [seasonnumber, weeknumber]
#requires relevent database to have been downloaded with download_database at the correct times


Functional, but undocumented and still in development. 

!!! Requires a file in the same directory ("credentials.txt") with an FTP username and password on the first two lines. !!!
