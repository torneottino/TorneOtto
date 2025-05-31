from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.player import Player, PlayerTournamentElo
from extensions import db

players_bp = Blueprint('players', __name__)

@players_bp.route('/giocatori')
def players_list():
    players = Player.query.order_by(Player.cognome).all()
    return render_template('players/list.html', players=players)

@players_bp.route('/giocatori/catalogo')
def players_catalog():
    players = Player.query.order_by(Player.cognome).all()
    return render_template('players/catalog.html', players=players)

@players_bp.route('/giocatori/nuovo', methods=['GET', 'POST'])
def new_player():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cognome = request.form.get('cognome')
        telefono = request.form.get('telefono')
        posizione = request.form.get('posizione')
        elo_standard = request.form.get('elo_standard', '1500.00')
        
        if not nome or not cognome or not posizione:
            flash('Nome, cognome e posizione sono campi obbligatori!', 'error')
            return redirect(url_for('players.new_player'))
        
        try:
            elo_standard = float(elo_standard)
        except ValueError:
            elo_standard = 1500.00
        
        player = Player(
            nome=nome,
            cognome=cognome,
            telefono=telefono,
            posizione=posizione,
            elo_standard=elo_standard
        )
        
        try:
            db.session.add(player)
            db.session.commit()
            flash('Giocatore aggiunto con successo!', 'success')
            return redirect(url_for('players.players_list'))
        except Exception as e:
            db.session.rollback()
            flash('Errore durante il salvataggio del giocatore.', 'error')
            return redirect(url_for('players.new_player'))
            
    return render_template('players/new.html')

@players_bp.route('/giocatori/modifica/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        cognome = request.form.get('cognome')
        telefono = request.form.get('telefono')
        posizione = request.form.get('posizione')
        elo_standard = request.form.get('elo_standard', '1500.00')
        
        if not nome or not cognome or not posizione:
            flash('Nome, cognome e posizione sono campi obbligatori!', 'error')
            return redirect(url_for('players.edit_player', player_id=player_id))
        
        try:
            elo_standard = float(elo_standard)
        except ValueError:
            elo_standard = 1500.00
        
        player.nome = nome
        player.cognome = cognome
        player.telefono = telefono
        player.posizione = posizione
        player.elo_standard = elo_standard
        
        try:
            db.session.commit()
            flash('Giocatore aggiornato con successo!', 'success')
            return redirect(url_for('players.players_list'))
        except Exception as e:
            db.session.rollback()
            flash('Errore durante l\'aggiornamento del giocatore.', 'error')
            return redirect(url_for('players.edit_player', player_id=player_id))
            
    return render_template('players/edit.html', player=player)

@players_bp.route('/giocatori/elimina/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    
    try:
        db.session.delete(player)
        db.session.commit()
        flash('Giocatore eliminato con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore durante l\'eliminazione del giocatore.', 'error')
        
    return redirect(url_for('players.players_list')) 