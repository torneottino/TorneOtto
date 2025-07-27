from extensions import db
from datetime import datetime
import json

class TournamentDay(db.Model):
    __tablename__ = 'tournament_day'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    stato = db.Column(db.String(100))  # Modificato da String(20) a String(100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Dati specifici della giornata come JSON
    config_json = db.Column(db.Text, nullable=True)
    
    # Tipo di discriminatore per il tipo di giornata
    tipo_giornata = db.Column(db.String(100), nullable=False)  # Modificato da String(20) a String(100)
    
    __mapper_args__ = {
        'polymorphic_on': tipo_giornata,
        'polymorphic_identity': 'base'
    }
    
    def __init__(self, **kwargs):
        super(TournamentDay, self).__init__(**kwargs)
        if 'id' in kwargs:
            del kwargs['id']  # Rimuovi l'ID se fornito esplicitamente
    
    def set_config(self, config_dict):
        """Impostare la configurazione specifica come JSON"""
        self.config_json = json.dumps(config_dict)
    
    def get_config(self):
        """Recuperare la configurazione specifica"""
        if self.config_json:
            return json.loads(self.config_json)
        return {}

class EliminDay(db.Model):
    __tablename__ = 'elimin_days'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    stato = db.Column(db.String(100), default="Pianificata")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TorneOtto30Day(TournamentDay):
    __mapper_args__ = {
        'polymorphic_identity': 'torneotto30'
    }
    
    def get_players(self):
        """Restituisce gli ID dei giocatori per questa giornata"""
        config = self.get_config()
        return config.get('players', [])
    
    def get_pairs(self):
        """Restituisce le coppie di giocatori per questa giornata"""
        config = self.get_config()
        return config.get('pairs', [])
    
    def get_matches(self):
        """Restituisce le partite per questa giornata"""
        config = self.get_config()
        return config.get('matches', [])
    
    def get_results(self):
        """Restituisce i risultati delle partite per questa giornata"""
        config = self.get_config()
        return config.get('results', {})
    
    def set_players(self, players):
        """Imposta gli ID dei giocatori per questa giornata"""
        config = self.get_config()
        config['players'] = players
        self.set_config(config)
    
    def set_pairs(self, pairs):
        """Imposta le coppie di giocatori per questa giornata"""
        config = self.get_config()
        config['pairs'] = pairs
        self.set_config(config)
    
    def set_matches(self, matches):
        """Imposta le partite per questa giornata"""
        config = self.get_config()
        config['matches'] = matches
        self.set_config(config)
    
    def set_results(self, results):
        """Imposta i risultati delle partite per questa giornata"""
        config = self.get_config()
        config['results'] = results
        self.set_config(config)

class TorneOtto45Day(TournamentDay):
    __mapper_args__ = {
        'polymorphic_identity': 'torneotto45'
    }
    
    def get_players(self):
        """Restituisce gli ID dei giocatori per questa giornata"""
        config = self.get_config()
        return config.get('players', [])
    
    def get_semifinals(self):
        """Restituisce le semifinali per questa giornata"""
        config = self.get_config()
        return config.get('semifinali', [])
    
    def get_finals(self):
        """Restituisce le finali per questa giornata"""
        config = self.get_config()
        return config.get('finali', {})
    
    def get_ranking(self):
        """Restituisce la classifica finale della giornata"""
        config = self.get_config()
        return config.get('classifica', [])
    
    def set_players(self, players):
        """Imposta gli ID dei giocatori per questa giornata"""
        config = self.get_config()
        config['players'] = players
        self.set_config(config)
    
    def set_semifinals(self, semifinals):
        """Imposta le semifinali per questa giornata"""
        config = self.get_config()
        config['semifinali'] = semifinals
        self.set_config(config)
    
    def set_finals(self, finals):
        """Imposta le finali per questa giornata"""
        config = self.get_config()
        config['finali'] = finals
        self.set_config(config)
    
    def set_ranking(self, ranking):
        """Imposta la classifica finale della giornata"""
        config = self.get_config()
        config['classifica'] = ranking
        self.set_config(config)

class GironiDay(TournamentDay):
    __mapper_args__ = {
        'polymorphic_identity': 'gironi'
    }
    
    def get_players(self):
        """Restituisce gli ID dei giocatori per questa giornata"""
        config = self.get_config()
        return config.get('players', [])
    
    def get_gironi(self):
        """Restituisce i gironi per questa giornata"""
        config = self.get_config()
        return config.get('gironi', [])
    
    def get_matches(self):
        """Restituisce le partite per questa giornata"""
        config = self.get_config()
        return config.get('matches', [])
    
    def get_results(self):
        """Restituisce i risultati delle partite per questa giornata"""
        config = self.get_config()
        return config.get('results', {})
    
    def get_ranking(self):
        """Restituisce la classifica finale della giornata"""
        config = self.get_config()
        return config.get('classifica', [])
    
    def get_semifinals(self):
        """Restituisce le semifinali per questa giornata"""
        config = self.get_config()
        return config.get('semifinali', [])
    
    def get_finals(self):
        """Restituisce le finali per questa giornata"""
        config = self.get_config()
        return config.get('finali', {})
    
    def get_group_standings(self):
        """Restituisce le classifiche dei gironi"""
        config = self.get_config()
        return config.get('classifiche_gironi', [])
    
    def set_players(self, players):
        """Imposta gli ID dei giocatori per questa giornata"""
        config = self.get_config()
        config['players'] = players
        self.set_config(config)
    
    def set_gironi(self, gironi):
        """Imposta i gironi per questa giornata"""
        config = self.get_config()
        config['gironi'] = gironi
        self.set_config(config)
    
    def set_matches(self, matches):
        """Imposta le partite per questa giornata"""
        config = self.get_config()
        config['matches'] = matches
        self.set_config(config)
    
    def set_results(self, results):
        """Imposta i risultati delle partite per questa giornata"""
        config = self.get_config()
        config['results'] = results
        self.set_config(config)
    
    def set_ranking(self, ranking):
        """Imposta la classifica finale della giornata"""
        config = self.get_config()
        config['classifica'] = ranking
        self.set_config(config)
    
    def set_semifinals(self, semifinals):
        """Imposta le semifinali per questa giornata"""
        config = self.get_config()
        config['semifinali'] = semifinals
        self.set_config(config)
    
    def set_finals(self, finals):
        """Imposta le finali per questa giornata"""
        config = self.get_config()
        config['finali'] = finals
        self.set_config(config)
    
    def set_group_standings(self, standings):
        """Imposta le classifiche dei gironi"""
        config = self.get_config()
        config['classifiche_gironi'] = standings
        self.set_config(config)

class AmericanaDay(TournamentDay):
    """Classe per gestire le giornate di torneo all'americana"""
    __mapper_args__ = {
        'polymorphic_identity': 'americana'
    }
    
    def get_players(self):
        """Restituisce gli ID dei giocatori per questa giornata"""
        config = self.get_config()
        return config.get('players', [])
    
    def get_teams(self):
        """Restituisce le coppie/squadre per questa giornata"""
        config = self.get_config()
        return config.get('teams', [])
    
    def get_matches(self):
        """Restituisce le partite per questa giornata"""
        config = self.get_config()
        return config.get('matches', [])
    
    def get_results(self):
        """Restituisce i risultati delle partite per questa giornata"""
        config = self.get_config()
        return config.get('results', {})
        
    def get_ranking(self):
        """Restituisce la classifica del torneo"""
        config = self.get_config()
        return config.get('ranking', [])
        
    def get_statistics(self):
        """Restituisce le statistiche del torneo"""
        config = self.get_config()
        return config.get('statistics', {})
        
    def get_rounds(self):
        """Restituisce i turni del torneo"""
        config = self.get_config()
        return config.get('rounds', [])
        
    def get_courts(self):
        """Restituisce i campi disponibili"""
        config = self.get_config()
        return config.get('courts', [])
    
    def set_players(self, players):
        """Imposta gli ID dei giocatori per questa giornata"""
        config = self.get_config()
        config['players'] = players
        self.set_config(config)
    
    def set_teams(self, teams):
        """Imposta le coppie/squadre per questa giornata"""
        config = self.get_config()
        config['teams'] = teams
        self.set_config(config)
    
    def set_matches(self, matches):
        """Imposta le partite per questa giornata"""
        config = self.get_config()
        config['matches'] = matches
        self.set_config(config)
    
    def set_results(self, results):
        """Imposta i risultati delle partite per questa giornata"""
        config = self.get_config()
        config['results'] = results
        self.set_config(config)
        
    def set_ranking(self, ranking):
        """Imposta la classifica del torneo"""
        config = self.get_config()
        config['ranking'] = ranking
        self.set_config(config)
        
    def set_statistics(self, statistics):
        """Imposta le statistiche del torneo"""
        config = self.get_config()
        config['statistics'] = statistics
        self.set_config(config)
        
    def set_rounds(self, rounds):
        """Imposta i turni del torneo"""
        config = self.get_config()
        config['rounds'] = rounds
        self.set_config(config)
        
    def set_courts(self, courts):
        """Imposta i campi disponibili"""
        config = self.get_config()
        config['courts'] = courts
        self.set_config(config) 