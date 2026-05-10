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
BASE_URL     = 'https://www.superenalotto.com/archivio/estrazioni'
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
    Parser DIV-based per superenalotto.com/archivio/estrazioni-YYYY.
    Struttura:
      <div class="boxArchiveNumbers">
        <div class="boxarchiveDate">09 maggio 2026</div>
        <div class="boxArchiveNumber">9</div>  (x6 numeri principali)
        <div class="boxArchiveNumber boxArchiveNumberRed">11<div>Jolly</div></div>
        <div class="boxArchiveNumber boxArchiveNumberstar">11<div>Superstar</div></div>
      </div>
    """
    MESI = {
        'gennaio':'01','febbraio':'02','marzo':'03','aprile':'04',
        'maggio':'05','giugno':'06','luglio':'07','agosto':'08',
        'settembre':'09','ottobre':'10','novembre':'11','dicembre':'12'
    }
    draws = []
    for part in re.split(r'<div[^>]+class=["\']boxArchiveNumbers["\']', html)[1:]:
        dm = re.search(r'boxarchiveDate[^>]*>(\d{1,2})\s+(\w+)\s+(\d{4})', part, re.I)
        if not dm:
            continue
        day, month_it, yr = dm.group(1), dm.group(2).lower(), dm.group(3)
        if int(yr) != year:
            continue
        month = MESI.get(month_it)
        if not month:
            continue
        date_str = f'{yr}-{month}-{day.zfill(2)}'
        jolly_m = re.search(r'boxArchiveNumberRed[^>]*>(\d{1,2})', part)
        ss_m    = re.search(r'boxArchiveNumberstar[^>]*>(\d{1,2})', part)
        jolly = int(jolly_m.group(1)) if jolly_m else None
        ss    = int(ss_m.group(1))    if ss_m    else None
        all_nums = [int(n) for n in re.findall(r'class=["\']boxArchiveNumber[^"\'>]*["\'][^>]*>(\d{1,2})', part)]
        mains = all_nums[:6]
        if len(mains) < 6 or not jolly:
            continue
        draw = {'date': date_str, 'nums': sorted(mains), 'jolly': jolly}
        if ss:
            draw['ss'] = ss
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
    url = f'{BASE_URL}-{THIS_YEAR}'
    html = fetch_url(url)
    if not html:
        print('   ERRORE: impossibile scaricare la pagina')
        sys.exit(1)

    print(f'   HTML: {len(html)} chars, boxArchiveNumbers: {html.count("boxArchiveNumbers")}')
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
