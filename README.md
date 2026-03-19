# SuperEnalotto — Analisi Statistica PWA

App web progressiva (PWA) per l'analisi statistica delle estrazioni del SuperEnalotto dal 1997 ad oggi. Dati reali da superenalotto.com.

🔗 **Live:** https://delpinsky.github.io/Superenalotto/

---

## Funzionalità principali

- Storico completo estrazioni 1997→oggi con aggiornamento automatico
- Analisi frequenze, ritardi e bilanciamento numeri 1-90
- Filtro per periodo (1/3/6/12 mesi, storico completo, ultime N estrazioni)
- La tua schedina con analisi personalizzata
- Sistema integrale e ridotto con calcolo combinazioni
- Schedine preferite con salvataggio e caricamento
- Previsioni di Claude e Grok con parser NLP in linguaggio naturale
- Jackpot in tempo reale da superenalotto.com
- Dark/Light mode con rilevamento automatico OS
- Sincronizzazione database su GitHub
- Sistema codici donazione

---

## Changelog

### v1.0.5 — Marzo 2026
- Aggiunto venerdì come giorno di estrazione (martedì/giovedì/venerdì/sabato)
- Pulsante "↑ Carica" spostato dentro la card Claude e Grok, accanto al titolo, con stile coerente ai preferiti

### v1.0.4 — Marzo 2026
- Sistema codici donazione `SUPER-XXXX-YYYY-ENA` con validazione HMAC-SHA256
- Codice valido → popup disattivato + caricamento database automatico senza token
- Sezione codice donazione si nasconde automaticamente dopo attivazione
- Supporto Gist privato GitHub per codici univoci e revocabili
- Pulsante "↑ Carica in schedina" nelle previsioni Claude e Grok
- GitHub Actions: aggiornamento automatico database martedì/giovedì/venerdì/sabato alle 20:30 IT

### v1.0.3 — Marzo 2026
- Parser NLP avanzato: "due/tre/quattro/cinque/sei numeri", "ultime N estrazioni", "gli altri numeri [tipo]"
- Fix regex trailing group per slot multipli nella stessa frase
- Sezioni Claude e Grok appaiono automaticamente al caricamento del database
- Pulsante jackpot aggiornato con XHR per bypassare interferenze estensioni Chrome

### v1.0.2 — Marzo 2026
- Fix "un numero [tipo]" riconosciuto come count=1
- Fix "completamente casuali" e "ritardatario" nel parser
- Fix encoding carattere ù nelle regex duplicate
- Jackpot salvato nel database JSON per distribuzione automatica

### v1.0.1 — Marzo 2026
- Numero di versione in alto a destra nell'header
- Toggle modalità chiara/scura con rilevamento automatico OS
- Jackpot in tempo reale con scraping da superenalotto.com/risultati

### v1.0.0 — Marzo 2026
- Prima release PWA installabile su Android
- Storico completo 1997→oggi con scraping multi-proxy
- Sincronizzazione GitHub con Personal Access Token
- Sistema integrale/ridotto, schedine preferite, previsioni Claude e Grok

---

## Note legali

Dati © superenalotto.com — Solo uso statistico e ricreativo.
I numeri del SuperEnalotto sono completamente casuali. Statistica narrativa, non profezia! 🍀
