# 🎰 SuperEnalotto — Analisi Statistica PWA

[![GitHub Pages](https://img.shields.io/badge/Live-delpinsky.github.io%2FSuperenalotto-brightgreen)](https://delpinsky.github.io/Superenalotto/)
[![Version](https://img.shields.io/badge/versione-v1.0.26-blue)]()
[![License](https://img.shields.io/badge/licenza-uso%20personale-lightgrey)]()

App web progressiva (PWA) per l'analisi statistica delle estrazioni del SuperEnalotto. Scarica l'intero storico dal 1997 ad oggi direttamente da superenalotto.com, costruisce un database locale nel browser e offre strumenti statistici, previsioni AI e sistemi di gioco.

> ⚠️ Il SuperEnalotto è un gioco d'azzardo completamente casuale. Nessun algoritmo può prevedere i numeri vincenti. Gioca responsabilmente.

---

## ✨ Funzionalità principali

- **Storico completo** — scarica tutte le estrazioni dal 1997 ad oggi via proxy CORS, anno per anno
- **Database locale** — esporta/importa JSON, sincronizzazione automatica con GitHub
- **Analisi schedina** — vincite storiche, frequenze, estrazioni con match
- **Previsioni statistiche** — 4 metodi: Hot, Cold, Bilanciato, Coppie & Terzine
- **Previsioni AI** — Claude, ChatGPT e Grok con parser NLP avanzato in italiano
- **Sistema di gioco** — Integrale e Ridotto (G3/G4/G5) con calcolo combinazioni
- **Cerca estrazione** — per data o numero concorso
- **Schedine preferite** — salva, carica, esporta/importa JSON
- **Vincite concorso** — tabella collassabile con Quote SuperEnalotto, SuperStar e WinBox
- **PWA installabile** — funziona offline su Android e desktop
- **Dark/Light mode** — rilevamento automatico del tema OS

---

## 🚀 Utilizzo

### Online
Apri direttamente: **https://delpinsky.github.io/Superenalotto/**

### Offline / Locale
1. Clona il repository: `git clone https://github.com/delpinsky/Superenalotto.git`
2. Apri `index.html` in un browser moderno (Chrome, Firefox, Edge)

### Prima configurazione
1. Premi **"⬇ Scarica Storico Completo"** per costruire il database (~5 minuti)
2. Al termine premi **"💾 Esporta JSON"** per salvare il database localmente
3. Ai prossimi avvii usa **"📂 Importa JSON"** per ricaricare istantaneamente

### Sincronizzazione GitHub (opzionale)
Configura un Personal Access Token GitHub per caricare/salvare il database automaticamente ad ogni avvio:
1. Crea un PAT su GitHub con permesso `contents: write`
2. Inseriscilo nella sezione **"🔗 Sincronizzazione GitHub"**

---

## 🤖 Previsioni AI — Come usarle

Le sezioni Claude, ChatGPT e Grok supportano un linguaggio naturale avanzato in italiano. Esempi di richieste:

```
3 numeri frequenti degli ultimi 4 mesi, 2 ritardatari degli ultimi 6 mesi, 1 casuale
dammi 4 caldi delle ultime 20 estrazioni e 2 bilanciati
voglio numeri freddi degli ultimi due anni
2 numeri frequenti degli ultimi tre mesi e gli altri bilanciati
```

**Tipi riconosciuti:** `frequenti`, `caldi`, `più usciti`, `freddi`, `ritardatari`, `bilanciati`, `casuali`, `random`, `in coppia`

**Periodi riconosciuti:** `degli ultimi N mesi/anni/estrazioni`, sia con cifre (`4 mesi`) che con parole (`due mesi`, `tre anni`)

---

## 📦 File principali

| File | Descrizione |
|------|-------------|
| `index.html` | App completa (unico file) |
| `sw.js` | Service Worker per cache offline |
| `manifest.json` | Manifest PWA |
| `icons/` | Icone 72→512px |
| `storico-estrazioni-superenalotto.json` | Database estrazioni (aggiornato da GitHub Actions) |
| `update_database.py` | Script Python per aggiornamento automatico |
| `.github/workflows/update_superenalotto.yml` | GitHub Actions: aggiorna il DB ogni martedì, giovedì, venerdì e sabato alle 20:30 |

---

## 📋 Changelog

### v1.0.26 — 2026-05-11

#### 🔧 `update_database.py` — Adattamento al nuovo sito superenalotto.com
- **Nuovo parser DIV-based** — il sito ha cambiato struttura da `<table><tr><td>` a `<div class="row"><div class="cell">` con classe `boxArchiveNumbers`; riscritto il parser per estrarre numeri e Jolly dalla nuova struttura
- **Nuovo URL archivio** — aggiornato da `/archivio/estrazioni?year=YYYY` a `/archivio/estrazioni-YYYY`
- **Scraping 2022-2026 ripristinato** — tutte le 830 date ora correttamente nel database

#### 🔧 `update_vincite.py` — Riscritto con multi-sorgente e parser robusto
- **Nuovo parser DIV-based per `.com`** — classe `WinningsParser` riscritta per la nuova struttura `tableHeader1` / `row` / `cell` di superenalotto.com
- **Nuova sorgente `.net`** — aggiunto `superenalotto.net` come sorgente di backup con parser TABLE dedicato (`WinningsParserNet`); usa la prima riga `"N punti"` come punto di partenza per saltare le sezioni WinBox
- **Catena di fallback** — `superenalotto.com → superenalotto.net → superenalotto.it`; il fallback `.net`/`.it` scatta anche quando `.com` risponde ma la sezione quote è vuota (es. 2023-02-07)
- **Fix numeri italiani** — parser `parse_quote()` gestisce correttamente il formato `54.019,52 €` (punti migliaia + virgola decimale)
- **Database completo** — 830/830 quote valide su 4194 estrazioni (1997-2026)

#### 🔧 `index.html` — Fix caricamento vincite lazy
- **Fix `vData` stantio** — il valore veniva letto una volta sola alla creazione della card; ora al click rilegge `getVincite(dr.date)` in tempo reale per intercettare il caricamento asincrono di `vinciteDB`
- **Cache di sessione** — dopo `fetchWinningsLive` il risultato viene salvato in `vinciteDB[dr.date]` evitando ricaricamenti nella stessa sessione
- **Auto-rimozione badge** — dopo il caricamento di `vinciteDB`, i badge "dati non disponibili" vengono rimossi automaticamente da tutte le card già renderizzate (classe `v-no-data-badge`)
- **Render diretto da cache** — se `vinciteDB` si è caricato nel frattempo, la card mostra i dati senza nessun fetch live
- **Fix parser JS** — `parseWinningsHtml` aggiornato alla struttura DIV; fix parsing numeri italiani con punti migliaia

#### ⚙️ Nuovi workflow GitHub Actions
- **`update_vincite_retry.yml`** — retry parallelo (6 job su range 5 anni) per tutte le date `{}` del database; merge degli artifact e commit automatico
- **`update_vincite_fix.yml`** — fix chirurgico: accetta una lista di date `YYYY-MM-DD` separate da virgola, le forza a `{}` e le ri-scrapa immediatamente; utile per correggere dati errati senza riprocessare l'intero database

### v1.0.25 — 2026-05-01
- **Fix bug `Media osservata: NaN×`** — causa radice: la funzione `topN()` usava destructuring `{num, score}` perdendo silenziosamente `rawFreq`, `lastDate` e tutte le altre proprietà degli oggetti. Ora itera con `for (const item of scored)` preservando l'intero oggetto
- **Fix typo `<btton>`** — tag non valido `<btton id="theme-toggle">` corretto in `<button>`
- **Status bar compatta** — la barra di stato superiore passa da layout a colonna (due righe) a riga singola con testo a sinistra e toggle MODALITÀ a destra, entrambi centrati verticalmente

### v1.0.24 — 2026-05-01
- **Aggiornamento numero versione** a v1.0.24 (preparazione release)

### v1.0.18 — 2026-03-22
- Miglioramenti interni e pulizia codice

### v1.0.17 — 2026-03-22
- **Sezione vincite parte chiusa** — la tabella "📊 Vincite concorso" è collassata di default, si apre cliccando
- **Rinominata** da "Montepremi concorso" a "Vincite concorso"
- **Quote WinBox in fondo** — ordine sezioni: Quote SuperEnalotto → Quote SuperStar → Quote WinBox

### v1.0.16 — 2026-03-22
- **Fix hook vincite** — il file conteneva due copie di `showLastDrawFromDB` e `fetchLastDraw`; JS usa sempre l'ultima definizione, quindi i hook nella prima copia venivano ignorati. Aggiunto `fetchWinnings` in tutte e 4 le posizioni attive
- **Log diagnostici** dettagliati in console per ogni proxy tentato

### v1.0.15 — 2026-03-22
- **Log diagnostici** per `fetchWinnings`: proxy index, URL, status HTTP, lunghezza risposta, sezioni trovate
- **Fallback link** a superenalotto.com se tutti i proxy falliscono

### v1.0.14 — 2026-03-22
- **Fix `GIST_ID_KEY is not defined`** — le costanti `GH_REPO`, `GH_FILE`, `GH_TOKEN_KEY`, `DONATION_KEY`, `GIST_ID_KEY`, `DONATION_SECRET`, `GH_API` erano dichiarate in fondo allo script ma usate molto prima; spostate nel blocco `CONSTANTS` iniziale

### v1.0.13 — 2026-03-22
- **Fix URL vincite** — formato corretto `estrazione-D-MM-YYYY` (giorno senza zero iniziale, mese con zero)
- Log dettagliati aggiuntivi per debug proxy

### v1.0.12 — 2026-03-22
- **Tabella vincite concorso** — scraping da `superenalotto.com/risultati/estrazione-DD-MM-YYYY` (stesso dominio già usato per lo storico, HTML statico)
- Parser `parseWinningsHtml`: trova sezioni `<h2>` con "Quote" e le rispettive tabelle
- Sezione collassabile con animazione `max-height`, si apre automaticamente con l'ultima estrazione
- Tre sezioni: Quote SuperEnalotto, Quote SuperStar, Quote WinBox
- Fallback discreto "dati vincite non disponibili" se tutti i proxy falliscono

### v1.0.11 — 2026-03-22
- Prima implementazione sezione vincite (su Sisal — poi abbandonata perché usa JS rendering)

### v1.0.10 — 2026-03-22
- **Auto-caricamento database dopo codice donazione** — dopo "✓ Attiva" con codice valido: scarica il DB raw da GitHub, ricostruisce `draws[]`/`freq[]`, aggiorna pillole anni, statistiche, sezioni previsioni, jackpot e ultima estrazione automaticamente senza F5

### v1.0.9 — 2026-03-21
- **Nuova sezione "🤖 Previsioni di ChatGPT"** — integrata con parser NLP identico a Claude
- Score `/100` e tag colorati (🔥 Hot, ❄️ Cold, ⚖️ Balanced, 🎲 Random) per ogni previsione
- Pulsante "↑ Carica" inline a destra dei pallini per caricare la schedina direttamente
- Pulsante "🤖 Chiedi di nuovo"

### v1.0.8 — 2026-03-21
- **Parser periodi con parole numerali** — `parsePeriod()` converte "due", "tre", "quattro"… in cifre prima del parsing: "ultimi due mesi" = 2, "ultimi tre anni" = 36 mesi, ecc.

### v1.0.7 — 2026-03-21
- **Fix `ritardatari` (plurale)** — `ritardatari[oi]` richiedeva un carattere extra dopo la parola; aggiunto `?` per renderlo opzionale
- **Fix lookahead `reMaster`** — ora si ferma anche davanti a `un ritardatario` senza la parola "numero" in mezzo

### v1.0.6 — 2026-03-21
- **Fix `frequenti` → hot** — `frequent[ei]` aggiunto nel gruppo 2 del `reMaster`; in precedenza senza "più" davanti lo slot spariva completamente
- **Fix regex `hot`** — rimosso `\bfrequent` (backslash doppio non funzionante in JS), sostituito con `/cald|frequent|uscit|volt/`
- **Pulsante "↑ Carica" a destra dei pallini** — allineato con `justify-content:space-between` e `margin-right:20px`
- **`buildStats` estratta a scope globale** — era locale in `generateClaudePrevisione` e non accessibile da Grok
- **Fix `parsePeriod` fallback** — rimosso `|| parsePeriod(text)` che propagava il primo periodo trovato a tutti gli slot
- **Fix caricamento numeri "↑ Carica"** — `textContent` includeva il testo del label `.lbl`; ora legge solo il primo text node diretto

### v1.0.5 — 2026-03-17
- **Parser previsioni Grok** — riscritto con stesso `reMaster` di Claude
- **Giorni estrazione corretti** — aggiunto venerdì (dow=5) accanto a martedì/giovedì/sabato
- **Pulsante "↑ Carica" inline** ai pallini di Claude e Grok
- Fix jackpot: usa `superenalotto.com/risultati` (senza anno) invece di `risultati/2026`
- Fix scraping: `XMLHttpRequest` invece di `fetch()` per bypassare estensioni Chrome

### v1.0.4 — 2026-03-15
- **Sistema codici donazione** — formato `SUPER-SEED-HMAC-ENA`, validazione con SubtleCrypto (online) + djb2 fallback (offline)
- **Gist privato** per codici univoci — configurabile da console con `setGistId('ID')`
- Sezione donazione si nasconde automaticamente dopo attivazione valida
- I donatori (senza token GitHub) caricano il database pubblico all'avvio automaticamente
- Generatore privato `codici_donazione.html`

### v1.0.3 — 2026-03-14
- **Sincronizzazione GitHub** — caricamento/salvataggio database via API GitHub con PAT
- **GitHub Actions** — workflow automatico che aggiorna il JSON ogni martedì/giovedì/venerdì/sabato alle 20:30 (ora italiana), usa `GITHUB_TOKEN` automatico
- Verifica proprietario via `api.github.com/user` (solo `delpinsky` vede i controlli avanzati)

### v1.0.2 — 2026-03-13
- **Previsioni di Claude** — parser NLP con `reMaster` regex, modalità strutturata e classica, periodi multipli per slot
- **Previsioni di Grok** — sezione analoga con stile cosmico
- **Sistema Integrale/Ridotto** — calcolo completo con algoritmo greedy asincrono, garanzie G3/G4/G5, paginazione combinazioni
- **Cerca estrazione** — per data o numero concorso, navigazione prev/next
- **Schedine preferite** — salva/carica/esporta/importa JSON

### v1.0.1 — 2026-03-12
- **PWA** — manifest, service worker con cache offline, icone 72→512px
- **Dark/Light mode** — rilevamento automatico OS + toggle manuale ☀/🌙
- **Jackpot scraping** — valore jackpot corrente da superenalotto.com
- **Griglia anni** — pillole colorate per stato scaricamento (pending/loading/done/error)
- **Ultima estrazione** — controllo aggiornamento con badge "✨ NUOVA!"

### v1.0.0 — 2026-03-12
- Prima versione pubblica
- Scraping estrazioni 1997→oggi via proxy CORS (codetabs, cors.sh, cors.lol, allorigins, corsproxy.io)
- Schedina con griglia numeri (modalità 1 numero e 6 numeri)
- Analisi vincite, estrazioni con match, frequenze per periodo
- 4 metodi previsione statistica: Hot 🔥, Cold ❄️, Bilanciato ⚖️, Coppie & Terzine 🔗

---

## 🛠️ Tecnologie

- HTML5 + CSS3 + JavaScript vanilla (zero dipendenze esterne)
- SubtleCrypto API per validazione HMAC codici donazione
- GitHub REST API v3 per sincronizzazione database
- GitHub Actions per aggiornamento automatico schedulato
- Service Worker + Cache API per funzionamento offline

---

## 👤 Autore

**Christian Scarpellini** — [@delpinsky](https://github.com/delpinsky)

Se questa app ti è utile, considera una piccola donazione: [paypal.me/delpinsky](https://paypal.me/delpinsky) ☕

---

*Dati © superenalotto.com · Solo uso statistico · Il gioco può causare dipendenza patologica*
