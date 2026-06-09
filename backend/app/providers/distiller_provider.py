import httpx
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime
from app.providers.base import WhiskyProvider
from app.models.schemas import WhiskySearchItem, WhiskyPriceItem

class DistillerProvider(WhiskyProvider):
    def __init__(self):
        self.base_url = "https://distiller.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        }

    def get_name(self) -> str:
        return "Distiller Live"

    def search(self, query: str) -> List[WhiskySearchItem]:
        url = f"{self.base_url}/search?term={query}"
        try:
            with httpx.Client(headers=self.headers, follow_redirects=True, timeout=10.0) as client:
                res = client.get(url)
            if res.status_code != 200:
                return []
                
            soup = BeautifulSoup(res.text, 'html.parser')
            results = []
            
            for li in soup.select('li.spirit')[:15]:
                name_elem = li.select_one('.name')
                if not name_elem:
                    continue
                name = name_elem.text.strip()
                
                link_elem = li.select_one('a')
                if not link_elem or not link_elem.get('href'):
                    continue
                href = link_elem['href']
                slug = href.split('/')[-1]
                
                type_elem = li.select_one('.accented-text')
                category = type_elem.text.strip() if type_elem else "Unknown"
                
                loc_elem = li.select_one('.location')
                location = loc_elem.text.strip() if loc_elem else "Unknown"
                country = location.split(',')[-1].strip() if ',' in location else location
                
                results.append(WhiskySearchItem(
                    external_id=f"ds-{slug}",
                    name=name,
                    country=country,
                    region=location,
                    category=category,
                    age=None, # Parsed in get_details if available
                    abv=None,
                    cask_type="Unknown",
                    tasting_notes=[],
                    companion_suggestions=[],
                    global_rating=None, # Fetch in get_details
                    default_price=0.0,
                    currency="USD",
                    source_name=self.get_name(),
                    source_url=f"{self.base_url}{href}"
                ))
            return results
        except Exception as e:
            print(f"Distiller search error: {e}")
            return []

    def get_details(self, external_id: str) -> Optional[WhiskySearchItem]:
        slug = external_id.replace("ds-", "")
        url = f"{self.base_url}/spirits/{slug}"
        try:
            with httpx.Client(headers=self.headers, follow_redirects=True, timeout=10.0) as client:
                res = client.get(url)
            if res.status_code != 200:
                return None
                
            soup = BeautifulSoup(res.text, 'html.parser')
            
            name_elem = soup.select_one('h1.spirit-name')
            name = name_elem.text.strip() if name_elem else slug.replace("-", " ").title()
            
            loc_elem = soup.select_one('.location')
            location = loc_elem.text.strip() if loc_elem else "Unknown"
            country = location.split(',')[-1].strip() if ',' in location else location
            
            type_elem = soup.select_one('.spirit-type')
            category = type_elem.text.strip() if type_elem else "Unknown"
            
            # Details block
            details = {}
            for row in soup.select('.detail-row'):
                label = row.select_one('.label')
                val = row.select_one('.value')
                if label and val:
                    details[label.text.strip().lower()] = val.text.strip()
                    
            age_str = details.get('age', '')
            age = None
            if age_str.isdigit():
                age = int(age_str)
            elif 'year' in age_str.lower():
                try:
                    age = int(age_str.split()[0])
                except: pass
                
            abv_str = details.get('abv', '')
            abv = None
            if abv_str:
                try:
                    abv = float(abv_str)
                except: pass
                
            cask_type = details.get('cask type', 'Unknown')
            
            notes = []
            
            # Extract Flavor Profile
            for h3 in soup.find_all('h3'):
                if h3.parent and h3.parent.find_previous_sibling('h2', string=lambda s: s and 'Flavor Profile' in s):
                    val = h3.text.strip()
                    if 'Remove ads' not in val:
                        notes.append(val)
                        
            # Extract Tasting Notes paragraph
            tn_header = soup.find('h2', string=lambda s: s and 'Tasting Notes' in s)
            if tn_header and tn_header.parent:
                # the paragraph is often mixed in the text of the parent
                tn_text = tn_header.parent.text.replace('Tasting Notes', '').strip()
                # Split by newline and take the first real paragraph
                lines = [l.strip() for l in tn_text.split('\n') if len(l.strip()) > 10 and 'Added by' not in l]
                if lines:
                    notes.append(lines[0][:150] + "...") # Limit length
                    
            # Generate Companion Suggestions based on notes/category
            companions = []
            notes_str = " ".join(notes).lower()
            if "peat" in notes_str or "smoke" in notes_str or "smoky" in notes_str:
                companions.extend(["Smoked Brisket", "Oysters", "Blue Cheese", "Dark Chocolate"])
            elif "sherry" in notes_str or "fruit" in notes_str or "raisin" in notes_str:
                companions.extend(["Dark Chocolate Truffles", "Aged Cheddar", "Dried Figs", "Pecan Pie"])
            elif "vanilla" in notes_str or "honey" in notes_str or "citrus" in notes_str:
                companions.extend(["Light Seafood", "Sushi", "Vanilla Pudding", "Soft Goat Cheese"])
            elif category and "bourbon" in category.lower():
                companions.extend(["BBQ Ribs", "Caramel Popcorn", "Grilled Steak", "Apple Pie"])
            else:
                companions.extend(["Mixed Nuts", "Mild Cheese Board", "Dark Chocolate"])
                
            # Remove duplicates and limit
            companions = list(dict.fromkeys(companions))[:3]
            
            price = 0.0
            price_elem = soup.select_one('.price')
            if price_elem:
                p_text = price_elem.text.strip().replace('$', '').replace(',', '')
                try:
                    price = float(p_text)
                except: pass
                
            global_rating = None
            rating_elem = soup.select_one('.rating-display__value')
            if rating_elem:
                try:
                    # Distiller rating is out of 100
                    global_rating = float(rating_elem.text.strip())
                except: pass

            return WhiskySearchItem(
                external_id=external_id,
                name=name,
                country=country,
                region=location,
                category=category,
                age=age,
                abv=abv,
                cask_type=cask_type,
                tasting_notes=notes[:5],
                companion_suggestions=companions,
                global_rating=global_rating,
                default_price=price,
                currency="USD",
                source_name=self.get_name(),
                source_url=url
            )
        except Exception as e:
            print(f"Distiller details error: {e}")
            return None

    def get_prices(self, external_id: str) -> List[WhiskyPriceItem]:
        details = self.get_details(external_id)
        if details and details.default_price > 0:
            return [
                WhiskyPriceItem(
                    source_name=self.get_name(),
                    price=details.default_price,
                    currency=details.currency,
                    country="Global",
                    source_url=details.source_url,
                    fetched_at=datetime.utcnow().isoformat() + "Z",
                    is_manual=False
                )
            ]
        return []
