import urllib.request
import ssl
import os

ssl._create_default_https_context = ssl._create_unverified_context

url = "https://raw.githubusercontent.com/AaronScruggs/whiskey-api/master/production_data.csv"

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

os.makedirs("data", exist_ok=True)
print("Downloading CSV...")
with urllib.request.urlopen(req) as response, open('data/whisky_database.csv', 'wb') as out_file:
    out_file.write(response.read())

print("First few lines:")
with open('data/whisky_database.csv', 'r', encoding='utf-8') as f:
    for _ in range(5):
        print(f.readline().strip())
