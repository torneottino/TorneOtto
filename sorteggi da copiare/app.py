from flask import Flask, render_template, request, jsonify
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
            from models.elimin_day import EliminationTournament, EliminationTeam, EliminationMatch
            
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
        app.logger.info('Blueprint importati con successo')

        # Register blueprints
        app.register_blueprint(players_bp)
        app.register_blueprint(tournaments_bp)
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
        # Escludi i tornei ad eliminazione dalle classifiche
        tornei = Tournament.query.filter(Tournament.tipo_torneo != 'eliminazione').order_by(Tournament.data_inizio.desc()).all()
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

    @app.route('/sorteggio-coppie')
    def sorteggio_coppie():
        app.logger.debug('Accesso alla pagina sorteggio coppie')
        return render_template('sorteggio_coppie.html')

    @app.route('/sorteggio-casuale')
    def sorteggio_casuale():
        app.logger.debug('Accesso alla pagina sorteggio casuale')
        return render_template('sorteggio_casuale.html')

    @app.route('/sorteggio-teste-serie')
    def sorteggio_teste_serie():
        app.logger.debug('Accesso alla pagina sorteggio teste di serie')
        return render_template('sorteggio_teste_serie.html')

    @app.route('/sorteggio-casuale-database')
    def sorteggio_casuale_database():
        app.logger.debug('Accesso alla pagina sorteggio casuale database')
        from models.player import Player
        players = Player.query.order_by(Player.nome).all()
        
        # Process players to separate surname and name
        for player in players:
            name_parts = player.nome.strip().split(' ', 1)
            if len(name_parts) > 1:
                player.surname = name_parts[1]  # Seconda parte = cognome
                player.first_name = name_parts[0]  # Prima parte = nome
            else:
                player.surname = player.nome
                player.first_name = ""
        
        return render_template('sorteggio_casuale_database.html', players=players)

    @app.route('/sorteggio-risultati')
    def sorteggio_risultati():
        app.logger.debug('Accesso alla pagina risultati sorteggio')
        return render_template('sorteggio_risultati.html')

    @app.route('/sorteggio-teste-database')
    def sorteggio_teste_database():
        app.logger.debug('Accesso alla pagina sorteggio teste di serie database')
        from models.player import Player
        players = Player.query.order_by(Player.cognome, Player.nome).all()
        return render_template('sorteggio_teste_serie_database.html', players=players)

    @app.route('/sorteggio-casuale-manuale')
    def sorteggio_casuale_manuale():
        app.logger.debug('Accesso alla pagina sorteggio casuale manuale')
        return render_template('sorteggio_casuale_manuale.html')

    @app.route('/sorteggio-teste-manuale')
    def sorteggio_teste_manuale():
        app.logger.debug('Accesso alla pagina sorteggio teste di serie manuale')
        return render_template('sorteggio_teste_serie_manuale.html')

    @app.route('/api/players')
    def api_players():
        app.logger.debug('API richiesta lista giocatori')
        from models.player import Player
        players = Player.query.order_by(Player.nome).all()
        return jsonify([
            {'id': p.id, 'nome': p.nome, 'cognome': getattr(p, 'cognome', '')} for p in players
        ])

    # Gestione errori globale
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f'Pagina non trovata: {request.url} - IP: {request.remote_addr} - User Agent: {request.user_agent}')
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Errore interno del server: {str(error)} - URL: {request.url} - IP: {request.remote_addr}')
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Cattura tutte le eccezioni non gestite"""
        app.logger.error(f'Eccezione non gestita: {str(error)} - URL: {request.url} - IP: {request.remote_addr} - User Agent: {request.user_agent}', exc_info=True)
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Middleware per logging delle richieste
    @app.before_request
    def log_request_info():
        app.logger.debug(f'REQUEST: {request.method} {request.url} - IP: {request.remote_addr} - User Agent: {request.user_agent}')

    @app.after_request
    def log_response_info(response):
        app.logger.debug(f'RESPONSE: {response.status_code} - {request.method} {request.url}')
        return response

    app.logger.info('=== TORNEOTTO INIZIALIZZATO CON SUCCESSO ===')
    return app

if __name__ == '__main__':
    app = create_app()
    app.logger.info(f'Avvio server su {app.config["HOST"]}:{app.config["PORT"]}')
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=True) 