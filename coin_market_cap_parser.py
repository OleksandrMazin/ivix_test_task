from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from time import sleep
import csv
import sqlite3
import sys
import signal

from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json

from env import api_key

# number of pager for html parse
PAGE_NUM = 1
# number of api results
API_RESULTS = 500
# csv file output path
CSV_FILE = 'coins.csv'


class CoinMarketCap():
    """
    Parser to get data from https://coinmarketcap.com/ in two ways:
    1) HTML parse - directly getting data from HTML pages, slow but more accurate, since the data is updating near every second
    2) API parse - getting data from https://coinmarketcap.com/api, much faster and simpler to use, but time of updating prices is unknown
    
    Saving data:
    1) DB - more efficient and better if data is needed to be processed in future
    2) CSV - easier to understand for user 
    """
    def __init__(self, parse_option, store_option):
        self.parse_option = parse_option
        self.store_option = store_option
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def turn_on_webdriver(self):
        options = Options()
        options.add_argument("--headless")
        self.driver = webdriver.Firefox(options=options)
        self.wait = WebDriverWait(self.driver, 3)
        
    
    def main(self):
        """
            Main function to parse Coin Market Cap via HTML or API 
        """
        # if no args - return notification
        if self.parse_option != 'html' and self.parse_option != 'api':
            print('choose action html or api')
            return
        
        if self.store_option != 'db' and self.store_option != 'csv':
            print('choose action db or csv')
            return
        
        if self.parse_option == 'html':
            coins = self.get_html_data()
        else:
            coins = self.get_api_data()

        if self.store_option == 'db':
            if self.insert_data_into_bd(coins):
                print('Data was inserted into DB')
        else:
            self.write_to_csv(coins, CSV_FILE)
            print(f'Data was inserter into {CSV_FILE}')
    
    
    def get_api_data(self):
        """
            Function copied from https://pro-api.coinmarketcap.com sample
        """
        # number of api results is passed in API_RESULTS constant
        url = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?start=1&limit={API_RESULTS}&convert=USD'

        headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
        }

        session = Session()
        session.headers.update(headers)

        try:
            response = session.get(url)
            data = json.loads(response.text).get('data')
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)
        except AttributeError:
            return
        
        coins = self.parse_api_data(data)
        return coins
    
    def parse_api_data(self, data):
        coins = list()
        for coin in data:
            rank = coin.get('cmc_rank')
            name = coin.get('name')
            symbol = coin.get('symbol')
            price = coin.get('quote').get('USD').get('price')
            price = round(float(price), 2)
            change = coin.get('quote').get('USD').get('percent_change_24h')
            change = round(float(change), 2)
            cap = coin.get('quote').get('USD').get('market_cap')
            cap = round(float(cap), 2)
            coins.append((rank, name, symbol, f'{float(price):,}', change, f'{float(cap):,}'))
        return coins
    
    def get_html_data(self):
        self.turn_on_webdriver()
        self.driver.get('https://coinmarketcap.com/')
        self.wait.until(EC.presence_of_all_elements_located((By.XPATH, '//*[@class="main-content"]')))
        self.driver.save_screenshot('coins_test.png')
        try:
            coins = self.parse_page()
        except Exception as e:
            print(e)
        finally:
            # closing driver to prevent memory overusage
            print('Closing driver...')
            self.driver.quit()
        return coins

    def parse_page(self):
        """
            Parsing pages via html parse. Loop is working PAGE_NUM times.
            If PAGE_NUM = 5, the parser will parse first 5 pages, for 10 first 10 pages, etc.
        Returns:
            list: list of collected data
        """
        coins = list()
        for i in range(PAGE_NUM):
            for i in range(1, 101):
                rank = self.driver.find_element(By.XPATH, f'//div[5]/div/table/tbody/tr[{i}]/td[2]').text
                name = self.driver.find_element(By.XPATH, f'//div[5]/div/table/tbody/tr[{i}]/td[3]').text
                symbol = name.split('\n')[-2]
                name = ' '.join(name.split('\n')[:-2])
                price = round(float(self.driver.find_element(By.XPATH, f'//div[5]/div/table/tbody/tr[{i}]/td[4]').text.strip('$').replace(',', '')), 2)
                change = round(float(self.driver.find_element(By.XPATH, f'//div[5]/div/table/tbody/tr[{i}]/td[6]').text.strip('%')), 2)
                class_name = self.driver.find_element(By.XPATH, f'//div[5]/div/table/tbody/tr[{i}]/td[6]/span/span').get_attribute('class')
                # checking if change is up or down
                if 'down' in class_name:
                    change = -abs(change)
                cap = round(float(self.driver.find_element(By.XPATH, f'//div[5]/div/table/tbody/tr[{i}]/td[8]/p').text.strip('$').replace(',', '')), 2)
                coins.append((rank, name, symbol, f'{float(price):,}', change, f'{float(cap):,}'))
                
                # every 10 rows scrolls down the page to make sure that all data have been loaded
                if i % 10 == 0:
                    html = self.driver.find_element(By.TAG_NAME, 'html')
                    for _ in range(2):
                        html.send_keys(Keys.PAGE_DOWN)
                    sleep(1)
                    
            self.paginate()
        return coins

    def paginate(self):
        self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[1]/div[2]/div/div[1]/div[7]/div[1]/div/ul/li[10]/a').click()
        self.wait.until(EC.presence_of_all_elements_located((By.XPATH, '//*[@class="main-content"]')))
        
    def write_to_csv(products, data, csv_file):
        """
        Write the extracted product information to a CSV file.
        """
        if not data:
            print("No data found to write to CSV.")
            return False
        
        with open(csv_file, 'w') as file:
            writer = csv.writer(file)
            writer.writerow(["rank", "name", "symbol", "price", "change", "market_cap"]) 
            writer.writerows(data)

        
    def insert_data_into_bd(self, data):
        """
            Inserting data into DB.
            To prevent any duplicates - previous data is deleted
        """
        if not data:
            print("No data found to write to DB.")
            return
        
        cursor = self.create_db()
        # cleaning previous data
        cursor.execute("DELETE FROM coins")
        self.connection.commit()
        for coin in data:
            cursor.execute("""
                INSERT INTO coins (rank, name, symbol, price, change, market_cap)
                VALUES (?, ?, ?, ?, ?, ?)
                """, coin)
        
        self.connection.commit()
        self.connection.close()
        return True
        
    def create_db(self):
        """
            Connection to DB and creating a new table
            If the DB and table are present - only connection
        """
        self.connection = sqlite3.connect("ivix_task.db")
        cursor = self.connection.cursor()
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS coins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rank INTEGER,
                        name TEXT,
                        symbol TEXT,
                        price TEXT,
                        change FLOAT,
                        market_cap TEXT
                    )
                    """)
        self.connection.commit()
        return cursor
    
    # gently closing crawler in case of ctrl+c
    def signal_handler(self, sig, frame):
        print('Shutting down...')
        try:
            # closing driver to prevent memory overusage
            self.driver.quit()
            print('Driver closed')
        except:
            pass
        sys.exit(0)
    
    
if '__main__' == __name__:
    try:
        parse_option = sys.argv[1]
        store_option = sys.argv[2]
        proc = CoinMarketCap(parse_option, store_option).main()
    except IndexError:
        print('Enter parse and store options')
        
    
    
