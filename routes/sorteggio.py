from flask import Blueprint, render_template, jsonify, current_app
from models.player import Player

sorteggio_bp = Blueprint('sorteggio', __name__)

@sorteggio_bp.route('/sorteggio-coppie')
def sorteggio_coppie():
    current_app.logger.debug('Accesso alla pagina sorteggio coppie')
    return render_template('sorteggio_coppie.html')

@sorteggio_bp.route('/sorteggio-casuale')
def sorteggio_casuale():
    current_app.logger.debug('Accesso alla pagina sorteggio casuale')
    return render_template('sorteggio_casuale.html')

@sorteggio_bp.route('/sorteggio-teste-serie')
def sorteggio_teste_serie():
    current_app.logger.debug('Accesso alla pagina sorteggio teste di serie')
    return render_template('sorteggio_teste_serie.html')

@sorteggio_bp.route('/sorteggio-casuale-database')
def sorteggio_casuale_database():
    current_app.logger.debug('Accesso alla pagina sorteggio casuale database')
    players = Player.query.order_by(Player.nome).all()
    # Split nome into first and surname for display
    for p in players:
        parts = p.nome.strip().split(' ', 1)
        if len(parts) > 1:
            p.first_name, p.surname = parts[0], parts[1]
        else:
            p.first_name = ''
            p.surname = p.nome
    return render_template('sorteggio_casuale_database.html', players=players)

@sorteggio_bp.route('/sorteggio-teste-database')
def sorteggio_teste_database():
    current_app.logger.debug('Accesso alla pagina sorteggio teste di serie database')
    players = Player.query.order_by(Player.cognome, Player.nome).all()
    return render_template('sorteggio_teste_serie_database.html', players=players)

@sorteggio_bp.route('/sorteggio-risultati')
def sorteggio_risultati():
    current_app.logger.debug('Accesso alla pagina risultati sorteggio')
    return render_template('sorteggio_risultati.html')

@sorteggio_bp.route('/sorteggio-casuale-manuale')
def sorteggio_casuale_manuale():
    current_app.logger.debug('Accesso alla pagina sorteggio casuale manuale')
    return render_template('sorteggio_casuale_manuale.html')

@sorteggio_bp.route('/sorteggio-teste-manuale')
def sorteggio_teste_manuale():
    current_app.logger.debug('Accesso alla pagina sorteggio teste di serie manuale')
    return render_template('sorteggio_teste_serie_manuale.html')

@sorteggio_bp.route('/api/players')
def api_players():
    """API semplice JSON dei giocatori (id, nome, cognome)"""
    players = Player.query.order_by(Player.nome).all()
    return jsonify([{'id': p.id, 'nome': p.nome, 'cognome': getattr(p, 'cognome', '')} for p in players])
