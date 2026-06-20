# Whiskey Mapper Source Audit

**HTTP Status:** 200
**Content-Type:** text/html
**Content-Length:** 2011 bytes
**Is Redirect:** False

Found 2 JS bundle(s).
- https://whiskeymapper.com/static/js/2.ce3ec3c2.chunk.js
- https://whiskeymapper.com/static/js/main.aacc1b64.chunk.js

**Patterns found in HTML:** json, whiskey

**Patterns found in JS bundles:**
- https://whiskeymapper.com/static/js/2.ce3ec3c2.chunk.js: api, json, profile, vector, search
- https://whiskeymapper.com/static/js/main.aacc1b64.chunk.js: api, json, whiskey, flavor, similar, profile, search, distillery

**Potential API Endpoints found in bundles:**
- https://maps.googleapis.com
- https://whiskeymapper.com/api
- /maps/api/js?callback=_$_google_map_initialize_$_
- https://api.mapbox.com
- https://api.mapbox.cn
- https://github.com/d3/d3-3.x-api-reference/blob/master/Time-Formatting.md#format
- https://github.com/d3/d3-3.x-api-reference/blob/master/Formatting.md#d3_format

**Decision:** PARTIAL: candidate endpoints/assets found, manual inspection needed