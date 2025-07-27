from extensions import db
from datetime import datetime
import json
import math

class EliminationTournament(db.Model):
    """Modello per tornei ad eliminazione diretta e doppia eliminazione"""
    __tablename__ = 'elimination_tournaments'
    
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    tipo_eliminazione = db.Column(db.String(20), nullable=False)  # 'single' o 'double'
    num_partecipanti = db.Column(db.Integer, nullable=False)
    num_squadre = db.Column(db.Integer, nullable=False)  # numero effettivo di squadre (potenza di 2)
    metodo_accoppiamento = db.Column(db.String(20), nullable=False)  # 'random', 'seeded', 'manual'
    best_of_three = db.Column(db.Boolean, default=False)  # partite al meglio dei 3 set
    data_inizio = db.Column(db.Date, nullable=False)
    stato = db.Column(db.String(20), default="Setup")  # Setup, InProgress, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Configurazione JSON per flessibilità
    config_json = db.Column(db.Text, nullable=True)
    
    # Relazioni
    matches = db.relationship('EliminationMatch', backref='tournament', lazy=True, cascade='all, delete-orphan')
    teams = db.relationship('EliminationTeam', backref='tournament', lazy=True, cascade='all, delete-orphan')
    
    def set_config(self, config_dict):
        """Imposta la configurazione come JSON"""
        self.config_json = json.dumps(config_dict)
    
    def get_config(self):
        """Recupera la configurazione"""
        if self.config_json:
            return json.loads(self.config_json)
        return {}
    
    def get_num_rounds(self):
        """Calcola il numero di turni necessari"""
        if self.tipo_eliminazione == 'single':
            return int(math.log2(self.num_squadre))
        else:  # double elimination
            # Nel double elimination ci sono più turni
            return int(math.log2(self.num_squadre)) * 2 - 1
    
    def get_next_power_of_2(self, n):
        """Trova la prossima potenza di 2 maggiore o uguale a n"""
        return 2 ** math.ceil(math.log2(n))
    
    def initialize_bracket(self):
        """Inizializza il tabellone con le squadre"""
        # Assicurati che il numero di squadre sia una potenza di 2
        self.num_squadre = self.get_next_power_of_2(self.num_partecipanti)
        
        # Crea le squadre "bye" se necessario
        byes_needed = self.num_squadre - self.num_partecipanti
        
        config = self.get_config()
        config['byes_needed'] = byes_needed
        config['num_rounds'] = self.get_num_rounds()
        self.set_config(config)

class EliminationTeam(db.Model):
    """Modello per le squadre nel torneo ad eliminazione"""
    __tablename__ = 'elimination_teams'
    
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('elimination_tournaments.id'), nullable=False)
    team_name = db.Column(db.String(200), nullable=True)  # Nome libero della squadra
    posizione_seed = db.Column(db.Integer, nullable=True)  # posizione nel seeding (1-N)
    is_bye = db.Column(db.Boolean, default=False)  # squadra "bye"
    eliminata = db.Column(db.Boolean, default=False)
    sconfitte = db.Column(db.Integer, default=0)  # per doppia eliminazione
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Giocatori della squadra (JSON) - può contenere sia ID che nomi liberi
    players_json = db.Column(db.Text, nullable=False)
    
    def set_players(self, player_data):
        """Imposta i giocatori della squadra (può essere lista di ID o lista di nomi)"""
        self.players_json = json.dumps(player_data)
    
    def get_players(self):
        """Recupera i dati dei giocatori della squadra"""
        if self.players_json:
            return json.loads(self.players_json)
        return []
    
    def get_display_name(self):
        """Ritorna il nome da visualizzare della squadra"""
        if self.is_bye:
            return "BYE"
        if self.team_name:
            # Rimuovi il prefisso "TEAM_NAME:" se presente (bug nei dati)
            clean_name = self.team_name.replace("TEAM_NAME:", "").strip()
            return clean_name if clean_name else self.team_name
        # Fallback: crea un nome dai giocatori
        players = self.get_players()
        if players:
            if isinstance(players[0], dict):
                # Formato: [{"nome": "Mario", "cognome": "Rossi"}, ...]
                names = [f"{p.get('nome', '')} {p.get('cognome', '')}" for p in players]
                return " / ".join(names)
            elif isinstance(players[0], str):
                # Formato: ["Mario Rossi", "Luigi Verdi"]
                return " / ".join(players)
            else:
                # Formato: [1, 2] (ID giocatori - per compatibilità)
                return f"Squadra {self.posizione_seed}"
        return f"Squadra {self.posizione_seed}"

class EliminationMatch(db.Model):
    """Modello per le partite nel torneo ad eliminazione"""
    __tablename__ = 'elimination_matches'
    
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('elimination_tournaments.id'), nullable=False)
    turno = db.Column(db.Integer, nullable=False)  # numero del turno (1, 2, 3, ...)
    posizione_turno = db.Column(db.Integer, nullable=False)  # posizione nel turno (1, 2, 3, ...)
    bracket_type = db.Column(db.String(10), default='winner')  # 'winner' o 'loser' per doppia eliminazione
    
    # Squadre
    team1_id = db.Column(db.Integer, db.ForeignKey('elimination_teams.id'), nullable=True)
    team2_id = db.Column(db.Integer, db.ForeignKey('elimination_teams.id'), nullable=True)
    
    # Risultati
    team1_score = db.Column(db.Integer, nullable=True)
    team2_score = db.Column(db.Integer, nullable=True)
    winner_team_id = db.Column(db.Integer, db.ForeignKey('elimination_teams.id'), nullable=True)
    
    # Stato
    stato = db.Column(db.String(20), default="Pending")  # Pending, InProgress, Completed
    data_partita = db.Column(db.DateTime, nullable=True)
    
    # Best of 3 set
    set_scores_json = db.Column(db.Text, nullable=True)  # per memorizzare i punteggi dei set
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    team1 = db.relationship('EliminationTeam', foreign_keys=[team1_id], backref='matches_as_team1')
    team2 = db.relationship('EliminationTeam', foreign_keys=[team2_id], backref='matches_as_team2')
    winner_team = db.relationship('EliminationTeam', foreign_keys=[winner_team_id], backref='won_matches')
    
    def set_set_scores(self, set_scores):
        """Imposta i punteggi dei set (per best of 3)"""
        self.set_scores_json = json.dumps(set_scores)
    
    def get_set_scores(self):
        """Recupera i punteggi dei set"""
        if self.set_scores_json:
            return json.loads(self.set_scores_json)
        return []
    
    def get_formatted_score_display(self):
        """Ritorna il punteggio formattato per la visualizzazione"""
        if self.stato != 'Completed':
            return "-", "-"
            
        set_scores = self.get_set_scores()
        
        # Se non abbiamo i punteggi dei set, mostra i punteggi normali
        if not set_scores:
            return str(self.team1_score or 0), str(self.team2_score or 0)
        
        # Formatta i punteggi dei set come "6-4 / 6-7 / 6-4"
        team1_sets = []
        team2_sets = []
        
        for set_score in set_scores:
            if len(set_score) >= 2:
                team1_sets.append(str(set_score[0]))
                team2_sets.append(str(set_score[1]))
        
        team1_display = " / ".join(team1_sets) if team1_sets else str(self.team1_score or 0)
        team2_display = " / ".join(team2_sets) if team2_sets else str(self.team2_score or 0)
        
        return team1_display, team2_display
    
    def get_sets_scores_for_display(self):
        """Ritorna i punteggi dei set separati per la visualizzazione a quadrati"""
        if self.stato != 'Completed':
            return [], []
            
        set_scores = self.get_set_scores()
        
        # Se non abbiamo i punteggi dei set, ritorna punteggi singoli
        if not set_scores:
            return [str(self.team1_score or 0)], [str(self.team2_score or 0)]
        
        team1_sets = []
        team2_sets = []
        
        for set_score in set_scores:
            if len(set_score) >= 2:
                team1_sets.append(str(set_score[0]))
                team2_sets.append(str(set_score[1]))
        
        # Assicurati di avere sempre 3 posizioni per i set (anche vuote)
        while len(team1_sets) < 3:
            team1_sets.append("")
        while len(team2_sets) < 3:
            team2_sets.append("")
            
        return team1_sets[:3], team2_sets[:3]
    
    def is_walkover(self):
        """Controlla se è una partita con bye"""
        return (self.team1 and self.team1.is_bye) or (self.team2 and self.team2.is_bye)
    
    def get_advancing_team(self):
        """Ritorna la squadra che avanza (vincitrice o l'unica presente se bye)"""
        if self.is_walkover():
            return self.team1 if not self.team1.is_bye else self.team2
        return self.winner_team 