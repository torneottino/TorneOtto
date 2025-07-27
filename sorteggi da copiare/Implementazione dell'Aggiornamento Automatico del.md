<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# Implementazione dell'Aggiornamento Automatico del Tabellone per Tornei di Eliminazione Diretta

Analizzando la tua pagina web di riepilogo del torneo "Elimin_Diretta_Test" e la struttura della tua applicazione TorneOtto, è assolutamente possibile implementare un sistema di aggiornamento automatico del tabellone che funzioni come desideri[^1][^2]. Questo sistema permetterebbe di inserire i risultati delle partite e vedere immediatamente l'avanzamento dei vincitori nei turni successivi, senza necessità di ricaricare la pagina[^3].

## Panoramica della Soluzione

La soluzione prevede l'aggiunta di elementi interattivi alle card delle partite esistenti e l'implementazione di un sistema AJAX per comunicare con il server Flask[^3][^4]. Ecco come struttureremo l'implementazione:

1. Aggiungere campi di input per i punteggi accanto a ciascuna squadra
2. Inserire un pulsante di conferma (freccia/icona) per ogni partita
3. Implementare la logica JavaScript per l'invio dei risultati
4. Creare un endpoint Flask per ricevere e processare i risultati
5. Aggiornare dinamicamente il DOM per mostrare i vincitori nei turni successivi

## Modifiche al Frontend

### 1. Aggiornamento delle Card delle Partite

Per ogni partita nel primo turno (e nei turni successivi), dobbiamo modificare la struttura HTML per includere campi di input e un pulsante di conferma[^5][^3]:

```html
<div class="match-card" data-match-id="1" data-round="1" data-next-match="7" data-next-position="1">
    <div class="match-header">
        <span class="match-number">Partita 1</span>
    </div>
    <div class="match-content">
        <div class="team">
            <span class="team-name">Russo / Marino</span>
            <input type="number" class="score-input" min="0" placeholder="0">
        </div>
        <div class="team">
            <span class="team-name">Esposito / Bruno</span>
            <input type="number" class="score-input" min="0" placeholder="0">
        </div>
        <button class="submit-result" title="Conferma risultato">
            <i class="fas fa-arrow-circle-right"></i>
        </button>
    </div>
</div>
```


### 2. Stile CSS per i Nuovi Elementi

Aggiungiamo lo stile CSS per i nuovi elementi interattivi[^5]:

```css
.match-content {
    position: relative;
    padding-right: 40px; /* Spazio per il pulsante */
}

.score-input {
    width: 40px;
    background: #1a1b1f;
    border: 1px solid #444;
    color: #fff;
    border-radius: 4px;
    padding: 4px;
    text-align: center;
    margin-left: auto;
}

.submit-result {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: #28a745;
    font-size: 1.5rem;
    cursor: pointer;
    transition: all 0.2s;
}

.submit-result:hover {
    color: #218838;
    transform: translateY(-50%) scale(1.1);
}

.team.winner {
    background: #1a2e1a;
    border-color: #28a745;
}

.team.winner::after {
    content: "✓";
    color: #28a745;
    margin-left: 8px;
}
```


## Implementazione JavaScript

### 1. Gestione degli Eventi e Aggiornamento AJAX

Implementiamo la logica JavaScript per gestire l'invio dei risultati e l'aggiornamento del tabellone[^6][^3]:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Trova tutti i pulsanti di conferma risultato
    const submitButtons = document.querySelectorAll('.submit-result');
    
    // Aggiungi event listener a ciascun pulsante
    submitButtons.forEach(button => {
        button.addEventListener('click', function() {
            const matchCard = this.closest('.match-card');
            const matchId = matchCard.dataset.matchId;
            const nextMatchId = matchCard.dataset.nextMatch;
            const nextPosition = matchCard.dataset.nextPosition;
            
            // Ottieni i punteggi inseriti
            const teams = matchCard.querySelectorAll('.team');
            const team1Name = teams[^0].querySelector('.team-name').textContent;
            const team2Name = teams[^1].querySelector('.team-name').textContent;
            const team1Score = parseInt(teams[^0].querySelector('.score-input').value) || 0;
            const team2Score = parseInt(teams[^1].querySelector('.score-input').value) || 0;
            
            // Verifica che i punteggi siano validi
            if (team1Score === team2Score) {
                alert('I punteggi non possono essere uguali. Inserisci un vincitore.');
                return;
            }
            
            // Prepara i dati da inviare
            const data = {
                match_id: matchId,
                team1_name: team1Name,
                team2_name: team2Name,
                team1_score: team1Score,
                team2_score: team2Score,
                next_match_id: nextMatchId,
                next_position: nextPosition
            };
            
            // Invia i dati al server tramite AJAX
            updateMatchResult(data);
        });
    });
    
    // Funzione per inviare i risultati al server
    function updateMatchResult(data) {
        fetch('/tornei/19/eliminazione/update-match', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken() // Funzione per ottenere il token CSRF
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Aggiorna l'UI per mostrare il vincitore
                updateMatchUI(data.match_updated);
                
                // Aggiorna il match successivo con il vincitore
                if (data.next_match_updated) {
                    updateNextMatchUI(data.next_match_updated);
                }
            } else {
                alert('Errore durante l\'aggiornamento: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            alert('Si è verificato un errore durante l\'aggiornamento.');
        });
    }
    
    // Funzione per ottenere il token CSRF
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }
    
    // Funzione per aggiornare l'UI della partita corrente
    function updateMatchUI(matchData) {
        const matchCard = document.querySelector(`.match-card[data-match-id="${matchData.match_id}"]`);
        const teams = matchCard.querySelectorAll('.team');
        
        // Rimuovi classe winner da entrambe le squadre
        teams.forEach(team => team.classList.remove('winner'));
        
        // Aggiungi classe winner alla squadra vincitrice
        if (matchData.winner === matchData.team1) {
            teams[^0].classList.add('winner');
        } else {
            teams[^1].classList.add('winner');
        }
        
        // Disabilita gli input e il pulsante
        matchCard.querySelectorAll('.score-input').forEach(input => {
            input.disabled = true;
        });
        matchCard.querySelector('.submit-result').disabled = true;
        matchCard.querySelector('.submit-result').style.opacity = '0.5';
    }
    
    // Funzione per aggiornare l'UI del match successivo
    function updateNextMatchUI(nextMatchData) {
        const nextMatchCard = document.querySelector(`.match-card[data-match-id="${nextMatchData.match_id}"]`);
        if (nextMatchCard) {
            const teams = nextMatchCard.querySelectorAll('.team');
            
            // Aggiorna il nome della squadra nella posizione corretta
            if (nextMatchData.team1) {
                teams[^0].querySelector('.team-name').textContent = nextMatchData.team1;
            }
            if (nextMatchData.team2) {
                teams[^1].querySelector('.team-name').textContent = nextMatchData.team2;
            }
        }
    }
});
```


## Implementazione Backend (Flask)

### 1. Nuovo Endpoint per l'Aggiornamento dei Risultati

Dobbiamo creare un nuovo endpoint Flask per gestire l'aggiornamento dei risultati[^3][^4]:

```python
@app.route('/tornei/<int:id>/eliminazione/update-match', methods=['POST'])
def update_elimination_match(id):
    if request.method == 'POST':
        data = request.json
        
        # Estrai i dati dalla richiesta
        match_id = data.get('match_id')
        team1_score = data.get('team1_score')
        team2_score = data.get('team2_score')
        next_match_id = data.get('next_match_id')
        next_position = data.get('next_position')
        
        try:
            # Trova la partita nel database
            match = EliminationMatch.query.filter_by(
                id=match_id, 
                tournament_id=id
            ).first()
            
            if not match:
                return jsonify({'success': False, 'error': 'Partita non trovata'})
            
            # Aggiorna i punteggi
            match.team1_score = team1_score
            match.team2_score = team2_score
            
            # Determina il vincitore
            winner_team_id = match.team1_id if team1_score > team2_score else match.team2_id
            match.winner_team_id = winner_team_id
            match.stato = "Completed"
            
            # Trova la squadra vincitrice
            winner_team = EliminationTeam.query.get(winner_team_id)
            
            # Aggiorna il match successivo se esiste
            if next_match_id:
                next_match = EliminationMatch.query.filter_by(
                    id=next_match_id, 
                    tournament_id=id
                ).first()
                
                if next_match:
                    # Aggiorna team1 o team2 in base alla posizione
                    if int(next_position) == 1:
                        next_match.team1_id = winner_team_id
                    else:
                        next_match.team2_id = winner_team_id
            
            # Salva le modifiche nel database
            db.session.commit()
            
            # Prepara la risposta
            response = {
                'success': True,
                'match_updated': {
                    'match_id': match_id,
                    'team1': data.get('team1_name'),
                    'team2': data.get('team2_name'),
                    'team1_score': team1_score,
                    'team2_score': team2_score,
                    'winner': data.get('team1_name') if team1_score > team2_score else data.get('team2_name')
                }
            }
            
            # Aggiungi informazioni sul match successivo se esiste
            if next_match_id and next_match:
                team1_name = None
                team2_name = None
                
                if next_match.team1_id:
                    team1 = EliminationTeam.query.get(next_match.team1_id)
                    if team1:
                        team1_name = json.loads(team1.players_json)[^0]['cognome'] + ' / ' + json.loads(team1.players_json)[^1]['cognome']
                
                if next_match.team2_id:
                    team2 = EliminationTeam.query.get(next_match.team2_id)
                    if team2:
                        team2_name = json.loads(team2.players_json)[^0]['cognome'] + ' / ' + json.loads(team2.players_json)[^1]['cognome']
                
                response['next_match_updated'] = {
                    'match_id': next_match_id,
                    'team1': team1_name,
                    'team2': team2_name
                }
            
            return jsonify(response)
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
```


### 2. Aggiornamento del Template HTML

Dobbiamo modificare il template esistente per includere gli attributi data necessari e il token CSRF[^3]:

```html
<!-- Aggiungi il token CSRF nell'head -->
<head>
    <!-- ... altri meta tag ... -->
    <meta name="csrf-token" content="{{ csrf_token() }}">
</head>

<!-- Modifica il template delle partite -->
{% for match in matches %}
<div class="match-card" data-match-id="{{ match.id }}" data-round="{{ match.turno }}" 
     data-next-match="{{ match.next_match_id }}" data-next-position="{{ match.next_position }}">
    <div class="match-header">
        <span class="match-number">Partita {{ match.id }}</span>
    </div>
    <div class="match-content">
        <div class="team {% if match.winner_team_id == match.team1_id %}winner{% endif %}">
            <span class="team-name">{{ match.team1_name }}</span>
            {% if match.stato != "Completed" %}
            <input type="number" class="score-input" min="0" placeholder="0" 
                   value="{{ match.team1_score if match.team1_score is not none }}">
            {% else %}
            <span class="score">{{ match.team1_score }}</span>
            {% endif %}
        </div>
        <div class="team {% if match.winner_team_id == match.team2_id %}winner{% endif %}">
            <span class="team-name">{{ match.team2_name }}</span>
            {% if match.stato != "Completed" %}
            <input type="number" class="score-input" min="0" placeholder="0" 
                   value="{{ match.team2_score if match.team2_score is not none }}">
            {% else %}
            <span class="score">{{ match.team2_score }}</span>
            {% endif %}
        </div>
        {% if match.stato != "Completed" %}
        <button class="submit-result" title="Conferma risultato">
            <i class="fas fa-arrow-circle-right"></i>
        </button>
        {% endif %}
    </div>
</div>
{% endfor %}
```


## Considerazioni per l'Implementazione

1. **Struttura del Database**: La tua struttura attuale con `ELIMINATION_MATCHES` è già predisposta per supportare questa funzionalità, con campi per i punteggi e il vincitore[^4].
2. **Validazione**: Assicurati di implementare una validazione adeguata sia lato client che lato server per evitare risultati non validi[^6].
3. **Gestione degli Errori**: Implementa una gestione degli errori robusta per gestire casi come punteggi mancanti o problemi di connessione[^3].
4. **Sicurezza**: Utilizza token CSRF e validazione dei dati per proteggere le tue API da attacchi[^3][^4].
5. **Esperienza Utente**: Aggiungi feedback visivi come animazioni o notifiche per migliorare l'esperienza utente durante l'aggiornamento del tabellone[^5][^7].

## Istruzioni per l'IA che Genererà il Codice

Quando chiederai a un'IA di generare il codice per questa funzionalità, fornisci queste informazioni chiare[^1][^4]:

1. **Descrizione del Problema**: "Voglio implementare un sistema di aggiornamento automatico del tabellone per un torneo di eliminazione diretta. Quando inserisco i risultati di una partita e confermo, il vincitore deve essere automaticamente avanzato al turno successivo senza ricaricare la pagina."
2. **Struttura del Database**: Fornisci la struttura delle tabelle `ELIMINATION_TOURNAMENTS`, `ELIMINATION_TEAMS` e `ELIMINATION_MATCHES`.
3. **Tecnologie Utilizzate**: "L'applicazione è sviluppata con Flask, SQLAlchemy, Jinja2 per i template e JavaScript vanilla/jQuery per il frontend."
4. **Requisiti Specifici**:
    - "Voglio aggiungere campi di input per i punteggi accanto a ciascuna squadra"
    - "Ogni partita deve avere un pulsante (freccia) per confermare il risultato"
    - "Dopo la conferma, il vincitore deve apparire automaticamente nella partita del turno successivo"
    - "L'aggiornamento deve avvenire senza ricaricare la pagina (AJAX)"
    - "Voglio un feedback visivo per indicare il vincitore della partita"
5. **Esempi di Codice Esistente**: Fornisci frammenti del tuo codice HTML, CSS e JavaScript esistente per aiutare l'IA a mantenere lo stile e la struttura coerenti.

Seguendo queste linee guida, potrai implementare con successo un sistema di aggiornamento automatico del tabellone che migliorerà significativamente l'esperienza utente della tua applicazione TorneOtto[^7][^4].

<div style="text-align: center">⁂</div>

[^1]: https://www.npmjs.com/package/brackets-manager/v/1.0.0

[^2]: https://cs.stackexchange.com/questions/79207/algorithm-to-create-tournament-brackets

[^3]: https://stackoverflow.com/questions/69721638/dynamically-update-divs-on-webpage-flask

[^4]: https://github.com/Drarig29/brackets-manager.js/

[^5]: https://www.jqueryscript.net/chart-graph/jQuery-Plugin-For-Customizable-Tournament-Brackets-Bracket.html

[^6]: https://github.com/bracketclub/bracket-updater

[^7]: https://tournamentbracketsoftware.com/Tournament-Bracket-System.php

[^8]: paste.txt

[^9]: ANALISI_COMPLETA_TORNEOTTO.txt

[^10]: https://gist.github.com/sevastos/1e6ef806fedef25c8c022d43f38e7120

[^11]: https://stackoverflow.com/questions/77697029/tournament-bracket-rounds-not-updating-with-winner-when-entering-scores-in-previ

[^12]: https://github.com/wgoode3/neo-bracket

[^13]: https://sportsconnect.com/stack-tourney/

[^14]: https://bloximages.newyork1.vip.townnews.com/lancasteronline.com/content/tncms/assets/v3/editorial/2/7f/27f5bdfa-d103-11e5-b036-4397abf7eff5/56bcf7c93cbab.pdf.pdf

[^15]: https://www.npmjs.com/package/bracket-generator

[^16]: https://github.com/topics/padel?o=desc\&s=updated

[^17]: https://github.com/srpepperoni/padel-api

[^18]: https://github.com/Padelanalytics

[^19]: https://www.jsdelivr.com/package/npm/@unitetheculture/brackets-manager

[^20]: https://flask.palletsprojects.com/en/stable/patterns/javascript/

