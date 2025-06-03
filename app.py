from flask import Flask, render_template
import os
import logging
from logging.handlers import RotatingFileHandler
from extensions import db
from flask_migrate import Migrate
from config import config
from routes.players import players_bp
from routes.tournaments import tournaments_bp
import argparse

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inizializzazione delle estensioni
    db.init_app(app)
    
    # Configurazione del logging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/torneotto.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Applicazione avviata')
    
    # Registrazione dei blueprint
    app.register_blueprint(players_bp)
    app.register_blueprint(tournaments_bp)
    
    with app.app_context():
        db.create_all()
    
    migrate = Migrate(app, db)
    
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
    # Parsing degli argomenti da linea di comando
    parser = argparse.ArgumentParser(description='TorneOtto Server')
    parser.add_argument('--port', type=int, help='Porta su cui avviare il server')
    parser.add_argument('--host', help='Host su cui avviare il server')
    args = parser.parse_args()
    
    app = create_app('development')
    
    # Usa gli argomenti da linea di comando se specificati, altrimenti usa i valori di default
    port = args.port if args.port is not None else app.config['PORT']
    host = args.host if args.host is not None else app.config['HOST']
    
    app.run(host=host, port=port, debug=app.config['DEBUG']) 