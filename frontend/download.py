import urllib.request
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

req_wasm = urllib.request.Request(
    'https://github.com/simolus3/sqlite3.dart/releases/download/sqlite3-2.4.6/sqlite3.wasm',
    headers={'User-Agent': 'Mozilla/5.0'}
)

req_worker = urllib.request.Request(
    'https://raw.githubusercontent.com/simolus3/drift/main/drift/assets/drift_worker.js',
    headers={'User-Agent': 'Mozilla/5.0'}
)

print("Downloading sqlite3.wasm...")
with urllib.request.urlopen(req_wasm) as response, open('web/sqlite3.wasm', 'wb') as out_file:
    out_file.write(response.read())

print("Downloading drift_worker.js...")
with urllib.request.urlopen(req_worker) as response, open('web/drift_worker.js', 'wb') as out_file:
    out_file.write(response.read())

print("Done.")
