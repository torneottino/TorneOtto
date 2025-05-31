from flask import Flask, render_template
import os
import logging
from logging.handlers import RotatingFileHandler
from extensions import db
from flask_migrate import Migrate
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inizializzazione delle estensioni
    db.init_app(app)
    
    # Configurazione del logging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler(
        'logs/' + app.config['LOG_FILE'],
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    file_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info('Torneotto startup')
    
    # Aggiungo un handler per loggare le richieste HTTP (solo in modalità debug)
    if app.debug:
         from flask.logging import default_handler
         app.logger.addHandler(default_handler)
    
    # Creazione del contesto dell'applicazione
    with app.app_context():
        # Importazione dei modelli
        from models.player import Player, PlayerTournamentElo
        from models.tournament import Tournament
        from models.tournament_day import TournamentDay
        
        # Creazione delle tabelle del database
        db.create_all()
    
    migrate = Migrate(app, db)
    
    # Import routes dopo i modelli
    from routes.players import players_bp
    from routes.tournaments import tournaments_bp

    # Register blueprints
    app.register_blueprint(players_bp)
    app.register_blueprint(tournaments_bp)

    # Definizione delle route principali
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/classifiche')
    def classifiche():
        from models.tournament import Tournament
        tornei = Tournament.query.order_by(Tournament.data_inizio.desc()).all()
        return render_template('classifiche.html', tornei=tornei)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=True) 