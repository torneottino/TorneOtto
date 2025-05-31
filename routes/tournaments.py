from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from models.tournament import Tournament
from models.player import Player, PlayerTournamentElo, PlayerEloHistory
from models.tournament_day import TorneOtto30Day, TorneOtto45Day, TournamentDay
from extensions import db
from datetime import datetime, date, timedelta
import json
from services import pairing
import random
import io
from functools import wraps
from sqlalchemy import func
from services.elo_calculator import update_tournament_elos, delete_tournament_day_elos, calculate_match_elo_change, get_team_elo, get_player_current_elo
from elo_tournament_fix import get_player_tournament_elo
from services.tournament_service import delete_tournament_day_simple

tournaments_bp = Blueprint('tournaments', __name__)

@tournaments_bp.route('/tornei')
def tournaments_list():
    """Visualizza la pagina di gestione dei tornei con la scelta delle tipologie."""
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    for torneo in tournaments:
        # Recupera tutte le giornate di qualunque tipo
        days = torneo.tournament_days
        if not days or len(days) == 0:
            torneo.stato = "Pianificato"
        else:
            stati = [d.stato for d in days]
            if all(s in ["Aperta", "Risultati da inserire"] for s in stati):
                torneo.stato = "In attesa"
            elif all(s == "Completata" for s in stati):
                torneo.stato = "Completato"
            elif any(s == "Completata" for s in stati) and any(s in ["Aperta", "Risultati da inserire"] for s in stati):
                torneo.stato = "In corso"
            else:
                torneo.stato = "Pianificato"
    return render_template('tournaments/list.html', tournaments=tournaments)

@tournaments_bp.route('/tornei/attivi')
def active_tournaments():
    """Visualizza i tornei attualmente attivi."""
    tournaments = Tournament.query.filter_by(stato="In corso").all()
    return render_template('tournaments/active.html', tournaments=tournaments)

@tournaments_bp.route('/tornei/nuovo', methods=['GET', 'POST'])
def new_tournament():
    """Pagina di selezione del tipo di torneo"""
    if request.method == 'POST':
        tipo_torneo = request.form.get('tipo_torneo')
        if tipo_torneo:
            return redirect(url_for('tournaments.tournament_type', tipo=tipo_torneo))
        else:
            flash('Seleziona un tipo di torneo!', 'error')
    
    tipi_tornei = {
        "torneotto30": "TorneOtto 30'", 
        "torneotto45": "TorneOtto 45'", 
        "gironi": "A Gironi", 
        "eliminazione": "Eliminazione Diretta"
    }
    return render_template('tournaments/new.html', tipi_tornei=tipi_tornei)

@tournaments_bp.route('/tornei/tipo/<string:tipo>', methods=['GET', 'POST'])
def tournament_type(tipo):
    """Reindirizza alla creazione di un tipo specifico di torneo"""
    tipi_validi = ["torneotto30", "torneotto45", "gironi", "eliminazione"]
    if tipo not in tipi_validi:
        flash('Tipo di torneo non valido!', 'error')
        return redirect(url_for('tournaments.tournaments_list'))
    
    return redirect(url_for(f'tournaments.create_{tipo}_tournament'))

# ROUTE PER TORNEO TORNEOTTO 30'
@tournaments_bp.route('/tornei/nuovo/torneotto30', methods=['GET', 'POST'])
def create_torneotto30_tournament():
    """Creazione di un torneo TorneOtto 30"""
    if request.method == 'POST':
        # Recupera i dati dal form
        nome = request.form.get('nome')
        circolo = request.form.get('circolo')
        note = request.form.get('note')
        
        # Validazione
        if not nome:
            flash('Il nome del torneo è obbligatorio!', 'error')
            return render_template('tournaments/types/torneotto30.html')
        
        # Date predefinite (una settimana)
        data_inizio = date.today()
        data_fine = data_inizio + timedelta(days=7)
        
        # Creazione torneo
        torneo = Tournament(
            nome=nome,
            tipo_torneo='torneotto30',
            circolo=circolo,
            note=note,
            data_inizio=data_inizio,
            data_fine=data_fine,
            stato="Pianificato"
        )
        
        # Configurazione fissa: 4 squadre, 8 giocatori, 30 minuti
        torneo.set_config({
            'num_squadre': 4,
            'num_giocatori': 8,
            'tempo_partita': 30
        })
        
        try:
            db.session.add(torneo)
            db.session.commit()
            flash('Torneo TorneOtto 30\' creato con successo!', 'success')
            return redirect(url_for('tournaments.tournaments_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione del torneo: {str(e)}', 'error')
    
    return render_template('tournaments/types/torneotto30.html')

# ROUTE PER TORNEO TORNEOTTO 45'
@tournaments_bp.route('/tornei/nuovo/torneotto45', methods=['GET', 'POST'])
def create_torneotto45_tournament():
    """Creazione di un torneo TorneOtto 45"""
    if request.method == 'POST':
        # Recupera i dati dal form
        nome = request.form.get('nome')
        circolo = request.form.get('circolo')
        note = request.form.get('note')
        num_squadre = request.form.get('num_squadre', 8)
        tempo_partita = request.form.get('tempo_partita', 45)
        finali = request.form.get('finali', 1)
        
        # Validazione
        if not nome:
            flash('Il nome del torneo è obbligatorio!', 'error')
            return render_template('tournaments/types/torneotto45.html')
        
        # Date predefinite (una settimana)
        data_inizio = date.today()
        data_fine = data_inizio + timedelta(days=7)
        
        # Creazione torneo
        torneo = Tournament(
            nome=nome,
            tipo_torneo='torneotto45',
            circolo=circolo,
            note=note,
            data_inizio=data_inizio,
            data_fine=data_fine,
            stato="Pianificato"
        )
        
        # Aggiungi la configurazione specifica
        torneo.set_config({
            'num_squadre': int(num_squadre),
            'tempo_partita': int(tempo_partita),
            'finali': int(finali)
        })
        
        try:
            db.session.add(torneo)
            db.session.commit()
            flash('Torneo TorneOtto 45\' creato con successo!', 'success')
            return redirect(url_for('tournaments.tournaments_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione del torneo: {str(e)}', 'error')
    
    return render_template('tournaments/types/torneotto45.html')

# ROUTE PER TORNEO A GIRONI
@tournaments_bp.route('/tornei/nuovo/gironi', methods=['GET', 'POST'])
def create_gironi_tournament():
    """Creazione di un torneo a gironi"""
    if request.method == 'POST':
        # Recupera i dati dal form
        nome = request.form.get('nome')
        circolo = request.form.get('circolo')
        note = request.form.get('note')
        num_gironi = request.form.get('num_gironi', 4)
        squadre_per_girone = request.form.get('squadre_per_girone', 4)
        
        # Validazione
        if not nome:
            flash('Il nome del torneo è obbligatorio!', 'error')
            return render_template('tournaments/types/gironi.html')
        
        # Date predefinite (una settimana)
        data_inizio = date.today()
        data_fine = data_inizio + timedelta(days=14)  # I tornei a gironi sono più lunghi
        
        # Creazione torneo
        torneo = Tournament(
            nome=nome,
            tipo_torneo='gironi',
            circolo=circolo,
            note=note,
            data_inizio=data_inizio,
            data_fine=data_fine,
            stato="Pianificato"
        )
        
        # Aggiungi la configurazione specifica
        torneo.set_config({
            'num_gironi': int(num_gironi),
            'squadre_per_girone': int(squadre_per_girone)
        })
        
        try:
            db.session.add(torneo)
            db.session.commit()
            flash('Torneo a gironi creato con successo!', 'success')
            return redirect(url_for('tournaments.tournaments_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione del torneo: {str(e)}', 'error')
    
    return render_template('tournaments/types/gironi.html')

# ROUTE PER TORNEO A ELIMINAZIONE DIRETTA
@tournaments_bp.route('/tornei/nuovo/eliminazione', methods=['GET', 'POST'])
def create_eliminazione_tournament():
    """Creazione di un torneo a eliminazione diretta"""
    if request.method == 'POST':
        # Recupera i dati dal form
        nome = request.form.get('nome')
        circolo = request.form.get('circolo')
        note = request.form.get('note')
        num_partecipanti = request.form.get('num_partecipanti', 16)
        teste_di_serie = request.form.get('teste_di_serie', 4)
        consolazione = request.form.get('consolazione', 0)
        
        # Validazione
        if not nome:
            flash('Il nome del torneo è obbligatorio!', 'error')
            return render_template('tournaments/types/eliminazione.html')
        
        # Date predefinite (una settimana)
        data_inizio = date.today()
        data_fine = data_inizio + timedelta(days=10)
        
        # Creazione torneo
        torneo = Tournament(
            nome=nome,
            tipo_torneo='eliminazione',
            circolo=circolo,
            note=note,
            data_inizio=data_inizio,
            data_fine=data_fine,
            stato="Pianificato"
        )
        
        # Aggiungi la configurazione specifica
        torneo.set_config({
            'num_partecipanti': int(num_partecipanti),
            'teste_di_serie': int(teste_di_serie),
            'consolazione': int(consolazione)
        })
        
        try:
            db.session.add(torneo)
            db.session.commit()
            flash('Torneo a eliminazione diretta creato con successo!', 'success')
            return redirect(url_for('tournaments.tournaments_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione del torneo: {str(e)}', 'error')
    
    return render_template('tournaments/types/eliminazione.html')

@tournaments_bp.route('/tornei/<int:tournament_id>')
def view_tournament(tournament_id):
    torneo = Tournament.query.get_or_404(tournament_id)
    # Recupera tutte le giornate di qualunque tipo
    days = torneo.tournament_days
    if not days or len(days) == 0:
        torneo.stato = "Pianificato"
    else:
        stati = [d.stato for d in days]
        if all(s in ["Aperta", "Risultati da inserire"] for s in stati):
            torneo.stato = "In attesa"
        elif all(s == "Completata" for s in stati):
            torneo.stato = "Completato"
        elif any(s == "Completata" for s in stati) and any(s in ["Aperta", "Risultati da inserire"] for s in stati):
            torneo.stato = "In corso"
        else:
            torneo.stato = "Pianificato"
    # Recupera le giornate del torneo per tipo
    if torneo.tipo_torneo == 'torneotto30':
        giornate = TorneOtto30Day.query.filter_by(tournament_id=torneo.id).order_by(TorneOtto30Day.data).all()
    elif torneo.tipo_torneo == 'torneotto45':
        giornate = TorneOtto45Day.query.filter_by(tournament_id=torneo.id).order_by(TorneOtto45Day.data).all()
    else:
        giornate = []
    return render_template('tournaments/view.html', torneo=torneo, giornate=giornate)

@tournaments_bp.route('/tornei/modifica/<int:tournament_id>', methods=['GET', 'POST'])
def edit_tournament(tournament_id):
    torneo = Tournament.query.get_or_404(tournament_id)
    if request.method == 'POST':
        torneo.nome = request.form.get('nome')
        torneo.circolo = request.form.get('circolo')
        torneo.note = request.form.get('note')
        # Puoi aggiungere qui la logica per aggiornare la configurazione se necessario
        try:
            db.session.commit()
            flash('Torneo aggiornato con successo!', 'success')
            return redirect(url_for('tournaments.view_tournament', tournament_id=torneo.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiornamento: {str(e)}', 'error')
    return render_template('tournaments/edit.html', torneo=torneo)

@tournaments_bp.route('/tornei/nuova_giornata/torneotto30')
def new_day_torneotto():
    return render_template('tournaments/new_day_torneotto.html')

@tournaments_bp.route('/tornei/torneotto30/new_day', methods=['GET', 'POST'])
def new_day_torneotto30():
    if request.method == 'POST':
        date = request.form.get('date')
        selected_players = request.form.get('selected_players')
        tournament_id = request.form.get('tournament_id')
        
        if not all([date, selected_players, tournament_id]):
            flash('Tutti i campi sono obbligatori', 'error')
            return redirect(url_for('tournaments.new_day_torneotto30', tournament_id=tournament_id))
        
        # Verifica che il torneo esista e sia del tipo corretto
        tournament = Tournament.query.get(tournament_id)
        if not tournament or tournament.tipo_torneo != 'torneotto30':
            flash('Torneo non valido', 'error')
            return redirect(url_for('tournaments.tournaments_list'))
        
        # Converti la stringa dei giocatori in lista di ID
        player_ids = [int(id) for id in selected_players.split(',')]
        
        if len(player_ids) != 8:
            flash('Devi selezionare esattamente 8 giocatori', 'error')
            return redirect(url_for('tournaments.new_day_torneotto30', tournament_id=tournament_id))
        
        # Reindirizza alla pagina di scelta del metodo di formazione coppie
        return redirect(url_for('tournaments.choose_pairing_method', 
                              date=date, 
                              players=selected_players,
                              tournament_id=tournament_id))
    
    # GET: mostra il form
    tournament_id = request.args.get('tournament_id')
    if not tournament_id:
        flash('ID torneo mancante', 'error')
        return redirect(url_for('tournaments.tournaments_list'))
        
    # Verifica che il torneo esista e sia del tipo corretto
    tournament = Tournament.query.get(tournament_id)
    if not tournament or tournament.tipo_torneo != 'torneotto30':
        flash('Torneo non valido', 'error')
        return redirect(url_for('tournaments.tournaments_list'))
    
    players = Player.query.order_by(Player.cognome, Player.nome).all()
    return render_template('tournaments/new_day_torneotto30.html', 
                         players=players,
                         tournament=tournament)

@tournaments_bp.route('/tornei/torneotto30/choose_method', methods=['GET'])
def choose_pairing_method():
    date = request.args.get('date')
    players_ids = request.args.get('players')
    tournament_id = request.args.get('tournament_id')
    
    if not all([date, players_ids, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))
    
    # Recupera i dettagli dei giocatori
    player_ids = [int(id) for id in players_ids.split(',')]
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    tournament = Tournament.query.get_or_404(tournament_id)
    
    return render_template('tournaments/choose_pairing_method.html',
                         date=date,
                         players=players,
                         tournament=tournament)

def assegna_tournament_elo(players, tournament_id):
    for player in players:
        player.tournament_elo = get_player_tournament_elo(player.id, tournament_id)
    return players

# TorneOtto30 - pairing random
@tournaments_bp.route('/tornei/torneotto30/pairing/random', methods=['POST'])
def random_pairing():
    date_str = request.form.get('date')
    players_ids = request.form.get('players')
    tournament_id = request.form.get('tournament_id')
    if not all([date_str, players_ids, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))
    player_ids = [int(id) for id in players_ids.split(',')]
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    tournament = Tournament.query.get_or_404(tournament_id)
    assegna_tournament_elo(players, tournament_id)
    return render_template('tournaments/pairing_animation.html',
                         tournament=tournament,
                         date=date_str,
                         players=players,
                         method="random",
                         method_title="Sorteggio Totalmente Casuale",
                         method_description="Le squadre vengono formate in modo completamente casuale",
                         tournament_id=tournament_id,
                         form_action=url_for('tournaments.process_random_pairing'))

@tournaments_bp.route('/tornei/torneotto30/pairing/random/process', methods=['POST'])
def process_random_pairing():
    date_str = request.form.get('date')
    tournament_id = request.form.get('tournament_id')
    pairs_json = request.form.get('pairs')
    
    # Validazione
    if not all([date_str, tournament_id, pairs_json]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))
    
    # Decodifica le coppie
    pairs = json.loads(pairs_json)
    player_ids = [id for pair in pairs for id in pair]
    
    # Recupera i dettagli dei giocatori
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    player_dict = {p.id: p for p in players}
    
    # Forma le squadre
    teams = [[player_dict[pair[0]], player_dict[pair[1]]] for pair in pairs]
    
    # Genera il calendario delle partite
    schedule = get_torneotto30_schedule()
    
    # Converte i dati in JSON per il passaggio alla pagina di riepilogo
    teams_json = json.dumps([[p.id for p in team] for team in teams])
    schedule_json = json.dumps(schedule)
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    return render_template('tournaments/pairing_summary.html',
                         tournament=tournament,
                         date=date_str,
                         teams=teams,
                         schedule=schedule,
                         teams_json=teams_json,
                         schedule_json=schedule_json,
                         all_players=players)

# TorneOtto30 - pairing elo
@tournaments_bp.route('/tornei/torneotto30/pairing/elo', methods=['POST'])
def elo_pairing():
    date_str = request.form.get('date')
    players_ids = request.form.get('players')
    tournament_id = request.form.get('tournament_id')
    if not all([date_str, players_ids, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))
    player_ids = [int(id) for id in players_ids.split(',')]
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    tournament = Tournament.query.get_or_404(tournament_id)
    assegna_tournament_elo(players, tournament_id)
    return render_template('tournaments/pairing_animation.html',
                         tournament=tournament,
                         date=date_str,
                         players=players,
                         method="elo",
                         method_title="Sorteggio per Punti e Posizione",
                         method_description="Le squadre vengono formate considerando i punti ELO e la posizione preferita dei giocatori",
                         tournament_id=tournament_id,
                         form_action=url_for('tournaments.process_elo_pairing'))

@tournaments_bp.route('/tornei/torneotto30/pairing/elo/process', methods=['POST'])
def process_elo_pairing():
    date_str = request.form.get('date')
    tournament_id = request.form.get('tournament_id')
    pairs_json = request.form.get('pairs')
    
    # Validazione
    if not all([date_str, tournament_id, pairs_json]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))
    
    # Decodifica le coppie
    pairs = json.loads(pairs_json)
    player_ids = [id for pair in pairs for id in pair]
    
    # Recupera i dettagli dei giocatori
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    player_dict = {p.id: p for p in players}
    
    # Forma le squadre
    teams = [[player_dict[pair[0]], player_dict[pair[1]]] for pair in pairs]
    
    # Genera il calendario delle partite
    schedule = get_torneotto30_schedule()
    
    # Converte i dati in JSON per il passaggio alla pagina di riepilogo
    teams_json = json.dumps([[p.id for p in team] for team in teams])
    schedule_json = json.dumps(schedule)
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    return render_template('tournaments/pairing_summary.html',
                         tournament=tournament,
                         date=date_str,
                         teams=teams,
                         schedule=schedule,
                         teams_json=teams_json,
                         schedule_json=schedule_json,
                         all_players=players)

# TorneOtto30 - pairing seeded
@tournaments_bp.route('/tornei/torneotto30/pairing/seeded', methods=['GET', 'POST'])
def seeded_pairing():
    if request.method == 'POST':
        date_str = request.form.get('date')
        tournament_id = request.form.get('tournament_id')
        players_ids = request.form.get('players')
        seeded_players = request.form.getlist('seeded_players')
        if not all([date_str, tournament_id, players_ids]) or not seeded_players:
            flash('Dati mancanti o teste di serie non selezionate', 'error')
            return redirect(url_for('tournaments.new_day_torneotto30'))
        player_ids = [int(id) for id in players_ids.split(',')]
        players = Player.query.filter(Player.id.in_(player_ids)).all()
        tournament = Tournament.query.get_or_404(tournament_id)
        assegna_tournament_elo(players, tournament_id)
        return render_template('tournaments/pairing_animation.html',
                             tournament=tournament,
                             date=date_str,
                             players=players,
                             method="seeded",
                             method_title="Sorteggio con Teste di Serie",
                             method_description="Le squadre vengono formate assicurando che ogni testa di serie sia in una squadra diversa",
                             tournament_id=tournament_id,
                             seeded_players=seeded_players,
                             form_action=url_for('tournaments.process_seeded_pairing'))
    # GET
    date_str = request.args.get('date')
    players_ids = request.args.get('players')
    tournament_id = request.args.get('tournament_id')
    if not all([date_str, players_ids, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))
    player_ids = [int(id) for id in players_ids.split(',')]
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    tournament = Tournament.query.get_or_404(tournament_id)
    assegna_tournament_elo(players, tournament_id)
    players.sort(key=lambda x: x.tournament_elo, reverse=True)
    return render_template('tournaments/seeded_pairing.html',
                         tournament=tournament,
                         date=date_str,
                         players=players_ids,
                         tournament_id=tournament_id,
                         all_players=players)

@tournaments_bp.route('/tornei/torneotto30/pairing/seeded/process', methods=['POST'])
def process_seeded_pairing():
    date_str = request.form.get('date')
    tournament_id = request.form.get('tournament_id')
    pairs_json = request.form.get('pairs')
    
    # Validazione
    if not all([date_str, tournament_id, pairs_json]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))
    
    # Decodifica le coppie
    pairs = json.loads(pairs_json)
    player_ids = [id for pair in pairs for id in pair]
    
    # Recupera i dettagli dei giocatori
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    player_dict = {p.id: p for p in players}
    
    # Forma le squadre
    teams = [[player_dict[pair[0]], player_dict[pair[1]]] for pair in pairs]
    
    # Genera il calendario delle partite
    schedule = get_torneotto30_schedule()
    
    # Converte i dati in JSON per il passaggio alla pagina di riepilogo
    teams_json = json.dumps([[p.id for p in team] for team in teams])
    schedule_json = json.dumps(schedule)
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    return render_template('tournaments/pairing_summary.html',
                         tournament=tournament,
                         date=date_str,
                         teams=teams,
                         schedule=schedule,
                         teams_json=teams_json,
                         schedule_json=schedule_json,
                         all_players=players)

# TorneOtto30 - pairing manual
@tournaments_bp.route('/tornei/torneotto30/pairing/manual', methods=['GET', 'POST'])
def manual_pairing():
    if request.method == 'POST':
        date_str = request.form.get('date')
        tournament_id = request.form.get('tournament_id')
        teams = []
        for i in range(1, 5):
            player1_id = int(request.form.get(f'team{i}_player1'))
            player2_id = int(request.form.get(f'team{i}_player2'))
            teams.append([player1_id, player2_id])
        all_players = [p for team in teams for p in team]
        if len(all_players) != len(set(all_players)) or len(all_players) != 8:
            flash('Ogni giocatore deve essere selezionato esattamente una volta', 'error')
            return redirect(url_for('tournaments.manual_pairing', 
                                  date=date_str, 
                                  players=','.join(str(p) for p in all_players),
                                  tournament_id=tournament_id))
        player_objects = Player.query.filter(Player.id.in_(all_players)).all()
        assegna_tournament_elo(player_objects, tournament_id)
        player_dict = {p.id: p for p in player_objects}
        teams_objects = [[player_dict[p1], player_dict[p2]] for p1, p2 in teams]
        schedule = get_torneotto30_schedule()
        teams_json = json.dumps(teams)
        schedule_json = json.dumps(schedule)
        tournament = Tournament.query.get_or_404(tournament_id)
        return render_template('tournaments/pairing_summary.html',
                             tournament=tournament,
                             date=date_str,
                             teams=teams_objects,
                             schedule=schedule,
                             teams_json=teams_json,
                             schedule_json=schedule_json,
                             all_players=player_objects)
    # GET
    date_str = request.args.get('date')
    players_ids = request.args.get('players')
    tournament_id = request.args.get('tournament_id')
    if not all([date_str, players_ids, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))
    player_ids = [int(id) for id in players_ids.split(',')]
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    tournament = Tournament.query.get_or_404(tournament_id)
    assegna_tournament_elo(players, tournament_id)
    return render_template('tournaments/manual_pairing.html',
                         tournament=tournament,
                         date=date_str,
                         players=players,
                         tournament_id=tournament_id)

@tournaments_bp.route('/tornei/torneotto30/save_day', methods=['POST'])
def save_tournament_day():
    date_str = request.form.get('date')
    tournament_id = request.form.get('tournament_id')
    teams_json = request.form.get('teams')
    schedule_json = request.form.get('schedule')
    
    # Validazione
    if not all([date_str, tournament_id, teams_json, schedule_json]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))
    
    try:
        # Converti la data in formato datetime
        tournament_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Aggiorna lo stato del torneo se necessario
        tournament = Tournament.query.get_or_404(tournament_id)
        if tournament.stato == "Pianificato":
            tournament.stato = "In corso"
        
        # Decodifica i dati
        teams = json.loads(teams_json)
        schedule = json.loads(schedule_json)
        
        # Estrai gli ID dei giocatori
        player_ids = [id for team in teams for id in team]
        
        # Crea una nuova giornata del torneo
        day = TorneOtto30Day(
            tournament_id=tournament_id,
            data=tournament_date,
            stato="Aperta",
            tipo_giornata="torneotto30"
        )
        
        # Prepara i dati di configurazione della giornata
        day_config = {
            'players': player_ids,
            'teams': teams,
            'schedule': schedule,
            'results': {}  # Inizializza risultati vuoti
        }
        
        # Salva la configurazione della giornata
        day.set_config(day_config)
        
        # Aggiungi e committa
        db.session.add(day)
        db.session.commit()
        
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore durante il salvataggio: {str(e)}")
        flash('Errore durante il salvataggio della giornata', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))

@tournaments_bp.route('/tornei/torneotto30/export_pdf')
def export_pdf():
    date_str = request.args.get('date')
    tournament_id = request.args.get('tournament_id')
    teams_json = request.args.get('teams')
    schedule_json = request.args.get('schedule')
    
    # Validazione
    if not all([date_str, tournament_id, teams_json, schedule_json]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_day_torneotto30'))
    
    try:
        # Decodifica i dati
        teams = json.loads(teams_json)
        schedule = json.loads(schedule_json)
        
        # Recupera i dettagli del torneo e dei giocatori
        tournament = Tournament.query.get_or_404(tournament_id)
        
        # Prepara i dati per il template
        player_ids = [id for team in teams for id in team]
        players = Player.query.filter(Player.id.in_(player_ids)).all()
        player_dict = {p.id: p for p in players}
        
        # Crea le squadre con gli oggetti giocatore
        teams_objects = [[player_dict[p1], player_dict[p2]] for p1, p2 in teams]
        
        # Renderizza direttamente il template HTML
        return render_template('tournaments/incorso_torneotto30.html',
                            tournament=tournament,
                            date=date_str,
                            teams=teams_objects,
                            schedule=schedule,
                            print_view=True)  # Aggiungo un flag per la vista stampa
    except Exception as e:
        current_app.logger.error(f"Errore nella generazione della vista: {str(e)}")
        flash(f'Errore nella generazione della vista: {str(e)}', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))

def get_torneotto30_schedule():
    """Restituisce lo schema fisso del torneotto30 con 3 turni di 2 partite ciascuno."""
    return [
        [(1, 2), (3, 4)],  # Turno 1: A vs B, C vs D
        [(1, 3), (2, 4)],  # Turno 2: A vs C, B vs D
        [(1, 4), (2, 3)]   # Turno 3: A vs D, B vs C
    ]

@tournaments_bp.route('/tornei/<int:tournament_id>/delete', methods=['POST'])
def delete_tournament(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    try:
        db.session.delete(tournament)
        db.session.commit()
        
        # Resetta la sequenza degli ID se non ci sono più tornei
        if Tournament.query.count() == 0:
            if db.engine.url.drivername == 'sqlite':
                db.session.execute('DELETE FROM sqlite_sequence WHERE name="tournament"')
                db.session.commit()
        
        flash('Torneo eliminato con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione del torneo: {str(e)}', 'error')
    
    return redirect(url_for('tournaments.tournaments_list'))

@tournaments_bp.route('/tornei/giornata/<int:day_id>')
def view_tournament_day(day_id):
    # Recupera la giornata del torneo dal database
    day = TorneOtto30Day.query.get_or_404(day_id)
    tournament = Tournament.query.get_or_404(day.tournament_id)
    
    # Recupera la configurazione della giornata
    config = day.get_config()
    teams = config.get('teams', [])
    schedule = config.get('schedule', [])
    results = config.get('results', {})
    
    # Recupera i dettagli dei giocatori
    player_ids = [id for team in teams for id in team]
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    player_dict = {p.id: p for p in players}
    
    # --- PATCH: Assegna tournament_elo corretto per la visualizzazione ---
    for p in players:
        p.tournament_elo = get_player_tournament_elo(p.id, tournament.id)
    # ---------------------------------------------------------------
    
    # Forma le squadre con gli oggetti giocatore
    teams_objects = [[player_dict[p1], player_dict[p2]] for p1, p2 in teams]

    standings = None
    if day.stato == "Completata":
        # Calcola la classifica
        standings = []
        for i in range(len(teams)):
            standings.append({'points': 0, 'diff': 0, 'win': 0, 'draw': 0, 'lose': 0})
        for round_matches in schedule:
            for match in round_matches:
                match_key = f"{match[0]}-{match[1]}"
                result = results.get(match_key)
                if result:
                    try:
                        score_a, score_b = map(int, result.split('-'))
                    except Exception:
                        continue
                    idx_a = match[0] - 1
                    idx_b = match[1] - 1
                    # Aggiorna differenza games
                    standings[idx_a]['diff'] += score_a - score_b
                    standings[idx_b]['diff'] += score_b - score_a
                    # Aggiorna punti e W/D/L
                    if score_a > score_b:
                        standings[idx_a]['points'] += 3
                        standings[idx_a]['win'] += 1
                        standings[idx_b]['lose'] += 1
                    elif score_b > score_a:
                        standings[idx_b]['points'] += 3
                        standings[idx_b]['win'] += 1
                        standings[idx_a]['lose'] += 1
                    else:
                        standings[idx_a]['points'] += 1
                        standings[idx_b]['points'] += 1
                        standings[idx_a]['draw'] += 1
                        standings[idx_b]['draw'] += 1
    
    return render_template('tournaments/view_day.html',
                          tournament=tournament,
                          day=day,
                          teams=teams_objects,
                          schedule=schedule,
                          results=results,
                          standings=standings)

@tournaments_bp.route('/tornei/giornata/<int:day_id>/risultati', methods=['GET', 'POST'])
def enter_results(day_id):
    # Recupera la giornata del torneo dal database
    day = TorneOtto30Day.query.get_or_404(day_id)
    tournament = Tournament.query.get_or_404(day.tournament_id)
    
    # Recupera la configurazione della giornata
    config = day.get_config()
    teams = config.get('teams', [])
    schedule = config.get('schedule', [])
    results = config.get('results', {})
    
    if request.method == 'POST':
        try:
            # Aggiorna i risultati
            new_results = {}
            for round_idx, round_matches in enumerate(schedule):
                for match in round_matches:
                    match_key = f"{match[0]}-{match[1]}"
                    score_a = request.form.get(f"result_{match_key}_a")
                    score_b = request.form.get(f"result_{match_key}_b")
                    if score_a is not None and score_b is not None and score_a != '' and score_b != '':
                        new_results[match_key] = f"{score_a}-{score_b}"
            
            # Aggiorna la configurazione con i nuovi risultati
            config['results'] = new_results
            day.set_config(config)
            
            # Aggiorna lo stato della giornata se tutti i risultati sono stati inseriti
            all_results_entered = len(new_results) == len([m for r in schedule for m in r])
            if all_results_entered:
                day.stato = "Completata"
                # Aggiorna gli ELO solo quando tutti i risultati sono stati inseriti
                try:
                    # Aggiorna gli ELO
                    update_tournament_elos(day_id)
                    db.session.commit()
                    flash('ELO aggiornati con successo!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Errore durante l\'aggiornamento degli ELO: {str(e)}', 'error')
            else:
                day.stato = "Risultati da inserire"
                db.session.commit()
                flash('Risultati salvati con successo!', 'success')
            
            return redirect(url_for('tournaments.view_tournament_day', day_id=day_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante il salvataggio dei risultati: {str(e)}', 'error')
            return redirect(url_for('tournaments.view_tournament_day', day_id=day_id))
    
    # Recupera i dettagli dei giocatori
    player_ids = [id for team in teams for id in team]
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    player_dict = {p.id: p for p in players}
    
    # Forma le squadre con gli oggetti giocatore
    teams_objects = [[player_dict[p1], player_dict[p2]] for p1, p2 in teams]
    
    return render_template('tournaments/enter_results.html',
                          tournament=tournament,
                          day=day,
                          teams=teams_objects,
                          schedule=schedule,
                          results=results)

@tournaments_bp.route('/api/tournaments/day/<int:day_id>', methods=['DELETE'])
def delete_day(day_id):
    try:
        # Usa la funzione robusta che elimina anche i record ELO
        delete_tournament_day_simple(day_id)
        return jsonify({'success': True, 'message': 'Giornata eliminata con successo'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore durante l'eliminazione della giornata: {str(e)}")
        return jsonify({'error': str(e)}), 500

@tournaments_bp.route('/tornei/<int:tournament_id>/classifica')
def tournament_ranking(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    from sqlalchemy import func

    # Recupera tutte le giornate del torneo (sia 30 che 45)
    days_30 = TorneOtto30Day.query.filter_by(tournament_id=tournament_id).all()
    days_45 = TorneOtto45Day.query.filter_by(tournament_id=tournament_id).all()
    player_stats = {}

    # TorneOtto30: come prima
    for day in days_30:
        config = day.get_config()
        teams = config.get('teams', [])
        for team in teams:
            for player_id in team:
                if player_id not in player_stats:
                    elo_rating = PlayerTournamentElo.query.filter_by(
                        player_id=player_id,
                        tournament_id=tournament_id
                    ).first()
                    player_stats[player_id] = {
                        'presenze': 0,
                        'elo_rating': elo_rating.elo_rating if elo_rating else 1500.00
                    }
                player_stats[player_id]['presenze'] += 1

    # TorneOtto45: aggiungo presenze e aggiorno ELO
    for day in days_45:
        classifica = day.get_ranking() or []
        for player_id in classifica:
            if player_id not in player_stats:
                elo_rating = PlayerTournamentElo.query.filter_by(
                    player_id=player_id,
                    tournament_id=tournament_id
                ).first()
                player_stats[player_id] = {
                    'presenze': 0,
                    'elo_rating': elo_rating.elo_rating if elo_rating else 1500.00
                }
            player_stats[player_id]['presenze'] += 1

    players = Player.query.filter(Player.id.in_(player_stats.keys())).all()
    players_with_stats = []
    for player in players:
        stats = player_stats[player.id]
        players_with_stats.append({
            'id': player.id,
            'nome': player.nome,
            'cognome': player.cognome,
            'elo_rating': stats['elo_rating'],
            'presenze': stats['presenze']
        })
    players_with_stats.sort(key=lambda x: x['elo_rating'], reverse=True)
    return render_template('tournaments/tournament_ranking.html', 
                         tournament=tournament,
                         players=players_with_stats)

@tournaments_bp.route('/api/tournaments/<int:tournament_id>/players/<int:player_id>/stats')
def get_player_stats(tournament_id, player_id):
    try:
        player = Player.query.get_or_404(player_id)
        days_30 = TorneOtto30Day.query.filter_by(tournament_id=tournament_id).order_by(TorneOtto30Day.data).all()
        days_45 = TorneOtto45Day.query.filter_by(tournament_id=tournament_id).order_by(TorneOtto45Day.data).all()
        player_elo = PlayerTournamentElo.query.filter_by(
            player_id=player_id,
            tournament_id=tournament_id
        ).first()
        stats = {
            'nome': player.nome,
            'cognome': player.cognome,
            'presenze_totali': 0,
            'presenze_completate': 0,
            'partite_totali': 0,
            'partite_giocate': 0,
            'vittorie': 0,
            'pareggi': 0,
            'sconfitte': 0,
            'elo_history': [],
            'elo_attuale': player_elo.elo_rating if player_elo else 1500.00
        }

        # Aggiungi l'ELO iniziale per entrambi i tipi di torneo
        first_day_30 = TorneOtto30Day.query.filter_by(tournament_id=tournament_id).order_by(TorneOtto30Day.data).first()
        first_day_45 = TorneOtto45Day.query.filter_by(tournament_id=tournament_id).order_by(TorneOtto45Day.data).first()
        
        if first_day_30 or first_day_45:
            stats['elo_history'].append({
                'data': (first_day_30 or first_day_45).data.strftime('%d.%m.%Y'),
                'giornata': f"{(first_day_30 or first_day_45).data.strftime('%d.%m.%Y')} Inserimento",
                'variazione': "+0.00",
                'elo': "1500.00"
            })

        # TorneOtto30: gestione come prima
        for day in days_30:
            if player_id in [p for team in day.get_config().get('teams', []) for p in team]:
                stats['presenze_totali'] += 1
                if day.stato == "Completata":
                    stats['presenze_completate'] += 1
                    stats['partite_totali'] += 3
                    config = day.get_config()
                    teams = config.get('teams', [])
                    results = config.get('results', {})
                    schedule = config.get('schedule', [])
                    # Trova la squadra del giocatore
                    player_team_idx = None
                    for i, team in enumerate(teams):
                        if player_id in team:
                            player_team_idx = i + 1
                            break
                    if player_team_idx is not None:
                        for round_matches in schedule:
                            for match in round_matches:
                                if player_team_idx in match:
                                    match_key = f"{match[0]}-{match[1]}"
                                    result = results.get(match_key)
                                    if result:
                                        try:
                                            score_a, score_b = map(int, result.split('-'))
                                            is_team_a = (match[0] == player_team_idx)
                                            player_score = score_a if is_team_a else score_b
                                            opponent_score = score_b if is_team_a else score_a
                                            if player_score > opponent_score:
                                                stats['vittorie'] += 1
                                            elif player_score < opponent_score:
                                                stats['sconfitte'] += 1
                                            else:
                                                stats['pareggi'] += 1
                                            stats['partite_giocate'] += 1
                                        except Exception:
                                            continue
                    # Recupera la variazione ELO per questa giornata
                    elo_history = PlayerEloHistory.query.filter_by(
                        player_id=player_id,
                        tournament_id=tournament_id,
                        tournament_day_id=day.id
                    ).first()
                    if elo_history:
                        stats['elo_history'].append({
                            'data': day.data.strftime('%d.%m.%Y'),
                            'giornata': f"{day.data.strftime('%d.%m.%Y')}",
                            'variazione': f"{elo_history.elo_change:+.2f}",
                            'elo': f"{elo_history.new_elo:.2f}",
                        })

        # TorneOtto45: nuova gestione
        for i, day in enumerate(days_45, 1):
            classifica = day.get_ranking() or []
            if player_id in classifica:
                stats['presenze_totali'] += 1
                if day.stato == "Completata":
                    stats['presenze_completate'] += 1
                    stats['partite_totali'] += 2  # Semifinale e finale/terzo posto
                    stats['partite_giocate'] += 2
                    
                    # Recupero la posizione in classifica
                    posizione = classifica.index(player_id)
                    if posizione < 2:  # Finale
                        stats['vittorie'] += 1
                        stats['sconfitte'] += 1
                    else:  # Terzo posto
                        stats['vittorie'] += 1
                        stats['sconfitte'] += 1

                    # Recupero la variazione ELO
                    elo_history = PlayerEloHistory.query.filter_by(
                        player_id=player_id,
                        tournament_id=tournament_id,
                        tournament_day_id=day.id
                    ).first()
                    
                    if elo_history:
                        stats['elo_history'].append({
                            'data': day.data.strftime('%d.%m.%Y'),
                            'giornata': f"{day.data.strftime('%d.%m.%Y')} {i}ª giornata",
                            'variazione': f"{elo_history.elo_change:+.2f}",
                            'elo': f"{elo_history.new_elo:.2f}",
                            'partite': 2,
                            'vittorie': 1,
                            'pareggi': 0,
                            'sconfitte': 1
                        })

        if stats['partite_giocate'] > 0:
            stats['percentuale_vittorie'] = f"{(stats['vittorie'] / stats['partite_giocate'] * 100):.1f}%"
        else:
            stats['percentuale_vittorie'] = "0.0%"

        return jsonify(stats)
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"API Error: {str(e)}\n{traceback_str}")
        return jsonify({'error': str(e)}), 500 

@tournaments_bp.route('/tornei/giornata/<int:day_id>/pdf')
def export_day_pdf(day_id):
    # Prova prima a recuperare come TorneOtto30Day
    day = TorneOtto30Day.query.get(day_id)
    if day is None:
        # Se non è TorneOtto30Day, prova come TorneOtto45Day
        day = TorneOtto45Day.query.get_or_404(day_id)
        tournament = Tournament.query.get_or_404(day.tournament_id)
        
        # Recupera la configurazione della giornata
        config = day.get_config()
        semifinali = config.get('semifinali', [])
        finali = config.get('finali', {})
        
        # Recupera i dettagli dei giocatori
        player_ids = []
        for semifinale in semifinali:
            player_ids.extend(semifinale['squadra_a'])
            player_ids.extend(semifinale['squadra_b'])
        
        players = Player.query.filter(Player.id.in_(player_ids)).all()
        players_by_id = {player.id: player for player in players}
        
        # Prepara le squadre per il template (lista piatta di 4 squadre)
        teams = []
        squadre_ids = []
        for semifinale in semifinali:
            if semifinale['squadra_a'] not in squadre_ids:
                squadre_ids.append(semifinale['squadra_a'])
            if semifinale['squadra_b'] not in squadre_ids:
                squadre_ids.append(semifinale['squadra_b'])
        for squadra in squadre_ids:
            teams.append([players_by_id[pid] for pid in squadra])
        
        # Renderizza il template per TorneOtto45
        return render_template('tournaments/pdf/completata_torneotto45.html',
                            tournament=tournament,
                            day=day,
                            semifinali=semifinali,
                            finali=finali,
                            players_by_id=players_by_id,
                            teams=teams,
                            print_view=True)
    
    # Gestione per TorneOtto30Day (codice esistente)
    tournament = Tournament.query.get_or_404(day.tournament_id)
    
    # Recupera la configurazione della giornata
    config = day.get_config()
    teams = config.get('teams', [])
    schedule = config.get('schedule', [])
    results = config.get('results', {})
    
    # Recupera i dettagli dei giocatori
    player_ids = [id for team in teams for id in team]
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    player_dict = {p.id: p for p in players}
    
    # Forma le squadre con gli oggetti giocatore (non riordinare teams_objects)
    teams_objects = [[player_dict[p1], player_dict[p2]] for p1, p2 in teams]

    standings = None
    if day.stato == "Completata":
        # Calcola la classifica
        standings = []
        for i in range(len(teams)):
            standings.append({'points': 0, 'diff': 0, 'win': 0, 'draw': 0, 'lose': 0})
        for round_matches in schedule:
            for match in round_matches:
                match_key = f"{match[0]}-{match[1]}"
                result = results.get(match_key)
                if result:
                    try:
                        score_a, score_b = map(int, result.split('-'))
                    except Exception:
                        continue
                    idx_a = match[0] - 1
                    idx_b = match[1] - 1
                    # Aggiorna differenza games
                    standings[idx_a]['diff'] += score_a - score_b
                    standings[idx_b]['diff'] += score_b - score_a
                    # Aggiorna punti e W/D/L
                    if score_a > score_b:
                        standings[idx_a]['points'] += 3
                        standings[idx_a]['win'] += 1
                        standings[idx_b]['lose'] += 1
                    elif score_b > score_a:
                        standings[idx_b]['points'] += 3
                        standings[idx_b]['win'] += 1
                        standings[idx_a]['lose'] += 1
                    else:
                        standings[idx_a]['points'] += 1
                        standings[idx_b]['points'] += 1
                        standings[idx_a]['draw'] += 1
                        standings[idx_b]['draw'] += 1

    # Ordina la classifica per punti e differenza reti, ma non riordinare teams_objects
    if standings:
        standings_with_index = list(enumerate(standings))
        standings_with_index.sort(key=lambda x: (-x[1]['points'], -x[1]['diff']))
        # Crea liste ordinate per la classifica senza modificare teams_objects
        sorted_team_indices = [x[0] for x in standings_with_index]  # Indici originali ordinati
        sorted_standings = [x[1] for x in standings_with_index]     # Statistiche ordinate
        standings = sorted_standings
    else:
        sorted_team_indices = None

    # Renderizza direttamente il template HTML, passando anche sorted_team_indices
    return render_template('tournaments/completata_torneotto30.html',
                          tournament=tournament,
                          day=day,
                          teams=teams_objects,
                          schedule=schedule,
                          results=results,
                          standings=standings,
                          sorted_team_indices=sorted_team_indices,  # ← Nuovo parametro
                          print_view=True)

@tournaments_bp.route('/tornei/<int:tournament_id>/classifica/pdf')
def export_ranking_pdf(tournament_id):
    """Esporta la classifica del torneo in formato HTML stampabile"""
    try:
        # Recupera il torneo
        tournament = Tournament.query.get_or_404(tournament_id)
        
        # Gestisce l'esportazione in base al tipo di torneo
        if tournament.tipo_torneo == 'torneotto45':
            return export_torneotto45_classifica_html(tournament_id)
        elif tournament.tipo_torneo == 'torneotto30':
            # Gestione per tornei TorneOtto30
            # Recupera l'ultima giornata del torneo
            last_day = TorneOtto30Day.query.filter_by(tournament_id=tournament_id).order_by(TorneOtto30Day.data.desc()).first()
            
            # Recupera tutte le giornate del torneo
            days = TorneOtto30Day.query.filter_by(tournament_id=tournament_id).order_by(TorneOtto30Day.data).all()
            
            # Dizionario per tenere traccia delle presenze e dell'ELO di ogni giocatore
            player_stats = {}
            
            # Prima passata: conta il numero totale di giornate completate
            total_days = len(days)
            completed_days = len([day for day in days if day.stato == "Completata"])
            partite_totali = completed_days * 3  # 3 partite per giornata completata
            
            # Seconda passata: analizza le presenze e i risultati
            for day_idx, day in enumerate(days, 1):
                config = day.get_config()
                if not config:
                    continue
                teams = config.get('teams', [])
                if not teams:
                    continue
                results = config.get('results', {})
                schedule = config.get('schedule', [])
                # Trova tutti i player_id presenti nella giornata
                player_ids_in_day = set()
                for team in teams:
                    for player_id in team:
                        player_ids_in_day.add(player_id)
                        if player_id not in player_stats:
                            elo_rating = PlayerTournamentElo.query.filter_by(
                                player_id=player_id,
                                tournament_id=tournament_id
                            ).first()
                            player_stats[player_id] = {
                                'presenze': 0,
                                'elo_rating': elo_rating.elo_rating if elo_rating else 1500.00,
                                'stats': {
                                    # presenze_totali ora è il totale delle giornate completate del torneo
                                    'presenze_totali': completed_days,
                                    'partite_totali': completed_days * 3,  # 3 partite per giornata
                                    'giornate_giocate': completed_days,  # Giornate completate
                                    'presenze_completate': 0,
                                    'partite_giocate': 0,
                                    'vittorie': 0,
                                    'pareggi': 0,
                                    'sconfitte': 0,
                                    'giornate': []  # Lista per tenere traccia delle variazioni ELO per giornata
                                }
                            }
                # Incrementa presenze solo se la giornata è completata
                if day.stato == "Completata":
                    for player_id in player_ids_in_day:
                        player_stats[player_id]['stats']['presenze_completate'] += 1
                        # Trova la squadra del giocatore
                        player_team_idx = None
                        for i, t in enumerate(teams):
                            if player_id in t:
                                player_team_idx = i + 1
                                break
                        if player_team_idx is not None:
                            for round_matches in schedule:
                                for match in round_matches:
                                    if player_team_idx in match:
                                        match_key = f"{match[0]}-{match[1]}"
                                        result = results.get(match_key)
                                        if result:
                                            try:
                                                score_a, score_b = map(int, result.split('-'))
                                                is_team_a = (match[0] == player_team_idx)
                                                player_score = score_a if is_team_a else score_b
                                                opponent_score = score_b if is_team_a else score_a
                                                if player_score > opponent_score:
                                                    player_stats[player_id]['stats']['vittorie'] += 1
                                                elif player_score < opponent_score:
                                                    player_stats[player_id]['stats']['sconfitte'] += 1
                                                else:
                                                    player_stats[player_id]['stats']['pareggi'] += 1
                                                player_stats[player_id]['stats']['partite_giocate'] += 1
                                            except Exception:
                                                continue
                        # Recupera la variazione ELO per questa giornata
                        elo_history = PlayerEloHistory.query.filter_by(
                            player_id=player_id,
                            tournament_id=tournament_id,
                            tournament_day_id=day.id
                        ).first()
                        if elo_history:
                            player_stats[player_id]['stats']['giornate'].append({
                                'numero': day_idx,
                                'variazione': elo_history.elo_change
                            })
            
            # Recupera i dettagli dei giocatori
            players = Player.query.filter(Player.id.in_(player_stats.keys())).all()
            
            # Combina i dati dei giocatori con le statistiche
            players_with_stats = []
            for player in players:
                stats = player_stats[player.id]
                players_with_stats.append({
                    'id': player.id,
                    'nome': player.nome,
                    'cognome': player.cognome,
                    'elo_rating': stats['elo_rating'],
                    'presenze': stats['presenze'],
                    'stats': stats['stats']
                })
            
            # Ordina i giocatori per ELO decrescente
            players_with_stats.sort(key=lambda x: x['elo_rating'], reverse=True)
            
            # Renderizza direttamente il template HTML
            return render_template('tournaments/pdf/classifica_torneotto30.html',
                                tournament=tournament,
                                players=players_with_stats,
                                now=datetime.now(),
                                last_day=last_day,
                                print_view=True,  # Aggiungo un flag per la vista stampa
                                giornate_giocate=completed_days,  # Aggiungo le variabili per il template
                                partite_totali=partite_totali)  # Aggiungo le variabili per il template
        else:
            # Gestione per tornei generici (non TorneOtto30/45)
            flash('Tipo di torneo non supportato', 'error')
            return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
            
    except Exception as e:
        current_app.logger.error(f"Errore durante la generazione della vista: {str(e)}")
        flash('Errore durante la generazione della vista', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/classifica/html')
def export_torneotto45_classifica_html(tournament_id):
    """Esporta la classifica del torneo TorneOtto45 in formato HTML stampabile"""
    try:
        # Recupera il torneo
        tournament = Tournament.query.get_or_404(tournament_id)
        if tournament.tipo_torneo != 'torneotto45':
            flash('Questa funzione è disponibile solo per i tornei TorneOtto45', 'error')
            return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
        
        # Recupera l'ultima giornata
        last_day = TorneOtto45Day.query.filter_by(tournament_id=tournament_id).order_by(TorneOtto45Day.data.desc()).first()
        
        # Recupera tutti i giocatori che hanno partecipato al torneo
        players_with_elo = PlayerTournamentElo.query.filter_by(tournament_id=tournament_id).all()
        player_ids = [p.player_id for p in players_with_elo]
        players = Player.query.filter(Player.id.in_(player_ids)).all()
        
        # Prepara i dati per il template
        players_data = []
        for player in players:
            # Recupera l'ELO del torneo
            tournament_elo = next((p.elo_rating for p in players_with_elo if p.player_id == player.id), 1500.0)
            
            # Recupera la storia ELO
            elo_history = PlayerEloHistory.query.filter_by(
                player_id=player.id,
                tournament_id=tournament_id
            ).order_by(PlayerEloHistory.tournament_day_id.asc()).all()
            
            # Calcola le statistiche
            stats = {
                'presenze_totali': len(tournament.tournament_days),
                'partite_totali': 0,
                'vittorie': 0,
                'pareggi': 0,
                'sconfitte': 0,
                'partite_giocate': 0,
                'giornate': []
            }
            
            # Analizza ogni giornata
            for day in tournament.tournament_days:
                if isinstance(day, TorneOtto45Day):
                    config = day.get_config()
                    players_day = config.get('players', [])
                    
                    # Controlla se il giocatore ha partecipato
                    if player.id in players_day:
                        stats['partite_giocate'] += 1
                        
                        # Analizza semifinali e finali
                        semifinals = config.get('semifinali', [])
                        finals = config.get('finali', {})
                        
                        # Conta le partite e i risultati
                        for semifinal in semifinals:
                            if player.id in semifinal['squadra_a'] or player.id in semifinal['squadra_b']:
                                stats['partite_totali'] += 1
                                if semifinal.get('risultato'):
                                    if player.id in semifinal['squadra_a']:
                                        if semifinal['risultato']['squadra_a'] > semifinal['risultato']['squadra_b']:
                                            stats['vittorie'] += 1
                                        elif semifinal['risultato']['squadra_a'] == semifinal['risultato']['squadra_b']:
                                            stats['pareggi'] += 1
                                        else:
                                            stats['sconfitte'] += 1
                                    else:
                                        if semifinal['risultato']['squadra_b'] > semifinal['risultato']['squadra_a']:
                                            stats['vittorie'] += 1
                                        elif semifinal['risultato']['squadra_b'] == semifinal['risultato']['squadra_a']:
                                            stats['pareggi'] += 1
                                        else:
                                            stats['sconfitte'] += 1
                        
                        for final_type in ['primo_posto', 'terzo_posto']:
                            if finals.get(final_type):
                                final = finals[final_type]
                                if player.id in final['squadra_a'] or player.id in final['squadra_b']:
                                    stats['partite_totali'] += 1
                                    if final.get('risultato'):
                                        if player.id in final['squadra_a']:
                                            if final['risultato']['squadra_a'] > final['risultato']['squadra_b']:
                                                stats['vittorie'] += 1
                                            elif final['risultato']['squadra_a'] == final['risultato']['squadra_b']:
                                                stats['pareggi'] += 1
                                            else:
                                                stats['sconfitte'] += 1
                                        else:
                                            if final['risultato']['squadra_b'] > final['risultato']['squadra_a']:
                                                stats['vittorie'] += 1
                                            elif final['risultato']['squadra_b'] == final['risultato']['squadra_a']:
                                                stats['pareggi'] += 1
                                            else:
                                                stats['sconfitte'] += 1
                    
                    # Aggiungi la variazione ELO per questa giornata
                    day_elo = next((h for h in elo_history if h.tournament_day_id == day.id), None)
                    if day_elo:
                        stats['giornate'].append({
                            'numero': len(stats['giornate']) + 1,
                            'variazione': day_elo.elo_change
                        })
            
            players_data.append({
                'cognome': player.cognome,
                'nome': player.nome,
                'elo_rating': tournament_elo,
                'stats': stats
            })
        
        # Ordina i giocatori per ELO
        players_data.sort(key=lambda x: x['elo_rating'], reverse=True)
        
        # Prepara il context per il template
        context = {
            'tournament': tournament,
            'players': players_data,
            'last_day': last_day,
            'now': datetime.now(),
            'print_view': True  # Aggiungo un flag per la vista stampa
        }
        
        # Renderizza direttamente il template HTML
        return render_template('tournaments/pdf/classifica_torneotto45.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Errore durante la generazione della vista: {str(e)}")
        flash('Errore durante la generazione della vista', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))

def get_player_stats_data(tournament_id, player_id):
    """Recupera le statistiche dettagliate di un giocatore per un torneo."""
    stats = {
        'presenze_totali': 0,
        'partite_totali': 0,
        'presenze_completate': 0,
        'partite_giocate': 0,
        'vittorie': 0,
        'pareggi': 0,
        'sconfitte': 0,
        'ultima_variazione': None
    }
    
    # Recupera tutte le giornate del torneo
    tournament_days = TorneOtto30Day.query.filter_by(tournament_id=tournament_id).order_by(TorneOtto30Day.data).all()
    
    # Lista delle giornate in cui il giocatore è presente
    giornate_presenti = []
    
    # Conta le presenze totali
    for day in tournament_days:
        config = day.get_config()
        if not config:
            continue
            
        teams = config.get('teams', [])
        if not teams:
            continue
            
        is_present = False
        for team in teams:
            if player_id in team:
                is_present = True
                break
                
        if is_present:
            giornate_presenti.append(day)
            stats['presenze_totali'] += 1
            stats['partite_totali'] += 3
    
    # Processa solo le giornate dove il giocatore è presente
    for day in giornate_presenti:
        config = day.get_config()
        teams = config.get('teams', [])
        results = config.get('results', {})
        schedule = config.get('schedule', [])
        if not schedule:
            continue
        
        # Trova la squadra del giocatore
        player_team_idx = None
        for i, team in enumerate(teams):
            if player_id in team:
                player_team_idx = i + 1
                break
        
        if player_team_idx is None:
            continue
        
        # Se la giornata è completata, incrementa il contatore delle presenze completate
        if day.stato == "Completata":
            stats['presenze_completate'] += 1
            
            # Conta le partite effettivamente giocate
            for round_matches in schedule:
                for match in round_matches:
                    if player_team_idx in match:
                        match_key = f"{match[0]}-{match[1]}"
                        result = results.get(match_key)
                        
                        if result:
                            try:
                                score_a, score_b = map(int, result.split('-'))
                                
                                # Determina se il giocatore è nella squadra A o B
                                is_team_a = (match[0] == player_team_idx)
                                player_score = score_a if is_team_a else score_b
                                opponent_score = score_b if is_team_a else score_a
                                
                                if player_score > opponent_score:
                                    stats['vittorie'] += 1
                                elif player_score < opponent_score:
                                    stats['sconfitte'] += 1
                                else:
                                    stats['pareggi'] += 1
                                    
                                stats['partite_giocate'] += 1
                            except Exception:
                                continue
            
            # Recupera la variazione ELO per questa giornata
            elo_history = PlayerEloHistory.query.filter_by(
                player_id=player_id,
                tournament_id=tournament_id,
                tournament_day_id=day.id
            ).first()
            
            if elo_history:
                stats['ultima_variazione'] = elo_history.elo_change
    
    return stats 

# ROUTE PER GESTIONE TORNEOTTO 45'
@tournaments_bp.route('/tornei/<int:tournament_id>/nuova-giornata/torneotto45', methods=['GET', 'POST'])
def new_torneotto45_day(tournament_id):
    """Crea una nuova giornata per un torneo TorneOtto 45"""
    # Recupera il torneo
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Verifica che il torneo sia di tipo corretto
    if tournament.tipo_torneo != 'torneotto45':
        flash('Tipo di torneo non valido!', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    # Recupera tutti i giocatori disponibili
    players = Player.query.order_by(Player.cognome).all()
    
    data_oggi = date.today()
    
    return render_template('tournaments/torneotto45/day_setup.html', 
                          tournament_id=tournament_id,
                          tournament=tournament,
                          players=players,
                          data_oggi=data_oggi)

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/torneotto45/salva', methods=['POST'])
def save_torneotto45_day(tournament_id):
    """Salva una nuova giornata TorneOtto 45 con le semifinali generate casualmente"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Ottieni gli ID dei giocatori selezionati
    player_ids = request.form.getlist('player_ids')
    
    # Verifica che ci siano esattamente 8 giocatori
    if len(player_ids) != 8:
        flash('Sono necessari esattamente 8 giocatori per una giornata TorneOtto 45', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    
    # Converti gli ID da stringhe a interi
    player_ids = [int(pid) for pid in player_ids]
    
    # Crea le semifinali
    semifinali = [
        {
            'squadra_a': player_ids[0:2],
            'squadra_b': player_ids[2:4],
            'risultato': None
        },
        {
            'squadra_a': player_ids[4:6],
            'squadra_b': player_ids[6:8],
            'risultato': None
        }
    ]
    
    # Configurazione delle finali (vuote inizialmente)
    finali = {
        'primo_posto': {'squadra_a': None, 'squadra_b': None, 'risultato': None},
        'terzo_posto': {'squadra_a': None, 'squadra_b': None, 'risultato': None}
    }
    
    # Crea la nuova giornata
    day = TorneOtto45Day(
        tournament_id=tournament_id,
        data=datetime.strptime(request.form.get('data'), '%Y-%m-%d').date(),
        stato="Risultati da inserire",
        created_at=datetime.now(),
        tipo_giornata='torneotto45'
    )
    
    # Imposta la configurazione
    day.set_players(player_ids)
    day.set_semifinals(semifinali)
    day.set_finals(finali)
    
    try:
        db.session.add(day)
        db.session.commit()
        flash('Giornata TorneOtto 45 creata con successo!', 'success')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la creazione della giornata: {str(e)}', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/<int:day_id>/risultati-torneotto45', methods=['GET'])
def view_torneotto45_day(tournament_id, day_id):
    """Visualizza la pagina per l'inserimento dei risultati di una giornata TorneOtto 45"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = TorneOtto45Day.query.get_or_404(day_id)
    
    if day.tournament_id != tournament_id:
        flash('Giornata non valida per questo torneo!', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    # Ottieni i dati della giornata
    players_ids = day.get_players()
    semifinali = day.get_semifinals()
    finali = day.get_finals()
    classifica = day.get_ranking()
    
    # Verifica se le semifinali sono state completate (hanno risultati)
    semifinali_completate = all(semifinale.get('risultato') is not None for semifinale in semifinali)
    
    # Verifica se le finali sono state completate
    finali_completate = finali.get('primo_posto', {}).get('risultato') is not None and \
                       finali.get('terzo_posto', {}).get('risultato') is not None
    
    # Ottieni le informazioni dei giocatori per la visualizzazione
    players = Player.query.filter(Player.id.in_(players_ids)).all()
    players_by_id = {player.id: player for player in players}
    
    return render_template('tournaments/torneotto45/day_results.html',
                          tournament=tournament,
                          day=day,
                          semifinali=semifinali,
                          finali=finali,
                          classifica=classifica,
                          players_by_id=players_by_id,
                          semifinali_completate=semifinali_completate,
                          finali_completate=finali_completate)

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/<int:day_id>/semifinali-torneotto45', methods=['POST'])
def save_torneotto45_semifinals(tournament_id, day_id):
    """Salva i risultati delle semifinali e prepara le finali"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = TorneOtto45Day.query.get_or_404(day_id)
    
    if day.tournament_id != tournament_id:
        flash('Giornata non valida per questo torneo!', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    # Ottieni le semifinali esistenti
    semifinali = day.get_semifinals()
    
    # Aggiorna i risultati delle semifinali
    for i in range(2):
        risultato_a = int(request.form.get(f'risultato_semifinale_{i+1}_a'))
        risultato_b = int(request.form.get(f'risultato_semifinale_{i+1}_b'))
        
        semifinali[i]['risultato'] = {
            'squadra_a': risultato_a,
            'squadra_b': risultato_b
        }
    
    # Determina i vincitori e i perdenti
    vincitori = []
    perdenti = []
    
    for semifinale in semifinali:
        risultato = semifinale['risultato']
        if risultato['squadra_a'] > risultato['squadra_b']:
            vincitori.append(semifinale['squadra_a'])
            perdenti.append(semifinale['squadra_b'])
        else:
            vincitori.append(semifinale['squadra_b'])
            perdenti.append(semifinale['squadra_a'])
    
    # Configura le finali
    finali = day.get_finals()
    finali['primo_posto']['squadra_a'] = vincitori[0]
    finali['primo_posto']['squadra_b'] = vincitori[1]
    finali['terzo_posto']['squadra_a'] = perdenti[0]
    finali['terzo_posto']['squadra_b'] = perdenti[1]
    
    # Salva i dati aggiornati
    day.set_semifinals(semifinali)
    day.set_finals(finali)
    
    try:
        db.session.commit()
        flash('Risultati semifinali salvati con successo. Ora puoi inserire i risultati delle finali.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il salvataggio dei risultati: {str(e)}', 'error')
    
    return redirect(url_for('tournaments.view_torneotto45_day', tournament_id=tournament_id, day_id=day_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/<int:day_id>/finali-torneotto45', methods=['POST'])
def save_torneotto45_finals(tournament_id, day_id):
    """Salva i risultati delle finali e genera la classifica finale"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = TorneOtto45Day.query.get_or_404(day_id)
    
    if day.tournament_id != tournament_id:
        flash('Giornata non valida per questo torneo!', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    # Ottieni le finali esistenti
    finali = day.get_finals()
    
    # Aggiorna i risultati delle finali
    primo_a = int(request.form.get('risultato_finale_1_a'))
    primo_b = int(request.form.get('risultato_finale_1_b'))
    terzo_a = int(request.form.get('risultato_finale_3_a'))
    terzo_b = int(request.form.get('risultato_finale_3_b'))
    
    finali['primo_posto']['risultato'] = {
        'squadra_a': primo_a,
        'squadra_b': primo_b
    }
    
    finali['terzo_posto']['risultato'] = {
        'squadra_a': terzo_a,
        'squadra_b': terzo_b
    }
    
    # Determina la classifica (i giocatori in ordine di posizione)
    classifica = []
    
    # 1° e 2° posto
    if primo_a > primo_b:
        classifica.extend(finali['primo_posto']['squadra_a'])  # 1° posto
        classifica.extend(finali['primo_posto']['squadra_b'])  # 2° posto
    else:
        classifica.extend(finali['primo_posto']['squadra_b'])  # 1° posto
        classifica.extend(finali['primo_posto']['squadra_a'])  # 2° posto
    
    # 3° e 4° posto
    if terzo_a > terzo_b:
        classifica.extend(finali['terzo_posto']['squadra_a'])  # 3° posto
        classifica.extend(finali['terzo_posto']['squadra_b'])  # 4° posto
    else:
        classifica.extend(finali['terzo_posto']['squadra_b'])  # 3° posto
        classifica.extend(finali['terzo_posto']['squadra_a'])  # 4° posto
    
    # Salva i dati aggiornati
    day.set_finals(finali)
    day.set_ranking(classifica)
    
    try:
        db.session.commit()
        flash('Risultati finali salvati con successo. Ora puoi chiudere la giornata.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il salvataggio dei risultati: {str(e)}', 'error')
    
    return redirect(url_for('tournaments.view_torneotto45_day', tournament_id=tournament_id, day_id=day_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/<int:day_id>/chiudi-torneotto45', methods=['GET', 'POST'])
def close_torneotto45_day(tournament_id, day_id):
    """Chiude la giornata e calcola gli ELO"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = TorneOtto45Day.query.get_or_404(day_id)
    
    if day.tournament_id != tournament_id:
        flash('Giornata non valida per questo torneo!', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    # Ottieni la classifica
    classifica = day.get_ranking()
    
    if not classifica:
        flash('Devi prima completare le finali e generare la classifica!', 'error')
        return redirect(url_for('tournaments.view_torneotto45_day', tournament_id=tournament_id, day_id=day_id))
    
    # Aggiorna lo stato della giornata
    day.stato = "Completata"
    
    try:
        db.session.commit()
        
        # Calcola l'ELO
        calculate_torneotto45_elo(tournament_id, day_id)
        
        flash('Giornata completata con successo! Gli ELO sono stati aggiornati.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la chiusura della giornata: {str(e)}', 'error')
    
    return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/<int:day_id>/elimina-torneotto45', methods=['POST'])
def delete_torneotto45_day(tournament_id, day_id):
    """Elimina una giornata TorneOtto 45 e resetta l'ELO"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = TorneOtto45Day.query.get_or_404(day_id)
    
    if day.tournament_id != tournament_id:
        flash('Giornata non valida per questo torneo!', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    # Se la giornata è stata completata, resetta l'ELO
    if day.stato == "Completata":
        # Elimina lo storico ELO associato a questa giornata
        elo_history = PlayerEloHistory.query.filter_by(tournament_day_id=day_id).all()
        for history in elo_history:
            # Ripristina l'ELO precedente
            player_elo = PlayerTournamentElo.query.filter_by(
                player_id=history.player_id,
                tournament_id=tournament_id
            ).first()
            
            if player_elo:
                player_elo.elo_rating = history.old_elo
            
            # Elimina la voce di storico
            db.session.delete(history)
    
    # Elimina la giornata
    db.session.delete(day)
    
    try:
        db.session.commit()
        flash('Giornata eliminata con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione della giornata: {str(e)}', 'error')
    
    return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))

# Funzione di supporto per il calcolo dell'ELO
def calculate_torneotto45_elo(tournament_id, day_id):
    """
    Calcola l'ELO per una giornata TorneOtto 45 usando K-fattori diversi per semifinali e finali
    
    Args:
        tournament_id: ID del torneo
        day_id: ID della giornata
    """
    # Recupera la giornata dal database
    day = TorneOtto45Day.query.get_or_404(day_id)
    tournament = Tournament.query.get_or_404(tournament_id)
    
    current_app.logger.info(f"Calcolo ELO per giornata {day_id} del torneo {tournament_id}")
    
    # Estrai la classifica e la configurazione
    classifica = day.get_ranking()
    config = day.get_config()
    if not classifica or not config:
        current_app.logger.error(f"Classifica o configurazione mancante per giornata {day_id}")
        return
    
    current_app.logger.info(f"Classifica: {classifica}")
    current_app.logger.info(f"Config: {config}")
    
    # Recupera i risultati delle partite
    semifinali = config.get('semifinali', [])
    finali = config.get('finali', {})
    
    if not semifinali or not finali:
        current_app.logger.error(f"Semifinali o finali mancanti per giornata {day_id}")
        return
    
    # Per ogni giocatore nella classifica, recupera l'ELO attuale
    player_elos = {}
    for player_id in classifica:
        current_elo = get_player_current_elo(player_id, tournament_id, day_id)
        player_elos[player_id] = current_elo
        current_app.logger.info(f"Giocatore {player_id}: ELO attuale = {current_elo}")
    
    # Dizionario per tenere traccia delle variazioni ELO per ogni giocatore
    player_changes = {player_id: [] for player_id in classifica}
    
    # 1. Calcola le variazioni ELO per le semifinali (K=40)
    current_app.logger.info("Calcolo variazioni ELO per semifinali")
    for semifinale in semifinali:
        squadra_a = semifinale.get('squadra_a', [])
        squadra_b = semifinale.get('squadra_b', [])
        risultato = semifinale.get('risultato', {})
        
        if not risultato or not squadra_a or not squadra_b:
            current_app.logger.warning(f"Risultato semifinale mancante o squadre incomplete: {semifinale}")
            continue
            
        score_a = risultato.get('squadra_a', 0)
        score_b = risultato.get('squadra_b', 0)
        
        current_app.logger.info(f"Semifinale: Squadra A {squadra_a} vs Squadra B {squadra_b} - Risultato: {score_a}-{score_b}")
        
        # Determina il risultato (1 vittoria, 0.5 pareggio, 0 sconfitta)
        if score_a > score_b:
            match_result = 1
        elif score_a < score_b:
            match_result = 0
        else:
            match_result = 0.5
        
        # Calcola l'ELO totale delle squadre
        team1_elo = sum(player_elos[p] for p in squadra_a)
        team2_elo = sum(player_elos[p] for p in squadra_b)
        
        current_app.logger.info(f"ELO Squadra A: {team1_elo}, ELO Squadra B: {team2_elo}")
        
        # Calcola le variazioni ELO con K=40
        team1_change, team2_change = calculate_match_elo_change(team1_elo, team2_elo, match_result, k_factor=40)
        
        current_app.logger.info(f"Variazioni ELO semifinale: Squadra A {team1_change}, Squadra B {team2_change}")
        
        # Distribuisci le variazioni tra i giocatori della squadra
        for player_id in squadra_a:
            player_changes[player_id].append(team1_change)
        for player_id in squadra_b:
            player_changes[player_id].append(team2_change)
    
    # 2. Calcola le variazioni ELO per le finali (K=32)
    current_app.logger.info("Calcolo variazioni ELO per finali")
    for match_type in ['primo_posto', 'terzo_posto']:
        finale = finali.get(match_type, {})
        squadra_a = finale.get('squadra_a', [])
        squadra_b = finale.get('squadra_b', [])
        risultato = finale.get('risultato', {})
        
        if not risultato or not squadra_a or not squadra_b:
            current_app.logger.warning(f"Risultato finale {match_type} mancante o squadre incomplete: {finale}")
            continue
            
        score_a = risultato.get('squadra_a', 0)
        score_b = risultato.get('squadra_b', 0)
        
        current_app.logger.info(f"Finale {match_type}: Squadra A {squadra_a} vs Squadra B {squadra_b} - Risultato: {score_a}-{score_b}")
        
        # Determina il risultato (1 vittoria, 0.5 pareggio, 0 sconfitta)
        if score_a > score_b:
            match_result = 1
        elif score_a < score_b:
            match_result = 0
        else:
            match_result = 0.5
        
        # Calcola l'ELO totale delle squadre
        team1_elo = sum(player_elos[p] for p in squadra_a)
        team2_elo = sum(player_elos[p] for p in squadra_b)
        
        current_app.logger.info(f"ELO Squadra A: {team1_elo}, ELO Squadra B: {team2_elo}")
        
        # K=32 per tutte le finali
        team1_change, team2_change = calculate_match_elo_change(team1_elo, team2_elo, match_result, k_factor=32)
        
        current_app.logger.info(f"Variazioni ELO finale {match_type}: Squadra A {team1_change}, Squadra B {team2_change}")
        
        # Distribuisci le variazioni tra i giocatori della squadra
        for player_id in squadra_a:
            player_changes[player_id].append(team1_change)
        for player_id in squadra_b:
            player_changes[player_id].append(team2_change)
    
    # 3. Calcola la somma delle variazioni ELO per ogni giocatore
    current_app.logger.info("Calcolo somma variazioni ELO")
    final_changes = {}
    for player_id, changes in player_changes.items():
        if changes:  # Se il giocatore ha partecipato a delle partite
            final_changes[player_id] = round(sum(changes), 2)
            current_app.logger.info(f"Giocatore {player_id}: variazioni {changes}, somma {final_changes[player_id]}")
        else:
            final_changes[player_id] = 0
            current_app.logger.warning(f"Giocatore {player_id}: nessuna variazione ELO")
    
    # 4. Aggiorna gli ELO nel database e registra la storia
    current_app.logger.info("Aggiornamento ELO nel database")
    for player_id, elo_change in final_changes.items():
        old_elo = get_player_current_elo(player_id, tournament_id, day_id)
        new_elo = old_elo + elo_change
        
        current_app.logger.info(f"Giocatore {player_id}: ELO {old_elo} -> {new_elo} (variazione {elo_change})")
        
        # Aggiorna o crea il record ELO del giocatore
        player_elo = PlayerTournamentElo.query.filter_by(
            player_id=player_id,
            tournament_id=tournament_id
        ).first()
        
        if not player_elo:
            player_elo = PlayerTournamentElo(
                player_id=player_id,
                tournament_id=tournament_id,
                elo_rating=old_elo
            )
            db.session.add(player_elo)
        
        player_elo.elo_rating = new_elo
        
        # Elimina eventuali record duplicati per questa giornata
        PlayerEloHistory.query.filter_by(
            player_id=player_id,
            tournament_id=tournament_id,
            tournament_day_id=day_id
        ).delete()
        
        # Registra la modifica dell'ELO
        elo_history = PlayerEloHistory(
            player_id=player_id,
            tournament_id=tournament_id,
            tournament_day_id=day_id,
            old_elo=old_elo,
            new_elo=new_elo,
            elo_change=elo_change
        )
        db.session.add(elo_history)
    
    # Commit delle modifiche al database
    try:
        db.session.commit()
        current_app.logger.info("Aggiornamento ELO completato con successo")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore durante l'aggiornamento ELO: {str(e)}")
        raise

def calculate_match_elo_change(team1_elo, team2_elo, match_result, k_factor=32):
    """
    Calcola la variazione ELO per una partita
    
    Args:
        team1_elo: ELO totale della squadra 1
        team2_elo: ELO totale della squadra 2
        match_result: 1 per vittoria, 0.5 per pareggio, 0 per sconfitta
        k_factor: Fattore K per il calcolo (default 32)
    
    Returns:
        tuple: (variazione squadra 1, variazione squadra 2)
    """
    # Calcola la probabilità attesa per la squadra 1
    expected_score = 1 / (1 + 10 ** ((team2_elo - team1_elo) / 400))
    
    # Calcola la variazione ELO
    elo_change = k_factor * (match_result - expected_score)
    
    return round(elo_change, 2), round(-elo_change, 2)

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/torneotto45/players', methods=['POST'])
def torneotto45_players(tournament_id):
    """Riceve i giocatori selezionati e reindirizza alla pagina di scelta del metodo"""
    # Recupera i dati dal form
    date_str = request.form.get('data')
    selected_players = request.form.get('selected_players')
    tournament_id = request.form.get('tournament_id')
    
    # Validazione
    if not all([date_str, selected_players, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    
    # Verifiche aggiuntive
    player_ids = selected_players.split(',')
    if len(player_ids) != 8:
        flash('Devi selezionare esattamente 8 giocatori', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    
    # Reindirizza alla pagina di scelta del metodo
    return redirect(url_for('tournaments.torneotto45_choose_pairing_method', 
                          date=date_str, 
                          players=selected_players,
                          tournament_id=tournament_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/torneotto45/choose-method', methods=['GET'])
def torneotto45_choose_pairing_method(tournament_id):
    """Mostra la pagina di scelta del metodo di formazione coppie"""
    date = request.args.get('date')
    players = request.args.get('players')
    
    # Validazione
    if not all([date, players, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    
    # Recupera i dettagli del torneo
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Verifica che il torneo sia di tipo torneotto45
    if tournament.tipo_torneo != 'torneotto45':
        flash('Tipo di torneo non valido', 'error')
        return redirect(url_for('tournaments.tournaments_list'))
    
    return render_template('tournaments/torneotto45/choose_pairing_method.html',
                          tournament=tournament,
                          date=date,
                          players=players)

# TorneOtto45 - pairing random
@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/torneotto45/random', methods=['POST'])
def torneotto45_random_pairing(tournament_id):
    date_str = request.form.get('date')
    players_str = request.form.get('players')
    if not all([date_str, players_str, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    player_ids = players_str.split(',')
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    tournament = Tournament.query.get_or_404(tournament_id)
    assegna_tournament_elo(players, tournament_id)
    return render_template('tournaments/torneotto45/pairing_animation.html',
                         tournament=tournament,
                         date=date_str,
                         players=players,
                         method="random",
                         method_title="Sorteggio Totalmente Casuale",
                         method_description="Le squadre vengono formate in modo completamente casuale",
                         tournament_id=tournament_id,
                         form_action=url_for('tournaments.process_torneotto45_random_pairing', tournament_id=tournament_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/torneotto45/random/process', methods=['POST'])
def process_torneotto45_random_pairing(tournament_id):
    """Processa il risultato del sorteggio casuale per TorneOtto45"""
    date_str = request.form.get('date')
    tournament_id = request.form.get('tournament_id')
    pairs_json = request.form.get('pairs')
    
    # Validazione
    if not all([date_str, tournament_id, pairs_json]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    
    # Decodifica le coppie
    pairs = json.loads(pairs_json)
    player_ids = [id for pair in pairs for id in pair]
    
    # Recupera i dettagli dei giocatori
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    player_dict = {p.id: p for p in players}
    
    # Forma le squadre
    teams = [[player_dict[pair[0]], player_dict[pair[1]]] for pair in pairs]
    
    # Recupera l'ELO del torneo per ogni giocatore
    for player in players:
        tournament_elo = PlayerTournamentElo.query.filter_by(
            player_id=player.id,
                        tournament_id=tournament_id
                    ).first()
        player.tournament_elo = tournament_elo.elo_rating if tournament_elo else 1500.0
    
    # Converte i dati in JSON per il passaggio alla pagina di riepilogo
    teams_json = json.dumps([[p.id for p in team] for team in teams])
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    return render_template('tournaments/torneotto45/pairing_summary.html',
                         tournament=tournament,
                         date=date_str,
                         teams=teams,
                         teams_json=teams_json,
                         all_players=players)

# TorneOtto45 - pairing elo
@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/torneotto45/elo', methods=['POST'])
def torneotto45_elo_pairing(tournament_id):
    date_str = request.form.get('date')
    players_str = request.form.get('players')
    if not all([date_str, players_str, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    player_ids = players_str.split(',')
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    tournament = Tournament.query.get_or_404(tournament_id)
    assegna_tournament_elo(players, tournament_id)
    return render_template('tournaments/torneotto45/pairing_animation.html',
                         tournament=tournament,
                         date=date_str,
                         players=players,
                         method="elo",
                         method_title="Sorteggio per Punti e Posizione",
                         method_description="Le squadre vengono formate considerando i punti ELO e la posizione preferita dei giocatori",
                         tournament_id=tournament_id,
                         form_action=url_for('tournaments.process_torneotto45_elo_pairing', tournament_id=tournament_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/torneotto45/elo/process', methods=['POST'])
def process_torneotto45_elo_pairing(tournament_id):
    """Processa il risultato del sorteggio basato su ELO per TorneOtto45"""
    date_str = request.form.get('date')
    tournament_id = request.form.get('tournament_id')
    pairs_json = request.form.get('pairs')
    
    # Validazione
    if not all([date_str, tournament_id, pairs_json]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    
    # Decodifica le coppie
    pairs = json.loads(pairs_json)
    player_ids = [id for pair in pairs for id in pair]
    
    # Recupera i dettagli dei giocatori
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    player_dict = {p.id: p for p in players}
    
    # Forma le squadre
    teams = [[player_dict[pair[0]], player_dict[pair[1]]] for pair in pairs]
    
    # Recupera l'ELO del torneo per ogni giocatore
    for player in players:
        tournament_elo = PlayerTournamentElo.query.filter_by(
            player_id=player.id,
                        tournament_id=tournament_id
                    ).first()
        player.tournament_elo = tournament_elo.elo_rating if tournament_elo else 1500.0
    
    # Converte i dati in JSON per il passaggio alla pagina di riepilogo
    teams_json = json.dumps([[p.id for p in team] for team in teams])
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    return render_template('tournaments/torneotto45/pairing_summary.html',
                         tournament=tournament,
                         date=date_str,
                         teams=teams,
                         teams_json=teams_json,
                         all_players=players)

# TorneOtto45 - pairing seeded
@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/torneotto45/seeded', methods=['GET', 'POST'])
def torneotto45_seeded_pairing(tournament_id):
    if request.method == 'POST':
        date_str = request.form.get('date')
        players_str = request.form.get('players')
        seeded_players = request.form.getlist('seeded_players')
        if not all([date_str, players_str, tournament_id]) or not seeded_players:
            flash('Dati mancanti o teste di serie non selezionate', 'error')
            return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
        player_ids = players_str.split(',')
        players = Player.query.filter(Player.id.in_(player_ids)).all()
        tournament = Tournament.query.get_or_404(tournament_id)
        assegna_tournament_elo(players, tournament_id)
        return render_template('tournaments/torneotto45/pairing_animation.html',
                             tournament=tournament,
                             date=date_str,
                             players=players,
                             method="seeded",
                             method_title="Sorteggio con Teste di Serie",
                             method_description="Le squadre vengono formate assicurando che ogni testa di serie sia in una coppia diversa",
                             tournament_id=tournament_id,
                             seeded_players=seeded_players,
                             form_action=url_for('tournaments.process_torneotto45_elo_pairing', tournament_id=tournament_id))
    # GET
    date_str = request.args.get('date')
    players_str = request.args.get('players')
    if not all([date_str, players_str, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    player_ids = players_str.split(',')
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    tournament = Tournament.query.get_or_404(tournament_id)
    assegna_tournament_elo(players, tournament_id)
    players.sort(key=lambda x: x.tournament_elo, reverse=True)
    return render_template('tournaments/torneotto45/seeded_pairing.html',
                         tournament=tournament,
                         date=date_str,
                         players=players_str,
                         tournament_id=tournament_id,
                         all_players=players)

# TorneOtto45 - pairing manual
@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/torneotto45/manual', methods=['GET', 'POST'])
def torneotto45_manual_pairing(tournament_id):
    if request.method == 'POST':
        date_str = request.form.get('date')
        teams = []
        for i in range(1, 5):
            player1_id = int(request.form.get(f'team{i}_player1'))
            player2_id = int(request.form.get(f'team{i}_player2'))
            teams.append([player1_id, player2_id])
        all_players_ids = [p for team in teams for p in team]
        if len(all_players_ids) != len(set(all_players_ids)) or len(all_players_ids) != 8:
            flash('Ogni giocatore deve essere selezionato esattamente una volta', 'error')
            return redirect(url_for('tournaments.torneotto45_manual_pairing', 
                                  date=date_str, 
                                  players=','.join(str(p) for p in all_players_ids),
                                  tournament_id=tournament_id))
        player_objects = Player.query.filter(Player.id.in_(all_players_ids)).all()
        assegna_tournament_elo(player_objects, tournament_id)
        player_dict = {p.id: p for p in player_objects}
        teams_objects = [[player_dict[p1], player_dict[p2]] for p1, p2 in teams]
        teams_json = json.dumps(teams)
        tournament = Tournament.query.get_or_404(tournament_id)
        return render_template('tournaments/torneotto45/pairing_summary.html',
                             tournament=tournament,
                             date=date_str,
                             teams=teams_objects,
                             teams_json=teams_json,
                             all_players=player_objects)
    # GET
    date_str = request.args.get('date')
    players_str = request.args.get('players')
    if not all([date_str, players_str, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    player_ids = players_str.split(',')
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    tournament = Tournament.query.get_or_404(tournament_id)
    assegna_tournament_elo(players, tournament_id)
    return render_template('tournaments/torneotto45/manual_pairing.html',
                         tournament=tournament,
                         date=date_str,
                         players=players,
                         tournament_id=tournament_id)

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/torneotto45/save', methods=['POST'])
def save_torneotto45_day_from_pairing(tournament_id):
    """Salva una nuova giornata TorneOtto45 dalle coppie generate"""
    date_str = request.form.get('date')
    teams_json = request.form.get('teams_json')
    
    if not all([date_str, teams_json, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        teams = json.loads(teams_json)
    
        # Crea la configurazione
        semifinali = [
            {
                "squadra_a": teams[0],
                "squadra_b": teams[1],
                "risultato": None
            },
            {
                "squadra_a": teams[2],
                "squadra_b": teams[3],
                "risultato": None
            }
        ]
        
        finali = {
            "primo_posto": {
                "squadra_a": None,
                "squadra_b": None,
                "risultato": None
            },
            "terzo_posto": {
                "squadra_a": None,
                "squadra_b": None,
                "risultato": None
            }
        }
        
        # Estrai i giocatori
        players = []
        for team in teams:
            players.extend(team)
        
        # Crea una nuova giornata usando l'oggetto model
        day = TorneOtto45Day(
            tournament_id=tournament_id,
            data=date,
            stato="Risultati da inserire",
            created_at=datetime.now()
        )
    
        # Imposta la configurazione
        config = {
            "players": players,
            "semifinali": semifinali,
            "finali": finali
        }
        day.set_config(config)
        
        # Aggiungi e committa
        db.session.add(day)
        db.session.commit()
        
        flash('Giornata creata con successo!', 'success')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore durante il salvataggio: {str(e)}")
        flash(f'Errore durante il salvataggio della giornata: {str(e)}', 'error')
        return redirect(url_for('tournaments.new_torneotto45_day', tournament_id=tournament_id))