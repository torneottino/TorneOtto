"""
Implementazione del sistema di calcolo ELO per il torneo TorneOtto30.

DETTAGLI DEL CALCOLO ELO:
------------------------
1. K-Factor: 32 (valore standard per giocatori principianti)
   - Questo valore determina quanto velocemente l'ELO può cambiare
   - 32 è un buon compromesso per permettere ai giocatori di salire/scendere rapidamente
   - Non viene diviso per 2 quando applicato ai giocatori

2. Calcolo ELO di una partita:
   - ELO atteso = 1 / (1 + 10^((ELO_avversario - ELO_proprio) / 400))
   - Variazione = K * (risultato - ELO_atteso)
   - Risultato: 1 (vittoria), 0.5 (pareggio), 0 (sconfitta)

3. Calcolo ELO di una giornata:
   - Per ogni partita:
     * Si calcola l'ELO totale della squadra (somma degli ELO dei giocatori)
     * Si calcola la variazione ELO per la squadra
     * Ogni giocatore della squadra riceve la variazione COMPLETA (non divisa per 2)
   - Alla fine della giornata:
     * Le variazioni di ogni giocatore vengono medie sul numero di partite giocate
     * Questo evita che chi gioca più partite abbia un vantaggio/svantaggio

ESEMPIO PRATICO:
--------------
Squadra A (ELO totale 3000):
- Giocatore 1: 1500
- Giocatore 2: 1500

Squadra B (ELO totale 3000):
- Giocatore 3: 1500
- Giocatore 4: 1500

Partita: Squadra A vs Squadra B (11-9)
- ELO atteso per Squadra A: 0.5 (stesso ELO)
- Variazione: 32 * (1 - 0.5) = +16 per Squadra A, -16 per Squadra B
- Ogni giocatore della Squadra A riceve +16
- Ogni giocatore della Squadra B riceve -16

Se un giocatore gioca 3 partite con variazioni +16, +16, -16:
- Variazione finale = (+16 + 16 - 16) / 3 = +5.33
"""

from models.player import Player, PlayerTournamentElo, PlayerEloHistory
from models.tournament_day import TorneOtto30Day
from extensions import db
from sqlalchemy import desc

def calculate_match_elo_change(team1_elo, team2_elo, result):
    """
    Calcola la variazione ELO per una singola partita
    
    Args:
        team1_elo: ELO della prima squadra (somma degli ELO dei giocatori)
        team2_elo: ELO della seconda squadra (somma degli ELO dei giocatori)
        result: 1 per vittoria team1, 0.5 per pareggio, 0 per sconfitta team1
        
    Returns:
        tuple: (variazione_team1, variazione_team2)
    """
    k_factor = 32  # K-factor standard per principianti
    expected = 1 / (1 + 10**((team2_elo - team1_elo) / 400))
    change = k_factor * (result - expected)
    return round(change, 2), round(-change, 2)

def get_team_elo(player_ids, tournament_id):
    """
    Calcola l'ELO di una squadra sommando gli ELO dei giocatori
    """
    total_elo = 0
    for player_id in player_ids:
        elo = PlayerTournamentElo.query.filter_by(
            player_id=player_id,
            tournament_id=tournament_id
        ).first()
        total_elo += elo.elo_rating if elo else 1500.0
    return total_elo

def calculate_day_elo_changes(day_id):
    """
    Calcola le variazioni ELO per tutti i giocatori in una giornata
    
    Returns:
        dict: {player_id: somma_variazioni_elo}
    """
    day = TorneOtto30Day.query.get(day_id)
    config = day.get_config()
    teams = config.get('teams', [])
    schedule = config.get('schedule', [])
    results = config.get('results', {})
    
    # Dizionario per tenere traccia delle variazioni ELO e del numero di partite per ogni giocatore
    player_changes = {player_id: 0 for team in teams for player_id in team}
    player_matches = {player_id: 0 for team in teams for player_id in team}
    
    # Per ogni partita nel calendario
    for round_matches in schedule:
        for match in round_matches:
            match_key = f"{match[0]}-{match[1]}"
            result = results.get(match_key)
            if not result:
                continue
                
            try:
                score_a, score_b = map(int, result.split('-'))
            except:
                continue
                
            # Determina il risultato (1 vittoria, 0.5 pareggio, 0 sconfitta)
            if score_a > score_b:
                match_result = 1
            elif score_a < score_b:
                match_result = 0
            else:
                match_result = 0.5
                
            # Ottieni gli ID dei giocatori delle due squadre
            team1_players = teams[match[0]-1]
            team2_players = teams[match[1]-1]
            
            # Calcola gli ELO delle squadre
            team1_elo = get_team_elo(team1_players, day.tournament_id)
            team2_elo = get_team_elo(team2_players, day.tournament_id)
            
            # Calcola le variazioni ELO
            team1_change, team2_change = calculate_match_elo_change(team1_elo, team2_elo, match_result)
            
            # Distribuisci le variazioni tra i giocatori della squadra (variazione completa per ogni giocatore)
            for player_id in team1_players:
                player_changes[player_id] += team1_change  # Variazione completa
                player_matches[player_id] += 1
            for player_id in team2_players:
                player_changes[player_id] += team2_change  # Variazione completa
                player_matches[player_id] += 1
    
    # Calcola la media delle variazioni per ogni giocatore
    return {
        player_id: round(change / player_matches[player_id], 2) if player_matches[player_id] > 0 else 0 
        for player_id, change in player_changes.items()
    }

def get_player_current_elo(player_id, tournament_id, before_day_id=None):
    """
    Ottiene l'ELO corrente di un giocatore per un torneo.
    Se before_day_id è specificato, restituisce l'ELO prima di quella giornata.
    """
    query = PlayerEloHistory.query.filter_by(
        player_id=player_id,
        tournament_id=tournament_id
    )
    
    if before_day_id:
        query = query.filter(PlayerEloHistory.tournament_day_id < before_day_id)
    
    last_history = query.order_by(desc(PlayerEloHistory.tournament_day_id)).first()
    
    if last_history:
        return last_history.new_elo
    return 1500.0  # ELO iniziale se non ci sono giornate precedenti

def update_tournament_elos(day_id):
    """
    Aggiorna gli ELO di tutti i giocatori per una giornata di torneo.
    Usa l'ELO dell'ultima giornata come base per il calcolo.
    """
    day = TorneOtto30Day.query.get(day_id)
    config = day.get_config()
    teams = config.get('teams', [])
    
    # Calcola le variazioni medie per ogni giocatore
    avg_changes = calculate_day_elo_changes(day_id)
    
    # Per ogni giocatore, aggiorna l'ELO e registra la storia
    for team in teams:
        for player_id in team:
            # Ottieni l'ELO corrente del giocatore (dall'ultima giornata o 1500 se è la prima)
            current_elo = get_player_current_elo(player_id, day.tournament_id, day_id)
            
            # Calcola il nuovo ELO
            elo_change = avg_changes.get(player_id, 0)
            new_elo = current_elo + elo_change
            
            # Aggiorna o crea il record ELO del giocatore per questo torneo
            elo_rating = PlayerTournamentElo.query.filter_by(
                player_id=player_id,
                tournament_id=day.tournament_id
            ).first()
            
            if not elo_rating:
                elo_rating = PlayerTournamentElo(
                    player_id=player_id,
                    tournament_id=day.tournament_id,
                    elo_rating=current_elo  # Usa l'ELO corrente invece di 1500
                )
                db.session.add(elo_rating)
            
            # Aggiorna l'ELO
            elo_rating.elo_rating = new_elo
            
            # Elimina eventuali record duplicati per questa giornata
            PlayerEloHistory.query.filter_by(
                player_id=player_id,
                tournament_id=day.tournament_id,
                tournament_day_id=day_id
            ).delete()
            
            # Registra la storia
            history = PlayerEloHistory(
                player_id=player_id,
                tournament_id=day.tournament_id,
                tournament_day_id=day_id,
                old_elo=current_elo,
                new_elo=new_elo,
                elo_change=elo_change
            )
            db.session.add(history)
    
    db.session.commit()

def delete_tournament_day_elos(day_id):
    """
    Elimina i record ELO di una giornata e aggiorna gli ELO dei giocatori
    basandosi sulle giornate rimanenti.
    """
    day = TorneOtto30Day.query.get_or_404(day_id)
    if not day:
        return
    
    # Elimina tutti i record ELO della giornata
    PlayerEloHistory.query.filter_by(
        tournament_id=day.tournament_id,
        tournament_day_id=day_id
    ).delete()
    
    # Recupera tutte le giornate del torneo in ordine cronologico
    remaining_days = TorneOtto30Day.query.filter_by(
        tournament_id=day.tournament_id
    ).order_by(TorneOtto30Day.data).all()
    
    # Se non ci sono più giornate, resetta tutti gli ELO a 1500
    if not remaining_days:
        PlayerTournamentElo.query.filter_by(
            tournament_id=day.tournament_id
        ).delete()
        db.session.commit()
        return
    
    # Resetta tutti gli ELO a 1500 prima di ricalcolare
    PlayerTournamentElo.query.filter_by(
        tournament_id=day.tournament_id
    ).delete()
    
    # Ricalcola gli ELO per tutte le giornate rimanenti in ordine
    for remaining_day in remaining_days:
        update_tournament_elos(remaining_day.id)
    
    db.session.commit() 