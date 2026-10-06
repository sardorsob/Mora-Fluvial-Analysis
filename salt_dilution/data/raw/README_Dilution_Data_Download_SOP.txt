############Things to Remember############
This methods creates multiple datasets that are easy to get confused after the fact. The more metadata that is collected during the injection the easier it will be to put the pieces together days, weeks, months later.

Minimum documentation during each trial: 
- a list of the loggers serial number and location.
- A photo of each logger installation taken a wide enough angle to provide context. 
- sketch map of the locations.
- noting times of sensor recording start/stop, injection dumps, travel times.
 

############Dilution Data Download Standard Operating Procedure############

Following the naming convention I have outlined below will make the python automation scripts run correctly. Not following these instructions may make you have a bad time. 

text surrounded by [square brackets] indicates a user-defined variable.
# <- this denotes a comment.

Folder structure:

Raw data root folder: M:\NCR\NCR_Geology\NCRShare\Imminent_Threats_Program\Projects\ActiveResearch\Dilution\Data\[YYYYMMDD]\raw_data

inside the raw_data folder:
	\LiveReadings 	#Aquatroll LiveReading html files
	\Logs 		#Aquatroll Log html files AND General xlsx files


File name variables:

Full file name example: [YYYYMMDD_HHMMSS]_LiveReadings_[number]_[site]_[bank].[file-extension]

[YYYYMMDD_HHMMSS] - The date and time that the recording was started formatted as Year-Month-Day Hour_minute_second. #Keeping timestamps can be helpful when multiple trials took place or when multiple loggers were used for different things.

General/Log/LiveReading - This denotes the brand of instrument that collected the data. Log and LiveReadings are BOTH associated with In-Situ AquaTrolls. General refers to General DCT430SD.


[number] - For General brand this refers to number (1 or 2) labeled on the carrying case the side of the data logger. 

AquaTrolls have six digit serial numbers printed on the silver casing and are used to ID the sensor when connected via Bluetooth. Serial numbers are the best identifier to track these sensors. 

[site] - e.g. mixing, attenuation, calibration. This refers to location along the channel profile and denotes the experimental purpose of the logger. There are three so far with more added as needed.

[bank] - e.g. River Left, River Right. This refers to the location on the channel bank when facing downstream.

[file-extension] - e.g. .csv, .html, .xlsx. The file extension. Raw data from the Logs and LiveReadings are .html files and get converted to .csv. The general loggers output .xlsx files

Other examples:

20250709_LiveReading_790478_mixing_riverRight.html
20250709_Log_790478_mixing_riverRight.html
20250709_General1_mixing_riverRight.xlsx


AquaTroll 200 Live Readings and Logs.

Live Readings are stored on the mobile device by default and have Live Reading in the file name.

Logs are stored by default on the logger and have Log in the file name. Logs must be downloaded onto mobile device.

In the In-situ app, stop the log or live reading. Go to data and files tab. Select all the relevant files (best to batch all files recorded on a given day). Tap the share button > to save to files > navigate to In-situ > data reports. BEFORE saving make sure the file name is correct. Sharing files in this way results in a zipped folder on the iPad.

Plug the iPad into a computer with iTunes and click on the file sharing. Navigate and select In-Situ\Data Reports. you can't open the data reports folder but make sure it's highlighted and locate save button in bottom right corner to open a file explorer window to select the save location. I usually save to my downloads folder and then continue organizing the files from there.

############Export AquaTroll raw data to csv############
This does not apply to data from the General Loggers. Once all the raw_data files named properly and cozy in their directories right-click on a html file and navigate to open with > Edge browser
This open a browser window and with a data table. 
Find and click the export to csv link along the top of the browser window. This open a file explorer window. save the csv file where it needs to be with SAME FILE NAME but make sure the file extension is csv (NOT .xlsx).

General Logger
- Remove the SD card from logger and connect it to computer.
- Find the spreadsheet file and save as a copy with .xlsx file extension in the Dilution\Data\[YYYYMMDD]\raw_data\Logs


Other Notes:
If you see older files that aren't named correctly then fix it.










	 

