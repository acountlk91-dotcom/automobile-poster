import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time
import os
import pickle

# Try DrissionPage, but don't fail if missing
try:
    from DrissionPage import ChromiumPage
    HAS_DRISSION = True
except ImportError:
    HAS_DRISSION = False
    print("WARNING: DrissionPage not found. Using requests (limited capability).")

class CarScraper:
    BASE_URL = "https://www.automobile-catalog.com/"
    COOKIES_FILE = "cf_cookies.pkl"

    def __init__(self, use_drission=True):
        self.use_drission = use_drission and HAS_DRISSION
        print(f"Initializing Scraper (DrissionPage={self.use_drission})...")

        if self.use_drission:
            try:
                # Use auto_port to avoid conflicts with existing processes
                from DrissionPage import ChromiumOptions
                co = ChromiumOptions()
                co.auto_port()
                self.page = ChromiumPage(addr_or_opts=co)
                self._load_cookies_drission()
            except Exception as e:
                print(f"DrissionPage init failed: {e}. Falling back to requests.")
                self.use_drission = False
                self.session = requests.Session()
                self._load_cookies_requests()
        else:
            self.session = requests.Session()
            self._load_cookies_requests()

            # Add headers
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.BASE_URL
            })

    def _load_cookies_drission(self):
        if os.path.exists(self.COOKIES_FILE):
             try:
                with open(self.COOKIES_FILE, 'rb') as f:
                    cookies = pickle.load(f)
                for c in cookies:
                    try: self.page.set.cookies(c)
                    except: pass
             except: pass

    def _load_cookies_requests(self):
        if os.path.exists(self.COOKIES_FILE):
             try:
                with open(self.COOKIES_FILE, 'rb') as f:
                    cookies = pickle.load(f)
                c_dict = {}
                for c in cookies:
                    c_dict[c['name']] = c['value']
                self.session.cookies.update(c_dict)
             except: pass

    def _get_soup(self, url):
        print(f"Navigating to {url}...")

        if self.use_drission:
            self.page.get(url)
            self.page.get(url)
            # Smarter CF wait
            for i in range(20): # 40 seconds max
                title = self.page.title.lower()
                if "just a moment" not in title and "один момент" not in title and "cloudflare" not in title:
                    break
                print(f"Waiting for Cloudflare... ({i+1}/20)")
                time.sleep(2)

            # Additional check for turnstile iframe if still stuck?
            return BeautifulSoup(self.page.html, 'html.parser')
        else:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"Error: Status {resp.status_code}")
            return BeautifulSoup(resp.text, 'html.parser')

    def close(self):
        if self.use_drission:
            try: self.page.quit()
            except: pass

    def search_make(self, make_name):
        # SIMPLIFIED SEARCH
        print(f"Searching for {make_name}...")
        soup = self._get_soup(self.BASE_URL)

        # 1. Look for direct link text
        for a in soup.find_all('a', href=True):
            if make_name.lower() == a.get_text(strip=True).lower():
                return urljoin(self.BASE_URL, a['href'])

        # 2. Check browse.php if not found
        browse_url = urljoin(self.BASE_URL, "browse.php")
        soup = self._get_soup(browse_url)
        for a in soup.find_all('a', href=True):
            if make_name.lower() in a.get_text(strip=True).lower():
                 return urljoin(self.BASE_URL, a['href'])

        # DEBUG: Dump HTML if failed
        with open("debug_failed_search.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
        print("Dumping HTML to debug_failed_search.html")

        raise ValueError(f"Make '{make_name}' not found. Page title: {soup.title}")

    def get_models(self, make_url, make_name=None):
        soup = self._get_soup(make_url)
        models = []

        # Parse logic (simplified from original)
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)

            if '/model/' in href or '/make/' in href:
                if len(text) > 2 and 'photo' not in href:
                    # Basic cleanup
                    full_url = urljoin(self.BASE_URL, href)
                    models.append({
                        'name': text,
                        'url': full_url,
                        'start_year': 0, 'end_year': 0 # formatting filler
                    })

        if not models:
            print("[WARN] No models found. Dumping HTML to debug_models_dump.html")
            with open("debug_models_dump.html", "w", encoding="utf-8") as f:
                f.write(str(soup))

        return models


    def get_submodels(self, model_url):
        soup = self._get_soup(model_url)
        submodels = []

        tables = soup.find_all('table')
        for table in tables:
            # Submodel Title is usually in a <p style="font-size: 14pt;monospace">
            # We look for something that looks like a title
            title_p = table.find('p', style=lambda s: s and '14pt' in s)
            if not title_p: continue

            title_text = title_p.get_text(strip=True)

            # Find description text (specs summary)
            desc_p = table.find('p', style=lambda s: s and '12pt' in s)
            desc_text = desc_p.get_text(" ", strip=True) if desc_p else ""

            if not desc_text.strip().startswith("Cars belonging to"):
                continue

            # Image
            image_url = None
            imgs = table.find_all('img')
            for img in imgs:
                src = img.get('src', '')
                data_src = img.get('data-src', '')
                valid = src if ('/picto30/' in src or '/picto28h/' in src) else (data_src if ('/picto30/' in data_src or '/picto28h/' in data_src) else None)
                if valid:
                    image_url = urljoin(self.BASE_URL, valid)
                    break

            # Parse rough specs from description for searching
            year = "N/A"
            y_match = re.search(r'years\s+(\d{4}\s*-\s*\d{4})', desc_text)
            if y_match: year = y_match.group(1).replace(' ', '')

            # Navigation URL (to full specs)
            nav_url = None
            for a in table.find_all('a', href=True):
                if '/make/' in a['href'] and '.html' in a['href']:
                     nav_url = urljoin(self.BASE_URL, a['href'])
                     break

            submodels.append({
                'name': title_text,
                'description': desc_text,
                'image_url': image_url,
                'navigation_url': nav_url,
                'year': year
            })

        return submodels

    def get_specs(self, config_url):
        soup = self._get_soup(config_url)

        # Initialize default specs
        specs = {
            'year': 'N/A', 'engine': 'N/A', 'power': 'N/A', 'torque': 'N/A',
            'weight': 'N/A', '0-100': 'N/A', 'top_speed': 'N/A', 'image_url': None
        }

        # Get full text content
        text_content = soup.get_text(" ", strip=True)
        # Normalize spaces
        text_content = re.sub(r'\s+', ' ', text_content)

        # Patterns
        patterns = {
            'engine': [r'displacement[\s\:]*(\d+[\s]*cm3)', r'capacity[\s\:]*(\d+[\s]*cm3)', r'(\d+\s*cu\s*in)'],
            'power': [r'power[\s\:]*[\d\.,\s]*kW[\s/]*(\d+[\s]*hp)', r'power[\s\:]*.*?(\d+[\s]*PS)', r'(\d+[\s]*PS)', r'(\d+[\s]*hp)'],
            'torque': [r'torque[\s\:]*(\d+[\s]*Nm)', r'torque[\s\:]*[\d\.,\s]*Nm[\s/]*(\d+[\s]*lb-ft)', r'(\d+[\s]*Nm)', r'(\d+[\s]*lb-ft)'],
            'year': [r'(?:manufactured|sold).*?in[\s]*(\d{4})'],
            'top_speed': [r'top[\s]*speed[\s\:]*(\d+)', r'(\d+)\s*km/h', r'(\d+)\s*mph'],
            '0-100': [r'0-[\s]*100[\s]*km/h[\s\:]*(\d+\.?\d*)', r'0-[\s]100[\s]*km/h[\s]*(\d+\.?\d*)', r'0-\s*60\s*mph\s*(\d+\.?\d*)'],
            'weight': [r'curb[\s]*weight[\s\:]*(\d+[\s]*kg)', r'weight[\s\:]*(\d+[\s]*kg)']
        }

        for key, pat_list in patterns.items():
            for pat in pat_list:
                m = re.search(pat, text_content, re.IGNORECASE)
                if m:
                    specs[key] = m.group(1)
                    break

        # Fallback Year from Title
        if specs['year'] == 'N/A' or not specs['year']:
            title = soup.find('title')
            if title:
                ym = re.search(r'\b(19|20)\d{2}\b', title.text)
                if ym:
                    specs['year'] = ym.group(0)

        # Image Logic - Enhanced
        best_img = None

        # Normalize make for check
        make_slug = self.current_make.lower().replace(' ', '_') if hasattr(self, 'current_make') else ''
        if not make_slug and '/make/' in config_url:
            try:
                parts = config_url.split('/make/')
                if len(parts) > 1:
                    make_slug = parts[1].split('/')[0]
            except:
                pass

        # 1. Try to find the specific "blue table" image (main catalog image)
        blue_tds = soup.find_all('td', style=lambda s: s and '#3333ff' in s.lower())
        if not blue_tds:
            blue_tds = soup.find_all('td', bgcolor=re.compile(r'#?3333ff', re.I))

        for td in blue_tds:
            img = td.find('img')
            if img:
                src = img.get('data-src') or img.get('src')
                if src and ('picto' in src or 'photo' in src):
                    # Strict make name check
                    if make_slug:
                        make_pattern = make_slug.replace('_', '[-_]')
                        if not re.search(make_pattern, src.lower()):
                            continue

                    if 'driver' in src.lower() or 'promo' in src.lower():
                        continue
                    best_img = src
                    break

        # 2. Fallback to scoring logic
        if not best_img:
            potential_images = []
            imgs = soup.find_all('img')

            for img in imgs:
                src = img.get('data-src') or img.get('src') or ''
                if not src or ('picto' not in src and 'photo' not in src):
                    continue

                if make_slug:
                    make_pattern = make_slug.replace('_', '[-_]')
                    if not re.search(make_pattern, src.lower()):
                        continue

                width = 0
                try:
                    width = int(img.get('width', 0))
                except:
                    pass

                if 'pictocrop' in src and width < 200:
                    continue

                score = width
                if 'picto30' in src:
                    score += 500
                elif 'picto28h' in src:
                    score += 400

                potential_images.append({'src': src, 'width': width, 'score': score})

            potential_images.sort(key=lambda x: x['score'], reverse=True)
            if potential_images:
                 best_img = potential_images[0]['src']

        if best_img:
            if not best_img.startswith('http'):
                 from urllib.parse import urljoin
                 base = self.BASE_URL.rstrip('/')
                 path = best_img.lstrip('/')
                 best_img = f"{base}/{path}"
        specs['image_url'] = best_img

        return specs

    def download_image(self, url, path):
        print(f"Downloading {url} to {path}...")
        if not url: return False

        # Ensure directory exists
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Force delete old file to avoid using stale image
        if os.path.exists(path):
            try: os.remove(path)
            except: pass

        try:
            # 1. Try requests with LIVE cookies (most efficient)
            if not hasattr(self, 'session'):
                import requests
                self.session = requests.Session()

            if self.use_drission and hasattr(self, 'page'):
                try:
                    c_dict = {c['name']: c['value'] for c in self.page.cookies()}
                    self.session.cookies.update(c_dict)
                except: pass

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.BASE_URL,
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
            }

            resp = self.session.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                with open(path, 'wb') as f:
                    f.write(resp.content)
                print("Download success via requests.")
                return True

            # 2. Try DrissionPage Screenshot (The Foolproof Way)
            if self.use_drission and hasattr(self, 'page'):
                print("Requests failed. Attempting screenshot capture...")
                try:
                    # Navigate to the image directly
                    self.page.get(url)
                    # Wait for image to render
                    import time
                    time.sleep(2)
                    # Save screenshot of the whole page (image usually takes full visible area)
                    # We can also try to find the img element
                    img_ele = self.page.ele('tag:img')
                    if img_ele:
                        img_ele.get_screenshot(path=path)
                    else:
                        self.page.get_screenshot(path)

                    if os.path.exists(path) and os.path.getsize(path) > 1000:
                        print("Download success via screenshot.")
                        return True
                except Exception as screenshot_err:
                    print(f"Screenshot capture failed: {screenshot_err}")

            print(f"All download methods failed (Last status: {resp.status_code if 'resp' in locals() else 'N/A'})")
            return False

        except Exception as e:
            print(f"Global download exception: {str(e).encode('ascii', errors='ignore').decode()}")
            return False
