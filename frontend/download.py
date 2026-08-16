import urllib.request
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

# Pinned versions (must match pubspec.lock: drift 2.33.0, sqlite3 3.3.2).
# The drift web worker speaks a versioned protocol; pulling from `main`
# silently breaks the handshake with the compiled drift 2.33.0 client and
# drops the database into in-memory fallback (lost session on reload).
req_wasm = urllib.request.Request(
    'https://github.com/simolus3/sqlite3.dart/releases/download/sqlite3-3.3.2/sqlite3.wasm',
    headers={'User-Agent': 'Mozilla/5.0'}
)

req_worker = urllib.request.Request(
    'https://github.com/simolus3/drift/releases/download/drift-2.33.0/drift_worker.js',
    headers={'User-Agent': 'Mozilla/5.0'}
)

print("Downloading sqlite3.wasm...")
with urllib.request.urlopen(req_wasm) as response, open('web/sqlite3.wasm', 'wb') as out_file:
    out_file.write(response.read())

print("Downloading drift_worker.js...")
with urllib.request.urlopen(req_worker) as response, open('web/drift_worker.js', 'wb') as out_file:
    out_file.write(response.read())

print("Done.")
