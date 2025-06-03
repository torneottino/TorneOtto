from datetime import datetime, timedelta
from models.player import Player, PlayerTournamentElo, PlayerEloHistory
from models.tournament_day import TournamentDay
from extensions import db
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class EloMonitor:
    def __init__(self):
        self.last_check = datetime.utcnow()
        self.issues_history = []
    
    def check_elo_changes(self, hours=24):
        """
        Monitora i cambiamenti ELO nelle ultime ore.
        NON modifica il database, solo verifica.
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            issues = []
            
            # Controlla cambiamenti ELO recenti
            recent_changes = PlayerEloHistory.query.filter(
                PlayerEloHistory.created_at >= since
            ).all()
            
            # Raggruppa per giocatore
            player_changes = defaultdict(list)
            for change in recent_changes:
                player_changes[change.player_id].append(change)
            
            # Analizza i cambiamenti per ogni giocatore
            for player_id, changes in player_changes.items():
                player = Player.query.get(player_id)
                if not player:
                    continue
                
                # Ordina per data
                changes.sort(key=lambda x: x.created_at)
                
                # Controlla variazioni anomale
                for i in range(1, len(changes)):
                    prev_change = changes[i-1]
                    curr_change = changes[i]
                    
                    # Calcola la variazione percentuale
                    pct_change = abs(curr_change.elo_change / prev_change.old_elo * 100)
                    
                    if pct_change > 50:  # Variazione superiore al 50%
                        issues.append({
                            'type': 'LARGE_ELO_CHANGE',
                            'player_id': player_id,
                            'player_name': f"{player.nome} {player.cognome}",
                            'change_time': curr_change.created_at.isoformat(),
                            'old_elo': prev_change.old_elo,
                            'new_elo': curr_change.new_elo,
                            'change_pct': pct_change
                        })
            
            # Controlla partite senza risultati
            recent_days = TournamentDay.query.filter(
                TournamentDay.data >= since.date()
            ).all()
            
            for day in recent_days:
                config = day.get_config()
                matches = config.get('matches', [])
                results = config.get('results', {})
                
                for match in matches:
                    match_key = f"{match[0]}-{match[1]}"
                    if match_key not in results:
                        issues.append({
                            'type': 'MISSING_RESULT',
                            'tournament_day_id': day.id,
                            'date': day.data.isoformat(),
                            'match': match
                        })
            
            # Aggiorna la storia dei problemi
            self.issues_history.extend(issues)
            self.last_check = datetime.utcnow()
            
            return {
                'issues': issues,
                'total_issues': len(issues),
                'check_time': self.last_check.isoformat(),
                'period_hours': hours
            }
            
        except Exception as e:
            logger.error(f"Errore durante monitoraggio ELO: {str(e)}")
            return {
                'issues': [],
                'total_issues': 0,
                'check_time': self.last_check.isoformat(),
                'error': str(e)
            }
    
    def get_player_stats(self, player_id):
        """
        Ottiene statistiche dettagliate per un giocatore.
        NON modifica il database, solo verifica.
        """
        try:
            player = Player.query.get(player_id)
            if not player:
                return None
            
            # Recupera storia ELO
            history = PlayerEloHistory.query.filter_by(
                player_id=player_id
            ).order_by(PlayerEloHistory.created_at.desc()).all()
            
            if not history:
                return {
                    'player': f"{player.nome} {player.cognome}",
                    'current_elo': player.elo_standard,
                    'history': [],
                    'stats': {
                        'total_matches': 0,
                        'highest_elo': player.elo_standard,
                        'lowest_elo': player.elo_standard,
                        'avg_change': 0
                    }
                }
            
            # Calcola statistiche
            total_matches = len(history)
            highest_elo = max(h.old_elo for h in history)
            lowest_elo = min(h.old_elo for h in history)
            avg_change = sum(abs(h.elo_change) for h in history) / total_matches
            
            return {
                'player': f"{player.nome} {player.cognome}",
                'current_elo': player.elo_standard,
                'history': [{
                    'date': h.created_at.isoformat(),
                    'old_elo': h.old_elo,
                    'new_elo': h.new_elo,
                    'change': h.elo_change
                } for h in history],
                'stats': {
                    'total_matches': total_matches,
                    'highest_elo': highest_elo,
                    'lowest_elo': lowest_elo,
                    'avg_change': avg_change
                }
            }
            
        except Exception as e:
            logger.error(f"Errore durante recupero statistiche giocatore: {str(e)}")
            return None
    
    def get_tournament_stats(self, tournament_id):
        """
        Ottiene statistiche dettagliate per un torneo.
        NON modifica il database, solo verifica.
        """
        try:
            # Recupera tutte le giornate del torneo
            days = TournamentDay.query.filter_by(
                tournament_id=tournament_id
            ).order_by(TournamentDay.data).all()
            
            if not days:
                return None
            
            stats = {
                'total_days': len(days),
                'total_matches': 0,
                'completed_matches': 0,
                'player_stats': defaultdict(lambda: {
                    'matches_played': 0,
                    'matches_won': 0,
                    'elo_start': None,
                    'elo_end': None,
                    'elo_change': 0
                })
            }
            
            # Analizza ogni giornata
            for day in days:
                config = day.get_config()
                matches = config.get('matches', [])
                results = config.get('results', {})
                
                stats['total_matches'] += len(matches)
                stats['completed_matches'] += len(results)
                
                # Analizza ogni partita
                for match in matches:
                    match_key = f"{match[0]}-{match[1]}"
                    result = results.get(match_key)
                    
                    # Aggiorna statistiche giocatori
                    for player_id in match:
                        player_stats = stats['player_stats'][player_id]
                        player_stats['matches_played'] += 1
                        
                        if result:
                            # Determina il team vincente
                            score_a, score_b = map(int, result.split('-'))
                            winner_team = 1 if score_a > score_b else 2
                            
                            # Aggiorna vittorie
                            if (player_id in match[:2] and winner_team == 1) or \
                               (player_id in match[2:] and winner_team == 2):
                                player_stats['matches_won'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Errore durante recupero statistiche torneo: {str(e)}")
            return None 