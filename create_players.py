from models.player import Player
from extensions import db
from app import create_app

def create_initial_players():
    # Lista di giocatori da creare
    players = [
        {
            'nome': 'Mario',
            'cognome': 'Rossi',
            'telefono': '3331234567',
            'posizione': 'Destra',
            'elo_standard': 1500.00
        },
        {
            'nome': 'Luigi',
            'cognome': 'Verdi',
            'telefono': '3332345678',
            'posizione': 'Sinistra',
            'elo_standard': 1500.00
        },
        {
            'nome': 'Giovanni',
            'cognome': 'Bianchi',
            'telefono': '3333456789',
            'posizione': 'Indifferente',
            'elo_standard': 1500.00
        },
        {
            'nome': 'Paolo',
            'cognome': 'Neri',
            'telefono': '3334567890',
            'posizione': 'Destra',
            'elo_standard': 1500.00
        },
        {
            'nome': 'Marco',
            'cognome': 'Gialli',
            'telefono': '3335678901',
            'posizione': 'Sinistra',
            'elo_standard': 1500.00
        },
        {
            'nome': 'Andrea',
            'cognome': 'Blu',
            'telefono': '3336789012',
            'posizione': 'Indifferente',
            'elo_standard': 1500.00
        },
        {
            'nome': 'Stefano',
            'cognome': 'Viola',
            'telefono': '3337890123',
            'posizione': 'Destra',
            'elo_standard': 1500.00
        },
        {
            'nome': 'Roberto',
            'cognome': 'Arancione',
            'telefono': '3338901234',
            'posizione': 'Sinistra',
            'elo_standard': 1500.00
        }
    ]

    # Creazione dell'applicazione
    app = create_app()
    
    # Utilizzo del contesto dell'applicazione
    with app.app_context():
        # Inserimento dei giocatori nel database
        for player_data in players:
            player = Player(**player_data)
            db.session.add(player)

        try:
            db.session.commit()
            print("Giocatori creati con successo!")
        except Exception as e:
            db.session.rollback()
            print(f"Errore durante la creazione dei giocatori: {str(e)}")

if __name__ == '__main__':
    create_initial_players() 