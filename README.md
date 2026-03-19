# SuperEnalotto — Analisi Statistica
## Changelog completo

---

## v1.0.4 — Marzo 2026
### Miglioramenti al codice dei codici donazione
- Sistema codici donazione completo
- Gist privato per codici univoci
- Pulsante "↑ Carica in schedina" per Claude e Grok
- GitHub Actions per aggiornamento automatico
- Fix validazione codici

---

## v1.0.3 — Marzo 2026
### Miglioramenti parser previsioni Claude
- Aggiunto riconoscimento parole numerali italiane: "due", "tre", "quattro", "cinque", "sei"
- Aggiunto riconoscimento "ultime N estrazioni" come periodo (separato dai mesi)
- Aggiunto pattern "gli altri numeri [tipo]" per riempire i posti rimanenti
- Corretto articolo "del/delle/dell'" nel reasoning in base al periodo
- Corretta regex `freddi?` → `freddo|freddi` che troncava la parola
- Corretto gruppo contesto regex per permettere cifre nei periodi ("delle ultime 10 estrazioni")
- Fix lookahead regex per separare correttamente slot consecutivi
- Integrazione modifiche Grok (versione aggiornata)

---

## v1.0.2 — Marzo 2026
### Fix parser previsioni Claude
- Corretto riconoscimento "un numero [tipo]" (prima richiedeva solo cifre)
- Aggiunto "completamente casuali" come variante di "casual"
- Aggiunto "ritardatario/ritardatari" come sinonimo di "freddo/in ritardo"
- Fix regex reMaster: lookahead per separare slot multipli nella stessa frase
- Fix encoding carattere `ù` (era codificato come `\xf9` nelle copie duplicate)
- Rimossi 3 duplicati del codice parseSlots inseriti per errore
- Sezioni Claude e Grok ora appaiono automaticamente al caricamento del database
- showForecastSection() agganciata a tutti i percorsi di caricamento DB (GitHub, raw, import)

---

## v1.0.1 — Marzo 2026
### PWA e interfaccia
- Aggiunto numero di versione in alto a destra nell'header
- Aggiunto rilevamento automatico modalità chiara/scura del sistema operativo
- Toggle modalità chiara/scura con colori corretti (sfondo scuro in light mode, bianco in dark mode)
- Verde celle anni aggiornato a #489a45 (verde ufficiale SuperEnalotto)
- Checkbox "Non mostrare più" nel popup donazione disabilitata (popup ad ogni avvio)
- Popup donazione: verifica token GitHub per non mostrarlo al proprietario

### Jackpot
- Aggiunto display "il prossimo jackpot è:" con scraping da superenalotto.com/risultati
- Fetch jackpot agganciato al caricamento database da GitHub
- Sostituito fetch() con XMLHttpRequest per bypassare interferenze estensioni Chrome
- Selettore CSS corretto: `.next-jackpot span` sulla pagina risultati (senza anno)
- Jackpot salvato nel database JSON per distribuzione automatica agli utenti

### Bug fix
- Corretto `lastJackpot is not defined` (variabile spostata a window scope)
- Rimosso blocco `jm` orfano in fetchLastDraw
- Aggiornati proxy CORS: codetabs, proxy.cors.sh, cors.lol come primari

---

## v1.0.0 — Marzo 2026
### PWA (Progressive Web App)
- Conversione da file HTML statico a PWA installabile su Android
- Creazione manifest.json con icone 72→512px
- Service worker con cache offline e aggiornamento automatico versione
- Header verde #489a45 (colore ufficiale SuperEnalotto)
- Layout responsive mobile-first
- Icona personalizzata SuperEnalotto (logo ufficiale)
- Pubblicazione su GitHub Pages

### Sincronizzazione GitHub
- Sezione "Sincronizzazione GitHub" con Personal Access Token
- Caricamento automatico database JSON da GitHub all'avvio
- Salvataggio database su GitHub con un click
- Verifica identità proprietario via API GitHub (popup donazione)
- Export con nome fisso: `storico-estrazioni-superenalotto.json`
- Jackpot incluso nel payload JSON

### Modalità chiara/scura
- Toggle ☀/🌙 nella barra di stato
- Variabili CSS separate per dark/light mode
- Sfondo crema in light mode, pillole anni verdi coerenti
- Rilevamento automatico preferenza sistema operativo
- Salvataggio preferenza in localStorage

### Popup donazione
- Popup con sfondo verde #489a45 al primo avvio
- Testo giallo #f2b225 + "Grazie!" rosso #d73239
- Logo PayPal SVG ufficiale con link paypal.me/delpinsky
- Nascosto per il proprietario (verifica token GitHub)

### Footer
- Copyright © Christian Scarpellini 2026
- Logo PayPal come link con sfondo bianco arrotondato
- Note legali: dati © superenalotto.com, solo uso statistico

---

## Pre-v1.0.0 — Febbraio/Marzo 2026 (superenalotto_V4.html)

### Core app
- Scraping estrazioni da superenalotto.com (1997→oggi) via proxy CORS
- Database locale in memoria con export/import JSON
- Parser HTML per tutte le estrazioni anno per anno
- Calcolo frequenze, ritardi, bilanciamento numeri 1-90

### Interfaccia
- Design dark mode con palette oro/viola/verde
- Griglia anni con stato (scaricato/in corso/corrente)
- Pillole anno con contatore estrazioni
- Ultima estrazione con palline animate
- Prossima data estrazione calcolata automaticamente

### Analisi statistica
- Overview: totale estrazioni, numero più frequente, più ritardatario
- Tab Vincite/Estrazioni/Frequenze con menu periodo
- Filtro per periodo: 1/3/6/12 mesi, storico completo
- Grafico frequenze con barre orizzontali

### La tua schedina
- 8 slot (6 numeri + Jolly + SuperStar)
- Griglia 90 numeri per selezione
- Modalità "1 numero" e "6 numeri" contemporaneamente
- Analisi schedina vs storico
- Generazione casuale
- Salvataggio in memoria (in-memory per PWA)

### Schedine preferite
- Salvataggio schedine classiche e sistemi
- Badge tipo sistema (INT/G5/G4/G3)
- Pulsante ↑ Carica per schedine e ↓ Sistema per sistemi
- Export/import JSON preferiti
- Event delegation per listener stabili

### Sistema di gioco
- Tab Integrale / Ridotto / Costo Sistemi
- Calcolo combinazioni C(n,6) in tempo reale
- Sistema ridotto asincrono (no freeze browser) con progress bar
- G5 (10-12 numeri), G4 (13-19), G3 (20-33) — dati ufficiali Sisal
- Paginazione combinazioni (50 per volta)
- Messaggio errore per range non valido
- Tasto SALVA sistema nei preferiti
- Riepilogo live al click su ogni numero

### Cerca estrazione
- Ricerca per data o numero concorso
- Display risultato con palline

### Previsioni prossima estrazione
- 4 metodi: frequenti, freddi, bilanciati, casuali
- Menu periodo configurabile

### Previsioni di Claude
- Parser NLP strutturato per istruzioni in linguaggio naturale
- Riconoscimento slot: caldi/freddi/casuali/bilanciati/in coppia/in terzina
- Periodi: ultimo mese, N mesi, ultimo anno, ultime N estrazioni
- Jolly: più ritardatario · SuperStar: più frequente recente
- Reasoning narrativo con dettagli freq/ritardo per numero
- Modalità fallback classica per input non strutturato

### Previsioni di Grok
- Sezione identica a Claude con reasoning cosmico
- Input suggerimento opzionale
- Pulsante "Chiedi di nuovo"
