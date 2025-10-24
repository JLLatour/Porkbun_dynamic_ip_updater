This Python script automatically monitors and update one or more A records on Porkbun DNS when your public IP address changes.

The file updater.conf must be in the same directory as the main with the following format:
  API_KEY = 'your_porkbun_api_key'
  SECRET_KEY = 'your_porkbun_secret_key'
  DOMAINS = 'sub1.domain.com', 'sub2.domain.org'
  
Dependencies
  •	Python 3.x
  •	requests library
    -	pip install requests
