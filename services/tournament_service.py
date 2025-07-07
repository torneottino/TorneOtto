from models.tournament_day import TournamentDay
from models.player import PlayerEloHistory
from extensions import db
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

def delete_tournament_day_simple(day_id):
    """
    Eliminazione di una giornata di torneo usando SQL diretto e commit forzati.
    IMPORTANTE: Ricalcola gli ELO dei giocatori dopo l'eliminazione!
    """
    try:
        # Prima recupera tournament_id per ricalcolo ELO
        tournament_id = db.session.execute(
            text("SELECT tournament_id FROM tournament_day WHERE id = :day_id"),
            {"day_id": day_id}
        ).scalar()
        
        if not tournament_id:
            logger.error(f"Giornata torneo con id {day_id} non trovata")
            raise ValueError(f"Giornata torneo con id {day_id} non trovata")
            
        # Recupera tutti i giocatori coinvolti nella giornata eliminata
        players_in_deleted_day = db.session.execute(
            text("""
                SELECT DISTINCT player_id 
                FROM player_elo_history 
                WHERE tournament_day_id = :day_id
            """),
            {"day_id": day_id}
        ).fetchall()
        
        affected_player_ids = [row[0] for row in players_in_deleted_day]
        logger.info(f"Giocatori coinvolti nella giornata eliminata: {affected_player_ids}")
            
        # Elimina i record ELO della giornata
        db.session.execute(
            text("DELETE FROM player_elo_history WHERE tournament_day_id = :day_id"),
            {"day_id": day_id}
        )
        db.session.commit()  # Commit immediato dopo eliminazione ELO
        logger.info(f"Eliminati record ELO per la giornata {day_id}")
        
        # Verifica che i record ELO siano stati eliminati
        elo_check = db.session.execute(
            text("SELECT COUNT(*) FROM player_elo_history WHERE tournament_day_id = :day_id"),
            {"day_id": day_id}
        ).scalar()
        
        if elo_check > 0:
            raise Exception(f"Record ELO ancora presenti dopo eliminazione: {elo_check}")
            
        # Elimina la giornata
        db.session.execute(
            text("DELETE FROM tournament_day WHERE id = :day_id"),
            {"day_id": day_id}
        )
        db.session.commit()  # Commit immediato dopo eliminazione giornata
        
        # Verifica finale
        final_check = db.session.execute(
            text("SELECT COUNT(*) FROM tournament_day WHERE id = :day_id"),
            {"day_id": day_id}
        ).scalar()
        
        if final_check > 0:
            raise Exception(f"Giornata {day_id} ancora presente dopo eliminazione!")
            
        logger.info(f"Giornata torneo {day_id} eliminata con successo")
        
        # CRUCIALE: Ricalcola gli ELO dei giocatori coinvolti
        if affected_player_ids:
            recalculate_players_elo(tournament_id, affected_player_ids)
            logger.info(f"Ricalcolati ELO per {len(affected_player_ids)} giocatori nel torneo {tournament_id}")
        
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore nell'eliminazione della giornata torneo {day_id}: {str(e)}")
        raise


def recalculate_players_elo(tournament_id, player_ids):
    """
    Ricalcola l'ELO attuale dei giocatori basandosi su tutte le giornate rimanenti
    """
    from models.player import PlayerTournamentElo, PlayerEloHistory
    
    logger.info(f"Ricalcolo ELO per giocatori {player_ids} nel torneo {tournament_id}")
    
    for player_id in player_ids:
        # Trova tutte le variazioni ELO rimanenti per questo giocatore in questo torneo
        remaining_elo_changes = db.session.execute(
            text("""
                SELECT elo_change 
                FROM player_elo_history 
                WHERE player_id = :player_id 
                AND tournament_id = :tournament_id 
                ORDER BY created_at ASC
            """),
            {"player_id": player_id, "tournament_id": tournament_id}
        ).fetchall()
        
        # Calcola l'ELO finale sommando tutte le variazioni a partire da 1500
        final_elo = 1500.0
        for change_row in remaining_elo_changes:
            final_elo += change_row[0]
        
        logger.info(f"Giocatore {player_id}: ELO ricalcolato = {final_elo}")
        
        # Aggiorna o crea il record PlayerTournamentElo
        db.session.execute(
            text("""
                INSERT INTO player_tournament_elo (player_id, tournament_id, elo_rating)
                VALUES (:player_id, :tournament_id, :elo_rating)
                ON CONFLICT (player_id, tournament_id) 
                DO UPDATE SET elo_rating = :elo_rating
            """),
            {
                "player_id": player_id,
                "tournament_id": tournament_id,
                "elo_rating": final_elo
            }
        )
        
        db.session.commit()
        logger.info(f"Aggiornato ELO giocatore {player_id} a {final_elo}")

def delete_tournament_day_sql(day_id):
    """
    Eliminazione di una giornata di torneo utilizzando SQL diretto.
    Approccio più veloce ma meno flessibile.
    
    Args:
        day_id (int): ID della giornata di torneo da eliminare
        
    Returns:
        bool: True se l'eliminazione è avvenuta con successo
        
    Raises:
        Exception: Per errori durante l'eliminazione
    """
    try:
        # Elimina prima la storia ELO
        db.session.execute(
            "DELETE FROM player_elo_history WHERE tournament_day_id = :day_id",
            {"day_id": day_id}
        )
        
        # Elimina la giornata del torneo
        db.session.execute(
            "DELETE FROM tournament_day WHERE id = :day_id",
            {"day_id": day_id}
        )
        
        db.session.commit()
        logger.info(f"Giornata torneo {day_id} eliminata con successo via SQL")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore nell'eliminazione SQL della giornata torneo {day_id}: {str(e)}")
        raise 