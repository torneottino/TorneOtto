#!/usr/bin/env python3
"""
Script per risolvere manualmente il problema di eliminazione torneo.
Esegui questo script per pulire i record orfani che causano violazioni di foreign key.
"""

from app import create_app
from extensions import db
from sqlalchemy import text

# Crea l'app usando il factory pattern
app = create_app()

def fix_tournament_deletion(tournament_id):
    """Risolve il problema di eliminazione per un torneo specifico"""
    
    with app.app_context():
        try:
            print(f"Risoluzione problema eliminazione per torneo ID: {tournament_id}")
            
            # 1. Elimina record dalle tabelle legacy
            legacy_tables = ['pozzo_courts', 'pozzo_teams', 'pozzo_matches', 'pozzo_players']
            
            for table_name in legacy_tables:
                try:
                    result = db.session.execute(
                        text(f"DELETE FROM {table_name} WHERE tournament_id = :tournament_id"),
                        {"tournament_id": tournament_id}
                    )
                    db.session.commit()  # Commit individuale per ogni tabella
                    print(f"✓ Eliminati record dalla tabella {table_name}")
                except Exception as e:
                    db.session.rollback()  # Rollback solo per questa tabella
                    print(f"✗ Tabella {table_name}: {str(e)}")
            
            # 2. Elimina ELO history
            try:
                db.session.execute(
                    text("DELETE FROM player_elo_history WHERE tournament_id = :tournament_id"),
                    {"tournament_id": tournament_id}
                )
                db.session.commit()
                print("✓ Eliminati record ELO history")
            except Exception as e:
                db.session.rollback()
                print(f"✗ Errore ELO history: {str(e)}")
            
            # 3. Elimina ELO ratings
            try:
                db.session.execute(
                    text("DELETE FROM player_tournament_elo WHERE tournament_id = :tournament_id"),
                    {"tournament_id": tournament_id}
                )
                db.session.commit()
                print("✓ Eliminati record ELO ratings")
            except Exception as e:
                db.session.rollback()
                print(f"✗ Errore ELO ratings: {str(e)}")
            
            # 4. Elimina giornate eliminazione
            try:
                db.session.execute(
                    text("DELETE FROM elimin_day WHERE tournament_id = :tournament_id"),
                    {"tournament_id": tournament_id}
                )
                db.session.commit()
                print("✓ Eliminate giornate eliminazione")
            except Exception as e:
                db.session.rollback()
                print(f"✗ Errore giornate eliminazione: {str(e)}")
            
            # 5. Elimina giornate torneo
            try:
                db.session.execute(
                    text("DELETE FROM tournament_day WHERE tournament_id = :tournament_id"),
                    {"tournament_id": tournament_id}
                )
                db.session.commit()
                print("✓ Eliminate giornate torneo")
            except Exception as e:
                db.session.rollback()
                print(f"✗ Errore giornate torneo: {str(e)}")
            
            # 6. Elimina il torneo
            try:
                db.session.execute(
                    text("DELETE FROM tournament WHERE id = :tournament_id"),
                    {"tournament_id": tournament_id}
                )
                db.session.commit()
                print("✓ Eliminato il torneo")
                return True
            except Exception as e:
                db.session.rollback()
                print(f"✗ Errore eliminazione torneo: {str(e)}")
                return False
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Errore generale: {str(e)}")
            return False

def cleanup_all_orphaned_records():
    """Pulisce tutti i record orfani dal database"""
    
    with app.app_context():
        try:
            print("Pulizia di tutti i record orfani...")
            
            # Lista delle tabelle legacy
            legacy_tables = ['pozzo_courts', 'pozzo_teams', 'pozzo_matches', 'pozzo_players']
            
            for table_name in legacy_tables:
                try:
                    result = db.session.execute(text(f"""
                        DELETE FROM {table_name} 
                        WHERE tournament_id NOT IN (SELECT id FROM tournament);
                    """))
                    print(f"✓ Pulita tabella {table_name}")
                except Exception as e:
                    print(f"✗ Errore con tabella {table_name}: {str(e)}")
            
            db.session.commit()
            print("✓ Pulizia completata!")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Errore generale: {str(e)}")
            return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "cleanup":
            cleanup_all_orphaned_records()
        elif sys.argv[1].isdigit():
            tournament_id = int(sys.argv[1])
            fix_tournament_deletion(tournament_id)
        else:
            print("Uso:")
            print("  python fix_tournament_deletion.py <tournament_id>  - Risolve per un torneo specifico")
            print("  python fix_tournament_deletion.py cleanup          - Pulisce tutti i record orfani")
    else:
        print("Script per risolvere problemi di eliminazione torneo")
        print("Uso:")
        print("  python fix_tournament_deletion.py <tournament_id>  - Risolve per un torneo specifico")
        print("  python fix_tournament_deletion.py cleanup          - Pulisce tutti i record orfani") 