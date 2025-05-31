from extensions import db
from datetime import datetime

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    cognome = db.Column(db.String(50), nullable=False)
    telefono = db.Column(db.String(20))
    posizione = db.Column(db.String(20), nullable=False)  # Destra, Sinistra, Indifferente
    elo_standard = db.Column(db.Float, default=1500.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazione con i punteggi ELO nei vari tornei
    elo_ratings = db.relationship('PlayerTournamentElo', backref='player', lazy=True)
    elo_history = db.relationship('PlayerEloHistory', backref='player', lazy=True)

    def get_tournament_elo(self, tournament_id):
        """
        Ottiene l'ELO del giocatore per un torneo specifico, calcolato dalla storia ELO.
        """
        # Prendi l'ultimo record dalla storia ELO
        last_history = PlayerEloHistory.query.filter_by(
            player_id=self.id,
            tournament_id=tournament_id
        ).order_by(PlayerEloHistory.tournament_day_id.desc()).first()
        
        # Se esiste una storia, usa l'ultimo new_elo, altrimenti 1500
        return last_history.new_elo if last_history else 1500.00

    def get_elo_history(self, tournament_id, day_id=None):
        """
        Ottiene la storia dei punteggi ELO del giocatore per un torneo specifico
        Se viene specificato day_id, restituisce solo la storia fino a quella giornata
        """
        query = PlayerEloHistory.query.filter_by(
            player_id=self.id,
            tournament_id=tournament_id
        ).order_by(PlayerEloHistory.tournament_day_id.asc())
        
        if day_id:
            query = query.filter(PlayerEloHistory.tournament_day_id <= day_id)
            
        return query.all()

class PlayerTournamentElo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    elo_rating = db.Column(db.Float, default=1500.00)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('player_id', 'tournament_id', name='unique_player_tournament'),
    )

class PlayerEloHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    tournament_day_id = db.Column(db.Integer, db.ForeignKey('tournament_day.id'), nullable=False)
    old_elo = db.Column(db.Float, nullable=False)
    new_elo = db.Column(db.Float, nullable=False)
    elo_change = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_player_tournament_day', 'player_id', 'tournament_id', 'tournament_day_id'),
    ) 