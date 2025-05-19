import requests
import json
from datetime import datetime
from time import sleep, strftime, localtime
import sys
import signal


class CryproCrawler():
    """
        Class to run crypto crawler. 
        Crypto crawler gets endpoint and parse JSON data with Bitcoin price and output the last 10 different results.
    """
    def __init__(self):
        self.url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_last_updated_at=true'
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def parse(self):
        """
            Sending requests every 15 sec and parsing results.
            The last 10 results are outputs in terminal. 
        """
        self.clear_lines(10)
        output = list()
        while True:
            response = requests.get(self.url)
            status_code = response.status_code

            if status_code == 200:
                data = json.loads(response.text)
                try:
                    timestamp = strftime('%Y-%m-%dT%H:%M:%S', localtime(data.get('bitcoin').get('last_updated_at')))
                    bit_price = data.get('bitcoin').get('usd')
                    
                # handling empty response
                except AttributeError as e:
                    print(f'Error occured - {e}')
                    print('Shutting down...')
                    return
                
                # preventing output duplicates
                if (timestamp, bit_price) not in output:
                    output.append((timestamp, bit_price))
                    
                # storing last 10 results
                self.clear_lines(10)
                if len(output) > 10:
                    output.pop(0)

                for i in output:
                    print(f'[{i[0]}] BTC → USD: SMA({output.index(i) + 1}): ${float(i[1]):,}')
            
            # handling status code 429 (too much requests)
            elif status_code == 429:
                print(f'Too much requests to {self.url}, please wait')
                sleep(60)
            
            # handling status code 5XX
            elif status_code >= 500:
                tries = 0
                ping = 1
                
                while True:
                    tries += 1
                    if self.handle_500_status_code:
                        # increasing latency between requests
                        sleep(ping)
                        ping = ping * 2
                    else:
                        break
                    
                    if tries % 5 == 0:
                        print(f'Status code {status_code}, trying to reconnect')
            sleep(12)
    
    def handle_500_status_code(self):
        """
            Handling 5XX status code    
        Returns:
            bool (True): if request returns 5XX status code - repeat process with increased latency
            bool (False): status code not 5XX, continue parsing
        """
        response = requests.get(self.url)
        status_code = response.status_code
        if status_code >= 500:
            return True
        else:
            return False
    
    # cleaning line to keep only output
    def clear_lines(self, n):
        for _ in range(n):
            sys.stdout.write("\033[F\033[K")
    
    # gently closing crawler
    def signal_handler(self, sig, frame):
        print('Shutting down...')
        # sleep for wait to last request will processed
        sleep(5)
        sys.exit(0)

                   
if '__main__' == __name__:
    proc = CryproCrawler().parse()
    

    