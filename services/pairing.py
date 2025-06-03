"""
Modulo per la gestione degli accoppiamenti dei giocatori nei tornei.
Implementa diverse strategie di accoppiamento:
- Random: accoppiamento casuale
- ELO: accoppiamento basato sul rating ELO
- Seeded: accoppiamento con teste di serie
- Manual: accoppiamento manuale
"""

from models.player import Player, PlayerTournamentElo
from models.tournament import Tournament
from models.tournament_day import TorneOtto30Day, TorneOtto45Day
import random
from sqlalchemy import func

def random_pairing(players, num_teams=4):
    """
    Crea accoppiamenti casuali tra i giocatori.
    
    Args:
        players: lista di ID dei giocatori
        num_teams: numero di squadre da creare
        
    Returns:
        list: lista di squadre (ogni squadra è una lista di ID giocatori)
    """
    if not players:
        return []
        
    # Mescola i giocatori
    shuffled_players = players.copy()
    random.shuffle(shuffled_players)
    
    # Calcola giocatori per squadra
    players_per_team = len(shuffled_players) // num_teams
    
    # Crea le squadre
    teams = []
    for i in range(num_teams):
        start_idx = i * players_per_team
        end_idx = start_idx + players_per_team
        team = shuffled_players[start_idx:end_idx]
        if team:  # Aggiungi solo squadre non vuote
            teams.append(team)
            
    return teams

def elo_pairing(players, tournament_id, num_teams=4):
    """
    Crea accoppiamenti basati sul rating ELO dei giocatori.
    
    Args:
        players: lista di ID dei giocatori
        tournament_id: ID del torneo
        num_teams: numero di squadre da creare
        
    Returns:
        list: lista di squadre (ogni squadra è una lista di ID giocatori)
    """
    if not players:
        return []
        
    # Recupera gli ELO dei giocatori
    player_elos = {}
    for player_id in players:
        elo = PlayerTournamentElo.query.filter_by(
            player_id=player_id,
            tournament_id=tournament_id
        ).first()
        player_elos[player_id] = elo.elo_rating if elo else 1500.0
        
    # Ordina i giocatori per ELO
    sorted_players = sorted(players, key=lambda x: player_elos[x], reverse=True)
    
    # Calcola giocatori per squadra
    players_per_team = len(sorted_players) // num_teams
    
    # Crea le squadre bilanciando gli ELO
    teams = [[] for _ in range(num_teams)]
    for i, player_id in enumerate(sorted_players):
        team_idx = i % num_teams
        teams[team_idx].append(player_id)
        
    return teams

def seeded_pairing(players, tournament_id, num_teams=4, num_seeds=4):
    """
    Crea accoppiamenti con teste di serie.
    
    Args:
        players: lista di ID dei giocatori
        tournament_id: ID del torneo
        num_teams: numero di squadre da creare
        num_seeds: numero di teste di serie
        
    Returns:
        list: lista di squadre (ogni squadra è una lista di ID giocatori)
    """
    if not players:
        return []
        
    # Recupera gli ELO dei giocatori
    player_elos = {}
    for player_id in players:
        elo = PlayerTournamentElo.query.filter_by(
            player_id=player_id,
            tournament_id=tournament_id
        ).first()
        player_elos[player_id] = elo.elo_rating if elo else 1500.0
        
    # Ordina i giocatori per ELO
    sorted_players = sorted(players, key=lambda x: player_elos[x], reverse=True)
    
    # Seleziona le teste di serie
    seeds = sorted_players[:num_seeds]
    remaining_players = sorted_players[num_seeds:]
    
    # Mescola i giocatori rimanenti
    random.shuffle(remaining_players)
    
    # Crea le squadre
    teams = [[] for _ in range(num_teams)]
    
    # Assegna le teste di serie
    for i, seed in enumerate(seeds):
        teams[i].append(seed)
        
    # Distribuisci i giocatori rimanenti
    for i, player_id in enumerate(remaining_players):
        team_idx = i % num_teams
        teams[team_idx].append(player_id)
        
    return teams

def validate_pairing(teams, tournament_id):
    """
    Valida gli accoppiamenti creati.
    
    Args:
        teams: lista di squadre
        tournament_id: ID del torneo
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not teams:
        return False, "Nessuna squadra creata"
        
    # Verifica che tutte le squadre abbiano lo stesso numero di giocatori
    team_sizes = [len(team) for team in teams]
    if len(set(team_sizes)) > 1:
        return False, "Le squadre devono avere lo stesso numero di giocatori"
        
    # Verifica che non ci siano giocatori duplicati
    all_players = [player_id for team in teams for player_id in team]
    if len(all_players) != len(set(all_players)):
        return False, "Ci sono giocatori duplicati nelle squadre"
        
    # Verifica che tutti i giocatori esistano nel torneo
    for player_id in all_players:
        player = Player.query.get(player_id)
        if not player:
            return False, f"Giocatore {player_id} non trovato"
            
    return True, "Accoppiamenti validi" 