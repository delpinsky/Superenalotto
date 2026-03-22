#!/usr/bin/env python3
"""
update_vincite.py — Scraping quote SuperEnalotto da superenalotto.com
Costruisce/aggiorna vincite.json con le quote per ogni concorso.

Struttura vincite.json:
{
  "version": 1,
  "updated": "2026-03-22T...",
  "vincite": {
    "2026-03-21": {"p6": null, "p5j": null, "p5": 52205.24, "p4": 285.06, "p3": 24.74, "p2": 5.00},
    ...
  }
}

Quote null = jackpot non vinto (nessun importo fisso).
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, date
from html.parser import HTMLParser

# ── Configurazione ────────────────────────────────────────────────────────────
DRAWS_FILE   = 'storico-estrazioni-superenalotto.json'
VINCITE_FILE = 'vincite.json'
BASE_URL     = 'https://www.superenalotto.com/risultati/estrazione-{d}-{m:02d}-{y}'
DELAY_SEC    = 1.2   # pausa tra richieste (rispetto del server)
MAX_ERRORS   = 5     # errori consecutivi prima di fermarsi

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; SuperenalottoStats/1.0)',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'it-IT,it;q=0.9',
}

# ── Parser HTML ───────────────────────────────────────────────────────────────
class WinningsParser(HTMLParser):
    """Estrae le quote SuperEnalotto (non SuperStar/WinBox) dalla pagina."""

    def __init__(self):
        super().__init__()
        self.in_se_table   = False   # dentro la tabella Quote SuperEnalotto
        self.in_row        = False
        self.in_cell       = False
        self.current_row   = []
        self.current_text  = ''
        self.rows          = []
        self.found_h2      = False
        self.skip_table    = False   # tabella WinBox o SuperStar → salta

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.found_h2 = True
            self.in_se_table = False
        elif tag == 'table' and self.found_h2:
            self.in_se_table = not self.skip_table
            self.found_h2 = False
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
            if len(self.current_row) >= 3:
                self.rows.append(self.current_row[:3])
            self.in_row = False
        elif tag == 'table':
            self.in_se_table = False

    def handle_data(self, data):
        if self.found_h2:
            text = data.strip()
            if text:
                # Determina se la prossima tabella è quella giusta
                if 'SuperEnalotto' in text and 'SuperStar' not in text and 'WinBox' not in text:
                    self.skip_table = False
                else:
                    self.skip_table = True
        if self.in_cell:
            self.current_text += data


def parse_quote(text):
    """Converte '52.205,24 €' → 52205.24, '-' o '' → None."""
    text = text.strip().replace('€', '').replace('\xa0', '').strip()
    if not text or text in ('-', '—', 'N/D'):
        return None
    # Formato italiano: 52.205,24
    text = text.replace('.', '').replace(',', '.')
    try:
        return float(text)
    except ValueError:
        return None


def parse_page(html):
    """
    Estrae le 6 quote principali da una pagina estrazione.
    Ritorna dict {p6, p5j, p5, p4, p3, p2} o None se parsing fallisce.
    """
    parser = WinningsParser()
    parser.feed(html)

    rows = [r for r in parser.rows if r[0] and not r[0].lower().startswith('premi')]
    if len(rows) < 6:
        return None

    # Le prime 6 righe sono: 6 punti, 5+Jolly, 5, 4, 3, 2
    keys = ['p6', 'p5j', 'p5', 'p4', 'p3', 'p2']
    result = {}
    for i, key in enumerate(keys):
        if i < len(rows):
            # colonna 1 = Valore €, colonna 2 = Vincitori
            result[key] = parse_quote(rows[i][1])
        else:
            result[key] = None
    return result


def fetch_page(url, retries=3):
    """Scarica una pagina con retry."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # pagina non esiste
            print(f'  HTTP {e.code}, retry {attempt+1}/{retries}')
        except Exception as e:
            print(f'  Errore: {e}, retry {attempt+1}/{retries}')
        time.sleep(2 ** attempt)
    return None


def build_url(date_str):
    """YYYY-MM-DD → URL superenalotto.com"""
    y, m, d = date_str.split('-')
    return BASE_URL.format(d=int(d), m=int(m), y=y)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Carica il database estrazioni (per sapere quali date esistono)
    print(f'Caricamento {DRAWS_FILE}...')
    with open(DRAWS_FILE, 'r', encoding='utf-8') as f:
        draws_data = json.load(f)
    draws = draws_data.get('draws', draws_data) if isinstance(draws_data, dict) else draws_data
    all_dates = sorted(set(d['date'] for d in draws))
    print(f'  {len(all_dates)} estrazioni trovate ({all_dates[0]} → {all_dates[-1]})')

    # Carica vincite esistenti
    vincite = {}
    if os.path.exists(VINCITE_FILE):
        with open(VINCITE_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        vincite = existing.get('vincite', {})
        print(f'  {len(vincite)} quote già nel database')

    # Calcola quali date mancano
    missing = [d for d in all_dates if d not in vincite]
    print(f'  {len(missing)} date da scrapare')

    if not missing:
        print('Database vincite già aggiornato!')
        return

    # Scraping
    consecutive_errors = 0
    scraped = 0
    skipped = 0

    for i, date_str in enumerate(missing):
        url = build_url(date_str)
        print(f'[{i+1}/{len(missing)}] {date_str} → {url}', end=' ')

        html = fetch_page(url)

        if html is None:
            print('→ 404/errore, skip')
            vincite[date_str] = None  # segna come "tentato ma fallito"
            skipped += 1
            consecutive_errors += 1
        else:
            quote = parse_page(html)
            if quote:
                vincite[date_str] = quote
                print(f'→ OK (p5={quote.get("p5")}, p4={quote.get("p4")}, p3={quote.get("p3")})')
                scraped += 1
                consecutive_errors = 0
            else:
                print('→ parsing fallito, skip')
                vincite[date_str] = None
                skipped += 1
                consecutive_errors += 1

        if consecutive_errors >= MAX_ERRORS:
            print(f'STOP: {MAX_ERRORS} errori consecutivi')
            break

        if i < len(missing) - 1:
            time.sleep(DELAY_SEC)

    # Salva
    output = {
        'version': 1,
        'updated': datetime.utcnow().isoformat() + 'Z',
        'count': len([v for v in vincite.values() if v is not None]),
        'vincite': vincite
    }
    with open(VINCITE_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, separators=(',', ':'), ensure_ascii=False)

    print(f'\nDone: {scraped} aggiunte, {skipped} saltate')
    print(f'Database vincite: {output["count"]} concorsi con quote')


if __name__ == '__main__':
    main()
