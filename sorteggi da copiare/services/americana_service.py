try:
    from math import comb
except ImportError:
    # Fallback for Python < 3.8
    from math import factorial
    comb = lambda n, k: 0 if k > n or k < 0 else 1 if k == 0 or k == n else factorial(n) // (factorial(k) * factorial(n - k))

import random
from itertools import combinations
from collections import defaultdict

class AmericanaService:
    """Servizio per la logica dei tornei all'americana"""
    
    @staticmethod
    def calculate_total_matches(num_players, tournament_type):
        """
        Calcola il numero totale di partite basato sul tipo di torneo
        - semplice: il numero di partite è determinato dai turni scelti dall'utente
        - completo: round robin completo con tutte le combinazioni possibili
        """
        if tournament_type == "semplice":
            # Per torneo semplice: il numero di partite è determinato dai turni scelti dall'utente
            # Non possiamo calcolarlo a priori solo dal numero di giocatori.
            # Questo metodo verrà chiamato con i parametri num_rounds e num_courts nella nuova logica.
            # Per ora, restituiamo 0 o una stima se non abbiamo quei parametri.
            return 0  # Sarà gestito dalla nuova logica di generazione
        elif tournament_type == "completo":
            # Per torneo completo: tutte le combinazioni possibili
            # Ogni giocatore gioca con tutti gli altri e contro tutti gli altri
            # Correzione: in ogni round ci sono num_players // 2 partite
            num_rounds = num_players - 1
            matches_per_round = num_players // 2  # Correzione qui
            return num_rounds * matches_per_round
        return 0
    
    @staticmethod
    def create_teams_fixed(players, metodo_formazione):
        """Crea le coppie fisse per il torneo"""
        if len(players) % 2 != 0:
            raise ValueError("Il numero di giocatori deve essere pari per formare le coppie")
        
        teams = []
        players_copy = players.copy()
        
        if metodo_formazione == "casuale":
            random.shuffle(players_copy)
        elif metodo_formazione == "teste_serie":
            # Le teste di serie sono già nelle prime posizioni
            pass
        
        # Crea le coppie
        for i in range(0, len(players_copy), 2):
            team = {
                'id': i // 2 + 1,
                'player1_id': players_copy[i]['id'],
                'player1_name': players_copy[i]['nome'] + ' ' + players_copy[i]['cognome'],
                'player2_id': players_copy[i + 1]['id'],
                'player2_name': players_copy[i + 1]['nome'] + ' ' + players_copy[i + 1]['cognome'],
                'is_fixed': True
            }
            teams.append(team)
        
        return teams
    
    @staticmethod
    def create_teams_rotating(players):
        """Crea le coppie a girare (gruppi da 2 giocatori)"""
        if len(players) % 2 != 0:
            raise ValueError("Il numero di giocatori deve essere pari per formare le coppie")
        teams = []
        for i in range(0, len(players), 2):
            team = {
                'id': i // 2 + 1,
                'player1_id': players[i]['id'],
                'player1_name': players[i]['nome'] + ' ' + players[i]['cognome'],
                'player2_id': players[i + 1]['id'],
                'player2_name': players[i + 1]['nome'] + ' ' + players[i + 1]['cognome'],
                'is_fixed': False
            }
            teams.append(team)
        return teams
    
    @staticmethod
    def generate_round_robin_matches(teams):
        """Genera tutte le partite per un round robin completo tra squadre fisse"""
        matches = []
        match_id = 1
        
        # Algoritmo di round-robin per squadre fisse
        num_teams = len(teams)
        if num_teams % 2 == 1:
            # Se dispari, aggiungi una squadra "riposo"
            teams.append({'id': -1, 'player1_id': -1, 'player1_name': 'RIPOSO', 'player2_id': -1, 'player2_name': 'RIPOSO', 'is_fixed': True})
            num_teams += 1
        
        num_rounds = num_teams - 1
        team_ids = [team['id'] for team in teams]
        
        for round_num in range(num_rounds):
            round_matches = []
            
            # Genera le partite per questo turno
            for i in range(num_teams // 2):
                team1_id = team_ids[i]
                team2_id = team_ids[num_teams - 1 - i]
                
                # Salta se una delle squadre è riposo
                if team1_id != -1 and team2_id != -1:
                    team1 = next(t for t in teams if t['id'] == team1_id)
                    team2 = next(t for t in teams if t['id'] == team2_id)
                    
                    match = {
                        'id': match_id,
                        'team1': team1,
                        'team2': team2,
                        'court': None,
                        'round': round_num + 1,
                        'status': 'scheduled'
                    }
                    matches.append(match)
                    match_id += 1
            
            # Rotazione Berger per il turno successivo
            # Mantieni il primo elemento fisso, ruota gli altri
            team_ids = [team_ids[0]] + [team_ids[-1]] + team_ids[1:-1]
        
        return matches
    
    @staticmethod
    def generate_simplified_matches(teams, num_teams):
        """
        Genera il calendario round robin per squadre fisse (stesso di generate_round_robin_matches)
        """
        return AmericanaService.generate_round_robin_matches(teams)
    
    @staticmethod
    def generate_rotating_pairs_matches(players, num_rounds):
        """
        Genera partite con coppie giranti secondo l'algoritmo americano corretto
        Ogni giocatore gioca con tutti gli altri e contro tutti gli altri
        """
        if len(players) % 2 != 0:
            raise ValueError("Il numero di giocatori deve essere pari per le coppie giranti")
        
        if len(players) < 4:
            raise ValueError("Servono almeno 4 giocatori per le coppie giranti")
        
        matches = []
        match_id = 1
        num_players = len(players)
        
        # Algoritmo corretto per coppie giranti
        # Usa l'algoritmo di round-robin per coppie
        
        # Crea una lista di indici dei giocatori
        player_indices = list(range(num_players))
        
        for round_num in range(1, num_rounds + 1):
            # Crea le coppie per questo turno
            round_teams = []
            
            if round_num == 1:
                # Primo turno: accoppia semplicemente
                for i in range(0, num_players, 2):
                    team = {
                        'id': f"R{round_num}T{i//2 + 1}",
                        'player1_id': players[player_indices[i]]['id'],
                        'player1_name': players[player_indices[i]]['nome'] + ' ' + players[player_indices[i]]['cognome'],
                        'player2_id': players[player_indices[i + 1]]['id'],
                        'player2_name': players[player_indices[i + 1]]['nome'] + ' ' + players[player_indices[i + 1]]['cognome'],
                        'is_fixed': False
                    }
                    round_teams.append(team)
            else:
                # Turni successivi: usa l'algoritmo di rotazione corretto
                # Algoritmo: mantieni il primo fisso, ruota gli altri in senso orario
                rotated_indices = player_indices.copy()
                
                # Ruota gli indici per questo turno
                # Sposta il secondo elemento alla fine, mantieni il primo fisso
                for _ in range(round_num - 1):
                    # Rotazione: mantieni il primo, sposta il secondo alla fine
                    rotated_indices = [rotated_indices[0]] + rotated_indices[2:] + [rotated_indices[1]]
                
                for i in range(0, num_players, 2):
                    team = {
                        'id': f"R{round_num}T{i//2 + 1}",
                        'player1_id': players[rotated_indices[i]]['id'],
                        'player1_name': players[rotated_indices[i]]['nome'] + ' ' + players[rotated_indices[i]]['cognome'],
                        'player2_id': players[rotated_indices[i + 1]]['id'],
                        'player2_name': players[rotated_indices[i + 1]]['nome'] + ' ' + players[rotated_indices[i + 1]]['cognome'],
                        'is_fixed': False
                    }
                    round_teams.append(team)
            
            # Genera le partite per questo turno
            # Ogni squadra gioca contro tutte le altre squadre del turno
            num_teams = len(round_teams)
            
            # Per ogni turno, genera tutte le partite possibili tra le squadre
            for i in range(num_teams):
                for j in range(i + 1, num_teams):
                    match = {
                        'id': match_id,
                        'team1': round_teams[i],
                        'team2': round_teams[j],
                        'court': None,
                        'round': round_num,
                        'status': 'scheduled'
                    }
                    matches.append(match)
                    match_id += 1
        
        return matches
    
    @staticmethod
    def generate_unique_pairs_matches(players):
        """
        Genera partite con coppie SEMPRE DIVERSE: ogni giocatore gioca con tutti almeno una volta,
        nessuna coppia si ripete, ogni partita ha 4 giocatori.
        """
        if len(players) % 2 != 0:
            raise ValueError("Il numero di giocatori deve essere pari per le coppie giranti")
        if len(players) < 4:
            raise ValueError("Servono almeno 4 giocatori")

        # Crea tutte le possibili coppie (ogni giocatore con ogni altro)
        player_ids = [p['id'] for p in players]
        player_map = {p['id']: p for p in players}
        all_pairs = list(combinations(player_ids, 2))
        used_pairs = set()
        matches = []
        match_id = 1

        # Algoritmo greedy: finché ci sono almeno 4 giocatori disponibili, crea una partita con 2 coppie uniche
        available_pairs = set(all_pairs)
        while len(available_pairs) >= 2:
            # Trova due coppie disgiunte (nessun giocatore in comune)
            found = False
            for pair1 in available_pairs:
                for pair2 in available_pairs:
                    if pair1 == pair2:
                        continue
                    # Nessun giocatore in comune
                    if len(set(pair1) & set(pair2)) == 0:
                        # Crea la partita
                        team1 = {
                            'id': f"M{match_id}T1",
                            'player1_id': pair1[0],
                            'player1_name': player_map[pair1[0]]['nome'] + ' ' + player_map[pair1[0]]['cognome'],
                            'player2_id': pair1[1],
                            'player2_name': player_map[pair1[1]]['nome'] + ' ' + player_map[pair1[1]]['cognome'],
                            'is_fixed': False
                        }
                        team2 = {
                            'id': f"M{match_id}T2",
                            'player1_id': pair2[0],
                            'player1_name': player_map[pair2[0]]['nome'] + ' ' + player_map[pair2[0]]['cognome'],
                            'player2_id': pair2[1],
                            'player2_name': player_map[pair2[1]]['nome'] + ' ' + player_map[pair2[1]]['cognome'],
                            'is_fixed': False
                        }
                        match = {
                            'id': match_id,
                            'team1': team1,
                            'team2': team2,
                            'court': None,
                            'round': match_id,  # oppure raggruppa in round dopo
                            'status': 'scheduled'
                        }
                        matches.append(match)
                        match_id += 1
                        # Rimuovi le coppie usate
                        available_pairs.remove(pair1)
                        available_pairs.remove(pair2)
                        found = True
                        break
                if found:
                    break
            if not found:
                # Non ci sono più combinazioni possibili
                break
        return matches
    
    @staticmethod
    def distribute_matches_to_courts(matches, num_courts):
        """Distribuisce le partite sui campi disponibili"""
        court_schedule = {i + 1: [] for i in range(num_courts)}
        
        for i, match in enumerate(matches):
            court_number = (i % num_courts) + 1
            match['court'] = court_number
            court_schedule[court_number].append(match)
        
        return matches, court_schedule
    
    @staticmethod
    def calculate_ranking(teams, matches, results, scoring_method):
        """Calcola la classifica del torneo"""
        team_stats = {}
        
        # Inizializza le statistiche per ogni squadra
        for team in teams:
            team_id = team['id']
            team_stats[team_id] = {
                'team': team,
                'matches_played': 0,
                'matches_won': 0,
                'matches_lost': 0,
                'sets_won': 0,
                'sets_lost': 0,
                'games_won': 0,
                'games_lost': 0,
                'points': 0,
                'game_difference': 0  # Differenza games separata
            }
        
        # Processa i risultati
        for match in matches:
            match_id = str(match['id'])
            if match_id in results:
                result = results[match_id]
                team1_id = match['team1']['id']
                team2_id = match['team2']['id']
                
                # Aggiorna le statistiche delle squadre
                team_stats[team1_id]['matches_played'] += 1
                team_stats[team2_id]['matches_played'] += 1
                
                # Games e Sets
                team1_games = result.get('team1_games', 0)
                team2_games = result.get('team2_games', 0)
                team1_sets = result.get('team1_sets', 0)
                team2_sets = result.get('team2_sets', 0)
                
                # Aggiorna sempre games e sets
                team_stats[team1_id]['games_won'] += team1_games
                team_stats[team1_id]['games_lost'] += team2_games
                team_stats[team2_id]['games_won'] += team2_games
                team_stats[team2_id]['games_lost'] += team1_games
                team_stats[team1_id]['sets_won'] += team1_sets
                team_stats[team1_id]['sets_lost'] += team2_sets
                team_stats[team2_id]['sets_won'] += team2_sets
                team_stats[team2_id]['sets_lost'] += team1_sets
                
                # Calcola sempre la differenza games
                team1_game_diff = team1_games - team2_games
                team2_game_diff = team2_games - team1_games
                team_stats[team1_id]['game_difference'] += team1_game_diff
                team_stats[team2_id]['game_difference'] += team2_game_diff
                
                # Aggiorna sempre vittorie/sconfitte
                if team1_games > team2_games:
                    team_stats[team1_id]['matches_won'] += 1
                    team_stats[team2_id]['matches_lost'] += 1
                elif team2_games > team1_games:
                    team_stats[team2_id]['matches_won'] += 1
                    team_stats[team1_id]['matches_lost'] += 1
                
                # Calcola i punti in base al metodo di punteggio
                if scoring_method == 'game_difference':
                    # Differenza giochi: punti = giochi vinti - giochi persi
                    team_stats[team1_id]['points'] += team1_game_diff
                    team_stats[team2_id]['points'] += team2_game_diff
                    
                elif scoring_method == 'set_points':
                    # Punti set: 2 punti per set vinto, -1 per set perso
                    team1_points = (team1_sets * 2) - team2_sets
                    team2_points = (team2_sets * 2) - team1_sets
                    team_stats[team1_id]['points'] += team1_points
                    team_stats[team2_id]['points'] += team2_points
                    
                else:  # match_points
                    # Punti partita: 3 punti per vittoria, 0 per sconfitta
                    if team1_games > team2_games:
                        team_stats[team1_id]['points'] += 3
                    elif team2_games > team1_games:
                        team_stats[team2_id]['points'] += 3
        
        # Crea la classifica ordinata in base al metodo di punteggio
        ranking = list(team_stats.values())
        if scoring_method == 'game_difference':
            # Ordina per differenza games (decrescente)
            ranking.sort(key=lambda x: x['game_difference'], reverse=True)
        else:
            # Ordina per punti (decrescente), poi per differenza games
            ranking.sort(key=lambda x: (x['points'], x['game_difference']), reverse=True)
        
        return ranking
    
    @staticmethod
    def calculate_advanced_statistics(teams, matches, results):
        """Calcola statistiche avanzate del torneo"""
        statistics = {
            'most_frequent_pairs': [],
            'most_active_players': [],
            'biggest_game_differences': [],
            'player_partnerships': {}
        }
        
        # Analizza le coppie più frequenti (per coppie giranti)
        pair_frequency = {}
        for match in matches:
            team1 = match['team1']
            team2 = match['team2']
            
            # Conta le coppie
            if not team1.get('is_fixed', False):
                pair1 = tuple(sorted([team1['player1_id'], team1['player2_id']]))
                pair_frequency[pair1] = pair_frequency.get(pair1, 0) + 1
            
            if not team2.get('is_fixed', False):
                pair2 = tuple(sorted([team2['player1_id'], team2['player2_id']]))
                pair_frequency[pair2] = pair_frequency.get(pair2, 0) + 1
        
        # Trova le coppie più frequenti
        if pair_frequency:
            sorted_pairs = sorted(pair_frequency.items(), key=lambda x: x[1], reverse=True)
            statistics['most_frequent_pairs'] = sorted_pairs[:5]
        
        # Analizza i giocatori più attivi
        player_activity = {}
        for match in matches:
            for team in [match['team1'], match['team2']]:
                player1_id = team['player1_id']
                player2_id = team['player2_id']
                
                player_activity[player1_id] = player_activity.get(player1_id, 0) + 1
                player_activity[player2_id] = player_activity.get(player2_id, 0) + 1
        
        # Trova i giocatori più attivi
        if player_activity:
            sorted_players = sorted(player_activity.items(), key=lambda x: x[1], reverse=True)
            statistics['most_active_players'] = sorted_players[:5]
        
        # Analizza le differenze di giochi più grandi
        game_differences = []
        for match in matches:
            match_id = str(match['id'])
            if match_id in results:
                result = results[match_id]
                team1_games = result.get('team1_games', 0)
                team2_games = result.get('team2_games', 0)
                
                diff = abs(team1_games - team2_games)
                game_differences.append({
                    'match_id': match['id'],
                    'team1': match['team1'],
                    'team2': match['team2'],
                    'difference': diff
                })
        
        # Trova le differenze più grandi
        if game_differences:
            game_differences.sort(key=lambda x: x['difference'], reverse=True)
            statistics['biggest_game_differences'] = game_differences[:5]
        
        return statistics
    
    @staticmethod
    def generate_simple_american_tournament(players, num_courts, num_rounds_config):
        """
        Genera torneo americano "semplice" con distribuzione equa delle partite.
        Ogni giocatore dovrebbe giocare approssimativamente lo stesso numero di partite.
        """
        n = len(players)
        if n % 2 != 0:
            raise ValueError("Il numero di giocatori deve essere pari")
        if n < 4:
            raise ValueError("Servono almeno 4 giocatori per il torneo americano 'semplice'")

        matches = []
        match_id = 1
        
        # Traccia quante partite ha giocato ogni giocatore
        player_match_count = {player['id']: 0 for player in players}
        
        # Calcola il numero target di partite per giocatore
        # Con n giocatori e num_courts campi, ogni turno può avere al massimo num_courts partite
        # Ogni partita coinvolge 4 giocatori, quindi ogni turno coinvolge al massimo 4*num_courts giocatori
        max_players_per_round = min(n, 4 * num_courts)
        target_matches_per_player = (num_rounds_config * max_players_per_round) // n

        # Genera i turni
        for round_num in range(1, num_rounds_config + 1):
            current_round_matches = []
            
            # Seleziona i giocatori per questo turno
            # Preferisci quelli che hanno giocato meno partite
            available_players = sorted(players, key=lambda p: player_match_count[p['id']])
            
            # Prendi i primi giocatori disponibili per questo turno
            players_for_round = available_players[:max_players_per_round]
            
            # Se il numero di giocatori per turno è dispari, aggiungi un giocatore
            if len(players_for_round) % 2 != 0 and len(players_for_round) < n:
                players_for_round.append(available_players[len(players_for_round)])
            
            # Crea le coppie per questo turno
            round_teams = []
            for i in range(0, len(players_for_round), 2):
                if i + 1 < len(players_for_round):
                    team = {
                        'id': f"R{round_num}T{i//2 + 1}",
                        'player1_id': players_for_round[i]['id'],
                        'player1_name': players_for_round[i]['nome'] + ' ' + players_for_round[i]['cognome'],
                        'player2_id': players_for_round[i + 1]['id'],
                        'player2_name': players_for_round[i + 1]['nome'] + ' ' + players_for_round[i + 1]['cognome'],
                        'is_fixed': False
                    }
                    round_teams.append(team)
            
            # Genera le partite per questo turno
            available_teams = round_teams.copy()
            
            for court_idx in range(num_courts):
                if len(available_teams) < 2:
                    break
                
                team1 = available_teams.pop(0)
                team2 = available_teams.pop(0)
                
                # Aggiorna il conteggio delle partite per i giocatori
                player_match_count[team1['player1_id']] += 1
                player_match_count[team1['player2_id']] += 1
                player_match_count[team2['player1_id']] += 1
                player_match_count[team2['player2_id']] += 1
                
                match = {
                    'id': match_id,
                    'team1': team1,
                    'team2': team2,
                    'court': court_idx + 1,
                    'round': round_num,
                    'status': 'scheduled'
                }
                current_round_matches.append(match)
                match_id += 1
            
            matches.extend(current_round_matches)

        return matches
    
    @staticmethod
    def calculate_player_ranking(matches, results, scoring_method='match_points'):
        """
        Calcola la classifica individuale per tornei americana con coppie giranti.
        Rispetta il metodo di punteggio scelto dall'utente.
        """
        player_stats = {}
        player_names = {}  # Cache per i nomi dei giocatori
        
        for match in matches:
            match_id = str(match['id'])
            if match_id not in results:
                continue
            result = results[match_id]
            # Estrai giocatori e nomi
            t1p1 = match['team1']['player1_id']
            t1p1_name = match['team1']['player1_name']
            t1p2 = match['team1'].get('player2_id')
            t1p2_name = match['team1'].get('player2_name', '')
            t2p1 = match['team2']['player1_id']
            t2p1_name = match['team2']['player1_name']
            t2p2 = match['team2'].get('player2_id')
            t2p2_name = match['team2'].get('player2_name', '')
            
            # Cache dei nomi
            player_names[t1p1] = t1p1_name
            if t1p2:
                player_names[t1p2] = t1p2_name
            player_names[t2p1] = t2p1_name
            if t2p2:
                player_names[t2p2] = t2p2_name
            
            # Games e Sets
            g1 = result.get('team1_games', 0)
            g2 = result.get('team2_games', 0)
            s1 = result.get('team1_sets', 0)
            s2 = result.get('team2_sets', 0)
            
            # Calcola sempre la differenza games
            team1_game_diff = g1 - g2
            team2_game_diff = g2 - g1
            
            # Calcola i punti in base al metodo di punteggio
            if scoring_method == 'game_difference':
                # Differenza games: punti = games vinti - games persi
                team1_points = team1_game_diff
                team2_points = team2_game_diff
            elif scoring_method == 'set_points':
                # Punti set: 2 punti per set vinto, -1 per set perso
                team1_points = (s1 * 2) - s2
                team2_points = (s2 * 2) - s1
            else:  # match_points (default)
                # Punti partita: 3 punti per vittoria, 0 per sconfitta
                if g1 > g2:
                    team1_points = 3
                    team2_points = 0
                elif g2 > g1:
                    team1_points = 0
                    team2_points = 3
                else:
                    team1_points = 1  # pareggio
                    team2_points = 1
            
            # Aggiorna stats per ogni giocatore della squadra 1
            for pid in [t1p1, t1p2]:
                if pid is None:
                    continue
                if pid not in player_stats:
                    player_stats[pid] = {
                        'player_id': pid,
                        'player_name': player_names.get(pid, f'Giocatore {pid}'),
                        'matches_played': 0,
                        'matches_won': 0,
                        'matches_lost': 0,
                        'matches_drawn': 0,
                        'sets_won': 0,
                        'sets_lost': 0,
                        'games_won': 0,
                        'games_lost': 0,
                        'points': 0,
                        'game_difference': 0
                    }
                player_stats[pid]['matches_played'] += 1
                player_stats[pid]['games_won'] += g1
                player_stats[pid]['games_lost'] += g2
                player_stats[pid]['sets_won'] += s1
                player_stats[pid]['sets_lost'] += s2
                player_stats[pid]['points'] += team1_points
                player_stats[pid]['game_difference'] += team1_game_diff
                
                # Aggiorna sempre vittorie/sconfitte
                if g1 > g2:
                    player_stats[pid]['matches_won'] += 1
                elif g2 > g1:
                    player_stats[pid]['matches_lost'] += 1
                else:
                    player_stats[pid]['matches_drawn'] += 1
            
            # Aggiorna stats per ogni giocatore della squadra 2
            for pid in [t2p1, t2p2]:
                if pid is None:
                    continue
                if pid not in player_stats:
                    player_stats[pid] = {
                        'player_id': pid,
                        'player_name': player_names.get(pid, f'Giocatore {pid}'),
                        'matches_played': 0,
                        'matches_won': 0,
                        'matches_lost': 0,
                        'matches_drawn': 0,
                        'sets_won': 0,
                        'sets_lost': 0,
                        'games_won': 0,
                        'games_lost': 0,
                        'points': 0,
                        'game_difference': 0
                    }
                player_stats[pid]['matches_played'] += 1
                player_stats[pid]['games_won'] += g2
                player_stats[pid]['games_lost'] += g1
                player_stats[pid]['sets_won'] += s2
                player_stats[pid]['sets_lost'] += s1
                player_stats[pid]['points'] += team2_points
                player_stats[pid]['game_difference'] += team2_game_diff
                
                # Aggiorna sempre vittorie/sconfitte
                if g2 > g1:
                    player_stats[pid]['matches_won'] += 1
                elif g1 > g2:
                    player_stats[pid]['matches_lost'] += 1
                else:
                    player_stats[pid]['matches_drawn'] += 1
        
        # Ordina in base al metodo di punteggio
        ranking = list(player_stats.values())
        if scoring_method == 'game_difference':
            # Ordina per differenza games (decrescente)
            ranking.sort(key=lambda x: x['game_difference'], reverse=True)
        else:
            # Ordina per punti (decrescente), poi per differenza games
            ranking.sort(key=lambda x: (x['points'], x['game_difference']), reverse=True)
        
        return ranking
    
    @staticmethod
    def generate_tournament_schedule(players, courts, max_rounds=None):
        """
        Genera un calendario a coppie uniche diviso in turni e campi.
        players   : lista di dict {'id', 'nome', 'cognome'}
        courts    : campi disponibili per turno
        max_rounds: limite massimo di turni (None = fino a esaurimento coppie)
        Ritorna: lista di round, ognuno lista di match (dict)
        """
        n = len(players)
        if n % 2:
            raise ValueError("Serve un numero pari di giocatori")
        if n < 4:
            raise ValueError("Servono almeno 4 giocatori")
        if courts < 1:
            raise ValueError("Serve almeno un campo")

        matches_per_round = min(courts, n // 4)
        player_map = {p['id']: p for p in players}
        all_pairs = list(combinations([p['id'] for p in players], 2))
        rounds = []
        match_id = 1
        round_no = 1

        while len(all_pairs) >= 2 and (max_rounds is None or round_no <= max_rounds):
            used_players = set()
            matches_this_round = []

            # tenta di riempire tutti i campi
            for _ in range(matches_per_round):
                found = False
                for p1 in list(all_pairs):
                    if p1[0] in used_players or p1[1] in used_players:
                        continue
                    for p2 in list(all_pairs):
                        if p1 == p2: 
                            continue
                        if (p2[0] in used_players or p2[1] in used_players or
                            p2[0] in p1 or p2[1] in p1):
                            continue
                        # partita valida trovata
                        def make_team(pair, team_id):
                            a, b = pair
                            return {
                                'id'           : f"M{match_id}{team_id}",
                                'player1_id'   : a,
                                'player1_name' : f"{player_map[a]['nome']} {player_map[a]['cognome']}",
                                'player2_id'   : b,
                                'player2_name' : f"{player_map[b]['nome']} {player_map[b]['cognome']}",
                                'is_fixed'     : False
                            }
                        match = {
                            'id'   : match_id,
                            'round': round_no,
                            'court': len(matches_this_round) + 1,
                            'team1': make_team(p1, 'T1'),
                            'team2': make_team(p2, 'T2'),
                            'status':'scheduled'
                        }
                        matches_this_round.append(match)
                        match_id += 1
                        used_players.update(p1); used_players.update(p2)
                        all_pairs.remove(p1);  all_pairs.remove(p2)
                        found = True
                        break
                    if found:
                        break  # passa al prossimo campo
                else:
                    break      # impossibile riempire altri campi

            if not matches_this_round:
                break  # nessuna partita possibile, termina
            rounds.append(matches_this_round)
            round_no += 1

        return rounds 