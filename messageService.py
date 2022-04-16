from lib2to3.pgen2.grammar import opmap
import requests
import os


def send_sms(number, message):
    url = 'https://www.fast2sms.com/dev/bulkV2'
    params = {
        'authorization': os.environ.get("SMS_API_KEY"),
        # your fast2sms api code must be entered here.
        'sender_id': 'FSTSMS',
        'message': message,
        'language': 'english',
        'route': 'v3',
        'numbers': number
    }
    headers = {
    'cache-control': "no-cache"
    }
    response = requests.get(url, headers=headers, params=params)
    status = response.json()  # response.json() returns a JSON object of the URL you have requested.
    print(status)
    return status.get('return') #The get() method returns the value for the specified key if key is in dictionary.