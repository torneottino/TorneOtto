from models.tournament_day import TorneOtto30Day, TorneOtto45Day
from models.player import Player, PlayerTournamentElo
from models.tournament import Tournament
from extensions import db

# SOLUZIONE 1: Controllo se il torneo ha già giornate giocate

def get_player_tournament_elo(player_id, tournament_id):
    """
    Recupera l'ELO di un giocatore per un torneo specifico
    Se il torneo non ha ancora giornate, TUTTI partono da 1500
    """
    
    # CONTROLLO CRUCIALE: Il torneo ha già giornate giocate?
    has_played_games = (TorneOtto30Day.query.filter_by(tournament_id=tournament_id).count() > 0 or 
                       TorneOtto45Day.query.filter_by(tournament_id=tournament_id).count() > 0)
    
    if not has_played_games:
        # TORNEO NUOVO: Tutti partono da 1500 indipendentemente dalla history
        return 1500.0
    
    # TORNEO CON GIORNATE: Recupera ELO specifico del torneo
    tournament_elo = PlayerTournamentElo.query.filter_by(
        player_id=player_id,
        tournament_id=tournament_id
    ).first()
    
    # Se il giocatore non ha mai giocato in QUESTO torneo, parte da 1500
    return tournament_elo.elo_rating if tournament_elo else 1500.0


# SOLUZIONE 2: Modifica la funzione di sorteggio

def prepare_players_for_draw(tournament_id):
    """
    Prepara la lista giocatori con ELO corretto per il sorteggio
    """
    players = Player.query.all()  # O filtro per torneo
    
    # CONTROLLO: Il torneo ha già partite giocate?
    tournament_has_matches = GameDay.query.filter_by(tournament_id=tournament_id).count() > 0
    
    for player in players:
        if not tournament_has_matches:
            # TORNEO VERGINE: Tutti a 1500, ignora qualsiasi ELO esistente
            player.tournament_elo = 1500.0
        else:
            # TORNEO IN CORSO: Usa ELO specifico del torneo
            tournament_elo = PlayerTournamentElo.query.filter_by(
                player_id=player.id,
                tournament_id=tournament_id
            ).first()
            
            player.tournament_elo = tournament_elo.elo_rating if tournament_elo else 1500.0
    
    return players


# SOLUZIONE 3: Funzione completa per il sorteggio

def make_tournament_draw(tournament_id):
    """
    Effettua sorteggio con gestione corretta ELO torneo
    """
    
    # 1. Verifica stato torneo
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        raise ValueError("Torneo non trovato")
    
    # 2. CONTROLLO CRUCIALE: Torneo ha già giornate?
    existing_gamedays = GameDay.query.filter_by(tournament_id=tournament_id).count()
    is_fresh_tournament = existing_gamedays == 0
    
    # 3. Recupera giocatori
    players = Player.query.filter_by(tournament_id=tournament_id).all()
    
    # 4. Assegna ELO corretto
    for player in players:
        if is_fresh_tournament:
            # TORNEO NUOVO: Ignora tutto, tutti a 1500
            player.tournament_elo = 1500.0
            print(f"Giocatore {player.name}: ELO 1500 (torneo nuovo)")
        else:
            # TORNEO IN CORSO: Cerca ELO specifico di questo torneo
            player_elo = PlayerTournamentElo.query.filter_by(
                player_id=player.id,
                tournament_id=tournament_id
            ).first()
            
            if player_elo:
                player.tournament_elo = player_elo.elo_rating
                print(f"Giocatore {player.name}: ELO {player_elo.elo_rating} (da torneo)")
            else:
                # Nuovo giocatore in torneo esistente
                player.tournament_elo = 1500.0
                print(f"Giocatore {player.name}: ELO 1500 (nuovo nel torneo)")
    
    # 5. Procedi con sorteggio usando player.tournament_elo
    return create_balanced_matches(players)


# SOLUZIONE 4: Controllo per reset torneo

def reset_tournament_if_needed(tournament_id):
    """
    Se un torneo non ha giornate, assicurati che tutti gli ELO siano a 1500
    """
    
    has_gamedays = GameDay.query.filter_by(tournament_id=tournament_id).count() > 0
    
    if not has_gamedays:
        # Torneo senza giornate: resetta tutti gli ELO a 1500
        PlayerTournamentElo.query.filter_by(tournament_id=tournament_id).delete()
        
        # Oppure aggiorna tutti a 1500
        existing_elos = PlayerTournamentElo.query.filter_by(tournament_id=tournament_id).all()
        for elo_record in existing_elos:
            elo_record.elo_rating = 1500.0
        
        db.session.commit()
        print(f"Reset ELO torneo {tournament_id}: tutti i giocatori a 1500")


# SOLUZIONE 5: Versione robusta con logging

def get_player_elo_with_validation(player_id, tournament_id):
    """
    Versione robusta con logging per debug
    """
    
    # Controlla se torneo ha partite giocate
    gamedays_count = GameDay.query.filter_by(tournament_id=tournament_id).count()
    matches_count = Match.query.join(GameDay).filter(GameDay.tournament_id == tournament_id).count()
    
    print(f"DEBUG: Torneo {tournament_id} - Giornate: {gamedays_count}, Partite: {matches_count}")
    
    if gamedays_count == 0:
        print(f"DEBUG: Giocatore {player_id} -> ELO 1500 (torneo senza giornate)")
        return 1500.0
    
    # Cerca ELO specifico del torneo
    tournament_elo = PlayerTournamentElo.query.filter_by(
        player_id=player_id,
        tournament_id=tournament_id
    ).first()
    
    if tournament_elo:
        print(f"DEBUG: Giocatore {player_id} -> ELO {tournament_elo.elo_rating} (da DB torneo)")
        return tournament_elo.elo_rating
    else:
        print(f"DEBUG: Giocatore {player_id} -> ELO 1500 (nuovo in torneo esistente)")
        return 1500.0


# SOLUZIONE 6: Integrazione nel sorteggio esistente

def fixed_tournament_draw(tournament_id):
    """
    Modifica minima al codice esistente
    """
    
    # AGGIUNGI QUESTO CONTROLLO ALL'INIZIO
    tournament_has_played_games = GameDay.query.filter_by(tournament_id=tournament_id).count() > 0
    
    players = Player.query.filter_by(tournament_id=tournament_id).all()
    
    for player in players:
        if not tournament_has_played_games:
            # TORNEO NUOVO: Forza 1500 per tutti
            player.tournament_elo = 1500.0
        else:
            # CODICE ORIGINALE (ma solo se torneo ha già giornate)
            tournament_elo = PlayerTournamentElo.query.filter_by(
                player_id=player.id,
                tournament_id=tournament_id
            ).first()
            player.tournament_elo = tournament_elo.elo_rating if tournament_elo else 1500.0
    
    # Procedi con sorteggio...
    return create_matches(players)


# SOLUZIONE 7: Funzione di verifica

def verify_tournament_elo_integrity(tournament_id):
    """
    Verifica che gli ELO del torneo siano corretti
    """
    
    gamedays = GameDay.query.filter_by(tournament_id=tournament_id).count()
    players_with_elo = PlayerTournamentElo.query.filter_by(tournament_id=tournament_id).count()
    
    print(f"Torneo {tournament_id}:")
    print(f"  - Giornate giocate: {gamedays}")
    print(f"  - Giocatori con ELO: {players_with_elo}")
    
    if gamedays == 0 and players_with_elo > 0:
        print("  ⚠ PROBLEMA: Torneo senza giornate ma con ELO salvati")
        print("  💡 SOLUZIONE: Tutti dovrebbero essere a 1500")
        
        # Auto-fix
        PlayerTournamentElo.query.filter_by(tournament_id=tournament_id).update(
            {'elo_rating': 1500.0}
        )
        db.session.commit()
        print("  ✅ RISOLTO: Tutti gli ELO resettati a 1500")
    
    elif gamedays == 0:
        print("  ✅ OK: Torneo nuovo, tutti partiranno da 1500")
    
    else:
        print("  ✅ OK: Torneo in corso, ELO calcolati dalle partite")