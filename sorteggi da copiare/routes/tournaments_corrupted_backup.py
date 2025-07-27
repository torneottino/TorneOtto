from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app as app
from models.tournament import Tournament
from models.player import Player, PlayerTournamentElo, PlayerEloHistory
from models.tournament_day import TorneOtto30Day, TorneOtto45Day, TournamentDay, GironiDay, EliminDay, AmericanaDay
from extensions import db
from datetime import datetime, date, timedelta
import json
from services import pairing
import random
import io
from functools import wraps
from sqlalchemy import func, text
from services.elo_calculator import update_tournament_elos, delete_tournament_day_elos, calculate_match_elo_change, get_team_elo, get_player_current_elo
from services.tournament_service import delete_tournament_day_simple
from services.americana_service import AmericanaService

tournaments_bp = Blueprint('tournaments', __name__)

@tournaments_bp.route('/tornei')
def tournaments_list():
    """Visualizza la pagina di gestione dei tornei con la scelta delle tipologie."""
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    for torneo in tournaments:
        # Recupera tutte le giornate di qualunque tipo
        days = []
        # TournamentDay (base and subclasses)
        days += TournamentDay.query.filter_by(tournament_id=torneo.id).all()
        # EliminDay (separate table)
        days += EliminDay.query.filter_by(tournament_id=torneo.id).all()
        # Raccogli tutte le date effettive
        all_dates = [d.data for d in days if d.data]
        all_dates = sorted(set(all_dates))
        if not all_dates:
            # Nessuna giornata: mostra solo la data di inizio torneo
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
        # Stato torneo (già esistente)
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
        "eliminazione": "Eliminazione Diretta",
        "americana": "Torneo all'Americana"
    }
    return render_template('tournaments/new.html', tipi_tornei=tipi_tornei)

@tournaments_bp.route('/tornei/tipo/<string:tipo>', methods=['GET', 'POST'])
def tournament_type(tipo):
    """Reindirizza alla creazione di un tipo specifico di torneo"""
    tipi_validi = ["torneotto30", "torneotto45", "gironi", "eliminazione", "americana"]
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
        
        # La configurazione specifica (numero gironi, squadre per girone) 
        # verrà definita quando si creerà la prima giornata del torneo
        
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
    """Creazione di un torneo a eliminazione diretta o doppia"""
    if request.method == 'POST':
        # Recupera i dati dal form
        nome = request.form.get('nome')
        circolo = request.form.get('circolo')
        note = request.form.get('note')
        tipo_eliminazione = request.form.get('tipo_eliminazione', 'single')
        num_partecipanti = int(request.form.get('num_partecipanti', 16))
        metodo_accoppiamento = request.form.get('metodo_accoppiamento', 'random')
        best_of_three = request.form.get('best_of_three') == 'on'
        
        # Validazione
        if not nome:
            flash('Il nome del torneo è obbligatorio!', 'error')
            return render_template('tournaments/types/eliminazione.html')
        
        if num_partecipanti < 8 or num_partecipanti > 64:
            flash('Il numero di partecipanti deve essere tra 8 e 64!', 'error')
            return render_template('tournaments/types/eliminazione.html')
        
        # Date predefinite
        data_inizio = date.today()
        data_fine = data_inizio + timedelta(days=10)
        
        # Creazione torneo base
        torneo = Tournament(
            nome=nome,
            tipo_torneo='eliminazione',
            circolo=circolo,
            note=note,
            data_inizio=data_inizio,
            data_fine=data_fine,
            stato="Pianificato"
        )
        
        # Configurazione del torneo base
        torneo.set_config({
            'tipo_eliminazione': tipo_eliminazione,
            'num_partecipanti': num_partecipanti,
            'metodo_accoppiamento': metodo_accoppiamento,
            'best_of_three': best_of_three
        })
        
        try:
            db.session.add(torneo)
            db.session.flush()  # Per ottenere l'ID del torneo
            
            # Crea il torneo ad eliminazione associato
            from models.elimin_day import EliminationTournament
            elim_tournament = EliminationTournament(
                tournament_id=torneo.id,
                tipo_eliminazione=tipo_eliminazione,
                num_partecipanti=num_partecipanti,
                num_squadre=0,  # Sarà calcolato in initialize_bracket
                metodo_accoppiamento=metodo_accoppiamento,
                best_of_three=best_of_three,
                data_inizio=data_inizio
            )
            
            elim_tournament.initialize_bracket()
            db.session.add(elim_tournament)
            db.session.commit()
            
            tipo_nome = "Eliminazione Diretta" if tipo_eliminazione == 'single' else "Doppia Eliminazione"
            flash(f'Torneo a {tipo_nome} creato con successo!', 'success')
            
            # Reindirizza alla selezione giocatori
            return redirect(url_for('tournaments.elimination_select_players', tournament_id=torneo.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione del torneo: {str(e)}', 'error')
    
    return render_template('tournaments/types/eliminazione.html')

# ROUTE PER TORNEO ALL'AMERICANA
@tournaments_bp.route('/tornei/nuovo/americana', methods=['GET', 'POST'])
def create_americana_tournament():
    """Creazione di un torneo all'americana"""
    if request.method == 'POST':
        # Recupera i dati dal form
        nome = request.form.get('nome')
        circolo = request.form.get('circolo')
        note = request.form.get('note')
        data_torneo = request.form.get('data_torneo')
        num_coppie = request.form.get('num_coppie')
        metodo_formazione = request.form.get('metodo_formazione')
        origine_giocatori = request.form.get('origine_giocatori')
        tipo_torneo_americana = request.form.get('tipo_torneo')
        num_campi = request.form.get('num_campi')
        tipo_coppie = request.form.get('tipo_coppie')
        metodo_punteggio = request.form.get('metodo_punteggio')
        
        # Validazione
        if not nome:
            flash('Il nome del torneo è obbligatorio!', 'error')
            return render_template('tournaments/types/americana.html')
        
        if not data_torneo:
            flash('La data del torneo è obbligatoria!', 'error')
            return render_template('tournaments/types/americana.html')
        
        try:
            num_coppie = int(num_coppie)
            if num_coppie < 4:
                flash('Il numero minimo di coppie è 4!', 'error')
                return render_template('tournaments/types/americana.html')
        except (ValueError, TypeError):
            flash('Numero di coppie non valido!', 'error')
            return render_template('tournaments/types/americana.html')
        
        try:
            num_campi = int(num_campi)
            if num_campi < 2:
                flash('Il numero minimo di campi è 2!', 'error')
                return render_template('tournaments/types/americana.html')
        except (ValueError, TypeError):
            flash('Numero di campi non valido!', 'error')
            return render_template('tournaments/types/americana.html')
        
        # Date del torneo
        from datetime import datetime
        data_inizio = datetime.strptime(data_torneo, '%Y-%m-%d').date()
        data_fine = data_inizio  # Torneo in una giornata
        
        # Creazione torneo
        torneo = Tournament(
            nome=nome,
            tipo_torneo='americana',
            circolo=circolo,
            note=note,
            data_inizio=data_inizio,
            data_fine=data_fine,
            stato="Pianificato"
        )
        
        # Configurazione specifica del torneo americana
        torneo.set_config({
            'num_coppie': num_coppie,
            'metodo_formazione': metodo_formazione,
            'origine_giocatori': origine_giocatori,
            'tipo_torneo': tipo_torneo_americana,
            'num_campi': num_campi,
            'tipo_coppie': tipo_coppie,
            'metodo_punteggio': metodo_punteggio
        })
        
        try:
            db.session.add(torneo)
            db.session.commit()
            flash('Torneo all\'americana creato con successo!', 'success')
            return redirect(url_for('tournaments.tournaments_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione del torneo: {str(e)}', 'error')
    
    return render_template('tournaments/types/americana.html')

@tournaments_bp.route('/tornei/eliminazione/riepilogo', methods=['POST'])
def elimination_setup_summary():
    """Pagina di riepilogo delle impostazioni del torneo eliminazione prima del salvataggio"""
    # Recupera i dati dal form
    data_inizio = request.form.get('data_inizio')
    nome = request.form.get('nome')
    circolo = request.form.get('circolo')
    tipo_eliminazione = request.form.get('tipo_eliminazione')
    num_squadre = request.form.get('num_squadre')
    best_of_three = request.form.get('best_of_three') == 'on'
    note = request.form.get('note')
    
    # Validazione base
    if not nome or not data_inizio:
        flash('Nome torneo e data di inizio sono obbligatori!', 'error')
        return redirect(url_for('tournaments.create_eliminazione_tournament'))
    
    try:
        num_squadre = int(num_squadre)
        if num_squadre < 8 or num_squadre > 64:
            flash('Il numero di squadre deve essere tra 8 e 64!', 'error')
            return redirect(url_for('tournaments.create_eliminazione_tournament'))
    except (ValueError, TypeError):
        flash('Numero di squadre non valido!', 'error')
        return redirect(url_for('tournaments.create_eliminazione_tournament'))
    
    # Calcola la prossima potenza di 2 se necessario
    import math
    num_squadre_potenza2 = 2 ** math.ceil(math.log2(num_squadre))
    
    # Prepara i dati per il template
    tournament_data = {
        'data_inizio': data_inizio,
        'nome': nome,
        'circolo': circolo or 'Non specificato',
        'tipo_eliminazione': tipo_eliminazione,
        'num_squadre': num_squadre,
        'num_squadre_potenza2': num_squadre_potenza2,
        'best_of_three': best_of_three,
        'note': note or 'Nessuna nota'
    }
    
    return render_template('tournaments/elimination/setup_summary.html', tournament_data=tournament_data)

@tournaments_bp.route('/tornei/eliminazione/inserisci-squadre', methods=['POST'])
def elimination_team_setup():
    """Pagina per inserire i nomi delle squadre"""
    # Recupera i dati dal form precedente
    data_inizio = request.form.get('data_inizio')
    nome = request.form.get('nome')
    circolo = request.form.get('circolo')
    tipo_eliminazione = request.form.get('tipo_eliminazione')
    num_squadre = int(request.form.get('num_squadre'))
    best_of_three = request.form.get('best_of_three') == 'True'
    note = request.form.get('note')
    
    # Prepara i dati per il template
    tournament_data = {
        'data_inizio': data_inizio,
        'nome': nome,
        'circolo': circolo,
        'tipo_eliminazione': tipo_eliminazione,
        'num_squadre': num_squadre,
        'best_of_three': best_of_three,
        'note': note
    }
    
    return render_template('tournaments/elimination/team_setup.html', tournament_data=tournament_data)

@tournaments_bp.route('/tornei/eliminazione/crea-tabellone', methods=['POST'])
def elimination_create_bracket_page():
    """Pagina vuota per la creazione del tabellone (da riempire successivamente)"""
    # Recupera i dati del torneo
    data_inizio = request.form.get('data_inizio')
    nome = request.form.get('nome')
    circolo = request.form.get('circolo')
    tipo_eliminazione = request.form.get('tipo_eliminazione')
    num_squadre = int(request.form.get('num_squadre'))
    best_of_three = request.form.get('best_of_three') == 'True'
    note = request.form.get('note')
    
    # Recupera i nomi delle squadre e le teste di serie
    teams = []
    seeds = []
    
    for i in range(1, num_squadre + 1):
        team_name = request.form.get(f'team_{i}')
        is_seed = request.form.get(f'seed_{i}') == 'on'
        if team_name:
            teams.append({
                'name': team_name.strip(),
                'is_seed': is_seed,
                'position': i
            })
            if is_seed:
                seeds.append(team_name.strip())
    
    # Prepara i dati per il template
    tournament_data = {
        'data_inizio': data_inizio,
        'nome': nome,
        'circolo': circolo,
        'tipo_eliminazione': tipo_eliminazione,
        'num_squadre': num_squadre,
        'best_of_three': best_of_three,
        'note': note,
        'teams': teams,
        'seeds': seeds
    }
    
    # Pagina vuota come richiesto
    return render_template('tournaments/elimination/bracket_creation.html', tournament_data=tournament_data)

@tournaments_bp.route('/tornei/eliminazione/salva-tabellone', methods=['POST'])
def save_elimination_bracket():
    """Salva il tabellone di eliminazione nel database"""
    try:
        # Recupera i dati dal form
        data_inizio = request.form.get('data_inizio')
        nome = request.form.get('nome')
        circolo = request.form.get('circolo')
        tipo_eliminazione = request.form.get('tipo_eliminazione')
        num_squadre = int(request.form.get('num_squadre'))
        best_of_three = request.form.get('best_of_three') == 'True'
        note = request.form.get('note')
        teams_str = request.form.get('teams')
        seeds_str = request.form.get('seeds', '')
        
        # Converte le stringhe in liste
        teams = teams_str.split(',') if teams_str else []
        seeds = seeds_str.split(',') if seeds_str else []
        
        # Crea il torneo base
        from datetime import datetime
        tournament = Tournament(
            nome=nome,
            tipo_torneo='eliminazione',
            circolo=circolo,
            note=note,
            data_inizio=datetime.strptime(data_inizio, '%Y-%m-%d').date(),
            data_fine=datetime.strptime(data_inizio, '%Y-%m-%d').date(),
            stato="Pianificato"
        )
        
        # Configurazione del torneo
        tournament.set_config({
            'tipo_eliminazione': tipo_eliminazione,
            'num_squadre': num_squadre,
            'best_of_three': best_of_three,
            'teams': teams,
            'seeds': seeds
        })
        
        db.session.add(tournament)
        db.session.flush()  # Per ottenere l'ID
        
        # Crea il torneo ad eliminazione associato
        from models.elimin_day import EliminationTournament
        elim_tournament = EliminationTournament(
            tournament_id=tournament.id,
            tipo_eliminazione=tipo_eliminazione,
            num_partecipanti=num_squadre,
            num_squadre=num_squadre,
            metodo_accoppiamento='manual',
            best_of_three=best_of_three,
            data_inizio=tournament.data_inizio,
            stato='Setup'  # Cambiato da 'Configurato' a 'Setup'
        )
        
        # Salva la configurazione delle squadre
        elim_tournament.set_config({
            'teams': teams,
            'seeds': seeds,
            'first_round_created': False
        })
        
        db.session.add(elim_tournament)
        db.session.flush()  # Per ottenere l'ID del torneo eliminazione
        
        # Ora crea effettivamente il tabellone con le partite usando i NOMI delle squadre
        try:
            create_elimination_bracket(elim_tournament, teams)  # Passa i nomi delle squadre, non numeri!
            elim_tournament.stato = 'In Corso'  # Aggiorna lo stato dopo la creazione del tabellone
            app.logger.info(f"Tabellone creato con successo per torneo {elim_tournament.id}")
        except Exception as bracket_error:
            app.logger.error(f"Errore nella creazione del tabellone: {str(bracket_error)}")
            # Non bloccare il salvataggio, ma logga l'errore
            
        db.session.commit()
        
        flash('Torneo ad eliminazione creato con successo!', 'success')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament.id))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Errore durante il salvataggio del torneo: {str(e)}")
        flash(f'Errore durante il salvataggio: {str(e)}', 'error')
        return redirect(url_for('tournaments.tournaments_list'))

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
    elif torneo.tipo_torneo == 'gironi':
        giornate = GironiDay.query.filter_by(tournament_id=torneo.id).order_by(GironiDay.data).all()
    elif torneo.tipo_torneo == 'eliminazione':
        # Per i tornei ad eliminazione, non ci sono "giornate" tradizionali
        giornate = []
        # Recupera invece il torneo ad eliminazione
        from models.elimin_day import EliminationTournament
        elim_tournament = EliminationTournament.query.filter_by(tournament_id=torneo.id).first()
        
        # Recupera le squadre salvate
        teams = []
        
        # Prima prova nel Tournament.config_json
        tournament_config = torneo.get_config() or {}
        teams_list = tournament_config.get('teams', [])
        seeds_list = tournament_config.get('seeds', [])
        
        if teams_list:
            for i, team_name in enumerate(teams_list):
                team = {
                    'name': team_name,
                    'seed': str(i+1) in seeds_list if seeds_list else False
                }
                teams.append(team)
            app.logger.info(f"Recuperate {len(teams)} squadre da Tournament.config_json")
        
        # Se non trova niente, prova in EliminationTournament
        elif elim_tournament:
            elim_config = elim_tournament.get_config() if hasattr(elim_tournament, 'get_config') else {}
            elim_teams = elim_config.get('teams', [])
            elim_seeds = elim_config.get('seeds', [])
            
            if elim_teams:
                for i, team_name in enumerate(elim_teams):
                    team = {
                        'name': team_name,
                        'seed': str(i+1) in elim_seeds if elim_seeds else False
                    }
                    teams.append(team)
                app.logger.info(f"Recuperate {len(teams)} squadre da EliminationTournament.config_json")
        
        if not elim_tournament:
            # Se non esiste ancora un record EliminationTournament, crea uno vuoto per evitare errori nel template
            elim_tournament = type('EliminationTournament', (), {
                'tipo_eliminazione': 'single',
                'num_partecipanti': len(teams),
                'stato': 'Setup'
            })()
        
        return render_template('tournaments/view_elimination.html', 
                             torneo=torneo, 
                             elim_tournament=elim_tournament,
                             teams=teams)
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

@tournaments_bp.route('/tornei/torneotto30/new_day/<int:tournament_id>', methods=['GET', 'POST'])
def new_day_torneotto30(tournament_id):
    if request.method == 'POST':
        date = request.form.get('date')
        selected_players = request.form.get('selected_players')
        
        if not all([date, selected_players]):
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
        return redirect(url_for('tournaments.tournaments_list'))
    
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
        player.tournament_elo = get_player_current_elo(player.id, tournament_id)
    return players

# TorneOtto30 - pairing random
@tournaments_bp.route('/tornei/torneotto30/pairing/random', methods=['POST'])
def random_pairing():
    date_str = request.form.get('date')
    players_ids = request.form.get('players')
    tournament_id = request.form.get('tournament_id')
    if not all([date_str, players_ids, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.tournaments_list'))
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
        return redirect(url_for('tournaments.tournaments_list'))
    
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
        return redirect(url_for('tournaments.tournaments_list'))
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
        return redirect(url_for('tournaments.tournaments_list'))
    
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
        players_ids = request.form.get('players')
        tournament_id = request.form.get('tournament_id')
        
        if not all([date_str, players_ids, tournament_id]):
            flash('Dati mancanti', 'error')
            return redirect(url_for('tournaments.tournaments_list'))
        
        player_ids = [int(id) for id in players_ids.split(',')]
        players = Player.query.filter(Player.id.in_(player_ids)).all()
        tournament = Tournament.query.get_or_404(tournament_id)
        assegna_tournament_elo(players, tournament_id)
        
        return render_template('tournaments/pairing_animation.html',
                             tournament=tournament,
                             date=date_str,
                             players=players,
                             method="seeded",
                             method_title="Sorteggio per Seeding",
                             method_description="Le squadre vengono formate considerando il ranking dei giocatori",
                             tournament_id=tournament_id,
                             form_action=url_for('tournaments.process_seeded_pairing'))
    
    # GET: mostra il form
    date_str = request.args.get('date')
    players_ids = request.args.get('players')
    tournament_id = request.args.get('tournament_id')
    
    if not all([date_str, players_ids, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.tournaments_list'))
    
    player_ids = [int(id) for id in players_ids.split(',')]
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    tournament = Tournament.query.get_or_404(tournament_id)
    assegna_tournament_elo(players, tournament_id)
    
    return render_template('tournaments/seeded_pairing.html',
                         tournament=tournament,
                         date=date_str,
                         players=players,
                         tournament_id=tournament_id)

@tournaments_bp.route('/tornei/torneotto30/pairing/seeded/process', methods=['POST'])
def process_seeded_pairing():
    date_str = request.form.get('date')
    tournament_id = request.form.get('tournament_id')
    pairs_json = request.form.get('pairs')
    
    # Validazione
    if not all([date_str, tournament_id, pairs_json]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.tournaments_list'))
    
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
        players_ids = request.form.get('players')
        tournament_id = request.form.get('tournament_id')
        
        if not all([date_str, players_ids, tournament_id]):
            flash('Dati mancanti', 'error')
            return redirect(url_for('tournaments.tournaments_list'))
        
        player_ids = [int(id) for id in players_ids.split(',')]
        players = Player.query.filter(Player.id.in_(player_ids)).all()
        tournament = Tournament.query.get_or_404(tournament_id)
        assegna_tournament_elo(players, tournament_id)
        
        return render_template('tournaments/manual_pairing.html',
                             tournament=tournament,
                             date=date_str,
                             players=players,
                             tournament_id=tournament_id)
    
    # GET: mostra il form
    date_str = request.args.get('date')
    players_ids = request.args.get('players')
    tournament_id = request.args.get('tournament_id')
    
    if not all([date_str, players_ids, tournament_id]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.tournaments_list'))
    
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
        return redirect(url_for('tournaments.tournaments_list'))
    
    try:
        # Decodifica i dati
        teams = json.loads(teams_json)
        schedule = json.loads(schedule_json)
        
        # Recupera il torneo
        tournament = Tournament.query.get_or_404(tournament_id)
        
        # Crea la giornata del torneo
        day = TorneOtto30Day(
            tournament_id=tournament_id,
            data=datetime.strptime(date_str, '%Y-%m-%d').date(),
            stato="Aperta",
            tipo_giornata="torneotto30"
        )
        
        # Imposta la configurazione
        day.set_config({
            'players': [player_id for team in teams for player_id in team],
            'pairs': teams,
            'matches': schedule,
            'results': {}
        })
        
        db.session.add(day)
        db.session.commit()
        
        flash('Giornata del torneo salvata con successo!', 'success')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il salvataggio: {str(e)}', 'error')
        return redirect(url_for('tournaments.tournaments_list'))

@tournaments_bp.route('/tornei/torneotto30/export_pdf')
def export_pdf():
    date_str = request.args.get('date')
    tournament_id = request.args.get('tournament_id')
    teams_json = request.args.get('teams')
    schedule_json = request.args.get('schedule')
    
    # Validazione
    if not all([date_str, tournament_id, teams_json, schedule_json]):
        flash('Dati mancanti', 'error')
        return redirect(url_for('tournaments.tournaments_list'))
    
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
        app.logger.error(f"Errore nella generazione della vista: {str(e)}")
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
        # Elimina prima i record dalle tabelle legacy che potrebbero avere foreign key constraints
        legacy_tables = ['pozzo_courts', 'pozzo_teams', 'pozzo_matches', 'pozzo_players']
        
        for table_name in legacy_tables:
            try:
                db.session.execute(
                    text(f"DELETE FROM {table_name} WHERE tournament_id = :tournament_id"),
                    {"tournament_id": tournament_id}
                )
                db.session.commit()
                print(f"Eliminati record dalla tabella {table_name}")
            except Exception as e:
                # Se la tabella non esiste o non ha la colonna tournament_id, ignora l'errore
                db.session.rollback()
                print(f"Tabella {table_name} non trovata o senza colonna tournament_id: {str(e)}")
                pass
        
        # Elimina prima gli ELO history che dipendono dalle giornate
        PlayerEloHistory.query.filter_by(tournament_id=tournament_id).delete()
        
        # Elimina gli ELO ratings del torneo
        PlayerTournamentElo.query.filter_by(tournament_id=tournament_id).delete()
        
        # Ora possiamo eliminare le giornate
        EliminDay.query.filter_by(tournament_id=tournament_id).delete()
        TournamentDay.query.filter_by(tournament_id=tournament_id).delete()
        
        # Infine elimina il torneo
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
        p.tournament_elo = get_player_current_elo(p.id, tournament.id)
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
        app.logger.error(f"Errore durante l'eliminazione della giornata: {str(e)}")
        return jsonify({'error': str(e)}), 500

@tournaments_bp.route('/tornei/<int:tournament_id>/classifica')
def tournament_ranking(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # I tornei ad eliminazione non hanno classifiche tradizionali
    if tournament.tipo_torneo == 'eliminazione':
        flash('I tornei ad eliminazione non hanno classifiche. Usa la visualizzazione del torneo per vedere il tabellone.', 'info')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    from sqlalchemy import func

    # Recupera tutte le giornate del torneo (30, 45 e gironi)
    days_30 = TorneOtto30Day.query.filter_by(tournament_id=tournament_id).all()
    days_45 = TorneOtto45Day.query.filter_by(tournament_id=tournament_id).all()
    days_gironi = GironiDay.query.filter_by(tournament_id=tournament_id).all()
    player_stats = {}

    # TorneOtto30: conta solo giornate completate
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
                # CONTA SOLO LE GIORNATE COMPLETATE
                if day.stato == "Completata":
                    player_stats[player_id]['presenze'] += 1

    # TorneOtto45: aggiungo presenze SOLO per giornate completate e aggiorno ELO
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
            # CONTA SOLO LE GIORNATE COMPLETATE
            if day.stato == "Completata":
                player_stats[player_id]['presenze'] += 1

    # Gironi: aggiungo presenze SOLO per giornate COMPLETATE e calcolo ELO progressivo
    if tournament.tipo_torneo == 'gironi':
        # Per i gironi, calcola l'ELO progressivo per ogni giocatore
        all_players_in_gironi = set()
        for day in days_gironi:
            players_ids = day.get_players() or []
            all_players_in_gironi.update(players_ids)
        
        for player_id in all_players_in_gironi:
            if player_id not in player_stats:
                # Calcola ELO progressivo per questo giocatore
                current_elo = 1500.0
                presenze = 0
                
                # Ordina le giornate gironi per data
                sorted_days_gironi = sorted(days_gironi, key=lambda x: x.data)
                
                for day in sorted_days_gironi:
                    if player_id in (day.get_players() or []):
                        if day.stato == "Completata":
                            presenze += 1
                            # Recupera la variazione ELO per questa giornata
                            elo_history = PlayerEloHistory.query.filter_by(
                                player_id=player_id,
                                tournament_id=tournament_id,
                                tournament_day_id=day.id
                            ).first()
                            if elo_history:
                                current_elo += elo_history.elo_change
                
                app.logger.info(f"Ranking Gironi: Giocatore {player_id} - ELO calcolato progressivamente: {current_elo}")
                player_stats[player_id] = {
                    'presenze': presenze,
                    'elo_rating': current_elo
                }
    else:
        # Per altri tipi di torneo, usa la logica esistente
        for day in days_gironi:
            players_ids = day.get_players() or []
            for player_id in players_ids:
                if player_id not in player_stats:
                    elo_rating = PlayerTournamentElo.query.filter_by(
                        player_id=player_id,
                        tournament_id=tournament_id
                    ).first()
                    final_elo = elo_rating.elo_rating if elo_rating else 1500.00
                    app.logger.info(f"Ranking: Giocatore {player_id} - ELO da DB: {final_elo}")
                    player_stats[player_id] = {
                        'presenze': 0,
                        'elo_rating': final_elo
                    }
                # CONTA SOLO LE GIORNATE COMPLETATE
                if day.stato == "Completata":
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
        days_gironi = GironiDay.query.filter_by(tournament_id=tournament_id).order_by(GironiDay.data).all()
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

        # ELO progressivo per calcolo corretto
        current_elo = 1500.0
        
        # Recupera TUTTE le giornate ordinate per data
        all_days = []
        
        # Aggiungi le giornate TorneOtto30
        for day in days_30:
            all_days.append({
                'type': 'torneotto30',
                'day': day,
                'data': day.data,
                'id': day.id
            })
        
        # Aggiungi le giornate TorneOtto45  
        for day in days_45:
            all_days.append({
                'type': 'torneotto45',
                'day': day,
                'data': day.data,
                'id': day.id
            })
            
        # Aggiungi le giornate Gironi
        for day in days_gironi:
            all_days.append({
                'type': 'gironi',
                'day': day,
                'data': day.data,
                'id': day.id
            })
        
        # Ordina tutte le giornate per data
        all_days.sort(key=lambda x: x['data'])
        
        # Aggiungi l'ELO iniziale se ci sono giornate
        if all_days:
            first_day = all_days[0]
            stats['elo_history'].append({
                'data': first_day['data'].strftime('%d.%m.%Y'),
                'giornata': f"{first_day['data'].strftime('%d.%m.%Y')} Inserimento",
                'variazione': "+0.00",
                'elo': f"{current_elo:.2f}"
            })

        # Processa tutte le giornate in ordine cronologico
        giornata_counter = 1
        for day_info in all_days:
            day = day_info['day']
            day_type = day_info['type']
            
            # Verifica se il giocatore ha partecipato a questa giornata
            player_participated = False
            
            if day_type == 'torneotto30':
                if player_id in [p for team in day.get_config().get('teams', []) for p in team]:
                    player_participated = True
            elif day_type == 'torneotto45':
                classifica = day.get_ranking() or []
                if player_id in classifica:
                    player_participated = True
            elif day_type == 'gironi':
                config = day.get_config()
                matches = config.get('matches', [])
                for match in matches:
                    team1 = match.get('team1', [])
                    team2 = match.get('team2', [])
                    if player_id in team1 or player_id in team2:
                        player_participated = True
                        break
            
            if player_participated:
                stats['presenze_totali'] += 1
                if day.stato == "Completata":
                    stats['presenze_completate'] += 1
                    
                    # Calcola statistiche specifiche per tipo
                    if day_type == 'torneotto30':
                        stats['partite_totali'] += 3
                        # [logica TorneOtto30 semplificata]
                    elif day_type == 'torneotto45':
                        stats['partite_totali'] += 2
                        stats['partite_giocate'] += 2
                        # [logica TorneOtto45 semplificata]
                    elif day_type == 'gironi':
                        config = day.get_config()
                        matches = config.get('matches', [])
                        results = config.get('results', {})
                        
                        partite_giocate_giornata = 0
                        vittorie_giornata = 0
                        pareggi_giornata = 0
                        sconfitte_giornata = 0
                        
                        for match in matches:
                            team1 = match.get('team1', [])
                            team2 = match.get('team2', [])
                            
                            if player_id in team1 or player_id in team2:
                                match_id = str(match.get('id', ''))
                                if match_id in results:
                                    result = results[match_id]
                                    score_a = result.get('squadra_a', 0)
                                    score_b = result.get('squadra_b', 0)
                                    
                                    partite_giocate_giornata += 1
                                    stats['partite_totali'] += 1
                                    
                                    is_team_a = player_id in team1
                                    player_score = score_a if is_team_a else score_b
                                    opponent_score = score_b if is_team_a else score_a
                                    
                                    if player_score > opponent_score:
                                        vittorie_giornata += 1
                                        stats['vittorie'] += 1
                                    elif player_score < opponent_score:
                                        sconfitte_giornata += 1
                                        stats['sconfitte'] += 1
                                    else:
                                        pareggi_giornata += 1
                                        stats['pareggi'] += 1
                        
                        stats['partite_giocate'] += partite_giocate_giornata
                    
                    # Recupera la variazione ELO per questa giornata
                    elo_history = PlayerEloHistory.query.filter_by(
                        player_id=player_id,
                        tournament_id=tournament_id,
                        tournament_day_id=day.id
                    ).first()
                    
                    if elo_history:
                        current_elo += elo_history.elo_change
                        stats['elo_history'].append({
                            'data': day.data.strftime('%d.%m.%Y'),
                            'giornata': f"{day.data.strftime('%d.%m.%Y')} {giornata_counter}ª giornata",
                            'variazione': f"{elo_history.elo_change:+.2f}",
                            'elo': f"{current_elo:.2f}",
                        })
                        giornata_counter += 1

        # Aggiorna l'ELO attuale con il valore calcolato progressivamente
        stats['elo_attuale'] = current_elo

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
        elif tournament.tipo_torneo == 'gironi':
            # Gestione per tornei a gironi
            # Recupera l'ultima giornata del torneo
            last_day = GironiDay.query.filter_by(tournament_id=tournament_id).order_by(GironiDay.data.desc()).first()
            
            # Recupera tutte le giornate del torneo
            days = GironiDay.query.filter_by(tournament_id=tournament_id).order_by(GironiDay.data).all()
            
            # Recupera tutti i giocatori che hanno partecipato al torneo
            players_with_elo = PlayerTournamentElo.query.filter_by(tournament_id=tournament_id).all()
            player_ids = [p.player_id for p in players_with_elo]
            players = Player.query.filter(Player.id.in_(player_ids)).all()
            
            # Prima passata: conta il numero totale di giornate completate
            completed_days = len([day for day in days if day.stato == "Completata"])
            partite_totali = 0
            
            # Calcola il totale delle partite
            for day in days:
                if day.stato == "Completata":
                    matches = day.get_matches()
                    semifinals = day.get_semifinals()
                    finals = day.get_finals()
                    
                    # Conta partite round robin
                    if matches:
                        partite_totali += len(matches)
                    
                    # Conta semifinali
                    if semifinals:
                        partite_totali += len(semifinals)
                    
                    # Conta finali
                    if finals:
                        partite_totali += len(finals.values())
            
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
                    'presenze_totali': len(days),
                    'partite_totali': 0,
                    'vittorie': 0,
                    'pareggi': 0,
                    'sconfitte': 0,
                    'presenze_giocate': 0,
                    'giornate': []
                }
                
                # Analizza ogni giornata
                for day_idx, day in enumerate(days, 1):
                    if day.stato == "Completata":
                        players_in_day = day.get_players()
                        
                        # Controlla se il giocatore ha partecipato
                        if player.id in players_in_day:
                            stats['presenze_giocate'] += 1
                            
                            # Analizza le partite del round robin
                            matches = day.get_matches()
                            results = day.get_results()
                            
                            if matches and results:
                                for match in matches:
                                    # Verifica se il giocatore è in questa partita
                                    if player.id in match['team1'] or player.id in match['team2']:
                                        match_result = results.get(str(match['id']))
                                        if match_result:
                                            stats['partite_totali'] += 1
                                            
                                            # Determina se è squadra A o B
                                            is_team_a = player.id in match['team1']
                                            player_score = match_result['squadra_a'] if is_team_a else match_result['squadra_b']
                                            opponent_score = match_result['squadra_b'] if is_team_a else match_result['squadra_a']
                                            
                                            if player_score > opponent_score:
                                                stats['vittorie'] += 1
                                            elif player_score < opponent_score:
                                                stats['sconfitte'] += 1
                                            else:
                                                stats['pareggi'] += 1
                            
                            # Analizza semifinali e finali
                            semifinals = day.get_semifinals()
                            finals = day.get_finals()
                            
                            # Conta le partite e i risultati delle semifinali
                            if semifinals:
                                for semifinal in semifinals:
                                    if player.id in semifinal['squadra_a'] or player.id in semifinal['squadra_b']:
                                        stats['partite_totali'] += 1
                                        if semifinal.get('risultato'):
                                            is_team_a = player.id in semifinal['squadra_a']
                                            player_score = semifinal['risultato']['squadra_a'] if is_team_a else semifinal['risultato']['squadra_b']
                                            opponent_score = semifinal['risultato']['squadra_b'] if is_team_a else semifinal['risultato']['squadra_a']
                                            
                                            if player_score > opponent_score:
                                                stats['vittorie'] += 1
                                            elif player_score < opponent_score:
                                                stats['sconfitte'] += 1
                                            else:
                                                stats['pareggi'] += 1
                            
                            # Conta le partite e i risultati delle finali
                            if finals:
                                for final_type in ['primo_posto', 'terzo_posto']:
                                    if finals.get(final_type):
                                        final = finals[final_type]
                                        if player.id in final['squadra_a'] or player.id in final['squadra_b']:
                                            stats['partite_totali'] += 1
                                            if final.get('risultato'):
                                                is_team_a = player.id in final['squadra_a']
                                                player_score = final['risultato']['squadra_a'] if is_team_a else final['risultato']['squadra_b']
                                                opponent_score = final['risultato']['squadra_b'] if is_team_a else final['risultato']['squadra_a']
                                                
                                                if player_score > opponent_score:
                                                    stats['vittorie'] += 1
                                                elif player_score < opponent_score:
                                                    stats['sconfitte'] += 1
                                                else:
                                                    stats['pareggi'] += 1
                        
                        # Aggiungi la variazione ELO per questa giornata
                        day_elo = next((h for h in elo_history if h.tournament_day_id == day.id), None)
                        if day_elo:
                            stats['giornate'].append({
                                'numero': day_idx,
                                'variazione': day_elo.elo_change
                            })
                
                players_data.append({
                    'id': player.id,
                    'nome': player.nome,
                    'cognome': player.cognome,
                    'elo_rating': tournament_elo,
                    'stats': stats
                })
            
            # Ordina i giocatori per ELO decrescente
            players_data.sort(key=lambda x: x['elo_rating'], reverse=True)
            
            # Renderizza direttamente il template HTML
            return render_template('tournaments/pdf/classifica_gironi.html',
                                tournament=tournament,
                                players=players_data,
                                now=datetime.now(),
                                last_day=last_day,
                                print_view=True,
                                giornate_giocate=completed_days,
                                partite_totali=partite_totali)
        else:
            # Gestione per tornei generici (non supportati)
            flash('Tipo di torneo non supportato', 'error')
            return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
            
    except Exception as e:
        app.logger.error(f"Errore durante la generazione della vista: {str(e)}")
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
        app.logger.error(f"Errore durante la generazione della vista: {str(e)}")
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
    
    app.logger.info(f"Calcolo ELO per giornata {day_id} del torneo {tournament_id}")
    
    # Estrai la classifica e la configurazione
    classifica = day.get_ranking()
    config = day.get_config()
    if not classifica or not config:
        app.logger.error(f"Classifica o configurazione mancante per giornata {day_id}")
        return
    
    app.logger.info(f"Classifica: {classifica}")
    app.logger.info(f"Config: {config}")
    
    # Recupera i risultati delle partite
    semifinali = config.get('semifinali', [])
    finali = config.get('finali', {})
    
    if not semifinali or not finali:
        app.logger.error(f"Semifinali o finali mancanti per giornata {day_id}")
        return
    
    # Per ogni giocatore nella classifica, recupera l'ELO attuale
    player_elos = {}
    for player_id in classifica:
        current_elo = get_player_current_elo(player_id, tournament_id, day_id)
        player_elos[player_id] = current_elo
        app.logger.info(f"Giocatore {player_id}: ELO attuale = {current_elo}")
    
    # Dizionario per tenere traccia delle variazioni ELO per ogni giocatore
    player_changes = {player_id: [] for player_id in classifica}
    
    # 1. Calcola le variazioni ELO per le semifinali (K=40)
    app.logger.info("Calcolo variazioni ELO per semifinali")
    for semifinale in semifinali:
        squadra_a = semifinale.get('squadra_a', [])
        squadra_b = semifinale.get('squadra_b', [])
        risultato = semifinale.get('risultato', {})
        
        if not risultato or not squadra_a or not squadra_b:
            app.logger.warning(f"Risultato semifinale mancante o squadre incomplete: {semifinale}")
            continue
            
        score_a = risultato.get('squadra_a', 0)
        score_b = risultato.get('squadra_b', 0)
        
        app.logger.info(f"Semifinale: Squadra A {squadra_a} vs Squadra B {squadra_b} - Risultato: {score_a}-{score_b}")
        
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
        
        app.logger.info(f"ELO Squadra A: {team1_elo}, ELO Squadra B: {team2_elo}")
        
        # Calcola le variazioni ELO con K=40
        team1_change, team2_change = calculate_match_elo_change(team1_elo, team2_elo, match_result, k_factor=40)
        
        app.logger.info(f"Variazioni ELO semifinale: Squadra A {team1_change}, Squadra B {team2_change}")
        
        # Distribuisci le variazioni tra i giocatori della squadra
        for player_id in squadra_a:
            player_changes[player_id].append(team1_change)
        for player_id in squadra_b:
            player_changes[player_id].append(team2_change)
    
    # 2. Calcola le variazioni ELO per le finali (K=32)
    app.logger.info("Calcolo variazioni ELO per finali")
    for match_type in ['primo_posto', 'terzo_posto']:
        finale = finali.get(match_type, {})
        squadra_a = finale.get('squadra_a', [])
        squadra_b = finale.get('squadra_b', [])
        risultato = finale.get('risultato', {})
        
        if not risultato or not squadra_a or not squadra_b:
            app.logger.warning(f"Risultato finale {match_type} mancante o squadre incomplete: {finale}")
            continue
            
        score_a = risultato.get('squadra_a', 0)
        score_b = risultato.get('squadra_b', 0)
        
        app.logger.info(f"Finale {match_type}: Squadra A {squadra_a} vs Squadra B {squadra_b} - Risultato: {score_a}-{score_b}")
        
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
        
        app.logger.info(f"ELO Squadra A: {team1_elo}, ELO Squadra B: {team2_elo}")
        
        # K=32 per tutte le finali
        team1_change, team2_change = calculate_match_elo_change(team1_elo, team2_elo, match_result, k_factor=32)
        
        app.logger.info(f"Variazioni ELO finale {match_type}: Squadra A {team1_change}, Squadra B {team2_change}")
        
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

def get_player_current_elo(player_id, tournament_id, before_day_id=None):
    """
    Ottiene l'ELO corrente di un giocatore per un torneo.
    Se before_day_id è specificato, restituisce l'ELO prima di quella giornata.
    """
    from sqlalchemy import desc
    
    query = PlayerEloHistory.query.filter_by(
        player_id=player_id,
        tournament_id=tournament_id
    )
    
    if before_day_id:
        query = query.filter(PlayerEloHistory.tournament_day_id < before_day_id)
    
    last_history = query.order_by(desc(PlayerEloHistory.tournament_day_id)).first()
    
    if last_history:
        return last_history.new_elo
    return 1500.0  # ELO iniziale se non ci sono giornate precedenti

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


@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/americana/choose-method', methods=['POST'])
def americana_choose_method(tournament_id):
    """Gestisce la scelta del metodo di formazione coppie per i tornei all'americana"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Verifica che il torneo sia di tipo corretto
    if tournament.tipo_torneo != 'americana':
        flash('Tipo di torneo non valido!', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    # Recupera i dati dal form
    data = request.form.get('data')
    num_coppie = int(request.form.get('num_coppie'))
    metodo_coppie = request.form.get('metodo_coppie')
    selected_players = request.form.get('selected_players')
    
    # Validazione
    if not all([data, num_coppie, metodo_coppie, selected_players]):
        flash('Dati mancanti!', 'error')
        return redirect(url_for('tournaments.new_americana_day', tournament_id=tournament_id))
    
    # Converti gli ID dei giocatori selezionati
    player_ids = [int(pid) for pid in selected_players.split(',')]
    num_giocatori = num_coppie * 2
    
    if len(player_ids) != num_giocatori:
        flash(f'Numero di giocatori non corretto! Richiesti: {num_giocatori}, selezionati: {len(player_ids)}', 'error')
        return redirect(url_for('tournaments.new_americana_day', tournament_id=tournament_id))
    
    # Recupera i giocatori selezionati
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    players_by_id = {player.id: player for player in players}
    
    # Ordina i giocatori secondo l'ordine di selezione
    ordered_players = [players_by_id[pid] for pid in player_ids]
    
    # Reindirizza al metodo di formazione coppie appropriato
    if metodo_coppie == 'casuale':
        return redirect(url_for('tournaments.americana_random_pairing', 
                               tournament_id=tournament_id,
                               data=data,
                               num_coppie=num_coppie,
                               players=','.join(map(str, player_ids))))
    elif metodo_coppie == 'elo':
        return redirect(url_for('tournaments.americana_elo_pairing',
                               tournament_id=tournament_id,
                               data=data,
                               num_coppie=num_coppie,
                               players=','.join(map(str, player_ids))))
    elif metodo_coppie == 'seeded':
        return redirect(url_for('tournaments.americana_seeded_pairing',
                               tournament_id=tournament_id,
                               data=data,
                               num_coppie=num_coppie,
                               players=','.join(map(str, player_ids))))
    elif metodo_coppie == 'manuale':
        return redirect(url_for('tournaments.americana_manual_pairing',
                               tournament_id=tournament_id,
                               data=data,
                               num_coppie=num_coppie,
                               players=','.join(map(str, player_ids))))
    elif metodo_coppie == 'coppie_fisse':
        return redirect(url_for('tournaments.americana_fixed_pairs',
                               tournament_id=tournament_id,
                               data=data,
                               num_coppie=num_coppie,
                               players=','.join(map(str, player_ids))))
    else:
        flash('Metodo di formazione coppie non valido!', 'error')
        return redirect(url_for('tournaments.new_americana_day', tournament_id=tournament_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/americana/random', methods=['GET'])
def americana_random_pairing(tournament_id):
    """Gestisce il sorteggio casuale delle coppie per i tornei all'americana"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    day = GironiDay.query.get_or_404(day_id)
    
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
    finali = {
        'primo_posto': {
            'squadra_a': vincitori[0],
            'squadra_b': vincitori[1],
            'risultato': None
        },
        'terzo_posto': {
            'squadra_a': perdenti[0],
            'squadra_b': perdenti[1],
            'risultato': None
        }
    }
    
    # Salva i dati aggiornati
    day.set_semifinals(semifinali)
    day.set_finals(finali)
    day.stato = "finali"
    
    try:
        db.session.commit()
        flash('Risultati semifinali salvati con successo. Ora puoi inserire i risultati delle finali.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il salvataggio dei risultati: {str(e)}', 'error')
    
    return redirect(url_for('tournaments.view_gironi_day', tournament_id=tournament_id, day_id=day_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/<int:day_id>/finali', methods=['POST'])
def save_gironi_finals(tournament_id, day_id):
    """Salva i risultati delle finali e genera la classifica finale"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = GironiDay.query.get_or_404(day_id)
    
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
    
    # Determina la classifica finale (coppie in ordine di posizione)
    classifica = []
    
    # 1° e 2° posto
    if primo_a > primo_b:
        classifica.append(finali['primo_posto']['squadra_a'])  # 1° posto
        classifica.append(finali['primo_posto']['squadra_b'])  # 2° posto
    else:
        classifica.append(finali['primo_posto']['squadra_b'])  # 1° posto
        classifica.append(finali['primo_posto']['squadra_a'])  # 2° posto
    
    # 3° e 4° posto
    if terzo_a > terzo_b:
        classifica.append(finali['terzo_posto']['squadra_a'])  # 3° posto
        classifica.append(finali['terzo_posto']['squadra_b'])  # 4° posto
    else:
        classifica.append(finali['terzo_posto']['squadra_b'])  # 3° posto
        classifica.append(finali['terzo_posto']['squadra_a'])  # 4° posto
    
    # Aggiungi le altre squadre dei gironi ordinate per differenza games
    classifiche_gironi = day.get_group_standings()
    altre_squadre = []
    qualificati_ids = set()
    
    # Raccogli gli ID delle squadre qualificate
    for team in classifica:
        qualificati_ids.add(f"{team[0]}_{team[1]}")
    
    # Raccogli tutte le altre squadre
    for classifica_girone in classifiche_gironi:
        for team_stats in classifica_girone:
            team_id = f"{team_stats['team'][0]}_{team_stats['team'][1]}"
            if team_id not in qualificati_ids:
                altre_squadre.append(team_stats)
    
    # Ordina le altre squadre per differenza games
    altre_squadre.sort(key=lambda x: x['differenza_games'], reverse=True)
    
    # Aggiungi le altre squadre alla classifica
    for team_stats in altre_squadre:
        classifica.append(team_stats['team'])
    
    # Salva i dati aggiornati
    day.set_finals(finali)
    day.set_ranking(classifica)
    day.stato = "Completata"
    
    try:
        db.session.commit()
        
        # Calcola l'ELO
        calculate_gironi_elo(tournament_id, day_id)
        
        flash('Giornata completata con successo! Gli ELO sono stati aggiornati.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il salvataggio dei risultati: {str(e)}', 'error')
    
    return redirect(url_for('tournaments.view_gironi_day', tournament_id=tournament_id, day_id=day_id))

def calculate_gironi_elo(tournament_id, day_id):
    """
    Calcola l'ELO per una giornata a gironi usando K-fattori diversi per round robin, semifinali e finali
    
    Args:
        tournament_id: ID del torneo
        day_id: ID della giornata
    """
    # Recupera la giornata dal database
    day = GironiDay.query.get_or_404(day_id)
    tournament = Tournament.query.get_or_404(tournament_id)
    
    app.logger.info(f"Calcolo ELO per giornata {day_id} del torneo {tournament_id}")
    
    # Estrai la classifica e i dati
    classifica = day.get_ranking()
    matches = day.get_matches()
    results = day.get_results()
    semifinali = day.get_semifinals()
    finali = day.get_finals()
    
    if not classifica or not matches or not results:
        app.logger.error(f"Dati mancanti per giornata {day_id}")
        return
    
    # Per ogni giocatore nella classifica, recupera l'ELO attuale
    all_players = []
    for team in classifica:
        all_players.extend(team)
    
    player_elos = {}
    for player_id in all_players:
        current_elo = get_player_current_elo(player_id, tournament_id, day_id)
        player_elos[player_id] = current_elo
        app.logger.info(f"Giocatore {player_id}: ELO attuale = {current_elo}")
    
    # Dizionario per tenere traccia delle variazioni ELO per ogni giocatore
    player_changes = {player_id: [] for player_id in all_players}
    
    # 1. Calcola le variazioni ELO per il round robin (K=20)
    app.logger.info("Calcolo variazioni ELO per round robin")
    for match in matches:
        if str(match['id']) not in results:
            app.logger.info(f"Match {match['id']} non ha risultati")
            continue
            
        result = results[str(match['id'])]
        squadra_a = match['team1']
        squadra_b = match['team2']
        score_a = result['squadra_a']
        score_b = result['squadra_b']
        
        app.logger.info(f"Partita Round Robin: Squadra A {squadra_a} vs Squadra B {squadra_b} - Risultato: {score_a}-{score_b}")
        
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
        
        # Calcola le variazioni ELO con K=20
        team1_change, team2_change = calculate_match_elo_change(team1_elo, team2_elo, match_result, k_factor=20)
        
        app.logger.info(f"Variazioni ELO round robin: Squadra A {team1_change}, Squadra B {team2_change}")
        
        # Distribuisci le variazioni tra i giocatori della squadra (variazione completa per ogni giocatore)
        for player_id in squadra_a:
            player_changes[player_id].append(team1_change)
            app.logger.info(f"Giocatore {player_id} (squadra A): aggiunta variazione {team1_change}")
        for player_id in squadra_b:
            player_changes[player_id].append(team2_change)
            app.logger.info(f"Giocatore {player_id} (squadra B): aggiunta variazione {team2_change}")
    
    # 2. Calcola le variazioni ELO per le semifinali (K=40)
    app.logger.info("Calcolo variazioni ELO per semifinali")
    for semifinale in semifinali:
        squadra_a = semifinale['squadra_a']
        squadra_b = semifinale['squadra_b']
        risultato = semifinale['risultato']
        
        if not risultato:
            continue
            
        score_a = risultato['squadra_a']
        score_b = risultato['squadra_b']
        
        app.logger.info(f"Semifinale: Squadra A {squadra_a} vs Squadra B {squadra_b} - Risultato: {score_a}-{score_b}")
        
        # Determina il risultato
        if score_a > score_b:
            match_result = 1
        elif score_a < score_b:
            match_result = 0
        else:
            match_result = 0.5
        
        # Calcola l'ELO totale delle squadre
        team1_elo = sum(player_elos[p] for p in squadra_a)
        team2_elo = sum(player_elos[p] for p in squadra_b)
        
        # Calcola le variazioni ELO con K=40
        team1_change, team2_change = calculate_match_elo_change(team1_elo, team2_elo, match_result, k_factor=40)
        
        app.logger.info(f"Variazioni ELO semifinale: Squadra A {team1_change}, Squadra B {team2_change}")
        
        # Distribuisci le variazioni tra i giocatori della squadra (variazione completa per ogni giocatore)
        for player_id in squadra_a:
            player_changes[player_id].append(team1_change)
        for player_id in squadra_b:
            player_changes[player_id].append(team2_change)
    
    # 3. Calcola le variazioni ELO per le finali (K=32)
    app.logger.info("Calcolo variazioni ELO per finali")
    for match_type in ['primo_posto', 'terzo_posto']:
        finale = finali[match_type]
        squadra_a = finale['squadra_a']
        squadra_b = finale['squadra_b']
        risultato = finale['risultato']
        
        if not risultato:
            continue
            
        score_a = risultato['squadra_a']
        score_b = risultato['squadra_b']
        
        app.logger.info(f"Finale {match_type}: Squadra A {squadra_a} vs Squadra B {squadra_b} - Risultato: {score_a}-{score_b}")
        
        # Determina il risultato
        if score_a > score_b:
            match_result = 1
        elif score_a < score_b:
            match_result = 0
        else:
            match_result = 0.5
        
        # Calcola l'ELO totale delle squadre
        team1_elo = sum(player_elos[p] for p in squadra_a)
        team2_elo = sum(player_elos[p] for p in squadra_b)
        
        # K=32 per tutte le finali
        team1_change, team2_change = calculate_match_elo_change(team1_elo, team2_elo, match_result, k_factor=32)
        
        app.logger.info(f"Variazioni ELO finale {match_type}: Squadra A {team1_change}, Squadra B {team2_change}")
        
        # Distribuisci le variazioni tra i giocatori della squadra (variazione completa per ogni giocatore)
        for player_id in squadra_a:
            player_changes[player_id].append(team1_change)
        for player_id in squadra_b:
            player_changes[player_id].append(team2_change)
    
    # 4. Calcola la somma delle variazioni ELO per ogni giocatore
    app.logger.info("Calcolo somma variazioni ELO")
    final_changes = {}
    for player_id, changes in player_changes.items():
        if changes:  # Se il giocatore ha partecipato a delle partite
            final_changes[player_id] = round(sum(changes), 2)
            app.logger.info(f"Giocatore {player_id}: variazioni {changes}, somma {final_changes[player_id]}")
        else:
            final_changes[player_id] = 0
            app.logger.warning(f"Giocatore {player_id}: nessuna variazione ELO")
    
    # 5. Aggiorna gli ELO nel database e registra la storia
    app.logger.info("Aggiornamento ELO nel database")
    for player_id, elo_change in final_changes.items():
        old_elo = get_player_current_elo(player_id, tournament_id, day_id)
        new_elo = old_elo + elo_change
        
        app.logger.info(f"Giocatore {player_id}: ELO {old_elo} -> {new_elo} (variazione {elo_change})")
        
        # Aggiorna o crea il record ELO del giocatore
        player_elo = PlayerTournamentElo.query.filter_by(
            player_id=player_id,
            tournament_id=tournament_id
        ).first()
        
        if not player_elo:
            player_elo = PlayerTournamentElo(
                player_id=player_id,
                          tournament_id=tournament_id,
                elo_rating=old_elo  # Usa l'ELO di partenza invece di 1500 fisso
            )
            db.session.add(player_elo)
            app.logger.info(f"Creato record ELO per giocatore {player_id}: ELO iniziale = {old_elo}")
        
        old_rating = player_elo.elo_rating
        player_elo.elo_rating = new_elo
        app.logger.info(f"Aggiornato ELO giocatore {player_id}: {old_rating} -> {new_elo} (cambio: {elo_change})")
        
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
        app.logger.info("Aggiornamento ELO completato con successo")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Errore durante l'aggiornamento ELO: {str(e)}")
        raise

@tournaments_bp.route('/tornei/<int:tournament_id>/giornate/<int:day_id>/export-results-pdf')
def export_gironi_results_pdf(tournament_id, day_id):
    """Esporta i risultati completi della giornata a gironi in PDF"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = GironiDay.query.get_or_404(day_id)
    
    if day.tournament_id != tournament_id:
        flash('Giornata non valida per questo torneo!', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    # Ottieni tutti i dati necessari
    players_ids = day.get_players()
    gironi = day.get_gironi()
    matches = day.get_matches()
    results = day.get_results()
    classifica = day.get_ranking()
    semifinali = day.get_semifinals()
    finali = day.get_finals()
    classifiche_gironi = day.get_group_standings()
    
    # Ottieni le informazioni dei giocatori
    players = Player.query.filter(Player.id.in_(players_ids)).all()
    players_by_id = {player.id: player for player in players}
    
    # Converti tutte le chiavi dei risultati in stringhe per compatibilità template
    if results:
        normalized_results = {}
        for key, value in results.items():
            # Aggiungi sia la chiave originale che quella stringa
            normalized_results[str(key)] = value
            normalized_results[key] = value
        results = normalized_results
    
    # Debug: Mostra cosa viene passato al template
    app.logger.info(f"HTML Export debug - Matches: {len(matches) if matches else 0}")
    app.logger.info(f"HTML Export debug - Results: {len(results) if results else 0}")
    app.logger.info(f"HTML Export debug - Gironi: {len(gironi) if gironi else 0}")
    if matches:
        app.logger.info(f"HTML Export debug - Prima partita: {matches[0]}")
        app.logger.info(f"HTML Export debug - Tutte le partite per girone 1: {[m for m in matches if m.get('girone') == 1]}")
    if results:
        app.logger.info(f"HTML Export debug - Primi risultati: {dict(list(results.items())[:5])}")
    
    # Restituisce direttamente l'HTML stampabile (come fanno i torneotto30/45)
    try:
        return render_template('tournaments/pdf/gironi_complete_results.html',
                          tournament=tournament,
                          day=day,
                              gironi=gironi,
                              matches=matches,
                              results=results,
                              classifica=classifica,
                          semifinali=semifinali,
                          finali=finali,
                              classifiche_gironi=classifiche_gironi,
                              players_by_id=players_by_id,
                              now=datetime.now())
        
    except Exception as e:
        app.logger.error(f"Errore durante la generazione del PDF: {str(e)}")
        flash('Errore durante la generazione del PDF', 'error')
        return redirect(url_for('tournaments.view_gironi_day', tournament_id=tournament_id, day_id=day_id))

@tournaments_bp.route('/export-pdf/torneo/<int:tournament_id>')
def export_pdf_tournament(tournament_id):
    """Genera la pagina HTML stampabile con le statistiche del torneo selezionato"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Recupera tutte le giornate del torneo
    days_30 = TorneOtto30Day.query.filter_by(tournament_id=tournament_id).all()
    days_45 = TorneOtto45Day.query.filter_by(tournament_id=tournament_id).all()
    days_gironi = GironiDay.query.filter_by(tournament_id=tournament_id).all()
    
    # Calcola statistiche specifiche
    stats = {}
    
    # Numero totale di giocatori
    all_players = set()
    for day in days_30:
        config = day.get_config()
        teams = config.get('teams', [])
        for team in teams:
            all_players.update(team)
    
    for day in days_45:
        classifica = day.get_ranking() or []
        all_players.update(classifica)
    
    for day in days_gironi:
        players_ids = day.get_players() or []
        all_players.update(players_ids)
    
    stats['numero_giocatori'] = len(all_players)
    
    # Giornate giocate
    completed_days = []
    for day in days_30 + days_45 + days_gironi:
        if day.stato == "Completata":
            completed_days.append(day)
    
    stats['giornate_giocate'] = len(completed_days)
    
    # Partite giocate in totale
    total_matches = 0
    for day in completed_days:
        if hasattr(day, 'get_config'):
            config = day.get_config()
            if 'matches' in config:
                total_matches += len(config.get('matches', []))
            elif 'schedule' in config:
                # Per TorneOtto30 conta le partite dallo schedule (3 turni x 2 partite = 6)
                schedule = config.get('schedule', [])
                for round_matches in schedule:
                    total_matches += len(round_matches)
            elif 'teams' in config:
                # Fallback: Per TorneOtto45 calcola le partite dalle squadre
                teams = config.get('teams', [])
                if len(teams) >= 2:
                    total_matches += len(teams) // 2
    
    stats['partite_totali'] = total_matches
    
    # Top 3 classificati
    try:
        # Usa la stessa logica della classifica torneo
        players_stats = {}
        
        # Calcola le statistiche per tutti i giocatori
        for player_id in all_players:
            elo_rating = PlayerTournamentElo.query.filter_by(
                player_id=player_id,
                tournament_id=tournament_id
            ).first()
            
            players_stats[player_id] = {
                'elo_rating': elo_rating.elo_rating if elo_rating else 1500.00,
                'presenze': 0
            }
            
            # Conta presenze
            for day in completed_days:
                if hasattr(day, 'get_config'):
                    config = day.get_config()
                    if 'teams' in config:
                        teams = config.get('teams', [])
                        for team in teams:
                            if player_id in team:
                                players_stats[player_id]['presenze'] += 1
                                break
                    elif 'matches' in config:
                        matches = config.get('matches', [])
                        for match in matches:
                            if player_id in match.get('team1', []) or player_id in match.get('team2', []):
                                players_stats[player_id]['presenze'] += 1
                                break
        
        # Ottieni i dati dei giocatori
        players = Player.query.filter(Player.id.in_(all_players)).all()
        players_with_stats = []
        
        for player in players:
            if player.id in players_stats:
                stats_data = players_stats[player.id]
                players_with_stats.append({
                    'id': player.id,
                    'nome': player.nome,
                    'cognome': player.cognome,
                    'elo_rating': stats_data['elo_rating'],
                    'presenze': stats_data['presenze']
                })
        
        # Ordina per ELO
        players_with_stats.sort(key=lambda x: x['elo_rating'], reverse=True)
        stats['top_5'] = players_with_stats[:5]
        
    except Exception as e:
        app.logger.error(f"Errore nel calcolo top 5: {str(e)}")
        stats['top_5'] = []
    
    # ============== STATISTICHE AVANZATE ==============
    
    # Inizializza strutture dati per le statistiche avanzate
    all_matches_data = []  # Lista di tutte le partite con dettagli
    pair_count = {}  # Conta coppie più frequenti
    pair_days = {}  # Conta giornate per coppia
    player_games_won = {}  # Games vinti per giocatore
    player_games_lost = {}  # Games persi per giocatore
    
    # Inizializza contatori per tutti i giocatori
    for player_id in all_players:
        player_games_won[player_id] = 0
        player_games_lost[player_id] = 0
    
    # === ANALIZZA TUTTE LE PARTITE DI TUTTE LE GIORNATE ===
    
    # TorneOtto30 Days
    for day in days_30:
        if day.stato != "Completata":
            continue
            
        config = day.get_config()
        teams = config.get('teams', [])
        schedule = config.get('schedule', [])
        results = config.get('results', {})
        
        # Set per tenere traccia delle coppie di questa giornata
        day_pairs = set()
        
        # Analizza ogni partita della giornata
        for round_matches in schedule:
            for match in round_matches:
                match_key = f"{match[0]}-{match[1]}"
                result = results.get(match_key)
                
                if result:
                    try:
                        score_a, score_b = map(int, result.split('-'))
                        
                        # Ottieni giocatori delle due squadre
                        team_a_players = teams[match[0]-1]
                        team_b_players = teams[match[1]-1] 
                        
                        # Registra la partita
                        match_data = {
                            'team_a': team_a_players,
                            'team_b': team_b_players,
                            'score_a': score_a,
                            'score_b': score_b,
                            'diff': abs(score_a - score_b),
                            'total_games': score_a + score_b
                        }
                        all_matches_data.append(match_data)
                        
                        # Conta coppie più frequenti
                        pair_a = tuple(sorted(team_a_players))
                        pair_b = tuple(sorted(team_b_players))
                        pair_count[pair_a] = pair_count.get(pair_a, 0) + 1
                        pair_count[pair_b] = pair_count.get(pair_b, 0) + 1
                        
                        # Aggiungi coppie al set della giornata
                        day_pairs.add(pair_a)
                        day_pairs.add(pair_b)
                        
                        # Conta games vinti/persi per giocatore
                        for player_id in team_a_players:
                            player_games_won[player_id] += score_a
                            player_games_lost[player_id] += score_b
                        
                        for player_id in team_b_players:
                            player_games_won[player_id] += score_b  
                            player_games_lost[player_id] += score_a
                            
                    except (ValueError, IndexError):
                        continue
        
        # Aggiorna contatore giornate per le coppie di questa giornata
        for pair in day_pairs:
            pair_days[pair] = pair_days.get(pair, 0) + 1
    
    # TorneOtto45 Days
    for day in days_45:
        if day.stato != "Completata":
            continue
            
        config = day.get_config()
        matches = config.get('matches', [])
        results = config.get('results', {})
        
        # Set per tenere traccia delle coppie di questa giornata
        day_pairs = set()
        
        # Analizza partite della fase a gironi
        for match in matches:
            match_id = str(match.get('id', ''))
            result = results.get(match_id, {})
            
            if result and 'squadra_a' in result and 'squadra_b' in result:
                try:
                    score_a = result['squadra_a']
                    score_b = result['squadra_b']
                    
                    team_a_players = match.get('team1', [])
                    team_b_players = match.get('team2', [])
                    
                    # Registra la partita
                    match_data = {
                        'team_a': team_a_players,
                        'team_b': team_b_players,
                        'score_a': score_a,
                        'score_b': score_b,
                        'diff': abs(score_a - score_b),
                        'total_games': score_a + score_b
                    }
                    all_matches_data.append(match_data)
                    
                    # Conta coppie più frequenti
                    if len(team_a_players) >= 2:
                        pair_a = tuple(sorted(team_a_players[:2]))
                        pair_count[pair_a] = pair_count.get(pair_a, 0) + 1
                        day_pairs.add(pair_a)
                    if len(team_b_players) >= 2:
                        pair_b = tuple(sorted(team_b_players[:2]))
                        pair_count[pair_b] = pair_count.get(pair_b, 0) + 1
                        day_pairs.add(pair_b)
                    
                    # Conta games vinti/persi per giocatore  
                    for player_id in team_a_players:
                        player_games_won[player_id] += score_a
                        player_games_lost[player_id] += score_b
                    
                    for player_id in team_b_players:
                        player_games_won[player_id] += score_b
                        player_games_lost[player_id] += score_a
                        
                except (ValueError, KeyError):
                    continue
        
        # Aggiorna contatore giornate per le coppie di questa giornata
        for pair in day_pairs:
            pair_days[pair] = pair_days.get(pair, 0) + 1
        
    # Gironi Days
    for day in days_gironi:
        if day.stato != "Completata":
            continue
            
        matches = day.get_matches()
        results = day.get_results()
        
        # Set per tenere traccia delle coppie di questa giornata
        day_pairs = set()
        
        # Analizza partite round robin
        if matches and results:
            for match in matches:
                match_id = str(match['id'])
                result = results.get(match_id, {})
                
                if result and 'squadra_a' in result and 'squadra_b' in result:
                    try:
                        score_a = result['squadra_a']
                        score_b = result['squadra_b']
                        
                        team_a_players = match.get('team1', [])
                        team_b_players = match.get('team2', [])
                        
                        # Registra la partita
                        match_data = {
                            'team_a': team_a_players,
                            'team_b': team_b_players,
                            'score_a': score_a,
                            'score_b': score_b,
                            'diff': abs(score_a - score_b),
                            'total_games': score_a + score_b
                        }
                        all_matches_data.append(match_data)
                        
                        # Conta coppie più frequenti
                        if len(team_a_players) >= 2:
                            pair_a = tuple(sorted(team_a_players[:2]))
                            pair_count[pair_a] = pair_count.get(pair_a, 0) + 1
                            day_pairs.add(pair_a)
                        if len(team_b_players) >= 2:
                            pair_b = tuple(sorted(team_b_players[:2]))
                            pair_count[pair_b] = pair_count.get(pair_b, 0) + 1
                            day_pairs.add(pair_b)
                        
                        # Conta games vinti/persi per giocatore
                        for player_id in team_a_players:
                            player_games_won[player_id] += score_a
                            player_games_lost[player_id] += score_b
                        
                        for player_id in team_b_players:
                            player_games_won[player_id] += score_b
                            player_games_lost[player_id] += score_a
                            
                    except (ValueError, KeyError):
                        continue
        
        # Aggiorna contatore giornate per le coppie di questa giornata
        for pair in day_pairs:
            pair_days[pair] = pair_days.get(pair, 0) + 1
    
    # === CALCOLA LE STATISTICHE FINALI ===
    
    # 1. Coppia più frequente
    if pair_count:
        most_frequent_pair = max(pair_count.items(), key=lambda x: x[1])
        pair_ids = most_frequent_pair[0]
        pair_frequency = most_frequent_pair[1]
        pair_days_count = pair_days.get(pair_ids, 0)
        
        try:
            pair_players = Player.query.filter(Player.id.in_(pair_ids)).all()
            if len(pair_players) >= 2:
                stats['coppia_frequente'] = f"{pair_players[0].nome} {pair_players[0].cognome} / {pair_players[1].nome} {pair_players[1].cognome} ({pair_days_count} Giornate / {pair_frequency} Partite)"
            else:
                stats['coppia_frequente'] = "Dati insufficienti"
        except:
            stats['coppia_frequente'] = "Errore nel calcolo"
    else:
        stats['coppia_frequente'] = "Nessuna coppia trovata"
    
    # 2. Partita con più alto scarto
    if all_matches_data:
        highest_diff_match = max(all_matches_data, key=lambda x: x['diff'])
        try:
            team_a_players = Player.query.filter(Player.id.in_(highest_diff_match['team_a'])).all()
            team_b_players = Player.query.filter(Player.id.in_(highest_diff_match['team_b'])).all()
            
            if len(team_a_players) >= 2 and len(team_b_players) >= 2:
                stats['partita_alto_scarto'] = f"{team_a_players[0].cognome}/{team_a_players[1].cognome} vs {team_b_players[0].cognome}/{team_b_players[1].cognome} ({highest_diff_match['score_a']}-{highest_diff_match['score_b']}, diff: {highest_diff_match['diff']})"
            else:
                stats['partita_alto_scarto'] = f"Scarto massimo: {highest_diff_match['diff']} games"
        except:
            stats['partita_alto_scarto'] = f"Scarto massimo: {highest_diff_match['diff']} games"
    else:
        stats['partita_alto_scarto'] = "Nessuna partita trovata"
    
    # 3. Partita con punteggi più bassi
    if all_matches_data:
        lowest_total_match = min(all_matches_data, key=lambda x: x['total_games'])
        try:
            team_a_players = Player.query.filter(Player.id.in_(lowest_total_match['team_a'])).all()
            team_b_players = Player.query.filter(Player.id.in_(lowest_total_match['team_b'])).all()
            
            if len(team_a_players) >= 2 and len(team_b_players) >= 2:
                stats['partita_bassi_punteggi'] = f"{team_a_players[0].cognome}/{team_a_players[1].cognome} vs {team_b_players[0].cognome}/{team_b_players[1].cognome} ({lowest_total_match['score_a']}-{lowest_total_match['score_b']}, totale: {lowest_total_match['total_games']})"
            else:
                stats['partita_bassi_punteggi'] = f"Punteggio più basso: {lowest_total_match['total_games']} games totali"
        except:
            stats['partita_bassi_punteggi'] = f"Punteggio più basso: {lowest_total_match['total_games']} games totali"
    else:
        stats['partita_bassi_punteggi'] = "Nessuna partita trovata"
    
    # 4. Giocatore che ha vinto più games
    if player_games_won:
        max_games_won_player_id = max(player_games_won.items(), key=lambda x: x[1])
        try:
            player = Player.query.get(max_games_won_player_id[0])
            if player:
                stats['giocatore_vinto_games'] = f"{player.nome} {player.cognome} ({max_games_won_player_id[1]} games)"
            else:
                stats['giocatore_vinto_games'] = f"Giocatore ID {max_games_won_player_id[0]} ({max_games_won_player_id[1]} games)"
        except:
            stats['giocatore_vinto_games'] = f"{max_games_won_player_id[1]} games"
    else:
        stats['giocatore_vinto_games'] = "Nessun dato disponibile"
    
    # 5. Giocatore che ha perso più games  
    if player_games_lost:
        max_games_lost_player_id = max(player_games_lost.items(), key=lambda x: x[1])
        try:
            player = Player.query.get(max_games_lost_player_id[0])
            if player:
                stats['giocatore_perso_games'] = f"{player.nome} {player.cognome} ({max_games_lost_player_id[1]} games)"
            else:
                stats['giocatore_perso_games'] = f"Giocatore ID {max_games_lost_player_id[0]} ({max_games_lost_player_id[1]} games)"
        except:
            stats['giocatore_perso_games'] = f"{max_games_lost_player_id[1]} games"
    else:
        stats['giocatore_perso_games'] = "Nessun dato disponibile"
    
    return render_template('tournaments/export_pdf_tournament.html', 
                          tournament=tournament,
                         stats=stats, 
                         print_view=True,
                         now=datetime.now())

@tournaments_bp.route('/export-pdf/torneo/<int:tournament_id>/pdf')
def export_pdf_tournament_print(tournament_id):
    """Genera la pagina HTML stampabile ottimizzata per PDF con TUTTE le statistiche"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # STESSO IDENTICO CODICE della route principale per avere TUTTE le statistiche
    
    # Recupera tutte le giornate del torneo
    days_30 = TorneOtto30Day.query.filter_by(tournament_id=tournament_id).all()
    days_45 = TorneOtto45Day.query.filter_by(tournament_id=tournament_id).all()
    days_gironi = GironiDay.query.filter_by(tournament_id=tournament_id).all()
    
    # Calcola statistiche specifiche
    stats = {}
    
    # Numero totale di giocatori
    all_players = set()
    for day in days_30:
        config = day.get_config()
        teams = config.get('teams', [])
        for team in teams:
            all_players.update(team)
    
    for day in days_45:
        classifica = day.get_ranking() or []
        all_players.update(classifica)
    
    for day in days_gironi:
        players_ids = day.get_players() or []
        all_players.update(players_ids)
    
    stats['numero_giocatori'] = len(all_players)
    
    # Giornate giocate
    completed_days = []
    for day in days_30 + days_45 + days_gironi:
        if day.stato == "Completata":
            completed_days.append(day)
    
    stats['giornate_giocate'] = len(completed_days)
    
    # Partite giocate in totale
    total_matches = 0
    for day in completed_days:
        if hasattr(day, 'get_config'):
            config = day.get_config()
            if 'matches' in config:
                total_matches += len(config.get('matches', []))
            elif 'schedule' in config:
                # Per TorneOtto30 conta le partite dallo schedule (3 turni x 2 partite = 6)
                schedule = config.get('schedule', [])
                for round_matches in schedule:
                    total_matches += len(round_matches)
            elif 'teams' in config:
                # Fallback: Per TorneOtto45 calcola le partite dalle squadre
                teams = config.get('teams', [])
                if len(teams) >= 2:
                    total_matches += len(teams) // 2
    
    stats['partite_totali'] = total_matches
    
    # Top 5 classificati
    try:
        # Usa la stessa logica della classifica torneo
        players_stats = {}
        
        # Calcola le statistiche per tutti i giocatori
        for player_id in all_players:
            elo_rating = PlayerTournamentElo.query.filter_by(
                player_id=player_id,
                tournament_id=tournament_id
            ).first()
            
            players_stats[player_id] = {
                'elo_rating': elo_rating.elo_rating if elo_rating else 1500.00,
                'presenze': 0
            }
            
            # Conta presenze
            for day in completed_days:
                if hasattr(day, 'get_config'):
                    config = day.get_config()
                    if 'teams' in config:
                        teams = config.get('teams', [])
                        for team in teams:
                            if player_id in team:
                                players_stats[player_id]['presenze'] += 1
                                break
                    elif 'matches' in config:
                        matches = config.get('matches', [])
                        for match in matches:
                            if player_id in match.get('team1', []) or player_id in match.get('team2', []):
                                players_stats[player_id]['presenze'] += 1
                                break
        
        # Ottieni i dati dei giocatori
        players = Player.query.filter(Player.id.in_(all_players)).all()
        players_with_stats = []
        
        for player in players:
            if player.id in players_stats:
                stats_data = players_stats[player.id]
                players_with_stats.append({
                    'id': player.id,
                    'nome': player.nome,
                    'cognome': player.cognome,
                    'elo_rating': stats_data['elo_rating'],
                    'presenze': stats_data['presenze']
                })
        
        # Ordina per ELO
        players_with_stats.sort(key=lambda x: x['elo_rating'], reverse=True)
        stats['top_5'] = players_with_stats[:5]
        
    except Exception as e:
        app.logger.error(f"Errore nel calcolo top 5: {str(e)}")
        stats['top_5'] = []
    
    # ============== STATISTICHE AVANZATE ==============
    
    # Inizializza strutture dati per le statistiche avanzate
    all_matches_data = []  # Lista di tutte le partite con dettagli
    pair_count = {}  # Conta coppie più frequenti
    pair_days = {}  # Conta giornate per coppia
    player_games_won = {}  # Games vinti per giocatore
    player_games_lost = {}  # Games persi per giocatore
    
    # Inizializza contatori per tutti i giocatori
    for player_id in all_players:
        player_games_won[player_id] = 0
        player_games_lost[player_id] = 0
    
    # === ANALIZZA TUTTE LE PARTITE DI TUTTE LE GIORNATE ===
    
    # TorneOtto30 Days
    for day in days_30:
        if day.stato != "Completata":
            continue
            
        config = day.get_config()
        teams = config.get('teams', [])
        schedule = config.get('schedule', [])
        results = config.get('results', {})
        
        # Set per tenere traccia delle coppie di questa giornata
        day_pairs = set()
        
        # Analizza ogni partita della giornata
        for round_matches in schedule:
            for match in round_matches:
                match_key = f"{match[0]}-{match[1]}"
                result = results.get(match_key)
                
                if result:
                    try:
                        score_a, score_b = map(int, result.split('-'))
                        
                        # Ottieni giocatori delle due squadre
                        team_a_players = teams[match[0]-1]
                        team_b_players = teams[match[1]-1] 
                        
                        # Registra la partita
                        match_data = {
                            'team_a': team_a_players,
                            'team_b': team_b_players,
                            'score_a': score_a,
                            'score_b': score_b,
                            'diff': abs(score_a - score_b),
                            'total_games': score_a + score_b
                        }
                        all_matches_data.append(match_data)
                        
                        # Conta coppie più frequenti
                        pair_a = tuple(sorted(team_a_players))
                        pair_b = tuple(sorted(team_b_players))
                        pair_count[pair_a] = pair_count.get(pair_a, 0) + 1
                        pair_count[pair_b] = pair_count.get(pair_b, 0) + 1
                        
                        # Aggiungi coppie al set della giornata
                        day_pairs.add(pair_a)
                        day_pairs.add(pair_b)
                        
                        # Conta games vinti/persi per giocatore
                        for player_id in team_a_players:
                            player_games_won[player_id] += score_a
                            player_games_lost[player_id] += score_b
                        
                        for player_id in team_b_players:
                            player_games_won[player_id] += score_b  
                            player_games_lost[player_id] += score_a
                            
                    except (ValueError, IndexError):
                        continue
        
        # Aggiorna contatore giornate per le coppie di questa giornata
        for pair in day_pairs:
            pair_days[pair] = pair_days.get(pair, 0) + 1
    
    # TorneOtto45 Days
    for day in days_45:
        if day.stato != "Completata":
            continue
            
        config = day.get_config()
        matches = config.get('matches', [])
        results = config.get('results', {})
        
        # Set per tenere traccia delle coppie di questa giornata
        day_pairs = set()
        
        # Analizza partite della fase a gironi
        for match in matches:
            match_id = str(match.get('id', ''))
            result = results.get(match_id, {})
            
            if result and 'squadra_a' in result and 'squadra_b' in result:
                try:
                    score_a = result['squadra_a']
                    score_b = result['squadra_b']
                    
                    team_a_players = match.get('team1', [])
                    team_b_players = match.get('team2', [])
                    
                    # Registra la partita
                    match_data = {
                        'team_a': team_a_players,
                        'team_b': team_b_players,
                        'score_a': score_a,
                        'score_b': score_b,
                        'diff': abs(score_a - score_b),
                        'total_games': score_a + score_b
                    }
                    all_matches_data.append(match_data)
                    
                    # Conta coppie più frequenti
                    if len(team_a_players) >= 2:
                        pair_a = tuple(sorted(team_a_players[:2]))
                        pair_count[pair_a] = pair_count.get(pair_a, 0) + 1
                        day_pairs.add(pair_a)
                    if len(team_b_players) >= 2:
                        pair_b = tuple(sorted(team_b_players[:2]))
                        pair_count[pair_b] = pair_count.get(pair_b, 0) + 1
                        day_pairs.add(pair_b)
                    
                    # Conta games vinti/persi per giocatore  
                    for player_id in team_a_players:
                        player_games_won[player_id] += score_a
                        player_games_lost[player_id] += score_b
                    
                    for player_id in team_b_players:
                        player_games_won[player_id] += score_b
                        player_games_lost[player_id] += score_a
                        
                except (ValueError, KeyError):
                    continue
        
        # Aggiorna contatore giornate per le coppie di questa giornata
        for pair in day_pairs:
            pair_days[pair] = pair_days.get(pair, 0) + 1
        
    # Gironi Days
    for day in days_gironi:
        if day.stato != "Completata":
            continue
            
        matches = day.get_matches()
        results = day.get_results()
        
        # Set per tenere traccia delle coppie di questa giornata
        day_pairs = set()
        
        # Analizza partite round robin
        if matches and results:
            for match in matches:
                match_id = str(match['id'])
                result = results.get(match_id, {})
                
                if result and 'squadra_a' in result and 'squadra_b' in result:
                    try:
                        score_a = result['squadra_a']
                        score_b = result['squadra_b']
                        
                        team_a_players = match.get('team1', [])
                        team_b_players = match.get('team2', [])
                        
                        # Registra la partita
                        match_data = {
                            'team_a': team_a_players,
                            'team_b': team_b_players,
                            'score_a': score_a,
                            'score_b': score_b,
                            'diff': abs(score_a - score_b),
                            'total_games': score_a + score_b
                        }
                        all_matches_data.append(match_data)
                        
                        # Conta coppie più frequenti
                        if len(team_a_players) >= 2:
                            pair_a = tuple(sorted(team_a_players[:2]))
                            pair_count[pair_a] = pair_count.get(pair_a, 0) + 1
                            day_pairs.add(pair_a)
                        if len(team_b_players) >= 2:
                            pair_b = tuple(sorted(team_b_players[:2]))
                            pair_count[pair_b] = pair_count.get(pair_b, 0) + 1
                            day_pairs.add(pair_b)
                        
                        # Conta games vinti/persi per giocatore
                        for player_id in team_a_players:
                            player_games_won[player_id] += score_a
                            player_games_lost[player_id] += score_b
                        
                        for player_id in team_b_players:
                            player_games_won[player_id] += score_b
                            player_games_lost[player_id] += score_a
                            
                    except (ValueError, KeyError):
                        continue
        
        # Aggiorna contatore giornate per le coppie di questa giornata
        for pair in day_pairs:
            pair_days[pair] = pair_days.get(pair, 0) + 1
    
    # === CALCOLA LE STATISTICHE FINALI ===
    
    # 1. Coppia più frequente
    if pair_count:
        most_frequent_pair = max(pair_count.items(), key=lambda x: x[1])
        pair_ids = most_frequent_pair[0]
        pair_frequency = most_frequent_pair[1]
        pair_days_count = pair_days.get(pair_ids, 0)
        
        try:
            pair_players = Player.query.filter(Player.id.in_(pair_ids)).all()
            if len(pair_players) >= 2:
                stats['coppia_frequente'] = f"{pair_players[0].nome} {pair_players[0].cognome} / {pair_players[1].nome} {pair_players[1].cognome} ({pair_days_count} Giornate / {pair_frequency} Partite)"
            else:
                stats['coppia_frequente'] = "Dati insufficienti"
        except:
            stats['coppia_frequente'] = "Errore nel calcolo"
    else:
        stats['coppia_frequente'] = "Nessuna coppia trovata"
    
    # 2. Partita con più alto scarto
    if all_matches_data:
        highest_diff_match = max(all_matches_data, key=lambda x: x['diff'])
        try:
            team_a_players = Player.query.filter(Player.id.in_(highest_diff_match['team_a'])).all()
            team_b_players = Player.query.filter(Player.id.in_(highest_diff_match['team_b'])).all()
            
            if len(team_a_players) >= 2 and len(team_b_players) >= 2:
                stats['partita_alto_scarto'] = f"{team_a_players[0].cognome}/{team_a_players[1].cognome} vs {team_b_players[0].cognome}/{team_b_players[1].cognome} ({highest_diff_match['score_a']}-{highest_diff_match['score_b']}, diff: {highest_diff_match['diff']})"
            else:
                stats['partita_alto_scarto'] = f"Scarto massimo: {highest_diff_match['diff']} games"
        except:
            stats['partita_alto_scarto'] = f"Scarto massimo: {highest_diff_match['diff']} games"
    else:
        stats['partita_alto_scarto'] = "Nessuna partita trovata"
    
    # 3. Partita con punteggi più bassi
    if all_matches_data:
        lowest_total_match = min(all_matches_data, key=lambda x: x['total_games'])
        try:
            team_a_players = Player.query.filter(Player.id.in_(lowest_total_match['team_a'])).all()
            team_b_players = Player.query.filter(Player.id.in_(lowest_total_match['team_b'])).all()
            
            if len(team_a_players) >= 2 and len(team_b_players) >= 2:
                stats['partita_bassi_punteggi'] = f"{team_a_players[0].cognome}/{team_a_players[1].cognome} vs {team_b_players[0].cognome}/{team_b_players[1].cognome} ({lowest_total_match['score_a']}-{lowest_total_match['score_b']}, totale: {lowest_total_match['total_games']})"
            else:
                stats['partita_bassi_punteggi'] = f"Punteggio più basso: {lowest_total_match['total_games']} games totali"
        except:
            stats['partita_bassi_punteggi'] = f"Punteggio più basso: {lowest_total_match['total_games']} games totali"
    else:
        stats['partita_bassi_punteggi'] = "Nessuna partita trovata"
    
    # 4. Giocatore che ha vinto più games
    if player_games_won:
        max_games_won_player_id = max(player_games_won.items(), key=lambda x: x[1])
        try:
            player = Player.query.get(max_games_won_player_id[0])
            if player:
                stats['giocatore_vinto_games'] = f"{player.nome} {player.cognome} ({max_games_won_player_id[1]} games)"
            else:
                stats['giocatore_vinto_games'] = f"Giocatore ID {max_games_won_player_id[0]} ({max_games_won_player_id[1]} games)"
        except:
            stats['giocatore_vinto_games'] = f"{max_games_won_player_id[1]} games"
    else:
        stats['giocatore_vinto_games'] = "Nessun dato disponibile"
    
    # 5. Giocatore che ha perso più games  
    if player_games_lost:
        max_games_lost_player_id = max(player_games_lost.items(), key=lambda x: x[1])
        try:
            player = Player.query.get(max_games_lost_player_id[0])
            if player:
                stats['giocatore_perso_games'] = f"{player.nome} {player.cognome} ({max_games_lost_player_id[1]} games)"
            else:
                stats['giocatore_perso_games'] = f"Giocatore ID {max_games_lost_player_id[0]} ({max_games_lost_player_id[1]} games)"
        except:
            stats['giocatore_perso_games'] = f"{max_games_lost_player_id[1]} games"
    else:
        stats['giocatore_perso_games'] = "Nessun dato disponibile"
    
    return render_template('tournaments/pdf/stats_tournament_summary.html', 
                         tournament=tournament, 
                         stats=stats, 
                         now=datetime.now())

# FUNZIONI DI SUPPORTO PER ELIMINAZIONE

def create_elimination_bracket(elim_tournament, team_names_list):
    """Crea il tabellone di eliminazione con gestione corretta di bye e seeding"""
    from models.elimin_day import EliminationTeam, EliminationMatch
    import random
    import math
    
    # Pulisci eventuali dati esistenti
    EliminationMatch.query.filter_by(tournament_id=elim_tournament.id).delete()
    EliminationTeam.query.filter_by(tournament_id=elim_tournament.id).delete()
    
    # Ottieni la configurazione del torneo per le teste di serie
    config = elim_tournament.get_config()
    seeds_list = config.get('seeds', [])
    
    # Calcola il numero di squadre necessario (prossima potenza di 2)
    num_teams = len(team_names_list)
    elim_tournament.num_squadre = elim_tournament.get_next_power_of_2(num_teams)
    num_byes = elim_tournament.num_squadre - num_teams
    
    app.logger.info(f"Creazione tabellone: {num_teams} squadre -> {elim_tournament.num_squadre} posizioni, {num_byes} bye necessari")
    app.logger.info(f"Teste di serie configurate: {seeds_list}")
    
    # FASE 1: Crea e classifica le squadre per seeding
    teams = []
    seeded_teams = []
    non_seeded_teams = []
    
    for i, team_name in enumerate(team_names_list):
        team = EliminationTeam(
            tournament_id=elim_tournament.id,
            team_name=team_name,
            posizione_seed=i + 1
        )
        team.set_players([team_name])
        teams.append(team)
        db.session.add(team)
        
        # Classifica se è una testa di serie
        if team_name in seeds_list:
            seeded_teams.append(team)
        else:
            non_seeded_teams.append(team)
    
    # CORREZIONE: Commit prima del flush per evitare errori con ID None
    db.session.commit()
    
    # FASE 2: Crea le squadre BYE
    bye_teams = []
    for i in range(num_byes):
        bye_team = EliminationTeam(
            tournament_id=elim_tournament.id,
            team_name="BYE",
            is_bye=True,
            posizione_seed=len(teams) + i + 1
        )
        bye_team.set_players([])
        bye_teams.append(bye_team)
        db.session.add(bye_team)
    
    # Commit anche per i bye teams
    db.session.commit()
    
    # FASE 3: Posizionamento strategico nel tabellone
    bracket_positions = create_seeded_bracket_positions(elim_tournament.num_squadre, seeded_teams, non_seeded_teams, bye_teams)
    
    # FASE 4: Crea le partite del primo turno
    num_first_round_matches = elim_tournament.num_squadre // 2
    
    app.logger.info(f"Creando {num_first_round_matches} partite per il primo turno")
    app.logger.info(f"Posizioni bracket: {len(bracket_positions)} squadre posizionate")
    
    # DEBUG: Log delle posizioni del bracket
    for idx, team in enumerate(bracket_positions):
        if team:
            app.logger.info(f"Posizione {idx}: {team.team_name} (ID: {team.id})")
        else:
            app.logger.error(f"Posizione {idx}: NONE!")
    
    for i in range(num_first_round_matches):
        team1 = bracket_positions[i * 2]
        team2 = bracket_positions[i * 2 + 1]
        
        # Verifica che entrambe le squadre esistano
        if team1 is None or team2 is None:
            app.logger.error(f"ERRORE CRITICO: Una delle squadre è None nella partita {i+1}. Team1: {team1}, Team2: {team2}")
            app.logger.error(f"Bracket positions length: {len(bracket_positions)}, accessing indices {i*2} and {i*2+1}")
            continue
        
        try:
            match = EliminationMatch(
                tournament_id=elim_tournament.id,
                turno=1,
                posizione_turno=i + 1,
                team1_id=team1.id,
                team2_id=team2.id,
                bracket_type='winner'
            )
            
            # Se una squadra è bye, imposta automaticamente il vincitore
            if team1.is_bye:
                match.winner_team_id = team2.id
                match.stato = 'Completed'
                app.logger.info(f"PARTITA {i+1}: {team2.team_name} avanza automaticamente (bye vs {team1.team_name})")
            elif team2.is_bye:
                match.winner_team_id = team1.id
                match.stato = 'Completed'
                app.logger.info(f"PARTITA {i+1}: {team1.team_name} avanza automaticamente ({team1.team_name} vs bye)")
            else:
                app.logger.info(f"PARTITA {i+1}: {team1.team_name} vs {team2.team_name} - NORMALE")
            
            db.session.add(match)
            app.logger.info(f"AGGIUNTA partita {i+1} al database con successo")
            
        except Exception as e:
            app.logger.error(f"ERRORE nella creazione della partita {i+1}: {str(e)}")
            app.logger.error(f"Team1: {team1}, Team2: {team2}")
            continue
        
    # Se è doppia eliminazione, crea anche il bracket dei perdenti
    if elim_tournament.tipo_eliminazione == 'double':
        create_double_elimination_bracket(elim_tournament, bracket_positions)
    
    # Aggiorna lo stato del torneo a "In Corso" dopo aver creato il tabellone
    elim_tournament.stato = 'In Corso'
    db.session.commit()

    # Crea automaticamente i turni successivi per le partite già completate (bye)
    completed_matches = EliminationMatch.query.filter_by(
        tournament_id=elim_tournament.id,
        turno=1,
        stato='Completed'
    ).all()
    
    for match in completed_matches:
        create_next_round_matches(elim_tournament, match)

def create_double_elimination_bracket(elim_tournament, teams):
    """Crea il bracket dei perdenti per la doppia eliminazione"""
    # Implementazione più complessa per la doppia eliminazione
    # Per ora, placeholder
    pass

def process_elimination_results(elim_tournament, form_data):
    """Processa i risultati delle partite"""
    from models.elimin_day import EliminationMatch, EliminationTeam
    
    for key, value in form_data.items():
        if key.startswith('match_') and '_winner' in key:
            match_id = int(key.split('_')[1])
            winner_team_id = int(value) if value else None
            
            match = EliminationMatch.query.get(match_id)
            if match and winner_team_id:
                # Recupera i punteggi
                team1_score = form_data.get(f'match_{match_id}_team1_score')
                team2_score = form_data.get(f'match_{match_id}_team2_score')
                
                match.team1_score = int(team1_score) if team1_score else 0
                match.team2_score = int(team2_score) if team2_score else 0
                match.winner_team_id = winner_team_id
                match.stato = 'Completed'
                match.data_partita = datetime.now()
                
                # Aggiorna il contatore delle sconfitte per doppia eliminazione
                if elim_tournament.tipo_eliminazione == 'double':
                    loser_team_id = match.team1_id if winner_team_id == match.team2_id else match.team2_id
                    loser_team = EliminationTeam.query.get(loser_team_id)
                    if loser_team:
                        loser_team.sconfitte += 1
                        if loser_team.sconfitte >= 2:
                            loser_team.eliminata = True
                
                # Crea la prossima partita se necessario
                create_next_round_matches(elim_tournament, match)
    
    db.session.commit()

def get_round_name_and_info(elim_tournament, current_round):
    """Determina il nome del turno e le informazioni correlate"""
    total_rounds = elim_tournament.get_num_rounds()
    
    # Calcola il numero di squadre rimanenti in questo turno
    teams_in_round = elim_tournament.num_squadre // (2 ** (current_round - 1))
    total_matches_in_round = teams_in_round // 2
    
    # Determina il nome del turno basato sul numero di squadre
    if teams_in_round == 2:
        round_name = "Finale"
    elif teams_in_round == 4:
        round_name = "Semifinali"
    elif teams_in_round == 8:
        round_name = "Quarti di Finale"
    elif teams_in_round == 16:
        round_name = "Ottavi di Finale"
    elif teams_in_round == 32:
        round_name = "Sedicesimi di Finale"
    else:
        # Per tornei con molte squadre o casi speciali
        if current_round == 1:
            round_name = "Primo Turno"
        else:
            round_name = f"Turno {current_round}"
    
    return round_name, total_matches_in_round

def create_next_round_matches(elim_tournament, completed_match):
    """Crea le partite del turno successivo"""
    from models.elimin_day import EliminationMatch, EliminationTeam
    
    # Ottieni tutte le partite del turno corrente
    current_round = completed_match.turno
    current_round_matches = EliminationMatch.query.filter_by(
        tournament_id=elim_tournament.id,
        turno=current_round,
        bracket_type='winner'
    ).all()
    
    # Controlla se tutte le partite del turno corrente sono completate
    completed_matches = [m for m in current_round_matches if m.stato == 'Completed']
    
    if len(completed_matches) != len(current_round_matches):
        # Non tutte le partite del turno sono completate
        return
    
    # Raccogli tutti i vincitori del turno corrente
    winners = []
    for match in completed_matches:
        if match.winner_team_id:
            winner_team = EliminationTeam.query.get(match.winner_team_id)
            if winner_team:
                winners.append(winner_team)
    
    # Se c'è solo un vincitore, il torneo è finito
    if len(winners) <= 1:
        elim_tournament.stato = 'Completed'
        db.session.commit()
        return
    
    # Crea le partite del turno successivo
    next_round = current_round + 1
    num_next_matches = len(winners) // 2
    
    app.logger.info(f"Creando {num_next_matches} partite per il turno {next_round}")
    
    for i in range(num_next_matches):
        team1 = winners[i * 2]
        team2 = winners[i * 2 + 1]
        
        next_match = EliminationMatch(
            tournament_id=elim_tournament.id,
            turno=next_round,
            posizione_turno=i + 1,
            team1_id=team1.id,
            team2_id=team2.id,
            bracket_type='winner'
        )
        
        db.session.add(next_match)
        app.logger.info(f"Creata partita {i+1} del turno {next_round}: Team {team1.id} vs Team {team2.id}")
    
    db.session.commit()

def create_seeded_bracket_positions(num_teams, seeded_teams, non_seeded_teams, bye_teams):
    """Crea una disposizione di squadre nel tabellone con seeding e bye"""
    import random
    
    # Crea una lista di posizioni vuote
    positions = [None] * num_teams
    
    # DEBUG: Log iniziale
    app.logger.info(f"create_seeded_bracket_positions: num_teams={num_teams}")
    app.logger.info(f"Teste di serie: {len(seeded_teams)}")
    app.logger.info(f"Non seeded: {len(non_seeded_teams)}")
    app.logger.info(f"Bye teams: {len(bye_teams)}")
    
    # Unisce tutte le squadre in un'unica lista mantenendo l'ordine di priorità
    all_teams = []
    
    # Prima le teste di serie
    all_teams.extend(seeded_teams)
    app.logger.info(f"Dopo seeded: {len(all_teams)} squadre")
    
    # Poi le squadre non di testa di serie (mischiate)
    random.shuffle(non_seeded_teams)
    all_teams.extend(non_seeded_teams)
    app.logger.info(f"Dopo non-seeded: {len(all_teams)} squadre")
    
    # Infine i bye
    all_teams.extend(bye_teams)
    app.logger.info(f"Totale squadre da posizionare: {len(all_teams)}")
    
    # Posiziona le squadre sequenzialmente nelle posizioni disponibili
    for i, team in enumerate(all_teams):
        if i < num_teams:
            positions[i] = team
            app.logger.info(f"Posizione {i}: {team.team_name} (ID: {team.id})")
        else:
            app.logger.warning(f"Più squadre ({len(all_teams)}) che posizioni disponibili ({num_teams})")
            break
    
    # Verifica che tutte le posizioni siano riempite
    none_count = positions.count(None)
    if none_count > 0:
        app.logger.error(f"Ci sono {none_count} posizioni vuote nel tabellone. Totale squadre: {len(all_teams)}, Posizioni: {num_teams}")
        
        # Riempi le posizioni vuote con squadre bye aggiuntive se necessario
        for i in range(num_teams):
            if positions[i] is None:
                from models.elimin_day import EliminationTeam
                # Questo non dovrebbe succedere, ma aggiungiamo un controllo di sicurezza
                app.logger.error(f"Posizione {i} è None - questo non dovrebbe succedere!")
    
    return positions

@tournaments_bp.route('/tornei/<int:tournament_id>/eliminazione/export-pdf')
def export_elimination_pdf(tournament_id):
    """Esporta il tabellone di eliminazione in PDF"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    from models.elimin_day import EliminationTournament, EliminationMatch, EliminationTeam
    elim_tournament = EliminationTournament.query.filter_by(tournament_id=tournament_id).first()
    
    if not elim_tournament:
        flash('Torneo ad eliminazione non trovato', 'error')
        return redirect(url_for('tournaments.tournaments_list'))
    
    # Recupera tutte le partite con le relazioni precaricate
    matches = EliminationMatch.query.filter_by(tournament_id=elim_tournament.id).options(
        db.joinedload(EliminationMatch.team1),
        db.joinedload(EliminationMatch.team2),
        db.joinedload(EliminationMatch.winner_team)
    ).order_by(EliminationMatch.turno, EliminationMatch.posizione_turno).all()
    
    # Recupera tutte le squadre
    teams = EliminationTeam.query.filter_by(tournament_id=elim_tournament.id).all()
    
    # DEBUG: Log per verificare quante partite abbiamo
    app.logger.info(f"Export PDF: Trovate {len(matches)} partite per il torneo {tournament_id}")
    for match in matches:
        team1_name = match.team1.team_name if match.team1 else "None"
        team2_name = match.team2.team_name if match.team2 else "None"
        app.logger.info(f"Partita turno {match.turno}, pos {match.posizione_turno}: {team1_name} vs {team2_name}")
    
    # Non serve recuperare i giocatori per questo template
    # Le squadre contengono già i nomi dei giocatori
    players_dict = {}
    
    # Organizza le partite per turno
    matches_by_round = {}
    for match in matches:
        round_key = f"{match.bracket_type}_{match.turno}"
        if round_key not in matches_by_round:
            matches_by_round[round_key] = []
        matches_by_round[round_key].append(match)
    
    # DEBUG: Log per verificare l'organizzazione dei turni
    app.logger.info(f"Export PDF: Turni organizzati: {list(matches_by_round.keys())}")
    for round_key, round_matches in matches_by_round.items():
        app.logger.info(f"Turno {round_key}: {len(round_matches)} partite")
    
    return render_template('tournaments/pdf/elimination_bracket.html',
                         tournament=tournament,
                          elim_tournament=elim_tournament,
                          matches=matches,
                         matches_by_round=matches_by_round,
                         teams=teams,
                         players_dict=players_dict,
                         now=datetime.now())

# ===== ROUTE PER TORNEO ALL'AMERICANA =====

@tournaments_bp.route('/tornei/<int:tournament_id>/nuova-giornata/americana', methods=['GET', 'POST'])
def new_americana_day(tournament_id):
    """Creazione di una nuova giornata per torneo all'americana"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    if tournament.tipo_torneo != 'americana':
        flash('Questo non è un torneo all\'americana!', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    # Controlla se esiste già una giornata
    # existing_day = AmericanaDay.query.filter_by(tournament_id=tournament_id).first()
    # if existing_day:
    #     flash('Esiste già una giornata per questo torneo!', 'warning')
    #     return redirect(url_for('tournaments.view_americana_day', tournament_id=tournament_id, day_id=existing_day.id))
    
    config = tournament.get_config()
    
    return render_template('tournaments/americana/player_selection.html', 
                             tournament=tournament,
                         config=config)

@tournaments_bp.route('/tornei/<int:tournament_id>/americana/players', methods=['POST'])
def americana_players(tournament_id):
    """Gestione della selezione dei giocatori per il torneo americana"""
    tournament = Tournament.query.get_or_404(tournament_id)
    config = tournament.get_config()
    origine_giocatori = config.get('origine_giocatori')
    
    if origine_giocatori == 'caricati':
        # Mostra lista giocatori dal database
        players = Player.query.all()
        return render_template('tournaments/americana/select_players.html',
                             tournament=tournament,
                             players=players,
                             config=config)
    else:
        # Pagina di inserimento manuale
        return render_template('tournaments/americana/manual_players.html',
                         tournament=tournament,
                             config=config)

@tournaments_bp.route('/tornei/<int:tournament_id>/americana/setup', methods=['POST'])
def americana_setup(tournament_id):
    """Setup delle coppie e generazione delle partite"""
    tournament = Tournament.query.get_or_404(tournament_id)
    config = tournament.get_config()
    
    # Recupera i giocatori selezionati
    if config.get('origine_giocatori') == 'caricati':
        selected_players_str = request.form.get('selected_players', '')
        if selected_players_str:
            selected_player_ids = selected_players_str.split(',')
        else:
            selected_player_ids = []
        
        players = []
        for player_id in selected_player_ids:
            if player_id.strip():  # Skip empty strings
                player = Player.query.get(player_id.strip())
                if player:
                    players.append({
                        'id': player.id,
                        'name': f"{player.nome} {player.cognome}"
                    })
    else:
        # Giocatori inseriti manualmente
        players = []
        i = 1
        while f'player_{i}_name' in request.form:
            name = request.form.get(f'player_{i}_name')
            if name and name.strip():
                players.append({
                    'id': f'manual_{i}',
                    'name': name.strip()
                })
            i += 1
    
    # CORREZIONE: Il numero di giocatori deve essere pari e deve corrispondere al numero di coppie * 2
    num_coppie = config.get('num_coppie', 8)
    expected_players = num_coppie * 2
    
    if len(players) != expected_players:
        flash(f'Devi selezionare esattamente {expected_players} giocatori per formare {num_coppie} coppie! (Attualmente: {len(players)} giocatori)', 'error')
        return redirect(url_for('tournaments.americana_players', tournament_id=tournament_id))
    
    # Validazione nomi unici
    player_names = [p['name'] for p in players]
    if len(set(player_names)) != len(player_names):
        flash('Alcuni giocatori hanno nomi duplicati! Ogni giocatore deve avere un nome unico.', 'error')
        return redirect(url_for('tournaments.americana_players', tournament_id=tournament_id))
    
    # Gestione teste di serie se necessario
    seeds = []
    if config.get('metodo_formazione') == 'teste_serie':
        # Le teste di serie sono pari al numero di coppie
        num_seeds = num_coppie
        seeded_players_str = request.form.get('seeded_players', '')
        if seeded_players_str:
            seeded_player_ids = seeded_players_str.split(',')
            for player_id in seeded_player_ids:
                if player_id.strip():
                    # Trova il giocatore nella lista dei giocatori selezionati
                    for player in players:
                        if str(player['id']) == player_id.strip():
                            seeds.append(player)
                            break
        
        # Se abbiamo teste di serie, le mettiamo in cima alla lista
        if seeds:
            non_seeds = [p for p in players if p not in seeds]
            players = seeds + non_seeds
    
    try:
        # Crea le coppie/squadre
        if config.get('tipo_coppie') == 'fisse':
            teams = AmericanaService.create_teams_fixed(players, config.get('metodo_formazione'))
        else:  # coppie giranti
            teams = AmericanaService.create_teams_rotating(players)
        
        # Genera le partite
        if config.get('tipo_coppie') == 'fisse':
            if config.get('tipo_torneo') == 'semplice':
                # CORREZIONE: Per torneo semplice all'americana, usa l'algoritmo delle coppie giranti
                # anche per le coppie fisse, ma con le coppie già formate
                matches = AmericanaService.generate_simplified_matches(teams, num_coppie)
            else:  # completo
                matches = AmericanaService.generate_round_robin_matches(teams)
        else:  # coppie giranti
            # CORREZIONE: Per coppie giranti, numero turni = numero giocatori - 1
            num_rounds = len(players) - 1
            matches = AmericanaService.generate_rotating_pairs_matches(players, num_rounds)
        
        # Distribuisci le partite sui campi
        matches, court_schedule = AmericanaService.distribute_matches_to_courts(
            matches, config.get('num_campi', 4)
        )
        
        # Crea la giornata del torneo
        day = AmericanaDay(
            tournament_id=tournament_id,
            data=date.today(),
            stato="Setup completato"
        )
        
        day.set_players(players)
        day.set_teams(teams)
        day.set_matches(matches)
        day.set_courts(list(range(1, config.get('num_campi', 4) + 1)))
        
        db.session.add(day)
        db.session.commit()
        
        flash('Setup del torneo completato con successo!', 'success')
        return redirect(url_for('tournaments.view_americana_day', 
                               tournament_id=tournament_id, 
                               day_id=day.id))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il setup: {str(e)}', 'error')
        return redirect(url_for('tournaments.americana_players', tournament_id=tournament_id))

@tournaments_bp.route('/tornei/<int:tournament_id>/americana/<int:day_id>')
def view_americana_day(tournament_id, day_id):
    """Visualizza la giornata del torneo americana"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = AmericanaDay.query.get_or_404(day_id)
    
    if day.tournament_id != tournament_id:
        flash('Giornata non valida per questo torneo!', 'error')
        return redirect(url_for('tournaments.view_tournament', tournament_id=tournament_id))
    
    config = tournament.get_config()
    teams = day.get_teams()
    matches = day.get_matches()
    results = day.get_results()
    
    # Calcola la classifica se ci sono risultati
    ranking = []
    statistics = {}
    
    if results:
        ranking = AmericanaService.calculate_ranking(
            teams, matches, results, config.get('metodo_punteggio')
        )
        statistics = AmericanaService.calculate_advanced_statistics(teams, matches, results)
    
    return render_template('tournaments/americana/view_day.html',
                          tournament=tournament,
                         day=day,
                         teams=teams,
                         matches=matches,
                         results=results,
                         ranking=ranking,
                         statistics=statistics,
                         config=config)

@tournaments_bp.route('/tornei/<int:tournament_id>/americana/<int:day_id>/risultati', methods=['GET', 'POST'])
def americana_enter_results(tournament_id, day_id):
    """Inserimento risultati per il torneo americana"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = AmericanaDay.query.get_or_404(day_id)
    
    if request.method == 'POST':
        try:
            results = day.get_results()
            
            # Processa i risultati dal form
            for key, value in request.form.items():
                if key.startswith('match_') and key.endswith('_team1_sets'):
                    match_id = key.replace('match_', '').replace('_team1_sets', '')
                    
                    team1_sets = request.form.get(f'match_{match_id}_team1_sets', 0)
                    team2_sets = request.form.get(f'match_{match_id}_team2_sets', 0)
                    team1_games = request.form.get(f'match_{match_id}_team1_games', 0)
                    team2_games = request.form.get(f'match_{match_id}_team2_games', 0)
                    
                    if team1_sets or team2_sets:  # Solo se sono stati inseriti dei risultati
                        results[match_id] = {
                            'team1_sets': int(team1_sets or 0),
                            'team2_sets': int(team2_sets or 0),
                            'team1_games': int(team1_games or 0),
                            'team2_games': int(team2_games or 0)
                        }
            
            day.set_results(results)
            
            # Calcola e salva classifica aggiornata
            teams = day.get_teams()
            matches = day.get_matches()
            config = tournament.get_config()
            
            ranking = AmericanaService.calculate_ranking(
                teams, matches, results, config.get('metodo_punteggio')
            )
            day.set_ranking(ranking)
            
            # Calcola e salva statistiche
            statistics = AmericanaService.calculate_advanced_statistics(teams, matches, results)
            day.set_statistics(statistics)
            
            db.session.commit()
            flash('Risultati salvati con successo!', 'success')
            return redirect(url_for('tournaments.view_americana_day', 
                                   tournament_id=tournament_id, 
                                   day_id=day_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante il salvataggio: {str(e)}', 'error')
    
    matches = day.get_matches()
    results = day.get_results()
    
    return render_template('tournaments/americana/enter_results.html',
                          tournament=tournament,
                          day=day,
                          matches=matches,
                         results=results)

@tournaments_bp.route('/tornei/<int:tournament_id>/americana/<int:day_id>/classifica')
def americana_ranking(tournament_id, day_id):
    """Visualizza la classifica del torneo americana"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = AmericanaDay.query.get_or_404(day_id)
    
    ranking = day.get_ranking()
    statistics = day.get_statistics()
    
    return render_template('tournaments/americana/ranking.html',
                         tournament=tournament,
                         day=day,
                         ranking=ranking,
                         statistics=statistics)

@tournaments_bp.route('/tornei/<int:tournament_id>/americana/<int:day_id>/statistiche')
def americana_statistics(tournament_id, day_id):
    """Visualizza le statistiche avanzate del torneo americana"""
    tournament = Tournament.query.get_or_404(tournament_id)
    day = AmericanaDay.query.get_or_404(day_id)
    
    statistics = day.get_statistics()
    teams = day.get_teams()
    matches = day.get_matches()
    results = day.get_results()
    
    return render_template('tournaments/americana/statistics.html',
                         tournament=tournament,
                         day=day,
                         statistics=statistics,
                         teams=teams,
                         matches=matches,
                         results=results)