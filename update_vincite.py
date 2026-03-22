#!/usr/bin/env python3
"""
update_vincite.py — Scraping quote SuperEnalotto via proxy CORS
Costruisce/aggiorna vincite.json con le quote per ogni concorso.

Struttura vincite.json:
{
  "version": 1,
  "updated": "2026-03-22T...",
  "count": 3500,
  "vincite": {
    "2026-03-21": {"p6": null, "p5j": null, "p5": 52205.24, "p4": 285.06, "p3": 24.74, "p2": 5.00},
    ...
  }
}
Quote null = jackpot non vinto (nessun importo fisso).
"""

import json, os, re, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime
from html.parser import HTMLParser

# ── Configurazione ────────────────────────────────────────────────────────────
DRAWS_FILE   = 'storico-estrazioni-superenalotto.json'
VINCITE_FILE = 'vincite.json'
DELAY_SEC    = 0.8    # pausa tra richieste
MAX_ERRORS   = 8      # errori consecutivi prima di fermarsi
MAX_NEW      = 1000    # max nuove date per run (evita timeout GitHub Actions)

BASE_URL = 'https://www.superenalotto.com/risultati/estrazione-{d}-{m:02d}-{y}'

# Proxy CORS — stesso set usato dall'app browser
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
            # Entra nella tabella solo se è Quote SuperEnalotto (non SuperStar/WinBox)
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
    """'52.205,24 €' → 52205.24,  '-' → None"""
    text = str(text).strip().replace('€', '').replace('\xa0', '').replace('\u00a0', '').strip()
    if not text or text in ('-', '—', 'N/D', '–'):
        return None
    text = text.replace('.', '').replace(',', '.')
    try:
        v = float(text)
        return v if v > 0 else None
    except ValueError:
        return None


def parse_page(html):
    """Estrae le 6 quote principali. Ritorna dict o None."""
    parser = WinningsParser()
    parser.feed(html)
    # Rimuovi header row
    rows = [r for r in parser.rows
            if r[0] and not r[0].lower().strip() in ('premio', 'categoria', '')]
    if len(rows) < 4:
        return None
    keys = ['p6', 'p5j', 'p5', 'p4', 'p3', 'p2']
    result = {}
    for i, key in enumerate(keys):
        if i < len(rows) and len(rows[i]) >= 2:
            result[key] = parse_quote(rows[i][1])
        else:
            result[key] = None
    return result if any(v is not None for v in result.values()) or len(rows) >= 4 else None


def fetch_via_proxy(target_url, retries=2):
    """Scarica tramite proxy CORS con fallback."""
    for proxy_fn in PROXIES:
        url = proxy_fn(target_url)
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    if len(html) > 1000 and ('Quote' in html or 'punti' in html or 'estrazione' in html.lower()):
                        return html
                    # Risposta troppo corta o senza dati utili
                    break
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(1)
        time.sleep(0.3)
    return None


def build_url(date_str):
    y, m, d = date_str.split('-')
    return BASE_URL.format(d=int(d), m=int(m), y=y)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f'Caricamento {DRAWS_FILE}...')
    with open(DRAWS_FILE, 'r', encoding='utf-8') as f:
        draws_data = json.load(f)
    draws = draws_data.get('draws', draws_data) if isinstance(draws_data, dict) else draws_data
    all_dates = sorted(set(d['date'] for d in draws))
    print(f'  {len(all_dates)} estrazioni ({all_dates[0]} → {all_dates[-1]})')

    # Carica vincite esistenti
    vincite = {}
    if os.path.exists(VINCITE_FILE):
        with open(VINCITE_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        vincite = existing.get('vincite', {})
        # Rimuovi le entry null per riprovare (potrebbero essere state errori temporanei)
        vincite = {k: v for k, v in vincite.items() if v is not None}
        print(f'  {len(vincite)} quote già nel database')

    # Date mancanti (non ancora scrappate con successo)
    missing = [d for d in all_dates if d not in vincite]
    print(f'  {len(missing)} date da scrapare (max {MAX_NEW} per run)')
    missing = missing[:MAX_NEW]

    if not missing:
        print('Database vincite già aggiornato!')
        _save(vincite)
        return

    consecutive_errors = 0
    scraped = 0
    failed = 0

    for i, date_str in enumerate(missing):
        url = build_url(date_str)
        print(f'[{i+1}/{len(missing)}] {date_str}', end=' ', flush=True)

        html = fetch_via_proxy(url)

        if html is None:
            print('→ FAIL (tutti i proxy)')
            failed += 1
            consecutive_errors += 1
        else:
            quote = parse_page(html)
            if quote is not None:
                vincite[date_str] = quote
                p3 = quote.get('p3')
                p5 = quote.get('p5')
                print(f'→ OK  p5={p5}  p3={p3}')
                scraped += 1
                consecutive_errors = 0
            else:
                # Pagina caricata ma senza dati vincite (es. estrazioni molto vecchie)
                # Salva come dict vuoto per non riprovare ogni volta
                vincite[date_str] = {}
                print('→ parsing fallito (dati non presenti)')
                failed += 1
                consecutive_errors += 1

        if consecutive_errors >= MAX_ERRORS:
            print(f'STOP: {MAX_ERRORS} errori consecutivi — possibile blocco proxy')
            break

        if i < len(missing) - 1:
            time.sleep(DELAY_SEC)

    _save(vincite)
    remaining = len([d for d in all_dates if d not in vincite or vincite[d] == {}])
    print(f'\nDone: +{scraped} aggiunte, {failed} fallite')
    print(f'Totale: {len([v for v in vincite.values() if v and v != {}])} concorsi con quote')
    print(f'Rimanenti: {remaining} (verranno processate ai prossimi run)')


def _save(vincite):
    valid_count = len([v for v in vincite.values() if v and v != {}])
    output = {
        'version': 1,
        'updated': datetime.utcnow().isoformat() + 'Z',
        'count': valid_count,
        'vincite': vincite
    }
    with open(VINCITE_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, separators=(',', ':'), ensure_ascii=False)
    print(f'Salvato {VINCITE_FILE}: {valid_count} quote valide')


if __name__ == '__main__':
    main()
