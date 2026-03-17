#!/usr/bin/env python3
"""
SuperEnalotto — Aggiornamento automatico database
Scarica le ultime estrazioni e aggiorna il JSON su GitHub.
Usato da GitHub Actions.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, date

# ── Configurazione ────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO  = 'delpinsky/Superenalotto'
JSON_FILE    = 'storico-estrazioni-superenalotto.json'
GITHUB_API   = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{JSON_FILE}'

BASE_URL     = 'https://www.superenalotto.com/risultati'
THIS_YEAR    = date.today().year

# ── Scraping ──────────────────────────────────────────────────────────────

def fetch_url(url, retries=3):
    """Scarica una pagina con retry."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; SuperEnalottoBot/1.0)',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'it-IT,it;q=0.9',
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            print(f'  Tentativo {attempt+1}/{retries} fallito: {e}')
            if attempt < retries - 1:
                time.sleep(5)
    return None


def parse_year_page(html, year):
    """Estrae le estrazioni dall'HTML di una pagina anno."""
    draws = []

    # Cerca righe con link estrazione-DD-MM-YYYY
    row_pattern = re.compile(
        r'estrazione-(\d{2})-(\d{2})-(\d{4})[^"]*"[^>]*>.*?'
        r'((?:\s*<td[^>]*>\s*\d{1,2}\s*</td>\s*){7,8})',
        re.DOTALL
    )

    # Approccio più robusto: trova tutte le righe della tabella
    # e cerca i numeri vicino ai link estrazione
    links = re.findall(r'estrazione-(\d{2})-(\d{2})-(\d{4})', html)

    for day, month, yr in links:
        if int(yr) != year:
            continue

        date_str = f'{yr}-{month}-{day}'

        # Trova la sezione dell'HTML vicino a questo link
        link_str = f'estrazione-{day}-{month}-{yr}'
        idx = html.find(link_str)
        if idx < 0:
            continue

        # Cerca i numeri nelle ~3000 chars successive
        section = html[idx:idx+3000]

        # Estrai tutti i numeri 1-90 in celle <td>
        nums = [int(n) for n in re.findall(r'<td[^>]*>\s*(\d{1,2})\s*</td>', section)
                if 1 <= int(n) <= 90]

        if len(nums) < 7:
            continue

        main  = sorted(nums[:6])
        jolly = nums[6]
        ss    = nums[7] if len(nums) >= 8 else None

        draw = {
            'date': date_str,
            'nums': main,
            'jolly': jolly,
        }
        if ss:
            draw['ss'] = ss

        draws.append(draw)

    return draws


def scrape_year(year):
    """Scarica e parsa le estrazioni di un anno."""
    url = f'{BASE_URL}/{year}'
    print(f'  Scarico {url}...')
    html = fetch_url(url)
    if not html:
        print(f'  ERRORE: impossibile scaricare {year}')
        return []
    draws = parse_year_page(html, year)
    print(f'  {len(draws)} estrazioni trovate per {year}')
    return draws


def scrape_jackpot():
    """Scarica il jackpot dalla pagina risultati."""
    html = fetch_url(BASE_URL)
    if not html:
        return None
    m = re.search(r'next-jackpot[\s\S]{0,300}?(\d[\d.,\s]+€)', html, re.IGNORECASE)
    if m:
        return m.group(1).strip().replace(' ', '')
    m2 = re.search(r'jackpot-value-sve[^>]*>([\d.,\s]+€)', html)
    if m2:
        return m2.group(1).strip().replace(' ', '')
    return None


# ── GitHub API ────────────────────────────────────────────────────────────

def github_get_file():
    """Scarica il JSON attuale da GitHub."""
    import base64
    req = urllib.request.Request(
        GITHUB_API,
        headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3.json',
            'User-Agent': 'SuperEnalottoBot/1.0',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            content = json.loads(base64.b64decode(data['content'].replace('\n', '')))
            return content, data['sha']
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        raise


def github_update_file(payload, sha, message):
    """Aggiorna il JSON su GitHub."""
    import base64
    body = {
        'message': message,
        'content': base64.b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode(),
    }
    if sha:
        body['sha'] = sha

    data = json.dumps(body).encode()
    req = urllib.request.Request(
        GITHUB_API,
        data=data,
        method='PUT',
        headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3.json',
            'Content-Type': 'application/json',
            'User-Agent': 'SuperEnalottoBot/1.0',
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    if not GITHUB_TOKEN:
        print('ERRORE: GITHUB_TOKEN non impostato')
        sys.exit(1)

    print('=== SuperEnalotto Database Updater ===')
    print(f'Data: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC')
    print()

    # 1. Scarica database attuale da GitHub
    print('1. Scarico database attuale da GitHub...')
    current, sha = github_get_file()
    if current:
        existing_draws = current.get('draws', [])
        existing_dates = {d['date'] for d in existing_draws}
        print(f'   Database attuale: {len(existing_draws)} estrazioni')
    else:
        existing_draws = []
        existing_dates = set()
        print('   Database non trovato, ne creo uno nuovo')

    # 2. Scraping anno corrente
    print(f'\n2. Scarico estrazioni {THIS_YEAR}...')
    new_draws = scrape_year(THIS_YEAR)

    # 3. Trova nuove estrazioni
    added = [d for d in new_draws if d['date'] not in existing_dates]
    print(f'\n3. Nuove estrazioni trovate: {len(added)}')

    if not added:
        print('   Nessuna nuova estrazione — database già aggiornato.')
        # Aggiorna comunque il jackpot
        print('\n4. Aggiorno jackpot...')
        jackpot = scrape_jackpot()
        if jackpot and jackpot != current.get('jackpot'):
            print(f'   Jackpot aggiornato: {jackpot}')
            payload = {
                'version': 1,
                'exported': datetime.utcnow().isoformat() + 'Z',
                'draws': existing_draws,
                'jackpot': jackpot,
            }
            github_update_file(payload, sha, f'Aggiornamento jackpot: {jackpot}')
            print('   ✓ Jackpot salvato su GitHub')
        else:
            print(f'   Jackpot invariato: {current.get("jackpot", "N/D")}')
        return

    # 4. Unisci e ordina
    all_draws = existing_draws + added
    all_draws.sort(key=lambda d: d['date'])

    # Rimuovi duplicati
    seen = set()
    unique_draws = []
    for d in all_draws:
        if d['date'] not in seen:
            seen.add(d['date'])
            unique_draws.append(d)

    # 5. Scraping jackpot
    print('\n4. Scarico jackpot...')
    jackpot = scrape_jackpot()
    print(f'   Jackpot: {jackpot or "N/D"}')

    # 6. Salva su GitHub
    print('\n5. Salvo su GitHub...')
    payload = {
        'version': 1,
        'exported': datetime.utcnow().isoformat() + 'Z',
        'draws': unique_draws,
        'jackpot': jackpot,
    }

    last_date = added[-1]['date'] if added else '?'
    message = f'Aggiornamento automatico: +{len(added)} estrazioni (ultima: {last_date})'
    github_update_file(payload, sha, message)

    print(f'   ✓ Database aggiornato: {len(unique_draws)} estrazioni totali')
    print(f'   ✓ Nuove: {[d["date"] for d in added]}')
    print('\n=== Completato ===')


if __name__ == '__main__':
    main()
