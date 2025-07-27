#!/usr/bin/env python3
"""
Funzione corretta per eliminare un torneo senza violazioni di foreign key constraint.
Copia questa funzione nel file routes/tournaments.py per sostituire la funzione esistente.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app as app
from models.tournament import Tournament
from models.player import Player, PlayerTournamentElo, PlayerEloHistory
from models.tournament_day import TorneOtto30Day, TorneOtto45Day, TournamentDay, GironiDay, EliminDay
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

def delete_tournament_fixed(tournament_id):
    """
    Funzione corretta per eliminare un torneo senza violazioni di foreign key constraint.
    Usa SQL diretto invece di ORM per evitare i controlli di foreign key di SQLAlchemy.
    """
    # Verifica che il torneo esista
    tournament = Tournament.query.get_or_404(tournament_id)
    
    try:
        # Usa SQL diretto per eliminare tutto in ordine corretto
        # 1. Elimina prima i record dalle tabelle legacy
        legacy_tables = ['pozzo_courts', 'pozzo_teams', 'pozzo_matches', 'pozzo_players']
        
        for table_name in legacy_tables:
            try:
                db.session.execute(
                    text(f"DELETE FROM {table_name} WHERE tournament_id = :tournament_id"),
                    {"tournament_id": tournament_id}
                )
                print(f"Eliminati record dalla tabella {table_name}")
            except Exception as e:
                print(f"Tabella {table_name} non trovata o senza colonna tournament_id: {str(e)}")
        
        # 2. Elimina gli ELO history
        db.session.execute(
            text("DELETE FROM player_elo_history WHERE tournament_id = :tournament_id"),
            {"tournament_id": tournament_id}
        )
        
        # 3. Elimina gli ELO ratings del torneo
        db.session.execute(
            text("DELETE FROM player_tournament_elo WHERE tournament_id = :tournament_id"),
            {"tournament_id": tournament_id}
        )
        
        # 4. Elimina le giornate di eliminazione
        db.session.execute(
            text("DELETE FROM elimin_day WHERE tournament_id = :tournament_id"),
            {"tournament_id": tournament_id}
        )
        
        # 5. Elimina le giornate del torneo
        db.session.execute(
            text("DELETE FROM tournament_day WHERE tournament_id = :tournament_id"),
            {"tournament_id": tournament_id}
        )
        
        # 6. Elimina il torneo stesso
        db.session.execute(
            text("DELETE FROM tournament WHERE id = :tournament_id"),
            {"tournament_id": tournament_id}
        )
        
        # Commit di tutto
        db.session.commit()
        
        # 7. Resetta la sequenza degli ID se non ci sono più tornei
        tournament_count = db.session.execute(text("SELECT COUNT(*) FROM tournament")).scalar()
        if tournament_count == 0:
            if db.engine.url.drivername == 'sqlite':
                db.session.execute(text('DELETE FROM sqlite_sequence WHERE name="tournament"'))
                db.session.commit()
        
        return True, 'Torneo eliminato con successo!'
        
    except Exception as e:
        db.session.rollback()
        return False, f'Errore durante l\'eliminazione del torneo: {str(e)}'

# Esempio di come usare la funzione nel route:
"""
@tournaments_bp.route('/tornei/<int:tournament_id>/delete', methods=['POST'])
def delete_tournament(tournament_id):
    success, message = delete_tournament_fixed(tournament_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('tournaments.tournaments_list'))
""" 