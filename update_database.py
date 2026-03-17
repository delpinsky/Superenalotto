#!/usr/bin/env python3
"""
SuperEnalotto — Aggiornamento automatico database
Scarica le ultime estrazioni e aggiorna il JSON su GitHub.
Usato da GitHub Actions.
"""

import json, os, re, sys, time, base64
import urllib.request, urllib.parse
from datetime import datetime, date
from html.parser import HTMLParser

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO  = 'delpinsky/Superenalotto'
JSON_FILE    = 'storico-estrazioni-superenalotto.json'
GITHUB_API   = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{JSON_FILE}'
BASE_URL     = 'https://www.superenalotto.com/risultati'
THIS_YEAR    = date.today().year


def fetch_url(url, retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
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
    """
    Replica esatta del parser JS dell'app:
    - Cerca righe <tr> con link estrazione-DD-MM-YYYY
    - Estrae tutti i <td> con numeri 1-90 dalla stessa riga
    """
    draws = []

    # Trova tutti i link estrazione e le loro posizioni
    for m in re.finditer(r'estrazione-(\d{2})-(\d{2})-(\d{4})', html):
        day, month, yr = m.group(1), m.group(2), m.group(3)
        if int(yr) != year:
            continue

        date_str = f'{yr}-{month}-{day}'

        # Trova l'inizio del <tr> che contiene questo link
        tr_start = html.rfind('<tr', 0, m.start())
        if tr_start < 0:
            continue

        # Trova la fine del </tr>
        tr_end = html.find('</tr>', m.start())
        if tr_end < 0:
            continue

        row_html = html[tr_start:tr_end]

        # Estrai tutti i testi dei <td> che sono numeri 1-90
        tds = re.findall(r'<td[^>]*>\s*(\d{1,2})\s*</td>', row_html)
        nums = [int(n) for n in tds if 1 <= int(n) <= 90]

        if len(nums) < 7:
            continue

        main  = sorted(nums[:6])
        jolly = nums[6]
        ss    = nums[7] if len(nums) >= 8 else None

        draw = {'date': date_str, 'nums': main, 'jolly': jolly}
        if ss:
            draw['ss'] = ss

        # Evita duplicati nella stessa esecuzione
        if not any(d['date'] == date_str for d in draws):
            draws.append(draw)

    draws.sort(key=lambda d: d['date'])
    print(f'  Parsed: {len(draws)} estrazioni per {year}')
    if draws:
        print(f'  Prima: {draws[0]["date"]}, Ultima: {draws[-1]["date"]}')
    return draws


def scrape_jackpot():
    html = fetch_url(BASE_URL)
    if not html:
        return None
    # Cerca il div next-jackpot
    m = re.search(r'next-jackpot[\s\S]{0,300}?(\d[\d.,\s]+€)', html, re.IGNORECASE)
    if m:
        return m.group(1).strip().replace(' ', '')
    m2 = re.search(r'jackpot-value-sve[^>]*>([\d.,\s]+€)', html)
    if m2:
        return m2.group(1).strip().replace(' ', '')
    return None


def github_get_file():
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
    body = {
        'message': message,
        'content': base64.b64encode(
            json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        ).decode(),
    }
    if sha:
        body['sha'] = sha

    req = urllib.request.Request(
        GITHUB_API,
        data=json.dumps(body).encode(),
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


def main():
    if not GITHUB_TOKEN:
        print('ERRORE: GITHUB_TOKEN non impostato')
        sys.exit(1)

    print('=== SuperEnalotto Database Updater ===')
    print(f'Data: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC')
    print()

    # 1. Scarica database attuale
    print('1. Scarico database attuale da GitHub...')
    current, sha = github_get_file()
    if current:
        existing_draws = current.get('draws', [])
        existing_dates = {d['date'] for d in existing_draws}
        print(f'   {len(existing_draws)} estrazioni nel database')
        print(f'   Ultima: {existing_draws[-1]["date"] if existing_draws else "N/A"}')
    else:
        existing_draws, existing_dates = [], set()
        print('   Database non trovato — ne creo uno nuovo')

    # 2. Scraping anno corrente
    print(f'\n2. Scarico estrazioni {THIS_YEAR}...')
    url = f'{BASE_URL}/{THIS_YEAR}'
    html = fetch_url(url)
    if not html:
        print('   ERRORE: impossibile scaricare la pagina')
        sys.exit(1)

    print(f'   HTML: {len(html)} chars, contiene estrazione-: {"estrazione-" in html}')
    new_draws = parse_year_page(html, THIS_YEAR)

    # 3. Nuove estrazioni
    added = [d for d in new_draws if d['date'] not in existing_dates]
    print(f'\n3. Nuove estrazioni: {len(added)}')
    for d in added:
        print(f'   + {d["date"]}: {d["nums"]} J:{d["jolly"]} SS:{d.get("ss")}')

    # 4. Jackpot
    print('\n4. Scarico jackpot...')
    jackpot = scrape_jackpot()
    print(f'   Jackpot: {jackpot or "N/D"}')

    # 5. Aggiorna se ci sono novità
    jackpot_changed = jackpot and jackpot != current.get('jackpot') if current else True

    if not added and not jackpot_changed:
        print('\nNessuna novità — database già aggiornato.')
        return

    # Unisci e salva
    all_draws = existing_draws + added
    all_draws.sort(key=lambda d: d['date'])

    # Deduplicazione
    seen, unique = set(), []
    for d in all_draws:
        if d['date'] not in seen:
            seen.add(d['date'])
            unique.append(d)

    payload = {
        'version': 1,
        'exported': datetime.utcnow().isoformat() + 'Z',
        'draws': unique,
        'jackpot': jackpot,
    }

    last = unique[-1]['date'] if unique else '?'
    if added:
        msg = f'Auto-update: +{len(added)} estrazioni (ultima: {last})'
    else:
        msg = f'Auto-update jackpot: {jackpot}'

    print(f'\n5. Salvo su GitHub...')
    github_update_file(payload, sha, msg)
    print(f'   ✓ {len(unique)} estrazioni totali')
    print(f'   ✓ Commit: "{msg}"')
    print('\n=== Completato ===')


if __name__ == '__main__':
    main()
