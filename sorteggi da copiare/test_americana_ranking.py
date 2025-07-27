#!/usr/bin/env python3
"""
Test rapido per verificare la classifica singola per tornei americana con coppie giranti
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models.tournament import Tournament
from models.player import Player
from models.tournament_day import AmericanaDay
from services.americana_service import AmericanaService
from datetime import date
import json

def test_ranking_singolo():
    """Test della classifica singola per coppie giranti"""
    print("=== TEST CLASSIFICA SINGOLA ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Crea giocatori di test
            print("\n1. Creazione giocatori...")
            players = []
            for i in range(1, 9):  # 8 giocatori
                player = Player(
                    nome=f"Giocatore{i}",
                    cognome=f"Test{i}",
                    posizione="Indifferente"
                )
                db.session.add(player)
                players.append(player)
            db.session.commit()
            print(f"✓ Creati {len(players)} giocatori")
            
            # 2. Crea torneo americana con coppie giranti
            print("\n2. Creazione torneo...")
            tournament = Tournament(
                nome="Test Americana Coppie Giranti",
                tipo_torneo="americana",
                circolo="Test Club",
                data_inizio=date.today(),
                data_fine=date.today(),
                stato="attivo"
            )
            tournament.set_config({
                'tipo_coppie': 'giranti',
                'tipo_torneo': 'semplice',
                'num_campi': 4,
                'metodo_punteggio': 'standard'
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
                player_dicts, 4, 5  # 4 campi, 5 turni
            )
            print(f"✓ Generate {len(matches)} partite")
            
            # 4. Crea giornata
            print("\n4. Creazione giornata...")
            day = AmericanaDay(
                tournament_id=tournament.id,
                data=date.today(),
                stato="Setup completato"
            )
            day.set_players(player_dicts)
            day.set_matches(matches)
            db.session.add(day)
            db.session.commit()
            print(f"✓ Giornata creata con ID {day.id}")
            
            # 5. Simula risultati
            print("\n5. Simulazione risultati...")
            results = {}
            for i, match in enumerate(matches):
                # Simula risultati casuali
                team1_games = (i % 3) + 1
                team2_games = ((i + 1) % 3) + 1
                winner = 1 if team1_games > team2_games else 2
                results[str(match['id'])] = {
                    'team1_games': team1_games,
                    'team2_games': team2_games,
                    'winner': winner
                }
            day.set_results(results)
            print(f"✓ Inseriti {len(results)} risultati")
            
            # 6. Calcola classifica singola
            print("\n6. Calcolo classifica singola...")
            player_ranking = AmericanaService.calculate_player_ranking(matches, results)
            day.set_ranking(player_ranking)
            db.session.commit()
            
            print(f"✓ Classifica calcolata per {len(player_ranking)} giocatori")
            
            # 7. Mostra classifica
            print("\n7. Classifica finale (singola):")
            for i, player_stats in enumerate(player_ranking[:5]):  # Top 5
                print(f"    {i+1}°. Giocatore ID {player_stats['player_id']} - {player_stats['points']} punti ({player_stats['matches_won']}V/{player_stats['matches_lost']}P, {player_stats['games_won']} games vinti)")
            
            # 8. Verifica che sia classifica singola
            print("\n8. Verifica tipo classifica...")
            if 'player_id' in player_ranking[0]:
                print("✓ Classifica singola corretta (contiene 'player_id')")
            else:
                print("✗ ERRORE: Classifica non singola!")
            
            print("\n=== TEST COMPLETATO CON SUCCESSO ===")
            
        except Exception as e:
            print(f"✗ ERRORE: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            try:
                db.session.query(AmericanaDay).filter_by(tournament_id=tournament.id).delete()
                db.session.query(Tournament).filter_by(id=tournament.id).delete()
                db.session.query(Player).filter(Player.nome.contains("Giocatore")).delete()
                db.session.commit()
                print("\n✓ Cleanup completato")
            except:
                pass

if __name__ == "__main__":
    test_ranking_singolo() 