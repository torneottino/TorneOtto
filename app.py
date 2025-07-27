from flask import Flask, render_template, request
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
    
    # Configurazione del logging avanzata
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Handler per file di log principale
    file_handler = RotatingFileHandler(
        'logs/' + app.config['LOG_FILE'],
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    file_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
    file_handler.setLevel(logging.INFO)
    
    # Handler per errori
    error_handler = RotatingFileHandler(
        'logs/errors.log',
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    error_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
    error_handler.setLevel(logging.ERROR)
    
    # Handler per debug
    debug_handler = RotatingFileHandler(
        'logs/debug.log',
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    debug_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
    debug_handler.setLevel(logging.DEBUG)
    
    # Configurazione del logger principale
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(debug_handler)

    # Console handler con colorlog se disponibile
    try:
        from colorlog import ColoredFormatter
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = ColoredFormatter(
            "% (log_color)s%(levelname)-8s%(reset)s | %(blue)s%(message)s",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            })
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)
    except ImportError:
        pass
    app.logger.setLevel(logging.DEBUG)
    
    # Log dell'avvio dell'applicazione
    app.logger.info('=== TORNEOTTO STARTUP ===')
    app.logger.info(f'Configurazione: {app.config["ENV"] if "ENV" in app.config else "development"}')
    app.logger.info(f'Debug mode: {app.debug}')
    app.logger.info(f'Database URI: {app.config["SQLALCHEMY_DATABASE_URI"][:50]}...')
    
    # Aggiungo un handler per loggare le richieste HTTP (solo in modalità debug)
    if app.debug:
         from flask.logging import default_handler
         app.logger.addHandler(default_handler)
         app.logger.info('Handler HTTP requests abilitato per debug')
    
    # Creazione del contesto dell'applicazione
    with app.app_context():
        try:
            # Importazione dei modelli
            from models.player import Player, PlayerTournamentElo
            from models.tournament import Tournament
            from models.tournament_day import TournamentDay, EliminDay
            
            app.logger.info('Modelli importati con successo')
            
            # Creazione delle tabelle del database
            db.create_all()
            app.logger.info('Tabelle del database create/verificate')
            
        except Exception as e:
            app.logger.error(f'Errore durante l\'inizializzazione del database: {str(e)}')
            raise
    
    migrate = Migrate(app, db)
    app.logger.info('Sistema di migrazione inizializzato')
    
    # Import routes dopo i modelli
    try:
        from routes.players import players_bp
        from routes.tournaments import tournaments_bp
        from routes.sorteggio import sorteggio_bp
        app.logger.info('Blueprint importati con successo')

        # Register blueprints
        app.register_blueprint(players_bp)
        app.register_blueprint(tournaments_bp)
        app.register_blueprint(sorteggio_bp)
        app.logger.info('Blueprint registrati con successo')
        
    except Exception as e:
        app.logger.error(f'Errore durante l\'importazione dei blueprint: {str(e)}')
        raise

    # Definizione delle route principali
    @app.route('/')
    def home():
        app.logger.debug('Accesso alla home page')
        return render_template('home.html')

    @app.route('/classifiche')
    def classifiche():
        app.logger.debug('Accesso alla pagina classifiche')
        from models.tournament import Tournament
        from models.tournament_day import TournamentDay, EliminDay
        tornei = Tournament.query.order_by(Tournament.data_inizio.desc()).all()
        for torneo in tornei:
            days = []
            days += TournamentDay.query.filter_by(tournament_id=torneo.id).all()
            days += EliminDay.query.filter_by(tournament_id=torneo.id).all()
            all_dates = [d.data for d in days if d.data]
            all_dates = sorted(set(all_dates))
            if not all_dates:
                torneo.date_display = torneo.data_inizio.strftime('%d/%m/%Y')
            elif len(all_dates) == 1:
                torneo.date_display = all_dates[0].strftime('%d/%m/%Y')
            else:
                first = all_dates[0].strftime('%d/%m/%Y')
                last = all_dates[-1].strftime('%d/%m/%Y')
                if first == last:
                    torneo.date_display = first
                else:
                    torneo.date_display = f"{first} - {last}"
        app.logger.debug(f'Trovati {len(tornei)} tornei per la pagina classifiche')
        return render_template('classifiche.html', tornei=tornei)

    # Gestione errori globale
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f'Pagina non trovata: {request.url}')
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Errore interno del server: {str(error)}')
        db.session.rollback()
        return render_template('errors/500.html'), 500

    app.logger.info('=== TORNEOTTO INIZIALIZZATO CON SUCCESSO ===')
    return app

if __name__ == '__main__':
    app = create_app()
    app.logger.info(f'Avvio server su {app.config["HOST"]}:{app.config["PORT"]}')
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=True) 