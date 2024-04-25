# Parsing Bot

## Описание
This project is a Python script that uses the Playwright library to automate the collection of data from a website containing car sales ads. The script moves through the pages of the site, extracts information from each ad and saves the data to the PostgreSQL database.

To speed up the process and reduce the load on the server, the script is configured to block image downloads. Exception handling and logging are also included to track errors and other key events during the operation. Errors and important notifications can be sent to the administrator's email using a specialized log handler.

In addition, the script has the functionality of returning to the top of the list of ads when reaching the end or meeting already known ads, which allows it to work in a continuous cycle, regularly updating the database with new data.

## Installation
Step-by-step instructions for setting up the project:

1. Clone the repository:
`git clone https://github.com/DatRush/Parsing_bot.git`

2. Install the required libraries:
`pip install -r requirements.txt`

## Configuration
You need to configure the config file according to the example in config,example.py. Copy it config.example.py in config.py and make the current settings to it:
`cp config.example.py config.py`

## Launch
1. To run the parsing bot:
`python3 parsing_kolesa.py`
This will start the data collection process, in which the script will navigate through the pages of the site, extract data from ads and save them to the database. Make sure that all settings are in config.py is configured correctly, including database and email settings.


## License
The license details can be found in the file LICENSE.txt .