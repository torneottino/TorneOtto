from models.tournament_day import TournamentDay
from models.player import PlayerEloHistory
from extensions import db
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

def delete_tournament_day_simple(day_id):
    """
    Eliminazione di una giornata di torneo usando SQL diretto e commit forzati.
    """
    try:
        # Verifica iniziale
        check = db.session.execute(
            text("SELECT COUNT(*) FROM tournament_day WHERE id = :day_id"),
            {"day_id": day_id}
        ).scalar()
        
        if check == 0:
            logger.error(f"Giornata torneo con id {day_id} non trovata")
            raise ValueError(f"Giornata torneo con id {day_id} non trovata")
            
        # Elimina i record ELO
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
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore nell'eliminazione della giornata torneo {day_id}: {str(e)}")
        raise

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