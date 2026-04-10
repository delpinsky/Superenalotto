#!/usr/bin/env python3
"""
update_vincite.py — Scraping quote SuperEnalotto
Costruisce/aggiorna vincite.json con le quote per ogni concorso.

Sorgenti (in ordine di priorità):
  1. superenalotto.com/risultati/estrazione-D-MM-YYYY
  2. superenalotto.it/archivio-estrazioni/concorso-N/D-mese-YYYY  (fallback)

Struttura vincite.json:
  { "version":1, "updated":"...", "count":N,
    "vincite": { "YYYY-MM-DD": {"p6":null,"p5j":null,"p5":52205.24,...} } }

Quote null = jackpot non vinto (0 vincitori).
Quote {}   = dati non disponibili su nessuna sorgente.

Utilizzo:
  python update_vincite.py                        # aggiorna date mancanti
  python update_vincite.py --year 2026            # solo un anno
  python update_vincite.py --from-year 2010       # da un anno in poi
  python update_vincite.py --retry-empty          # riprova le date con {}
  python update_vincite.py --retry-empty --year 2026
"""

import json, os, re, sys, time, argparse, urllib.request, urllib.error, urllib.parse
from datetime import datetime
from html.parser import HTMLParser

# ── Configurazione ────────────────────────────────────────────────────────────
DRAWS_FILE   = 'storico-estrazioni-superenalotto.json'
VINCITE_FILE = 'vincite.json'

DELAY_SEC  = 1.0   # pausa tra richieste
MAX_ERRORS = 10    # errori consecutivi prima di fermarsi su un anno

BASE_URL_COM = 'https://www.superenalotto.com/risultati/estrazione-{d:02d}-{m:02d}-{y}'
BASE_URL_IT  = 'https://www.superenalotto.it/archivio-estrazioni/concorso-{n}/{d}-{mese}-{y}'
MESI_IT = ['','gennaio','febbraio','marzo','aprile','maggio','giugno',
           'luglio','agosto','settembre','ottobre','novembre','dicembre']

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

# ── URL builders ──────────────────────────────────────────────────────────────
def build_url_com(date_str):
    y, m, d = date_str.split('-')
    return BASE_URL_COM.format(d=int(d), m=int(m), y=y)

def build_url_it(date_str, concorso_n):
    y, m, d = date_str.split('-')
    return BASE_URL_IT.format(n=concorso_n, d=int(d), mese=MESI_IT[int(m)], y=y)

# ── Parser HTML ───────────────────────────────────────────────────────────────
class WinningsParser(HTMLParser):
    """Estrae le righe della tabella Quote SuperEnalotto (non SuperStar/WinBox)."""
    def __init__(self):
        super().__init__()
        self.in_se_table = False
        self.pending_table = False
        self.last_h2 = ''
        self.in_row = self.in_cell = False
        self.current_row = []
        self.current_text = ''
        self.rows = []

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
    """'52.205,24 €' → 52205.24,  '880.400,00 L' → 880400.0,  '-' → None"""
    text = str(text).strip()
    # Rimuovi simboli valuta (€ e L per Lire)
    text = text.replace('€','').replace('\xa0','').replace('\u00a0','')
    # Rimuovi 'L' finale (Lire) — solo se preceduta da cifra o spazio
    import re as _re
    text = _re.sub(r'\s*L\s*$', '', text).strip()
    if not text or text in ('-','—','N/D','–'):
        return None
    try:
        return float(text.replace('.','').replace(',','.')) or None
    except ValueError:
        return None

def parse_vincitori(text):
    """'23.212' → 23212"""
    try:
        return int(str(text).strip().replace('.','').replace(',','').replace('\xa0',''))
    except ValueError:
        return None

def _extract_quotes(rows):
    """
    Estrae le 6 quote da una lista di righe (formato .com o .it).
    .com: [categoria, valore, vincitori]
    .it:  [categoria, vincitori, valore]
    Distingue automaticamente dall'ordine delle colonne.
    """
    skip = {'premio','categoria','vincitori','valori in euro',''}
    rows = [r for r in rows if r[0].lower().strip() not in skip]
    if len(rows) < 2:
        return None  # meno di 2 righe dati → sicuramente vuota

    # Determina formato: se col[1] è numerico (vincitori) → formato .it
    def is_numeric(s):
        try: int(s.strip().replace('.','').replace(',','')); return True
        except: return False

    it_format = len(rows[0]) >= 2 and is_numeric(rows[0][1])

    keys = ['p6','p5j','p5','p4','p3','p2']
    result = {}
    for i, key in enumerate(keys):
        if i >= len(rows):
            result[key] = None
            continue
        r = rows[i]
        if it_format:
            # .it: [cat, vincitori, valore]
            winners = parse_vincitori(r[1]) if len(r) > 1 else None
            prize   = parse_quote(r[2])     if len(r) > 2 else None
        else:
            # .com: [cat, valore, vincitori]
            prize   = parse_quote(r[1])     if len(r) > 1 else None
            winners = parse_vincitori(r[2]) if len(r) > 2 else None
        # FIX: se vincitori==0, il valore mostrato è il jackpot accumulato → None
        result[key] = None if winners == 0 else prize

    return result if any(v is not None for v in result.values()) else None

def parse_html(html):
    """Parsa HTML da qualsiasi sorgente (.com o .it). Ritorna dict o None."""
    p = WinningsParser()
    p.feed(html)
    return _extract_quotes(p.rows)

# ── Fetch via proxy ───────────────────────────────────────────────────────────
def fetch(url, aggressive=False):
    """
    Tenta il download via proxy CORS.
    aggressive=True: 3 round con delay crescente.
    """
    rounds = 3 if aggressive else 1
    for round_n in range(rounds):
        if round_n > 0:
            wait = round_n * 5
            print(f'[retry {round_n+1}/{rounds} +{wait}s]', end=' ', flush=True)
            time.sleep(wait)
        for proxy_fn in PROXIES:
            purl = proxy_fn(url)
            try:
                req = urllib.request.Request(purl, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=25) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    if len(html) > 1000 and ('Quote' in html or 'punti' in html or 'Punti' in html):
                        return html
            except Exception:
                pass
            time.sleep(0.4)
    return None

def fetch_with_fallback(date_str, concorso_n=None, aggressive=False):
    """
    Prova superenalotto.com, poi superenalotto.it come fallback.
    Ritorna (html, sorgente) o (None, None).
    """
    html = fetch(build_url_com(date_str), aggressive)
    if html:
        return html, 'com'
    if concorso_n:
        html = fetch(build_url_it(date_str, concorso_n), aggressive)
        if html:
            return html, 'it'
    return None, None

# ── Caricamento dati ──────────────────────────────────────────────────────────
def load_draws():
    """Ritorna lista di dict {date, concorso} ordinata per data."""
    with open(DRAWS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    draws = data.get('draws', data) if isinstance(data, dict) else data
    seen = {}
    for d in draws:
        date = d.get('date','')
        if date and date not in seen:
            seen[date] = d.get('concorso') or d.get('n')
    return [{'date': k, 'concorso': v} for k, v in sorted(seen.items())]

def load_vincite():
    if not os.path.exists(VINCITE_FILE):
        return {}
    with open(VINCITE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('vincite', {})

def save_vincite(vincite):
    valid = len([v for v in vincite.values() if v and v != {}])
    out = {
        'version': 1,
        'updated': datetime.utcnow().isoformat() + 'Z',
        'count': valid,
        'vincite': dict(sorted(vincite.items()))
    }
    with open(VINCITE_FILE, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',',':'), ensure_ascii=False)
    print(f'  → vincite.json: {valid} quote valide su {len(vincite)} totali')

# ── Scraping di un anno ───────────────────────────────────────────────────────
def scrape_year(year, draws_for_year, vincite, retry_empty=False, aggressive=False):
    """
    Scrapa le date mancanti per un anno.
    retry_empty=True: riprova anche le date con {}.
    Ritorna (vincite aggiornate, n_scraped, n_failed, n_still_missing).
    """
    if retry_empty:
        missing = [d for d in draws_for_year if vincite.get(d['date']) in (None, {})]
    else:
        missing = [d for d in draws_for_year if d['date'] not in vincite]

    if not missing:
        return vincite, 0, 0, 0

    scraped = failed = 0
    consecutive_errors = 0

    for i, draw in enumerate(missing):
        date_str   = draw['date']
        concorso_n = draw['concorso']
        print(f'  [{i+1:3d}/{len(missing)}] {date_str}', end=' ', flush=True)

        html, src = fetch_with_fallback(date_str, concorso_n, aggressive)

        if html is None:
            print('→ FAIL')
            vincite[date_str] = {}
            failed += 1
            consecutive_errors += 1
        else:
            quote = parse_html(html)
            if quote:
                vincite[date_str] = quote
                label = f'[{src}]' if src == 'it' else ''
                print(f'→ OK {label}  p5={quote.get("p5")}  p3={quote.get("p3")}')
                scraped += 1
                consecutive_errors = 0
            else:
                vincite[date_str] = {}
                print('→ no data (pagina senza quote)')
                failed += 1
                consecutive_errors += 1

        if consecutive_errors >= MAX_ERRORS:
            print(f'  STOP: {MAX_ERRORS} errori consecutivi')
            break

        if i < len(missing) - 1:
            time.sleep(DELAY_SEC)

    still_missing = [d['date'] for d in draws_for_year
                     if vincite.get(d['date']) in (None, {})]
    return vincite, scraped, failed, len(still_missing)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--year',        help='Solo questo anno (es. 2026)')
    ap.add_argument('--from-year',   help='Da questo anno in poi (es. 2010)')
    ap.add_argument('--to-year',     help='Fino a questo anno incluso (es. 2006)')
    ap.add_argument('--retry-empty', action='store_true',
                    help='Riprova le date con {} (precedentemente fallite)')
    ap.add_argument('--aggressive',  action='store_true',
                    help='3 round di retry per ogni data (più lento ma più robusto)')
    args = ap.parse_args()

    # Carica dati
    print(f'Caricamento {DRAWS_FILE}...')
    all_draws = load_draws()
    print(f'  {len(all_draws)} estrazioni totali  '
          f'({all_draws[0]["date"]} → {all_draws[-1]["date"]})')

    vincite = load_vincite()
    valid_existing = len([v for v in vincite.values() if v and v != {}])
    print(f'  {valid_existing} quote già nel database')

    # Seleziona anni da processare
    if args.year:
        years = [int(args.year)]
    else:
        all_years = sorted(set(d['date'][:4] for d in all_draws))
        first = int(args.from_year) if args.from_year else int(all_years[0])
        last  = int(args.to_year)   if args.to_year   else int(all_years[-1])
        years = list(range(first, last + 1))

    # Processa anno per anno
    total_scraped = total_failed = 0

    for year in years:
        year_str = str(year)
        draws_for_year = [d for d in all_draws if d['date'].startswith(year_str)]
        if not draws_for_year:
            continue

        # Calcola quante mancano per questo anno
        if args.retry_empty:
            n_missing = len([d for d in draws_for_year
                             if vincite.get(d['date']) in (None, {})])
        else:
            n_missing = len([d for d in draws_for_year
                             if d['date'] not in vincite])

        if n_missing == 0:
            valid_year = len([d for d in draws_for_year
                              if vincite.get(d['date']) and vincite[d['date']] != {}])
            print(f'[{year}] ✓ già completo ({valid_year}/{len(draws_for_year)} quote)')
            continue

        print(f'\n[{year}] {len(draws_for_year)} estrazioni — {n_missing} da scrapare'
              + (' [retry empty]' if args.retry_empty else '')
              + (' [aggressive]'  if args.aggressive  else ''))

        vincite, scraped, failed, still_missing = scrape_year(
            year_str, draws_for_year, vincite,
            retry_empty=args.retry_empty,
            aggressive=args.aggressive
        )
        total_scraped += scraped
        total_failed  += failed

        valid_year = len([d for d in draws_for_year
                          if vincite.get(d['date']) and vincite[d['date']] != {}])

        if still_missing == 0:
            print(f'  ✓ Anno {year} completo: {valid_year}/{len(draws_for_year)} quote valide')
        else:
            print(f'  ⚠ Anno {year}: {valid_year}/{len(draws_for_year)} quote valide, '
                  f'{still_missing} ancora mancanti (superenalotto.com non ha queste pagine)')

        # Salva dopo ogni anno (checkpoint)
        save_vincite(vincite)

    # Riepilogo finale
    print(f'\n{"─"*50}')
    print(f'Completato: +{total_scraped} aggiunte, {total_failed} fallite')
    valid_total = len([v for v in vincite.values() if v and v != {}])
    print(f'Totale database: {valid_total} quote valide su {len(all_draws)} estrazioni')


if __name__ == '__main__':
    main()
