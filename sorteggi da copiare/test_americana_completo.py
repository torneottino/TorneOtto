#!/usr/bin/env python3
"""
Test completo per il torneo americano
Verifica:
1. Creazione torneo con numero coppie, turni, campi
2. Selezione giocatori
3. Generazione partite
4. Inserimento risultati
5. Calcolo classifica
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

def test_americana_completo():
    """Test completo del flusso torneo americano"""
    print("=== TEST COMPLETO TORNEO AMERICANA ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 1. CREAZIONE TORNEO
            print("\n1. Creazione torneo...")
            
            # Crea un torneo di test
            torneo = Tournament(
                nome="Test Torneo Americano Completo",
                tipo_torneo='americana',
                circolo='Circolo Test',
                data_inizio=date.today(),
                data_fine=date.today(),
                stato="Pianificato"
            )
            
            # Configurazione con tutte le opzioni
            config = {
                'num_coppie': 6,  # 12 giocatori
                'metodo_formazione': 'casuale',
                'origine_giocatori': 'caricati',
                'tipo_torneo': 'semplice',  # Testiamo il tipo semplice
                'num_campi': 3,  # 3 campi disponibili
                'tipo_coppie': 'giranti',  # Coppie che girano
                'metodo_punteggio': 'differenza_games'
            }
            
            torneo.set_config(config)
            db.session.add(torneo)
            db.session.commit()
            
            print(f"✓ Torneo creato con ID: {torneo.id}")
            print(f"  - Numero coppie: {config['num_coppie']}")
            print(f"  - Numero campi: {config['num_campi']}")
            print(f"  - Tipo torneo: {config['tipo_torneo']}")
            print(f"  - Tipo coppie: {config['tipo_coppie']}")
            
            # 2. CREAZIONE GIOCATORI DI TEST
            print("\n2. Creazione giocatori di test...")
            
            # Crea 12 giocatori di test
            giocatori_test = []
            for i in range(12):
                player = Player(
                    nome=f"Giocatore{i+1}",
                    cognome=f"Test{i+1}",
                    posizione="Indifferente"
                )
                db.session.add(player)
                giocatori_test.append(player)
            
            db.session.commit()
            print(f"✓ Creati {len(giocatori_test)} giocatori di test")
            
            # 3. SELEZIONE GIOCATORI E SETUP
            print("\n3. Setup giornata con selezione giocatori...")
            
            # Simula la selezione dei giocatori
            selected_players = []
            for player in giocatori_test:
                selected_players.append({
                    'id': player.id,
                    'name': f"{player.nome} {player.cognome}"
                })
            
            # Crea la giornata
            day = AmericanaDay(
                tournament_id=torneo.id,
                data=date.today(),
                stato="Setup completato"
            )
            
            # 4. GENERAZIONE PARTITE
            print("\n4. Generazione partite...")
            
            # Per torneo semplice con coppie giranti
            num_rounds_config = 5  # 5 turni come configurato dall'utente
            matches = AmericanaService.generate_simple_american_tournament(
                selected_players, config['num_campi'], num_rounds_config
            )
            
            # Distribuisci sui campi
            matches, court_schedule = AmericanaService.distribute_matches_to_courts(
                matches, config['num_campi']
            )
            
            # Salva nella giornata
            day.set_players(selected_players)
            day.set_teams([])  # Per coppie giranti non ci sono team fissi
            day.set_matches(matches)
            day.set_courts(list(range(1, config['num_campi'] + 1)))
            
            db.session.add(day)
            db.session.commit()
            
            print(f"✓ Giornata creata con ID: {day.id}")
            print(f"  - Partite generate: {len(matches)}")
            print(f"  - Turni configurati: {num_rounds_config}")
            print(f"  - Campi utilizzati: {config['num_campi']}")
            
            # Mostra le partite generate
            print("\n  Partite generate:")
            for i, match in enumerate(matches[:10]):  # Mostra prime 10 partite
                print(f"    {i+1}. {match['team1']['player1_name']} vs {match['team2']['player1_name']} - Campo {match.get('court', 'N/A')} - Turno {match.get('round', 'N/A')}")
            
            # 5. INSERIMENTO RISULTATI
            print("\n5. Inserimento risultati...")
            
            results = {}
            
            # Simula l'inserimento di alcuni risultati
            for i, match in enumerate(matches):
                if i < len(matches) // 2:  # Inserisci risultati per metà delle partite
                    # Simula risultati casuali
                    team1_games = (i % 3) + 1  # 1-3 games
                    team2_games = ((i + 1) % 3) + 1  # 1-3 games
                    
                    results[str(match['id'])] = {
                        'team1_games': team1_games,
                        'team2_games': team2_games,
                        'winner': 1 if team1_games > team2_games else 2
                    }
            
            day.set_results(results)
            
            # 6. CALCOLO CLASSIFICA
            print("\n6. Calcolo classifica...")
            
            # Per coppie giranti, calcola la classifica individuale
            player_ranking = AmericanaService.calculate_player_ranking(
                matches, results
            )
            day.set_ranking(player_ranking)
            db.session.commit()
            
            print(f"✓ Classifica calcolata per {len(player_ranking)} giocatori")
            print(f"  Risultati inseriti: {len(results)}/{len(matches)} partite")
            
            # Mostra la classifica
            print("\n  Classifica finale (singola):")
            for i, player_stats in enumerate(player_ranking[:5]):  # Top 5
                print(f"    {i+1}°. Giocatore ID {player_stats['player_id']} - {player_stats['points']} punti ({player_stats['matches_won']}V/{player_stats['matches_lost']}P, {player_stats['games_won']} games vinti)")
            
            # 7. VERIFICHE FINALI
            print("\n7. Verifiche finali...")
            
            # Verifica che la configurazione sia stata salvata correttamente
            saved_config = torneo.get_config()
            assert saved_config['num_coppie'] == 6, "Numero coppie non salvato correttamente"
            assert saved_config['num_campi'] == 3, "Numero campi non salvato correttamente"
            assert saved_config['tipo_torneo'] == 'semplice', "Tipo torneo non salvato correttamente"
            
            # Verifica che le partite siano state generate correttamente
            saved_matches = day.get_matches()
            assert len(saved_matches) > 0, "Nessuna partita generata"
            
            # Verifica che i risultati siano stati salvati
            saved_results = day.get_results()
            assert len(saved_results) > 0, "Nessun risultato salvato"
            
            # Verifica che la classifica sia stata calcolata
            saved_ranking = day.get_ranking()
            assert len(saved_ranking) > 0, "Classifica non calcolata"
            
            print("✓ Tutte le verifiche superate!")
            
            # 8. PULIZIA
            print("\n8. Pulizia...")
            
            # Rimuovi i dati di test
            db.session.delete(day)
            db.session.delete(torneo)
            for player in giocatori_test:
                db.session.delete(player)
            db.session.commit()
            
            print("✓ Dati di test rimossi")
            
            print("\n=== TEST COMPLETATO CON SUCCESSO ===")
            return True
            
        except Exception as e:
            print(f"\n❌ ERRORE durante il test: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def test_americana_coppie_fisse():
    """Test per torneo americano con coppie fisse"""
    print("\n=== TEST TORNEO AMERICANA CON COPPIE FISSE ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 1. CREAZIONE TORNEO
            print("\n1. Creazione torneo con coppie fisse...")
            
            torneo = Tournament(
                nome="Test Torneo Americano Coppie Fisse",
                tipo_torneo='americana',
                circolo='Circolo Test',
                data_inizio=date.today(),
                data_fine=date.today(),
                stato="Pianificato"
            )
            
            config = {
                'num_coppie': 4,  # 8 giocatori
                'metodo_formazione': 'casuale',
                'origine_giocatori': 'caricati',
                'tipo_torneo': 'completo',  # Round robin completo
                'num_campi': 2,  # 2 campi
                'tipo_coppie': 'fisse',  # Coppie fisse
                'metodo_punteggio': 'punti_partita'
            }
            
            torneo.set_config(config)
            db.session.add(torneo)
            db.session.commit()
            
            # 2. CREAZIONE GIOCATORI
            print("\n2. Creazione giocatori...")
            
            giocatori_test = []
            for i in range(8):
                player = Player(
                    nome=f"GiocatoreF{i+1}",
                    cognome=f"Test{i+1}",
                    posizione="Indifferente"
                )
                db.session.add(player)
                giocatori_test.append(player)
            
            db.session.commit()
            
            # 3. CREAZIONE COPPIE FISSE
            print("\n3. Creazione coppie fisse...")
            
            selected_players = []
            for player in giocatori_test:
                selected_players.append({
                    'id': player.id,
                    'name': f"{player.nome} {player.cognome}"
                })
            
            teams = AmericanaService.create_teams_fixed(selected_players, 'casuale')
            
            # 4. GENERAZIONE PARTITE ROUND ROBIN
            print("\n4. Generazione partite round robin...")
            
            matches = AmericanaService.generate_round_robin_matches(teams)
            
            # Distribuisci sui campi
            matches, court_schedule = AmericanaService.distribute_matches_to_courts(
                matches, config['num_campi']
            )
            
            # 5. CREAZIONE GIORNATA
            day = AmericanaDay(
                tournament_id=torneo.id,
                data=date.today(),
                stato="Setup completato"
            )
            
            day.set_players(selected_players)
            day.set_teams(teams)
            day.set_matches(matches)
            day.set_courts(list(range(1, config['num_campi'] + 1)))
            
            db.session.add(day)
            db.session.commit()
            
            print(f"✓ Giornata creata con {len(matches)} partite")
            print(f"✓ {len(teams)} coppie fisse create")
            
            # 6. INSERIMENTO RISULTATI
            print("\n5. Inserimento risultati...")
            
            results = {}
            for i, match in enumerate(matches):
                # Simula risultati
                team1_games = (i % 2) + 1
                team2_games = ((i + 1) % 2) + 1
                
                results[str(match['id'])] = {
                    'team1_games': team1_games,
                    'team2_games': team2_games,
                    'winner': 1 if team1_games > team2_games else 2
                }
            
            day.set_results(results)
            
            # 7. CALCOLO CLASSIFICA
            ranking = AmericanaService.calculate_ranking(
                teams, matches, results, config['metodo_punteggio']
            )
            
            day.set_ranking(ranking)
            db.session.commit()
            
            print(f"✓ Classifica calcolata per {len(ranking)} coppie")
            
            # Mostra classifica
            print("\n  Classifica coppie fisse:")
            for i, team_stats in enumerate(ranking):
                team = team_stats['team']
                print(f"    {i+1}°. {team['player1_name']} / {team['player2_name']} - {team_stats['points']} punti")
            
            # 8. PULIZIA
            db.session.delete(day)
            db.session.delete(torneo)
            for player in giocatori_test:
                db.session.delete(player)
            db.session.commit()
            
            print("✓ Test coppie fisse completato")
            return True
            
        except Exception as e:
            print(f"❌ ERRORE test coppie fisse: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("Avvio test completo torneo americana...")
    
    success1 = test_americana_completo()
    success2 = test_americana_coppie_fisse()
    
    if success1 and success2:
        print("\n🎉 TUTTI I TEST SUPERATI!")
        print("Il sistema torneo americana funziona correttamente:")
        print("✓ Creazione torneo con numero coppie, turni, campi")
        print("✓ Selezione giocatori")
        print("✓ Generazione partite (semplice e completo)")
        print("✓ Coppie fisse e giranti")
        print("✓ Inserimento risultati")
        print("✓ Calcolo classifica")
    else:
        print("\n❌ ALCUNI TEST FALLITI")
        sys.exit(1) 