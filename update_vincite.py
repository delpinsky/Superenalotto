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

BASE_URL_COM = 'https://www.superenalotto.com/risultati-estrazione/{d:02d}-{m:02d}-{y}'
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
    """Estrae quote da superenalotto.com/risultati-estrazione/DD-MM-YYYY
    Il sito usa <div class="table"> con <div class="row"> e <div class="cell">
    NON usa <table><tr><td>.
    Struttura colonne: [Premio/categoria] [Valore € o "-"] [Vincitori]
    """

    def __init__(self):
        super().__init__()
        self.sections       = {}   # title → [rows]
        self.current_section = None
        self.in_header1     = False
        self.in_row         = False
        self.in_cell        = False
        self.current_cells  = []
        self.current_text   = ''
        self.div_depth      = 0    # profondità div mentre siamo in un row
        self.row_div_depth  = 0

    def _get_class(self, attrs):
        return dict(attrs).get('class', '')

    def handle_starttag(self, tag, attrs):
        if tag != 'div':
            return
        cls = self._get_class(attrs)
        classes = cls.split()

        if 'tableHeader1' in classes:
            self.in_header1  = True
            self.current_text = ''

        elif 'row' in classes and 'tableHeader' not in cls and 'tableFooter' not in cls:
            if self.current_section is not None:
                self.in_row        = True
                self.current_cells = []
                self.row_div_depth = 0

        elif 'cell' in classes and self.in_row:
            self.in_cell      = True
            self.current_text = ''
            self.div_depth    = 0

        elif self.in_cell:
            self.div_depth += 1

    def handle_endtag(self, tag):
        if tag != 'div':
            return
        if self.in_header1:
            title = self.current_text.strip()
            if title:
                if title not in self.sections:
                    self.sections[title] = []
                self.current_section = title
            self.in_header1 = False

        elif self.in_cell:
            if self.div_depth > 0:
                self.div_depth -= 1
            else:
                self.current_cells.append(self.current_text.strip())
                self.in_cell = False

        elif self.in_row:
            self.row_div_depth -= 1
            if self.row_div_depth < 0:
                # Fine del div.row
                if len(self.current_cells) >= 2 and self.current_section:
                    cat   = self.current_cells[0]
                    val   = self.current_cells[1] if len(self.current_cells) > 1 else '-'
                    nwin  = self.current_cells[2] if len(self.current_cells) > 2 else '0'
                    # Salta righe header
                    if not re.match(r'^(premio|valore|vincitori)', cat, re.I):
                        self.sections[self.current_section].append([cat, val, nwin])
                self.in_row = False
                self.current_cells = []

    def handle_data(self, data):
        if self.in_header1 or self.in_cell:
            self.current_text += data

    @property
    def rows(self):
        """Ritorna le righe della sezione Quote SuperEnalotto."""
        for title, rows in self.sections.items():
            if 'SuperEnalotto' in title and 'SuperStar' not in title and 'WinBox' not in title:
                return rows
        return []

    @property
    def all_rows(self):
        """Tutte le righe di tutte le sezioni."""
        all_r = []
        for rows in self.sections.values():
            all_r.extend(rows)
        return all_r


def parse_html(html):
    """Parsa HTML da superenalotto.com/risultati-estrazione/DD-MM-YYYY. Ritorna dict o None."""
    p = WinningsParser()
    p.feed(html)
    result = _extract_quotes(p.rows)
    if result:
        return result
    # Fallback: tutte le righe di tutte le sezioni
    return _extract_quotes(p.all_rows)

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
                    if len(html) > 1000 and ('punti' in html or 'tableHeader1' in html or 'Quote' in html):
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
