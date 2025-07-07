from models.player import Player, PlayerTournamentElo, PlayerEloHistory
from models.tournament_day import TorneOtto30Day
from extensions import db
from sqlalchemy import desc
from flask import current_app as app

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
    k_factor = 32  # Ripristinato a 32 come richiesto
    expected = 1 / (1 + 10**((team2_elo - team1_elo) / 400))
    change = k_factor * (result - expected)
    return round(change, 2), round(-change, 2)

def get_team_elo(player_ids, tournament_id):
    """
    Calcola l'ELO di una squadra sommando gli ELO dei giocatori.
    Usa sempre l'ELO più recente dalla storia.
    """
    total_elo = 0
    for player_id in player_ids:
        # Prendi l'ultimo record dalla storia ELO
        last_history = PlayerEloHistory.query.filter_by(
            player_id=player_id,
            tournament_id=tournament_id
        ).order_by(PlayerEloHistory.tournament_day_id.desc()).first()
        
        # Usa l'ultimo ELO dalla storia o 1500 se non ci sono record
        player_elo = last_history.new_elo if last_history else 1500.0
        total_elo += player_elo
        
        app.logger.info(f"Giocatore {player_id}: ELO corrente = {player_elo} (ultimo record: {last_history.tournament_day_id if last_history else 'nessuno'})")
    
    app.logger.info(f"ELO totale squadra: {total_elo}")
    return total_elo

def calculate_day_elo_changes(day_id):
    """
    Calcola le variazioni ELO per tutti i giocatori in una giornata.
    Ogni giocatore riceve la MEDIA delle variazioni ELO delle partite giocate nella giornata.
    
    Returns:
        dict: {player_id: media_variazioni_elo}
    """
    day = TorneOtto30Day.query.get(day_id)
    config = day.get_config()
    teams = config.get('teams', [])
    schedule = config.get('schedule', [])
    results = config.get('results', {})
    
    app.logger.info(f"Calcolo variazioni ELO per giornata {day_id}")
    app.logger.info(f"Config: {config}")
    
    # Dizionari per somma variazioni e numero partite per ogni giocatore
    player_changes = {player_id: 0 for team in teams for player_id in team}
    player_matches = {player_id: 0 for team in teams for player_id in team}
    
    # Per ogni partita nel calendario
    for round_matches in schedule:
        for match in round_matches:
            match_key = f"{match[0]}-{match[1]}"
            result = results.get(match_key)
            if not result:
                app.logger.warning(f"Risultato mancante per partita {match_key}")
                continue
                
            try:
                score_a, score_b = map(int, result.split('-'))
            except:
                app.logger.error(f"Formato risultato non valido per partita {match_key}: {result}")
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
            
            app.logger.info(f"Partita {match_key}: Squadra A {team1_players} vs Squadra B {team2_players} - Risultato: {score_a}-{score_b}")
            
            # Calcola gli ELO delle squadre
            team1_elo = get_team_elo(team1_players, day.tournament_id)
            team2_elo = get_team_elo(team2_players, day.tournament_id)
            
            app.logger.info(f"ELO Squadra A: {team1_elo}, ELO Squadra B: {team2_elo}")
            
            # Calcola le variazioni ELO
            team1_change, team2_change = calculate_match_elo_change(team1_elo, team2_elo, match_result)
            
            app.logger.info(f"Variazioni ELO: Squadra A {team1_change}, Squadra B {team2_change}")
            
            # Somma la variazione e conta la partita per ogni giocatore
            for player_id in team1_players:
                player_changes[player_id] += team1_change
                player_matches[player_id] += 1
                app.logger.info(f"Giocatore {player_id}: variazione {team1_change} (totale: {player_changes[player_id]}, partite: {player_matches[player_id]})")
            for player_id in team2_players:
                player_changes[player_id] += team2_change
                player_matches[player_id] += 1
                app.logger.info(f"Giocatore {player_id}: variazione {team2_change} (totale: {player_changes[player_id]}, partite: {player_matches[player_id]})")
    
    # Calcola la MEDIA delle variazioni per ogni giocatore
    final_changes = {}
    for player_id, change in player_changes.items():
        if player_matches[player_id] > 0:
            final_changes[player_id] = round(change / player_matches[player_id], 2)
        else:
            final_changes[player_id] = 0
    return final_changes

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
        app.logger.error(f"Giornata {day_id} non trovata")
        return
    
    tournament_id = day.tournament_id
    app.logger.info(f"=== INIZIO ELIMINAZIONE ELO PER GIORNATA {day_id} DEL TORNEO {tournament_id} ===")
    app.logger.info(f"Data giornata: {day.data}")
    
    try:
        # 1. Elimina tutti i record ELO della giornata da cancellare
        deleted_history = PlayerEloHistory.query.filter_by(
            tournament_id=tournament_id,
            tournament_day_id=day_id
        ).delete()
        app.logger.info(f"Eliminati {deleted_history} record ELO della giornata {day_id}")
        
        # 2. Elimina tutti i record ELO del torneo (sia history che current)
        deleted_all_history = PlayerEloHistory.query.filter_by(
            tournament_id=tournament_id
        ).delete()
        app.logger.info(f"Eliminati {deleted_all_history} record totali dalla storia ELO del torneo")
        
        deleted_current = PlayerTournamentElo.query.filter_by(
            tournament_id=tournament_id
        ).delete()
        app.logger.info(f"Eliminati {deleted_current} record ELO correnti del torneo")
        
        # 3. Recupera tutte le giornate del torneo in ordine cronologico
        remaining_days = TorneOtto30Day.query.filter_by(
            tournament_id=tournament_id
        ).order_by(TorneOtto30Day.data.asc()).all()
        
        app.logger.info(f"Giornate rimanenti per il ricalcolo ELO: {len(remaining_days)}")
        for d in remaining_days:
            app.logger.info(f"- Giornata {d.id} del {d.data}")
        
        # 4. Se non ci sono più giornate, abbiamo già eliminato tutto
        if not remaining_days:
            app.logger.info("Nessuna giornata rimanente, tutti gli ELO sono stati resettati")
            db.session.commit()
            return
        
        # 5. Ricalcola gli ELO per tutte le giornate rimanenti in ordine cronologico
        for remaining_day in remaining_days:
            app.logger.info(f"\n=== RICALCOLO ELO PER GIORNATA {remaining_day.id} DEL {remaining_day.data} ===")
            try:
                # Per ogni giornata, calcola le variazioni
                avg_changes = calculate_day_elo_changes(remaining_day.id)
                app.logger.info(f"Variazioni ELO calcolate: {avg_changes}")
                
                # Per ogni giocatore nella giornata
                config = remaining_day.get_config()
                teams = config.get('teams', [])
                app.logger.info(f"Squadre nella giornata: {teams}")
                
                for team_idx, team in enumerate(teams, 1):
                    app.logger.info(f"\n--- Squadra {team_idx} ---")
                    for player_id in team:
                        # Ottieni l'ELO corrente (dall'ultima giornata o 1500)
                        current_elo = get_player_current_elo(player_id, tournament_id, remaining_day.id)
                        app.logger.info(f"\nGiocatore {player_id}:")
                        app.logger.info(f"- ELO corrente: {current_elo}")
                        
                        # Calcola il nuovo ELO
                        elo_change = avg_changes.get(player_id, 0)
                        new_elo = current_elo + elo_change
                        app.logger.info(f"- Variazione: {elo_change}")
                        app.logger.info(f"- Nuovo ELO: {new_elo}")
                        
                        # Registra la storia
                        history = PlayerEloHistory(
                            player_id=player_id,
                            tournament_id=tournament_id,
                            tournament_day_id=remaining_day.id,
                            old_elo=current_elo,
                            new_elo=new_elo,
                            elo_change=elo_change
                        )
                        db.session.add(history)
                        app.logger.info(f"- Storico registrato: {current_elo} -> {new_elo} (variazione: {elo_change})")
                        
                        # Aggiorna o crea il record ELO corrente
                        elo_rating = PlayerTournamentElo.query.filter_by(
                            player_id=player_id,
                            tournament_id=tournament_id
                        ).first()
                        
                        if not elo_rating:
                            elo_rating = PlayerTournamentElo(
                                player_id=player_id,
                                tournament_id=tournament_id,
                                elo_rating=new_elo
                            )
                            db.session.add(elo_rating)
                            app.logger.info(f"- Creato nuovo record ELO corrente: {new_elo}")
                        else:
                            old_rating = elo_rating.elo_rating
                            elo_rating.elo_rating = new_elo
                            app.logger.info(f"- Aggiornato record ELO corrente: {old_rating} -> {new_elo}")
                
                db.session.commit()
                app.logger.info(f"\n=== ELO AGGIORNATI PER GIORNATA {remaining_day.id} ===")
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Errore durante il ricalcolo ELO per giornata {remaining_day.id}: {str(e)}")
                raise
        
        app.logger.info("\n=== RICALCOLO ELO COMPLETATO CON SUCCESSO ===")
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Errore durante l'eliminazione degli ELO: {str(e)}")
        raise 