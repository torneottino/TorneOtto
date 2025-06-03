import json
from datetime import datetime
import os
from models.player import Player, PlayerTournamentElo, PlayerEloHistory
from extensions import db
import logging

logger = logging.getLogger(__name__)

class EloBackupManager:
    def __init__(self, backup_dir='backups/elo'):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self, description=""):
        """
        Crea un backup completo dello stato ELO.
        NON modifica il database, solo legge.
        """
        try:
            backup_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'description': description,
                'players': [],
                'tournament_elos': [],
                'elo_history': []
            }
            
            # Backup giocatori
            for player in Player.query.all():
                backup_data['players'].append({
                    'id': player.id,
                    'nome': player.nome,
                    'cognome': player.cognome,
                    'elo_standard': player.elo_standard
                })
            
            # Backup ELO tornei
            for pte in PlayerTournamentElo.query.all():
                backup_data['tournament_elos'].append({
                    'player_id': pte.player_id,
                    'tournament_id': pte.tournament_id,
                    'elo_rating': pte.elo_rating
                })
            
            # Backup storia ELO
            for history in PlayerEloHistory.query.all():
                backup_data['elo_history'].append({
                    'player_id': history.player_id,
                    'old_elo': history.old_elo,
                    'new_elo': history.new_elo,
                    'elo_change': history.elo_change,
                    'created_at': history.created_at.isoformat()
                })
            
            # Salva il backup
            filename = f"elo_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.backup_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Backup ELO creato: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Errore durante creazione backup: {str(e)}")
            return None
    
    def list_backups(self):
        """
        Lista tutti i backup disponibili.
        """
        try:
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.backup_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        backups.append({
                            'filename': filename,
                            'timestamp': data['timestamp'],
                            'description': data['description'],
                            'players_count': len(data['players']),
                            'tournament_elos_count': len(data['tournament_elos']),
                            'history_count': len(data['elo_history'])
                        })
            
            return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Errore durante lettura lista backup: {str(e)}")
            return []
    
    def verify_backup(self, backup_file):
        """
        Verifica la validità di un backup.
        NON modifica il database, solo verifica.
        """
        try:
            filepath = os.path.join(self.backup_dir, backup_file)
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            issues = []
            
            # Verifica struttura
            required_keys = ['timestamp', 'players', 'tournament_elos', 'elo_history']
            for key in required_keys:
                if key not in data:
                    issues.append(f"Chiave mancante: {key}")
            
            # Verifica dati giocatori
            for player in data['players']:
                required_player_keys = ['id', 'nome', 'cognome', 'elo_standard']
                for key in required_player_keys:
                    if key not in player:
                        issues.append(f"Chiave giocatore mancante: {key}")
            
            # Verifica ELO tornei
            for pte in data['tournament_elos']:
                required_pte_keys = ['player_id', 'tournament_id', 'elo_rating']
                for key in required_pte_keys:
                    if key not in pte:
                        issues.append(f"Chiave ELO torneo mancante: {key}")
            
            # Verifica storia ELO
            for history in data['elo_history']:
                required_history_keys = ['player_id', 'old_elo', 'new_elo', 'elo_change', 'created_at']
                for key in required_history_keys:
                    if key not in history:
                        issues.append(f"Chiave storia ELO mancante: {key}")
            
            return {
                'is_valid': len(issues) == 0,
                'issues': issues,
                'backup_info': {
                    'timestamp': data['timestamp'],
                    'description': data.get('description', ''),
                    'players_count': len(data['players']),
                    'tournament_elos_count': len(data['tournament_elos']),
                    'history_count': len(data['elo_history'])
                }
            }
            
        except Exception as e:
            logger.error(f"Errore durante verifica backup: {str(e)}")
            return {
                'is_valid': False,
                'issues': [f"Errore durante verifica: {str(e)}"],
                'backup_info': None
            } 