# 🎰 SuperEnalotto — Analisi Statistica PWA

[![GitHub Pages](https://img.shields.io/badge/Live-delpinsky.github.io%2FSuperenalotto-brightgreen)](https://delpinsky.github.io/Superenalotto/)
[![Version](https://img.shields.io/badge/versione-v1.0.10-blue)]()
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

### v1.0.10 — 2026-03-21

- Dopo aver premuto "✓ Attiva" con un codice valido, ora avviene in sequenza:
- Il messaggio cambia subito in "✓ Codice valido! Caricamento database in corso…"
- Scarica il database raw da GitHub (lo stesso file che viene caricato al boot per i donatori)
- Ricostruisce draws[], freq[], aggiorna le pillole anni, le statistiche e le sezioni previsioni
- Chiama fetchJackpotOnly() per aggiornare il jackpot
- Chiama fetchLastDraw() per controllare e mostrare automaticamente l'ultima estrazione
- Il messaggio finale mostra il numero di estrazioni caricate
- La sezione donazione si nasconde dopo 2 secondi

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
