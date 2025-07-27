#!/usr/bin/env python3
"""
Test per verificare gli algoritmi di torneo americano (semplice e completo)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.americana_service import AmericanaService

def test_simple_8_players():
    """Test per 8 giocatori con algoritmo semplice"""
    print("=== TEST SEMPLICE 8 GIOCATORI ===")
    
    players = [
        {'id': 1, 'name': 'Marco'},
        {'id': 2, 'name': 'Luca'},
        {'id': 3, 'name': 'Andrea'},
        {'id': 4, 'name': 'Giovanni'},
        {'id': 5, 'name': 'Paolo'},
        {'id': 6, 'name': 'Stefano'},
        {'id': 7, 'name': 'Roberto'},
        {'id': 8, 'name': 'Francesco'}
    ]
    
    matches = AmericanaService.generate_simple_american_tournament(players, 2, 5)
    
    print(f"Numero di partite generate: {len(matches)}")
    
    # Raggruppa per turno
    rounds = {}
    for match in matches:
        round_num = match['round']
        if round_num not in rounds:
            rounds[round_num] = []
        rounds[round_num].append(match)
    
    print(f"Numero di turni: {len(rounds)}")
    
    for round_num in sorted(rounds.keys()):
        print(f"\nTurno {round_num}:")
        for match in rounds[round_num]:
            team1 = match['team1']
            team2 = match['team2']
            print(f"  {team1['player1_name']}-{team1['player2_name']} vs {team2['player1_name']}-{team2['player2_name']}")

def test_complete_8_players():
    """Test per 8 giocatori con algoritmo completo"""
    print("\n=== TEST COMPLETO 8 GIOCATORI ===")
    
    players = [
        {'id': 1, 'name': 'Marco'},
        {'id': 2, 'name': 'Luca'},
        {'id': 3, 'name': 'Andrea'},
        {'id': 4, 'name': 'Giovanni'},
        {'id': 5, 'name': 'Paolo'},
        {'id': 6, 'name': 'Stefano'},
        {'id': 7, 'name': 'Roberto'},
        {'id': 8, 'name': 'Francesco'}
    ]
    
    # Numero di turni = numero giocatori - 1 = 7
    num_rounds = len(players) - 1
    matches = AmericanaService.generate_rotating_pairs_matches(players, num_rounds)
    
    print(f"Numero di partite generate: {len(matches)}")
    print(f"Numero di turni: {num_rounds}")
    
    # Raggruppa per turno
    rounds = {}
    for match in matches:
        round_num = match['round']
        if round_num not in rounds:
            rounds[round_num] = []
        rounds[round_num].append(match)
    
    for round_num in sorted(rounds.keys()):
        print(f"\nTurno {round_num}:")
        for match in rounds[round_num]:
            team1 = match['team1']
            team2 = match['team2']
            print(f"  {team1['player1_name']}-{team1['player2_name']} vs {team2['player1_name']}-{team2['player2_name']}")

def test_simple_10_players():
    """Test per 10 giocatori con algoritmo semplice"""
    print("\n=== TEST SEMPLICE 10 GIOCATORI ===")
    
    players = [
        {'id': 1, 'name': 'Marco'},
        {'id': 2, 'name': 'Luca'},
        {'id': 3, 'name': 'Andrea'},
        {'id': 4, 'name': 'Giovanni'},
        {'id': 5, 'name': 'Paolo'},
        {'id': 6, 'name': 'Stefano'},
        {'id': 7, 'name': 'Roberto'},
        {'id': 8, 'name': 'Francesco'},
        {'id': 9, 'name': 'Alessandro'},
        {'id': 10, 'name': 'Davide'}
    ]
    
    matches = AmericanaService.generate_simple_american_tournament(players, 2, 5)
    
    print(f"Numero di partite generate: {len(matches)}")
    
    # Raggruppa per turno
    rounds = {}
    for match in matches:
        round_num = match['round']
        if round_num not in rounds:
            rounds[round_num] = []
        rounds[round_num].append(match)
    
    print(f"Numero di turni: {len(rounds)}")
    
    for round_num in sorted(rounds.keys()):
        print(f"\nTurno {round_num}:")
        for match in rounds[round_num]:
            team1 = match['team1']
            team2 = match['team2']
            print(f"  {team1['player1_name']}-{team1['player2_name']} vs {team2['player1_name']}-{team2['player2_name']}")

def test_complete_10_players():
    """Test per 10 giocatori con algoritmo completo"""
    print("\n=== TEST COMPLETO 10 GIOCATORI ===")
    
    players = [
        {'id': 1, 'name': 'Marco'},
        {'id': 2, 'name': 'Luca'},
        {'id': 3, 'name': 'Andrea'},
        {'id': 4, 'name': 'Giovanni'},
        {'id': 5, 'name': 'Paolo'},
        {'id': 6, 'name': 'Stefano'},
        {'id': 7, 'name': 'Roberto'},
        {'id': 8, 'name': 'Francesco'},
        {'id': 9, 'name': 'Alessandro'},
        {'id': 10, 'name': 'Davide'}
    ]
    
    # Numero di turni = numero giocatori - 1 = 9
    num_rounds = len(players) - 1
    matches = AmericanaService.generate_rotating_pairs_matches(players, num_rounds)
    
    print(f"Numero di partite generate: {len(matches)}")
    print(f"Numero di turni: {num_rounds}")
    
    # Raggruppa per turno
    rounds = {}
    for match in matches:
        round_num = match['round']
        if round_num not in rounds:
            rounds[round_num] = []
        rounds[round_num].append(match)
    
    for round_num in sorted(rounds.keys()):
        print(f"\nTurno {round_num}:")
        for match in rounds[round_num]:
            team1 = match['team1']
            team2 = match['team2']
            print(f"  {team1['player1_name']}-{team1['player2_name']} vs {team2['player1_name']}-{team2['player2_name']}")

if __name__ == "__main__":
    test_simple_8_players()
    test_complete_8_players()
    test_simple_10_players()
    test_complete_10_players() 