Usage:
    1. Create a new virtual enviroment `python -m venv venv`;
    2. Install requirements `pip install -r requirements.txt`;

crypto_crawler.py
    Run `python crypto_crawler.py`.

coin_market_cap_parser.py
    to run coin_market_cap_parser.py run `python coin_market_cap_parser.py <arg_1> <arg_2>`:
        arg_1 - type of parsing, could be html parsing or API parsing
        arg_2 - type of data storage, could be csv or db

    `python coin_market_cap_parser.py html csv` will run parser to get data via html parsing and store data into the DB 
    `python coin_market_cap_parser.py html csv` will run parser to get data via API parsing and store data into the CSV file

    NOTE! To use API requests - go to https://coinmarketcap.com/api/documentation/v1/#section/Introduction to generate API key
    API key is stored in the env.py file 



NOTES:
crypto_crawler.py
    Task:
        Create a script to get data from endpoint and output last 10 results.

    Dev note:
        The API works not like in task description. In case of request every 1 second - after 5 requests the API returns 429 status code (too much requests).
        Increasd request time from 1 to 12 sec to handle 429 status code. 
        Also, since the API not updates every 1 sec - there is no reason for so often requests.


