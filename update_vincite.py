#!/usr/bin/env python3
"""
update_vincite.py — Scraping quote SuperEnalotto via proxy CORS
Supporta esecuzione parallela per range di anni (argomento --years YYYY-YYYY)

Uso:
  python update_vincite.py                    # tutte le date mancanti
  python update_vincite.py --years 1997-2001  # solo anni 1997-2001
  python update_vincite.py --merge            # merge dei file parziali in vincite.json
"""

import json, os, re, sys, time, argparse, urllib.request, urllib.error, urllib.parse
from datetime import datetime
from html.parser import HTMLParser

DRAWS_FILE   = 'storico-estrazioni-superenalotto.json'
VINCITE_FILE = 'vincite.json'
DELAY_SEC    = 1.0
MAX_ERRORS   = 10

BASE_URL = 'https://www.superenalotto.com/risultati/estrazione-{d}-{m:02d}-{y}'

PROXIES = [
    lambda u: f'https://api.allorigins.win/raw?url={urllib.parse.quote(u)}&_={int(time.time())}',
    lambda u: f'https://api.codetabs.com/v1/proxy?quest={urllib.parse.quote(u)}',
    lambda u: f'https://api.cors.lol/?url={urllib.parse.quote(u)}',
    lambda u: f'https://corsproxy.io/?url={urllib.parse.quote(u)}',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'it-IT,it;q=0.9',
}

# ── Parser HTML ───────────────────────────────────────────────────────────────
class WinningsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_se_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_text = ''
        self.rows = []
        self.last_h2 = ''
        self.pending_table = False

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.pending_table = True
            self.last_h2 = ''
        elif tag == 'table' and self.pending_table:
            title = self.last_h2
            self.in_se_table = ('SuperEnalotto' in title and
                                'SuperStar' not in title and
                                'WinBox' not in title)
            self.pending_table = False
        elif tag == 'tr' and self.in_se_table:
            self.in_row = True
            self.current_row = []
        elif tag in ('td', 'th') and self.in_row:
            self.in_cell = True
            self.current_text = ''

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.in_cell:
            self.current_row.append(self.current_text.strip())
            self.in_cell = False
        elif tag == 'tr' and self.in_row:
            if len(self.current_row) >= 2:
                self.rows.append(self.current_row[:3])
            self.in_row = False
        elif tag == 'table':
            self.in_se_table = False

    def handle_data(self, data):
        if self.pending_table:
            self.last_h2 += data
        if self.in_cell:
            self.current_text += data


def parse_quote(text):
    text = str(text).strip().replace('€','').replace('\xa0','').replace('\u00a0','').strip()
    if not text or text in ('-','—','N/D','–'):
        return None
    text = text.replace('.','').replace(',','.')
    try:
        v = float(text)
        return v if v > 0 else None
    except ValueError:
        return None


def parse_vincitori(text):
    """Estrae numero vincitori dalla cella (es. '23.212' → 23212)"""
    text = str(text).strip().replace('.', '').replace(',', '').replace(' ', '')
    try:
        return int(text)
    except ValueError:
        return None


def parse_page(html):
    parser = WinningsParser()
    parser.feed(html)
    rows = [r for r in parser.rows
            if r[0] and r[0].lower().strip() not in ('premio','categoria','')]
    if len(rows) < 4:
        return None
    keys = ['p6','p5j','p5','p4','p3','p2']
    result = {}
    for i, key in enumerate(keys):
        if i >= len(rows) or len(rows[i]) < 2:
            result[key] = None
            continue
        prize_text   = rows[i][1]
        winners_text = rows[i][2] if len(rows[i]) > 2 else ''
        winners = parse_vincitori(winners_text)
        # FIX: se vincitori == 0, il valore mostrato è il jackpot accumulato,
        # non un premio unitario reale → forza None
        if winners == 0:
            result[key] = None
        else:
            result[key] = parse_quote(prize_text)
    return result if any(v is not None for v in result.values()) else None


def fetch_via_proxy(target_url):
    for proxy_fn in PROXIES:
        url = proxy_fn(target_url)
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                if len(html) > 1000 and ('Quote' in html or 'punti' in html):
                    return html
        except Exception:
            pass
        time.sleep(0.3)
    return None


def build_url(date_str):
    y, m, d = date_str.split('-')
    return BASE_URL.format(d=int(d), m=int(m), y=y)


def scrape(dates, existing):
    """Scrapa le date mancanti e ritorna dict aggiornato."""
    missing = [d for d in dates if d not in existing or existing[d] == {}]
    print(f'Date da scrapare: {len(missing)} su {len(dates)}')
    consecutive_errors = 0
    scraped = 0

    for i, date_str in enumerate(missing):
        url = build_url(date_str)
        print(f'[{i+1}/{len(missing)}] {date_str}', end=' ', flush=True)

        html = fetch_via_proxy(url)
        if html is None:
            print('→ FAIL')
            existing[date_str] = {}
            consecutive_errors += 1
        else:
            quote = parse_page(html)
            if quote:
                existing[date_str] = quote
                print(f'→ OK  p5={quote.get("p5")}  p3={quote.get("p3")}')
                scraped += 1
                consecutive_errors = 0
            else:
                existing[date_str] = {}
                print('→ no data')
                consecutive_errors += 1

        if consecutive_errors >= MAX_ERRORS:
            print(f'STOP: {MAX_ERRORS} errori consecutivi')
            break

        if i < len(missing) - 1:
            time.sleep(DELAY_SEC)

    return existing, scraped


def load_draws():
    with open(DRAWS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    draws = data.get('draws', data) if isinstance(data, dict) else data
    return sorted(set(d['date'] for d in draws))


def save_vincite(vincite, filename=None):
    fn = filename or VINCITE_FILE
    valid = {k: v for k, v in vincite.items() if v and v != {}}
    output = {
        'version': 1,
        'updated': datetime.utcnow().isoformat() + 'Z',
        'count': len(valid),
        'vincite': dict(sorted(vincite.items()))
    }
    with open(fn, 'w', encoding='utf-8') as f:
        json.dump(output, f, separators=(',',':'), ensure_ascii=False)
    print(f'Salvato {fn}: {len(valid)} quote valide su {len(vincite)} totali')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--years', help='Range anni es. 1997-2001')
    parser.add_argument('--merge', action='store_true', help='Merge file parziali in vincite.json')
    parser.add_argument('--fix-p6', action='store_true', help='Riprocessa voci con p6 non-null (bug jackpot)')
    args = parser.parse_args()

    # ── MERGE mode ───────────────────────────────────────────────────────────
    # ── FIX-P6 mode: riprocessa voci con p6 errato ──────────────────────────
    if getattr(args, 'fix_p6', False):
        print('Fix-p6: riprocesso voci con p6 non-null...')
        if not os.path.exists(VINCITE_FILE):
            print('vincite.json non trovato')
            return
        with open(VINCITE_FILE) as f:
            data = json.load(f)
        vincite = data.get('vincite', {})
        # Trova tutte le voci con p6 non-null (probabilmente errate)
        to_fix = [d for d, v in vincite.items() if v and isinstance(v, dict) and v.get('p6') is not None]
        print(f'  {len(to_fix)} voci con p6 non-null da verificare')
        fixed = 0
        for i, date_str in enumerate(to_fix):
            url = build_url(date_str)
            print(f'[{i+1}/{len(to_fix)}] {date_str}', end=' ', flush=True)
            html = fetch_via_proxy(url)
            if html:
                quote = parse_page(html)
                if quote:
                    old_p6 = vincite[date_str].get('p6')
                    if quote.get('p6') != old_p6:
                        print(f'→ FIXED p6: {old_p6} → {quote.get("p6")}')
                        vincite[date_str] = quote
                        fixed += 1
                    else:
                        print(f'→ OK (p6={old_p6} confermato)')
                else:
                    print('→ parse fail')
            else:
                print('→ fetch fail')
            if i < len(to_fix) - 1:
                time.sleep(DELAY_SEC)
        print(f'\nFixed {fixed} voci')
        save_vincite(vincite)
        return

    if args.merge:
        print('Merge file parziali...')
        all_vincite = {}
        # Carica vincite.json principale se esiste
        if os.path.exists(VINCITE_FILE):
            with open(VINCITE_FILE) as f:
                existing = json.load(f)
            all_vincite = existing.get('vincite', {})
            print(f'  Base: {len(all_vincite)} entries')
        # Carica tutti i file parziali vincite_YYYY-YYYY.json
        import glob
        for fn in sorted(glob.glob('vincite_*.json')):
            with open(fn) as f:
                partial = json.load(f)
            entries = partial.get('vincite', {})
            all_vincite.update(entries)
            print(f'  Merge {fn}: +{len(entries)} entries')
            os.remove(fn)
            print(f'  Rimosso {fn}')
        save_vincite(all_vincite)
        return

    # ── SCRAPE mode ──────────────────────────────────────────────────────────
    all_dates = load_draws()
    print(f'Database: {len(all_dates)} estrazioni totali')

    # Filtra per anni se specificato
    if args.years:
        y_from, y_to = args.years.split('-')
        dates = [d for d in all_dates if y_from <= d[:4] <= y_to]
        out_file = f'vincite_{args.years}.json'
        print(f'Range {args.years}: {len(dates)} estrazioni → {out_file}')
    else:
        dates = all_dates
        out_file = VINCITE_FILE

    # Carica esistenti per questo range
    existing = {}
    if os.path.exists(out_file):
        with open(out_file) as f:
            data = json.load(f)
        existing = data.get('vincite', {})
        existing = {k: v for k, v in existing.items() if v is not None}
        print(f'Esistenti: {len(existing)}')
    elif os.path.exists(VINCITE_FILE) and not args.years:
        with open(VINCITE_FILE) as f:
            data = json.load(f)
        existing = data.get('vincite', {})
        existing = {k: v for k, v in existing.items() if v is not None}
        print(f'Caricati da vincite.json: {len(existing)}')

    updated, scraped = scrape(dates, existing)
    save_vincite(updated, out_file)
    print(f'Completato: +{scraped} nuove quote')


if __name__ == '__main__':
    main()
