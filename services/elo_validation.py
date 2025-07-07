from datetime import datetime
from models.player import Player, PlayerTournamentElo, PlayerEloHistory
from models.tournament_day import TournamentDay
from extensions import db
import logging

logger = logging.getLogger(__name__)

class EloValidationError(Exception):
    """Eccezione personalizzata per errori di validazione ELO"""
    pass

def validate_match_creation(player1_id, player2_id, player3_id, player4_id, winner_team, date):
    """
    Validazione completa prima di creare una partita.
    NON modifica il database, solo verifica.
    """
    errors = []
    
    try:
        # Controllo giocatori unici
        players = [player1_id, player2_id, player3_id, player4_id]
        if len(set(players)) != 4:
            errors.append("Tutti i 4 giocatori devono essere diversi")
        
        # Controllo esistenza giocatori
        for player_id in players:
            if not Player.query.get(player_id):
                errors.append(f"Giocatore {player_id} non esiste")
        
        # Controllo winner_team
        if winner_team not in [1, 2]:
            errors.append("winner_team deve essere 1 o 2")
        
        # Controllo data
        if not isinstance(date, (datetime.date, datetime.datetime)):
            errors.append("Data non valida")
        
        # Controllo data nel futuro
        if date > datetime.date.today():
            errors.append("Non è possibile inserire partite future")
        
        if errors:
            logger.warning(f"Validazione partita fallita: {errors}")
            return False, errors
            
        return True, []
        
    except Exception as e:
        logger.error(f"Errore durante validazione partita: {str(e)}")
        return False, [f"Errore di validazione: {str(e)}"]

def verify_elo_integrity():
    """
    Verifica la coerenza degli ELO nel database.
    NON modifica il database, solo verifica.
    """
    issues = []
    
    try:
        # 1. Verifica che current_elo corrisponda all'ultimo calcolo
        for player in Player.query.all():
            # Recupera l'ultimo ELO dalla storia
            last_history = PlayerEloHistory.query.filter_by(
                player_id=player.id
            ).order_by(PlayerEloHistory.created_at.desc()).first()
            
            if last_history and abs(player.elo_standard - last_history.new_elo) > 0.01:
                issues.append({
                    'type': 'ELO_MISMATCH',
                    'player_id': player.id,
                    'player_name': f"{player.nome} {player.cognome}",
                    'stored_elo': player.elo_standard,
                    'last_history_elo': last_history.new_elo,
                    'difference': player.elo_standard - last_history.new_elo
                })
        
        # 2. Verifica che elo_history sia completo per ogni torneo
        for day in TournamentDay.query.all():
            config = day.get_config()
            matches = config.get('matches', [])
            results = config.get('results', {})
            
            for match in matches:
                match_key = f"{match[0]}-{match[1]}"
                if match_key not in results:
                    issues.append({
                        'type': 'MISSING_RESULT',
                        'tournament_day_id': day.id,
                        'match': match
                    })
        
        return issues
        
    except Exception as e:
        logger.error(f"Errore durante verifica integrità ELO: {str(e)}")
        return [{'type': 'VERIFICATION_ERROR', 'error': str(e)}]

def create_elo_backup():
    """
    Crea un backup dello stato attuale degli ELO.
    NON modifica il database, solo legge.
    """
    try:
        return {
            'players': {p.id: p.elo_standard for p in Player.query.all()},
            'tournament_elos': {
                (pte.player_id, pte.tournament_id): pte.elo_rating 
                for pte in PlayerTournamentElo.query.all()
            },
            'timestamp': datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Errore durante creazione backup ELO: {str(e)}")
        return None

def validate_ranking():
    """
    Verifica la coerenza della classifica.
    NON modifica il database, solo verifica.
    """
    issues = []
    ranking_data = []
    
    try:
        for player in Player.query.all():
            # Recupera l'ultimo ELO dalla storia
            last_history = PlayerEloHistory.query.filter_by(
                player_id=player.id
            ).order_by(PlayerEloHistory.created_at.desc()).first()
            
            calculated_elo = last_history.new_elo if last_history else 1500.0
            elo_diff = abs(player.elo_standard - calculated_elo)
            
            ranking_entry = {
                'player_id': player.id,
                'name': f"{player.nome} {player.cognome}",
                'current_elo': player.elo_standard,
                'calculated_elo': calculated_elo,
                'is_consistent': elo_diff < 0.01
            }
            
            if not ranking_entry['is_consistent']:
                issues.append({
                    'player': f"{player.nome} {player.cognome}",
                    'stored_elo': player.elo_standard,
                    'calculated_elo': calculated_elo,
                    'difference': elo_diff
                })
            
            ranking_data.append(ranking_entry)
        
        return {
            'ranking': sorted(ranking_data, key=lambda x: (x['is_consistent'], x['current_elo']), reverse=True),
            'issues': issues
        }
        
    except Exception as e:
        logger.error(f"Errore durante validazione classifica: {str(e)}")
        return {'ranking': [], 'issues': [{'type': 'VALIDATION_ERROR', 'error': str(e)}]}

def validate_tournament_day(day_id):
    """
    Verifica la coerenza di una giornata di torneo.
    NON modifica il database, solo verifica.
    """
    issues = []
    
    try:
        day = TournamentDay.query.get(day_id)
        if not day:
            return [{'type': 'DAY_NOT_FOUND', 'day_id': day_id}]
        
        config = day.get_config()
        matches = config.get('matches', [])
        results = config.get('results', {})
        
        # Verifica che ogni partita abbia un risultato
        for match in matches:
            match_key = f"{match[0]}-{match[1]}"
            if match_key not in results:
                issues.append({
                    'type': 'MISSING_RESULT',
                    'match': match
                })
        
        # Verifica che i risultati siano validi
        for match_key, result in results.items():
            try:
                score_a, score_b = map(int, result.split('-'))
                if score_a < 0 or score_b < 0:
                    issues.append({
                        'type': 'INVALID_SCORE',
                        'match': match_key,
                        'result': result
                    })
            except:
                issues.append({
                    'type': 'INVALID_RESULT_FORMAT',
                    'match': match_key,
                    'result': result
                })
        
        return issues
        
    except Exception as e:
        logger.error(f"Errore durante validazione giornata: {str(e)}")
        return [{'type': 'VALIDATION_ERROR', 'error': str(e)}] 