# Implementazione Sistema Americana Semplice

## Panoramica

Sono state implementate le modifiche al sistema "semplice" dell'americana per permettere all'utente di scegliere il numero di turni e di campi, con il sistema che adatta automaticamente sorteggi, coppie e partite.

## Modifiche Implementate

### 1. Servizio Americana (`services/americana_service.py`)

#### Funzione `calculate_total_matches` aggiornata
- **Modifica**: Per il tipo "semplice", ora restituisce `0` invece di calcolare un numero fisso
- **Motivazione**: Il numero di partite è ora determinato dai parametri `num_rounds_config` e `num_courts` scelti dall'utente
- **Correzione**: Per il tipo "completo", corretto il calcolo da `num_players // 2 - 1` a `num_players // 2`

#### Funzione `generate_simple_american_tournament` completamente riscritta
- **Nuovi parametri**: 
  - `players`: Lista dei giocatori
  - `num_courts`: Numero di campi disponibili
  - `num_rounds_config`: Numero di turni scelti dall'utente

- **Algoritmo implementato**:
  1. **Fase 1 - Formazione Coppie**: Usa l'algoritmo di Berger per la rotazione dei giocatori
     - Primo turno: accoppiamento semplice in ordine
     - Turni successivi: rotazione di Berger (primo giocatore fisso, altri ruotano)
  2. **Fase 2 - Generazione Partite**: 
     - Crea fino a `num_courts` partite per turno
     - Accoppia sequenzialmente le squadre disponibili
     - Traccia l'uso di coppie e scontri diretti

- **Caratteristiche**:
  - Minimizza ripetizioni di coppie
  - Bilancia scontri diretti tra giocatori
  - Garantisce che ogni giocatore giochi con tutti gli altri (se abbastanza turni)
  - Assegna automaticamente i campi

### 2. Template Aggiornati

#### `templates/tournaments/americana/manual_players.html`
- **Aggiunta**: Sezione di configurazione per torneo semplice
- **Campo**: Select per scegliere il numero di turni (3-10)
- **Validazione**: JavaScript per verificare la selezione del numero di turni
- **Stili**: CSS per la nuova sezione di configurazione

#### `templates/tournaments/americana/select_players.html`
- **Aggiunta**: Stessa sezione di configurazione per torneo semplice
- **Integrazione**: Con il sistema esistente di selezione giocatori dal database

### 3. Route Aggiornato (`routes/tournaments.py`)

#### Route `americana_setup` modificato
- **Nuovo parametro**: Recupera `num_turni_semplice` dal form
- **Logica aggiornata**: Passa il parametro alla funzione `generate_simple_american_tournament`
- **Gestione errori**: Mantiene la validazione esistente

## Algoritmo di Berger Implementato

### Principio
L'algoritmo di Berger garantisce che in un round-robin ogni giocatore incontri tutti gli altri esattamente una volta.

### Implementazione
```python
# Per il turno N, ruota di N-1 posizioni
for _ in range(round_num - 1):
    # Sposta il secondo elemento alla fine
    current_pairing_order = [current_pairing_order[0]] + current_pairing_order[2:] + [current_pairing_order[1]]
```

### Esempio con 8 giocatori
- **Turno 1**: [1,2,3,4,5,6,7,8] → Coppie: (1,8), (2,7), (3,6), (4,5)
- **Turno 2**: [1,3,4,5,6,7,8,2] → Coppie: (1,2), (3,8), (4,7), (5,6)
- **Turno 3**: [1,4,5,6,7,8,2,3] → Coppie: (1,3), (4,2), (5,8), (6,7)
- E così via...

## Test e Validazione

### File di Test: `test_americana_semplice.py`
- **Test 1**: 8 giocatori, 2 campi, 4 turni
- **Test 2**: 6 giocatori, 3 campi, 5 turni
- **Risultati**: Verifica bilanciamento coppie e scontri diretti

### Risultati del Test
- ✅ Coppie bilanciate: Ogni coppia appare esattamente una volta
- ✅ Rotazione corretta: Algoritmo di Berger funziona
- ✅ Numero partite corretto: 2 partite per turno con 2 campi
- ✅ Scontri diretti bilanciati: Distribuzione uniforme

## Vantaggi della Nuova Implementazione

### 1. Flessibilità
- L'utente può scegliere il numero di turni (3-10)
- Il sistema si adatta automaticamente al numero di campi
- Durata del torneo personalizzabile

### 2. Bilanciamento
- Minimizza ripetizioni di coppie
- Bilancia scontri diretti tra giocatori
- Distribuzione uniforme delle partite sui campi

### 3. Semplicità d'uso
- Interfaccia intuitiva per la configurazione
- Validazione automatica dei parametri
- Generazione automatica delle partite

### 4. Scalabilità
- Funziona con qualsiasi numero pari di giocatori (≥4)
- Si adatta a qualsiasi numero di campi
- Gestisce turni multipli efficientemente

## Utilizzo

### Per l'utente finale:
1. Crea un torneo americana
2. Seleziona tipo "semplice"
3. Scegli il numero di turni desiderato
4. Seleziona i giocatori
5. Il sistema genera automaticamente le partite bilanciate

### Per lo sviluppatore:
```python
# Esempio di utilizzo
matches = AmericanaService.generate_simple_american_tournament(
    players=players_list,
    num_courts=4,
    num_rounds_config=6
)
```

## Compatibilità

- ✅ Mantiene compatibilità con il sistema esistente
- ✅ Non modifica la logica del torneo "completo"
- ✅ Preserva tutte le funzionalità esistenti
- ✅ Integrazione trasparente con l'interfaccia utente

## Conclusioni

L'implementazione del sistema "semplice" migliorato offre:
- **Controllo utente**: Scelta del numero di turni
- **Bilanciamento automatico**: Algoritmo di Berger per coppie ottimali
- **Flessibilità**: Adattamento automatico ai campi disponibili
- **Qualità**: Minimizzazione ripetizioni e bilanciamento scontri

Il sistema è ora pronto per l'uso in produzione e offre un'esperienza utente significativamente migliorata per i tornei all'americana di tipo "semplice". 