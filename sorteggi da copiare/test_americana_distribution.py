#!/usr/bin/env python3
"""
Test per verificare la distribuzione equa delle partite nel torneo americano
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.tournament import Tournament
from models.tournament_day import AmericanaDay
from models.player import Player
from services.americana_service import AmericanaService
from datetime import date

app = create_app()

def test_americana_distribution():
    """Test per verificare che la distribuzione delle partite sia equa"""
    print("=== TEST DISTRIBUZIONE PARTITE AMERICANA ===")
    
    try:
        with app.app_context():
            # 1. Crea giocatori di test
            print("\n1. Creazione giocatori di test...")
            players = []
            for i in range(8):  # 8 giocatori per il test
                player = Player()
                player.nome = f"Giocatore{i+1}"
                player.cognome = f"Test{i+1}"
                player.elo_standard = 1500.0
                player.posizione = "Indifferente"
                db.session.add(player)
                players.append(player)
            db.session.commit()
            print(f"✓ Creati {len(players)} giocatori")
            
            # 2. Crea torneo
            print("\n2. Creazione torneo...")
            tournament = Tournament()
            tournament.nome = "Test Distribuzione Americana"
            tournament.data_inizio = date.today()
            tournament.data_fine = date.today()
            tournament.tipo_torneo = "americana"
            tournament.stato = "Attivo"
            tournament.set_config({
                'tipo_torneo': 'semplice',
                'tipo_coppie': 'giranti',
                'num_coppie': 4,
                'num_campi': 3,
                'num_turni': 5,
                'metodo_punteggio': 'game_difference'
            })
            db.session.add(tournament)
            db.session.commit()
            print(f"✓ Torneo creato con ID {tournament.id}")
            
            # 3. Genera partite
            print("\n3. Generazione partite...")
            player_dicts = [{
                'id': p.id,
                'nome': p.nome,
                'cognome': p.cognome
            } for p in players]
            
            matches = AmericanaService.generate_simple_american_tournament(
                player_dicts, 3, 5  # 3 campi, 5 turni
            )
            print(f"✓ Generate {len(matches)} partite")
            
            # 4. Analizza distribuzione
            print("\n4. Analisi distribuzione partite...")
            player_match_count = {}
            
            for match in matches:
                # Conta partite per ogni giocatore
                players_in_match = [
                    match['team1']['player1_id'],
                    match['team1']['player2_id'],
                    match['team2']['player1_id'],
                    match['team2']['player2_id']
                ]
                
                for player_id in players_in_match:
                    if player_id not in player_match_count:
                        player_match_count[player_id] = 0
                    player_match_count[player_id] += 1
            
            # 5. Mostra risultati
            print("\n5. Distribuzione partite per giocatore:")
            min_matches = min(player_match_count.values())
            max_matches = max(player_match_count.values())
            avg_matches = sum(player_match_count.values()) / len(player_match_count)
            
            print(f"   Min partite: {min_matches}")
            print(f"   Max partite: {max_matches}")
            print(f"   Media partite: {avg_matches:.1f}")
            print(f"   Differenza max-min: {max_matches - min_matches}")
            
            # Mostra dettaglio per ogni giocatore
            for player in players:
                matches_played = player_match_count.get(player.id, 0)
                print(f"   {player.nome} {player.cognome}: {matches_played} partite")
            
            # 6. Verifica equità
            print("\n6. Verifica equità...")
            if max_matches - min_matches <= 1:
                print("✓ Distribuzione EQUA: differenza massima ≤ 1 partita")
            else:
                print(f"✗ Distribuzione NON EQUA: differenza massima = {max_matches - min_matches} partite")
            
            # 7. Verifica che tutti i giocatori abbiano giocato
            players_without_matches = [p for p in players if player_match_count.get(p.id, 0) == 0]
            if not players_without_matches:
                print("✓ Tutti i giocatori hanno giocato almeno una partita")
            else:
                print(f"✗ {len(players_without_matches)} giocatori non hanno giocato nessuna partita")
                for p in players_without_matches:
                    print(f"   - {p.nome} {p.cognome}")
            
            print("\n=== TEST COMPLETATO ===")
    except Exception as e:
        print(f"✗ ERRORE: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            with app.app_context():
                db.session.query(AmericanaDay).delete()
                db.session.query(Tournament).delete()
                db.session.query(Player).filter(Player.nome.contains("Giocatore")).delete()
                db.session.commit()
                print("\n✓ Cleanup completato")
        except Exception as cleanup_e:
            print(f"Errore nel cleanup: {cleanup_e}")

if __name__ == "__main__":
    test_americana_distribution() 