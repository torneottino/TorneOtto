from app import create_app
from extensions import db
from models.tournament import Tournament
from models.tournament_day import AmericanaDay
from services.americana_service import AmericanaService
from datetime import date

app = create_app()
with app.app_context():
    tournament = db.session.get(Tournament, 103)
    players = tournament.get_config().get('players', [])
    if not players:
        old_day = AmericanaDay.query.filter_by(tournament_id=103).order_by(AmericanaDay.id.desc()).first()
        players = old_day.get_players() if old_day else []
    config = tournament.get_config()
    num_rounds = 5
    num_courts = config.get('num_campi', 2)
    rounds = AmericanaService.generate_tournament_schedule(players, num_courts, num_rounds)
    matches = [m for round_matches in rounds for m in round_matches]
    teams = AmericanaService.create_teams_rotating(players)
    matches, court_schedule = AmericanaService.distribute_matches_to_courts(matches, num_courts)
    day = AmericanaDay(tournament_id=103, data=date.today(), stato='Setup completato')
    day.set_players(players)
    day.set_teams(teams)
    day.set_matches(matches)
    day.set_courts(list(range(1, num_courts + 1)))
    db.session.add(day)
    db.session.commit()
    print('Nuova giornata creata con algoritmo VERO!')
    # Stampa dettagliata delle partite
    for match in matches:
        t1 = match['team1']
        t2 = match['team2']
        print(f"Turno {match['round']} - Campo {match['court']}: {t1['player1_name']} / {t1['player2_name']} vs {t2['player1_name']} / {t2['player2_name']}") 