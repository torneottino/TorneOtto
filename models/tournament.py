from extensions import db
from datetime import datetime
import json

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo_torneo = db.Column(db.String(20), nullable=False)  # torneotto30, torneotto45, gironi, eliminazione
    circolo = db.Column(db.String(100), nullable=True)
    note = db.Column(db.Text, nullable=True)
    data_inizio = db.Column(db.Date, nullable=False)
    data_fine = db.Column(db.Date, nullable=False)
    stato = db.Column(db.String(20), default="Pianificato")  # Pianificato, In corso, Completato
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Campi aggiuntivi per le proprietà specifiche del torneo
    # Memorizzati come JSON per flessibilità
    config_json = db.Column(db.Text, nullable=True)
    
    # Relazione con i punteggi ELO
    elo_ratings = db.relationship('PlayerTournamentElo', backref='tournament', lazy=True, cascade='all, delete-orphan')
    
    # Relazione con le giornate del torneo
    tournament_days = db.relationship('TournamentDay', backref='tournament', lazy=True, cascade='all, delete-orphan')
    
    # Relazione con le giornate di eliminazione
    elimin_days = db.relationship('EliminDay', backref='tournament', lazy=True, cascade='all, delete-orphan')
    
    # Relazione con lo storico ELO
    elo_history = db.relationship('PlayerEloHistory', backref='tournament', lazy=True, cascade='all, delete-orphan')
    
    def set_config(self, config_dict):
        """Impostare la configurazione specifica per il tipo di torneo come JSON"""
        self.config_json = json.dumps(config_dict)
    
    def get_config(self):
        """Recuperare la configurazione specifica per il tipo di torneo"""
        if self.config_json:
            return json.loads(self.config_json)
        return {}
    
    def get_torneotto30_config(self):
        """Recupera la configurazione specifica per TorneOtto 30"""
        config = self.get_config()
        return {
            'num_squadre': config.get('num_squadre', 8),
            'tempo_partita': config.get('tempo_partita', 30)
        }
    
    def get_torneotto45_config(self):
        """Recupera la configurazione specifica per TorneOtto 45"""
        config = self.get_config()
        return {
            'num_squadre': config.get('num_squadre', 8),
            'tempo_partita': config.get('tempo_partita', 45),
            'finali': config.get('finali', 1)
        }
    
    def get_gironi_config(self):
        """Recupera la configurazione specifica per tornei a gironi"""
        config = self.get_config()
        return {
            'num_gironi': config.get('num_gironi', 4),
            'squadre_per_girone': config.get('squadre_per_girone', 4)
        }
    
    def get_eliminazione_config(self):
        """Recupera la configurazione specifica per tornei a eliminazione diretta"""
        config = self.get_config()
        return {
            'num_partecipanti': config.get('num_partecipanti', 16),
            'teste_di_serie': config.get('teste_di_serie', 4),
            'consolazione': config.get('consolazione', 0)
        } 