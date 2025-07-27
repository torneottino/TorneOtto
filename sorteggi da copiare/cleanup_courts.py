#!/usr/bin/env python3
"""
Script per pulire la tabella pozzo_courts da record orfani che causano violazioni di foreign key.
"""

from app import app
from extensions import db
from sqlalchemy import text

def cleanup_legacy_tables():
    with app.app_context():
        try:
            # Lista delle tabelle legacy che potrebbero avere foreign key constraints
            legacy_tables = ['pozzo_courts', 'pozzo_teams', 'pozzo_matches', 'pozzo_players']
            
            for table_name in legacy_tables:
                try:
                    # Elimina record orfani dalla tabella
                    result = db.session.execute(text(f"""
                        DELETE FROM {table_name} 
                        WHERE tournament_id NOT IN (SELECT id FROM tournament);
                    """))
                    
                    db.session.commit()
                    print(f"Pulita tabella {table_name}")
                        
                except Exception as e:
                    print(f"Errore con tabella {table_name}: {str(e)}")
                    db.session.rollback()
                    
        except Exception as e:
            print(f"Errore generale: {str(e)}")
            db.session.rollback()

def list_courts_records():
    """Lista tutti i record nella tabella pozzo_courts"""
    
    with app.app_context():
        try:
            # Verifica se la tabella esiste
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pozzo_courts'
                );
            """)).scalar()
            
            if not result:
                print("La tabella pozzo_courts non esiste nel database.")
                return
            
            # Lista tutti i record
            records = db.session.execute(text("""
                SELECT pc.id, pc.tournament_id, t.nome as tournament_name
                FROM pozzo_courts pc 
                LEFT JOIN tournament t ON pc.tournament_id = t.id 
                ORDER BY pc.tournament_id;
            """)).fetchall()
            
            if not records:
                print("Nessun record trovato nella tabella pozzo_courts.")
                return
            
            print(f"Trovati {len(records)} record nella tabella pozzo_courts:")
            print("ID | Tournament ID | Tournament Name")
            print("-" * 50)
            for record in records:
                tournament_name = record[2] if record[2] else "TORNEO NON TROVATO"
                print(f"{record[0]} | {record[1]} | {tournament_name}")
                
        except Exception as e:
            print(f"Errore durante la lettura: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "list":
            list_courts_records()
        elif command == "cleanup":
            cleanup_legacy_tables()
        else:
            print("Comandi disponibili:")
            print("  python cleanup_courts.py list     - Lista tutti i record")
            print("  python cleanup_courts.py cleanup  - Pulisce i record orfani")
    else:
        print("Script per la gestione della tabella pozzo_courts")
        print("Comandi disponibili:")
        print("  python cleanup_courts.py list     - Lista tutti i record")
        print("  python cleanup_courts.py cleanup  - Pulisce i record orfani")
        cleanup_legacy_tables() 