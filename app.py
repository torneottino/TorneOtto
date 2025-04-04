from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import os
import time
import datetime
import random
from werkzeug.utils import secure_filename
from weasyprint import HTML
from io import BytesIO

app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')

# Abilita il reload automatico dei template
app.config['TEMPLATES_AUTO_RELOAD'] = True
# Disabilita la cache per i file statici durante lo sviluppo
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
# Chiave segreta per i messaggi flash
app.secret_key = 'torneotto_secret_key'

# Versione per il refresh dei file statici
VERSION = int(time.time())

# Configurazione del database
DATABASE = 'app/database/torneotto.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists('app/database'):
        os.makedirs('app/database')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Creazione tabella giocatori
    c.execute('''CREATE TABLE IF NOT EXISTS giocatori
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT NOT NULL,
                  punteggio_elo REAL DEFAULT 1500.0,
                  posizione TEXT CHECK(posizione IN ('DESTRA', 'SINISTRA', 'INDIFFERENTE')))''')
    
    # Creazione tabella tornei
    c.execute('''CREATE TABLE IF NOT EXISTS tornei
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT NOT NULL,
                  circolo TEXT,
                  tipo_torneo TEXT CHECK(tipo_torneo IN ('TORNEOTTO_30', 'TORNEOTTO_45')))''')
    
    # Creazione tabella giornate
    c.execute('''CREATE TABLE IF NOT EXISTS giornate
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  torneo_id INTEGER NOT NULL,
                  data TEXT NOT NULL,
                  stato TEXT DEFAULT 'BOZZA' CHECK(stato IN ('BOZZA', 'CONFERMATA', 'COMPLETATA')),
                  metodo_sorteggio TEXT CHECK(metodo_sorteggio IN ('TESTE_DI_SERIE', 'PUNTI_E_POSIZIONE', 'CASUALE')),
                  FOREIGN KEY (torneo_id) REFERENCES tornei (id) ON DELETE CASCADE)''')
    
    # Creazione tabella squadre
    c.execute('''CREATE TABLE IF NOT EXISTS squadre
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  giornata_id INTEGER NOT NULL,
                  giocatore1_id INTEGER NOT NULL,
                  giocatore2_id INTEGER NOT NULL,
                  nome_squadra TEXT,
                  punteggio_totale REAL,
                  FOREIGN KEY (giornata_id) REFERENCES giornate (id) ON DELETE CASCADE,
                  FOREIGN KEY (giocatore1_id) REFERENCES giocatori (id),
                  FOREIGN KEY (giocatore2_id) REFERENCES giocatori (id))''')
    
    # Creazione tabella partite
    c.execute('''CREATE TABLE IF NOT EXISTS partite
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  giornata_id INTEGER NOT NULL,
                  squadra1_id INTEGER NOT NULL,
                  squadra2_id INTEGER NOT NULL,
                  punteggio_squadra1 INTEGER DEFAULT 0,
                  punteggio_squadra2 INTEGER DEFAULT 0,
                  turno INTEGER NOT NULL,
                  campo INTEGER NOT NULL,
                  stato TEXT DEFAULT 'DA_GIOCARE' CHECK(stato IN ('DA_GIOCARE', 'COMPLETATA')),
                  FOREIGN KEY (giornata_id) REFERENCES giornate (id) ON DELETE CASCADE,
                  FOREIGN KEY (squadra1_id) REFERENCES squadre (id),
                  FOREIGN KEY (squadra2_id) REFERENCES squadre (id))''')
    
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('home.html', version=VERSION)

@app.route('/inserimento-giocatori', methods=['GET', 'POST'])
def inserimento_giocatori():
    if request.method == 'POST':
        nome = request.form['nome']
        punteggio_elo = request.form.get('punteggio_elo', 1500.0)
        posizione = request.form['posizione']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO giocatori (nome, punteggio_elo, posizione) VALUES (?, ?, ?)',
                     (nome, punteggio_elo, posizione))
        conn.commit()
        conn.close()
        
        return redirect(url_for('inserimento_giocatori'))
    
    # GET request
    conn = get_db_connection()
    giocatori = conn.execute('SELECT * FROM giocatori ORDER BY nome').fetchall()
    conn.close()
    
    return render_template('inserimento_giocatori.html', giocatori=giocatori, version=VERSION)

@app.route('/modifica-giocatore/<int:id>', methods=['GET', 'POST'])
def modifica_giocatore(id):
    conn = get_db_connection()
    giocatore = conn.execute('SELECT * FROM giocatori WHERE id = ?', (id,)).fetchone()
    
    if giocatore is None:
        conn.close()
        return redirect(url_for('inserimento_giocatori'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        punteggio_elo = request.form.get('punteggio_elo', 1500.0)
        posizione = request.form['posizione']
        
        conn.execute('UPDATE giocatori SET nome = ?, punteggio_elo = ?, posizione = ? WHERE id = ?',
                     (nome, punteggio_elo, posizione, id))
        conn.commit()
        conn.close()
        
        return redirect(url_for('inserimento_giocatori'))
    
    conn.close()
    return render_template('modifica_giocatore.html', giocatore=giocatore, version=VERSION)

@app.route('/elimina-giocatore/<int:id>')
def elimina_giocatore(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM giocatori WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('inserimento_giocatori'))

@app.route('/inserimento-torneo', methods=['GET', 'POST'])
def inserimento_torneo():
    if request.method == 'POST':
        nome = request.form['nome']
        circolo = request.form['circolo']
        tipo_torneo = request.form['tipo_torneo']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO tornei (nome, circolo, tipo_torneo) VALUES (?, ?, ?)',
                     (nome, circolo, tipo_torneo))
        conn.commit()
        conn.close()
        
        return redirect(url_for('inserimento_torneo'))
    
    # GET request
    conn = get_db_connection()
    tornei = conn.execute('SELECT * FROM tornei ORDER BY id DESC LIMIT 5').fetchall()
    conn.close()
    
    return render_template('inserimento_torneo.html', tornei=tornei, version=VERSION)

@app.route('/gestione-tornei')
def gestione_tornei():
    conn = get_db_connection()
    tornei = conn.execute('SELECT * FROM tornei ORDER BY nome').fetchall()
    
    # Per ogni torneo, aggiungiamo la lista delle giornate (ancora da implementare)
    tornei_con_giornate = []
    for torneo in tornei:
        torneo_dict = dict(torneo)
        # Qui in futuro caricheremo le giornate dal database
        torneo_dict['giornate'] = []
        tornei_con_giornate.append(torneo_dict)
    
    conn.close()
    
    return render_template('gestione_tornei.html', tornei=tornei_con_giornate, version=VERSION)

@app.route('/modifica-torneo/<int:id>', methods=['GET', 'POST'])
def modifica_torneo(id):
    conn = get_db_connection()
    torneo = conn.execute('SELECT * FROM tornei WHERE id = ?', (id,)).fetchone()
    
    if torneo is None:
        conn.close()
        return redirect(url_for('gestione_tornei'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        circolo = request.form['circolo']
        tipo_torneo = request.form['tipo_torneo']
        
        conn.execute('UPDATE tornei SET nome = ?, circolo = ?, tipo_torneo = ? WHERE id = ?',
                     (nome, circolo, tipo_torneo, id))
        conn.commit()
        conn.close()
        
        return redirect(url_for('gestione_tornei'))
    
    conn.close()
    return render_template('modifica_torneo.html', torneo=torneo, version=VERSION)

@app.route('/elimina-torneo/<int:id>')
def elimina_torneo(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM tornei WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('gestione_tornei'))

@app.route('/torneo/<int:id>')
def visualizza_torneo(id):
    conn = get_db_connection()
    torneo = conn.execute('SELECT * FROM tornei WHERE id = ?', (id,)).fetchone()
    
    if torneo is None:
        conn.close()
        return redirect(url_for('gestione_tornei'))
    
    # Carichiamo le giornate dal database
    giornate = conn.execute('SELECT * FROM giornate WHERE torneo_id = ? ORDER BY data DESC', (id,)).fetchall()
    
    conn.close()
    
    # Renderizziamo il template per la visualizzazione del torneo
    return render_template('visualizza_torneo.html', torneo=torneo, giornate=giornate, version=VERSION)

@app.route('/nuova-giornata/<int:torneo_id>', methods=['GET', 'POST'])
def nuova_giornata(torneo_id):
    conn = get_db_connection()
    torneo = conn.execute('SELECT * FROM tornei WHERE id = ?', (torneo_id,)).fetchone()
    
    if torneo is None:
        conn.close()
        return redirect(url_for('gestione_tornei'))
    
    if request.method == 'POST':
        data = request.form['data']
        
        # Creiamo la nuova giornata nel database
        cursor = conn.execute('INSERT INTO giornate (torneo_id, data) VALUES (?, ?)',
                     (torneo_id, data))
        giornata_id = cursor.lastrowid
        conn.commit()
        
        # Recuperiamo gli ID dei giocatori selezionati
        giocatori_selezionati = request.form.getlist('giocatori')
        
        # Verifichiamo che siano stati selezionati esattamente 8 giocatori
        if len(giocatori_selezionati) != 8:
            flash('Devi selezionare esattamente 8 giocatori per la giornata.')
            conn.close()
            return redirect(url_for('nuova_giornata', torneo_id=torneo_id))
        
        # Salviamo temporaneamente gli ID dei giocatori nella sessione
        session['giocatori_selezionati'] = giocatori_selezionati
        session['giornata_id'] = giornata_id
        
        conn.close()
        return redirect(url_for('sorteggio', giornata_id=giornata_id))
    
    # GET request
    giocatori = conn.execute('SELECT * FROM giocatori ORDER BY nome').fetchall()
    conn.close()
    
    return render_template('nuova_giornata.html', torneo=torneo, giocatori=giocatori, version=VERSION)

@app.route('/nuovo-torneo')
def nuovo_torneo():
    # Reindirizza alla pagina di inserimento torneo
    return redirect(url_for('inserimento_torneo'))

@app.route('/sorteggio/<int:giornata_id>', methods=['GET', 'POST'])
def sorteggio(giornata_id):
    conn = get_db_connection()
    giornata = conn.execute('SELECT * FROM giornate WHERE id = ?', (giornata_id,)).fetchone()
    
    if giornata is None:
        conn.close()
        return redirect(url_for('gestione_tornei'))
    
    torneo = conn.execute('SELECT * FROM tornei WHERE id = ?', (giornata['torneo_id'],)).fetchone()
    
    # Verifichiamo che ci siano giocatori selezionati nella sessione
    if 'giocatori_selezionati' not in session:
        conn.close()
        return redirect(url_for('nuova_giornata', torneo_id=torneo['id']))
    
    giocatori_ids = session['giocatori_selezionati']
    if len(giocatori_ids) != 8:
        conn.close()
        return redirect(url_for('nuova_giornata', torneo_id=torneo['id']))
    
    # Recuperiamo i dati dei giocatori
    giocatori = []
    for id in giocatori_ids:
        giocatore = conn.execute('SELECT * FROM giocatori WHERE id = ?', (id,)).fetchone()
        if giocatore:
            giocatori.append(dict(giocatore))
    
    if request.method == 'POST':
        # Verifichiamo se si tratta di un'azione di conferma o di sorteggio
        action = request.form.get('action')
        
        if action == 'conferma':
            # Qui aggiungiamo il codice per confermare la giornata
            conn.execute('UPDATE giornate SET stato = ? WHERE id = ?', ('CONFERMATA', giornata_id))
            conn.commit()
            conn.close()
            # Rimuoviamo i dati dalla sessione se ancora presenti
            if 'giocatori_selezionati' in session:
                session.pop('giocatori_selezionati', None)
            return redirect(url_for('visualizza_giornata', giornata_id=giornata_id))
        
        elif action == 'ripeti':
            # Eliminiamo tutte le squadre e partite esistenti per questa giornata
            conn.execute('DELETE FROM partite WHERE giornata_id = ?', (giornata_id,))
            conn.execute('DELETE FROM squadre WHERE giornata_id = ?', (giornata_id,))
            conn.commit()
            # Riportiamo l'utente alla pagina di scelta del metodo di sorteggio
            conn.close()
            return redirect(url_for('sorteggio', giornata_id=giornata_id))
        
        elif action == 'sorteggio':
            metodo_sorteggio = request.form['metodo_sorteggio']
            
            # Aggiorniamo la giornata con il metodo di sorteggio scelto, ma manteniamo lo stato BOZZA
            conn.execute('UPDATE giornate SET metodo_sorteggio = ? WHERE id = ?',
                        (metodo_sorteggio, giornata_id))
            conn.commit()
            
            # Prima di tutto, eliminiamo eventuali squadre e partite esistenti
            conn.execute('DELETE FROM partite WHERE giornata_id = ?', (giornata_id,))
            conn.execute('DELETE FROM squadre WHERE giornata_id = ?', (giornata_id,))
            conn.commit()
            
            # Eseguiamo il sorteggio in base al metodo scelto
            if metodo_sorteggio == 'TESTE_DI_SERIE':
                # Se abbiamo le teste di serie nella richiesta
                teste_di_serie = request.form.getlist('teste_di_serie')
                if teste_di_serie and len(teste_di_serie) == 4:
                    squadre = sorteggio_teste_di_serie(conn, giornata_id, giocatori, teste_di_serie)
                else:
                    # Se non abbiamo le teste di serie, mostriamo la pagina per selezionarle
                    conn.close()
                    return render_template('selezione_teste.html', giornata=giornata, torneo=torneo, 
                                        giocatori=giocatori, version=VERSION)
            elif metodo_sorteggio == 'PUNTI_E_POSIZIONE':
                squadre = sorteggio_punti_posizione(conn, giornata_id, giocatori)
            else:  # CASUALE
                squadre = sorteggio_casuale(conn, giornata_id, giocatori)
            
            # Creiamo le partite in base al tipo di torneo
            if torneo['tipo_torneo'] == 'TORNEOTTO_30':
                crea_partite_round_robin(conn, giornata_id, squadre)
            else:  # TORNEOTTO_45
                crea_partite_eliminazione_diretta(conn, giornata_id, squadre)
            
            conn.commit()
            
            # Dopo aver eseguito il sorteggio e creato le partite, redirect alla stessa pagina
            # per mostrare i risultati
            conn.close()
            return redirect(url_for('sorteggio', giornata_id=giornata_id))
    
    # GET request - Verifichiamo se ci sono già squadre create per questa giornata
    squadre = recupera_squadre(conn, giornata_id)
    partite = recupera_partite(conn, giornata_id)
    
    conn.close()
    return render_template('sorteggio.html', giornata=giornata, torneo=torneo, 
                         giocatori=giocatori, squadre=squadre, partite=partite, version=VERSION)

@app.route('/selezione-teste/<int:giornata_id>', methods=['GET', 'POST'])
def selezione_teste(giornata_id):
    conn = get_db_connection()
    giornata = conn.execute('SELECT * FROM giornate WHERE id = ?', (giornata_id,)).fetchone()
    
    if giornata is None:
        conn.close()
        return redirect(url_for('gestione_tornei'))
    
    torneo = conn.execute('SELECT * FROM tornei WHERE id = ?', (giornata['torneo_id'],)).fetchone()
    
    # Verifichiamo che ci siano giocatori selezionati nella sessione
    if 'giocatori_selezionati' not in session:
        conn.close()
        return redirect(url_for('nuova_giornata', torneo_id=torneo['id']))
    
    giocatori_ids = session['giocatori_selezionati']
    
    # Recuperiamo i dati dei giocatori
    giocatori = []
    for id in giocatori_ids:
        giocatore = conn.execute('SELECT * FROM giocatori WHERE id = ?', (id,)).fetchone()
        if giocatore:
            giocatori.append(dict(giocatore))
    
    if request.method == 'POST':
        # Recuperiamo le teste di serie selezionate
        teste_di_serie = request.form.getlist('teste_di_serie')
        
        if teste_di_serie and len(teste_di_serie) == 4:
            # Creiamo le squadre con le teste di serie selezionate
            squadre = sorteggio_teste_di_serie(conn, giornata_id, giocatori, teste_di_serie)
            
            # Creiamo le partite in base al tipo di torneo
            if torneo['tipo_torneo'] == 'TORNEOTTO_30':
                crea_partite_round_robin(conn, giornata_id, squadre)
            else:  # TORNEOTTO_45
                crea_partite_eliminazione_diretta(conn, giornata_id, squadre)
            
            # Aggiorniamo il metodo di sorteggio della giornata
            conn.execute('UPDATE giornate SET metodo_sorteggio = ? WHERE id = ?', 
                       ('TESTE_DI_SERIE', giornata_id))
            conn.commit()
            
            # Redirect alla pagina di sorteggio dove l'utente potrà confermare o ripetere
            conn.close()
            return redirect(url_for('sorteggio', giornata_id=giornata_id))
    
    # GET request o POST senza teste di serie valide
    conn.close()
    return render_template('selezione_teste.html', giornata=giornata, torneo=torneo, 
                         giocatori=giocatori, version=VERSION)

def sorteggio_teste_di_serie(conn, giornata_id, giocatori, teste_di_serie):
    # Ordiniamo i giocatori per testa di serie e non
    giocatori_teste = []
    giocatori_altri = []
    
    for giocatore in giocatori:
        if str(giocatore['id']) in teste_di_serie:
            giocatori_teste.append(giocatore)
        else:
            giocatori_altri.append(giocatore)
    
    # Mischiamo gli altri giocatori
    random.shuffle(giocatori_altri)
    
    # Creiamo 4 squadre, ognuna con una testa di serie
    squadre = []
    for i in range(4):
        giocatore1 = giocatori_teste[i]
        giocatore2 = giocatori_altri[i]
        
        # Calcoliamo il punteggio totale della squadra
        punteggio_totale = float(giocatore1['punteggio_elo']) + float(giocatore2['punteggio_elo'])
        
        # Inseriamo la squadra nel database
        cursor = conn.execute('''
            INSERT INTO squadre (giornata_id, giocatore1_id, giocatore2_id, nome_squadra, punteggio_totale)
            VALUES (?, ?, ?, ?, ?)
        ''', (giornata_id, giocatore1['id'], giocatore2['id'], f"Squadra {chr(65+i)}", punteggio_totale))
        
        squadra_id = cursor.lastrowid
        squadre.append({
            'id': squadra_id,
            'giocatore1': giocatore1,
            'giocatore2': giocatore2,
            'nome_squadra': f"Squadra {chr(65+i)}",
            'punteggio_totale': punteggio_totale
        })
    
    return squadre

def sorteggio_punti_posizione(conn, giornata_id, giocatori):
    # Ordiniamo i giocatori per punteggio ELO
    giocatori_sorted = sorted(giocatori, key=lambda x: float(x['punteggio_elo']), reverse=True)
    
    # Raggruppamento per posizione
    giocatori_destra = [g for g in giocatori_sorted if g['posizione'] == 'DESTRA']
    giocatori_sinistra = [g for g in giocatori_sorted if g['posizione'] == 'SINISTRA']
    giocatori_indifferente = [g for g in giocatori_sorted if g['posizione'] == 'INDIFFERENTE']
    
    # Creiamo 4 squadre cercando di bilanciare i punteggi e rispettare le posizioni
    squadre = []
    giocatori_assegnati = []
    
    for i in range(4):
        # Algoritmo semplificato: prendiamo il migliore disponibile e il peggiore disponibile
        disponibili = [g for g in giocatori_sorted if g['id'] not in [g['id'] for g in giocatori_assegnati]]
        
        if len(disponibili) >= 2:
            giocatore1 = disponibili[0]  # Il migliore
            giocatore2 = disponibili[-1]  # Il peggiore
            
            giocatori_assegnati.append(giocatore1)
            giocatori_assegnati.append(giocatore2)
            
            # Calcoliamo il punteggio totale della squadra
            punteggio_totale = float(giocatore1['punteggio_elo']) + float(giocatore2['punteggio_elo'])
            
            # Inseriamo la squadra nel database
            cursor = conn.execute('''
                INSERT INTO squadre (giornata_id, giocatore1_id, giocatore2_id, nome_squadra, punteggio_totale)
                VALUES (?, ?, ?, ?, ?)
            ''', (giornata_id, giocatore1['id'], giocatore2['id'], f"Squadra {chr(65+i)}", punteggio_totale))
            
            squadra_id = cursor.lastrowid
            squadre.append({
                'id': squadra_id,
                'giocatore1': giocatore1,
                'giocatore2': giocatore2,
                'nome_squadra': f"Squadra {chr(65+i)}",
                'punteggio_totale': punteggio_totale
            })
    
    return squadre

def sorteggio_casuale(conn, giornata_id, giocatori):
    # Mischiamo i giocatori
    giocatori_random = giocatori.copy()
    random.shuffle(giocatori_random)
    
    # Creiamo 4 squadre casuali
    squadre = []
    for i in range(4):
        giocatore1 = giocatori_random[i*2]
        giocatore2 = giocatori_random[i*2+1]
        
        # Calcoliamo il punteggio totale della squadra
        punteggio_totale = float(giocatore1['punteggio_elo']) + float(giocatore2['punteggio_elo'])
        
        # Inseriamo la squadra nel database
        cursor = conn.execute('''
            INSERT INTO squadre (giornata_id, giocatore1_id, giocatore2_id, nome_squadra, punteggio_totale)
            VALUES (?, ?, ?, ?, ?)
        ''', (giornata_id, giocatore1['id'], giocatore2['id'], f"Squadra {chr(65+i)}", punteggio_totale))
        
        squadra_id = cursor.lastrowid
        squadre.append({
            'id': squadra_id,
            'giocatore1': giocatore1,
            'giocatore2': giocatore2,
            'nome_squadra': f"Squadra {chr(65+i)}",
            'punteggio_totale': punteggio_totale
        })
    
    return squadre

def crea_partite_round_robin(conn, giornata_id, squadre):
    # Struttura del round robin:
    # Primo turno: A vs B, C vs D
    # Secondo turno: A vs C, B vs D
    # Terzo turno: A vs D, B vs C
    
    # Primo turno
    conn.execute('''
        INSERT INTO partite (giornata_id, squadra1_id, squadra2_id, turno, campo)
        VALUES (?, ?, ?, ?, ?)
    ''', (giornata_id, squadre[0]['id'], squadre[1]['id'], 1, 1))
    
    conn.execute('''
        INSERT INTO partite (giornata_id, squadra1_id, squadra2_id, turno, campo)
        VALUES (?, ?, ?, ?, ?)
    ''', (giornata_id, squadre[2]['id'], squadre[3]['id'], 1, 2))
    
    # Secondo turno
    conn.execute('''
        INSERT INTO partite (giornata_id, squadra1_id, squadra2_id, turno, campo)
        VALUES (?, ?, ?, ?, ?)
    ''', (giornata_id, squadre[0]['id'], squadre[2]['id'], 2, 1))
    
    conn.execute('''
        INSERT INTO partite (giornata_id, squadra1_id, squadra2_id, turno, campo)
        VALUES (?, ?, ?, ?, ?)
    ''', (giornata_id, squadre[1]['id'], squadre[3]['id'], 2, 2))
    
    # Terzo turno
    conn.execute('''
        INSERT INTO partite (giornata_id, squadra1_id, squadra2_id, turno, campo)
        VALUES (?, ?, ?, ?, ?)
    ''', (giornata_id, squadre[0]['id'], squadre[3]['id'], 3, 1))
    
    conn.execute('''
        INSERT INTO partite (giornata_id, squadra1_id, squadra2_id, turno, campo)
        VALUES (?, ?, ?, ?, ?)
    ''', (giornata_id, squadre[1]['id'], squadre[2]['id'], 3, 2))

def crea_partite_eliminazione_diretta(conn, giornata_id, squadre):
    # Primo turno (semifinali): squadra1 vs squadra4, squadra2 vs squadra3
    # Squadre ordinate per punteggio totale
    squadre_ordinate = sorted(squadre, key=lambda x: x['punteggio_totale'], reverse=True)
    
    # Semifinale 1: squadra1 vs squadra4
    conn.execute('''
        INSERT INTO partite (giornata_id, squadra1_id, squadra2_id, turno, campo)
        VALUES (?, ?, ?, ?, ?)
    ''', (giornata_id, squadre_ordinate[0]['id'], squadre_ordinate[3]['id'], 1, 1))
    
    # Semifinale 2: squadra2 vs squadra3
    conn.execute('''
        INSERT INTO partite (giornata_id, squadra1_id, squadra2_id, turno, campo)
        VALUES (?, ?, ?, ?, ?)
    ''', (giornata_id, squadre_ordinate[1]['id'], squadre_ordinate[2]['id'], 1, 2))

def recupera_squadre(conn, giornata_id):
    """Recupera tutte le squadre di una giornata con i relativi giocatori"""
    squadre_db = conn.execute('''
        SELECT s.id, s.nome_squadra, s.punteggio_totale, s.giocatore1_id, s.giocatore2_id
        FROM squadre s
        WHERE s.giornata_id = ?
    ''', (giornata_id,)).fetchall()
    
    squadre = []
    for squadra in squadre_db:
        # Recupera i dati dei giocatori
        giocatore1 = conn.execute('SELECT * FROM giocatori WHERE id = ?', (squadra['giocatore1_id'],)).fetchone()
        giocatore2 = conn.execute('SELECT * FROM giocatori WHERE id = ?', (squadra['giocatore2_id'],)).fetchone()
        
        squadre.append({
            'id': squadra['id'],
            'nome_squadra': squadra['nome_squadra'],
            'punteggio_totale': squadra['punteggio_totale'],
            'giocatore1': dict(giocatore1) if giocatore1 else None,
            'giocatore2': dict(giocatore2) if giocatore2 else None
        })
    
    return squadre

def recupera_partite(conn, giornata_id):
    """Recupera tutte le partite di una giornata con le relative squadre"""
    partite_db = conn.execute('''
        SELECT p.id, p.turno, p.campo, p.squadra1_id, p.squadra2_id, 
               p.punteggio_squadra1, p.punteggio_squadra2
        FROM partite p
        WHERE p.giornata_id = ?
        ORDER BY p.turno, p.campo
    ''', (giornata_id,)).fetchall()
    
    # Recuperiamo tutte le squadre della giornata
    squadre = recupera_squadre(conn, giornata_id)
    squadre_map = {squadra['id']: squadra for squadra in squadre}
    
    partite = []
    for partita in partite_db:
        partite.append({
            'id': partita['id'],
            'turno': partita['turno'],
            'campo': partita['campo'],
            'squadra1': squadre_map.get(partita['squadra1_id']),
            'squadra2': squadre_map.get(partita['squadra2_id']),
            'punteggio_squadra1': partita['punteggio_squadra1'],
            'punteggio_squadra2': partita['punteggio_squadra2']
        })
    
    return partite

@app.route('/visualizza-giornata/<int:giornata_id>')
def visualizza_giornata(giornata_id):
    conn = get_db_connection()
    giornata = conn.execute('SELECT * FROM giornate WHERE id = ?', (giornata_id,)).fetchone()
    
    if giornata is None:
        conn.close()
        return redirect(url_for('gestione_tornei'))
    
    torneo = conn.execute('SELECT * FROM tornei WHERE id = ?', (giornata['torneo_id'],)).fetchone()
    
    # Recuperiamo le squadre della giornata
    squadre_rows = conn.execute('SELECT * FROM squadre WHERE giornata_id = ?', (giornata_id,)).fetchall()
    squadre = []
    
    for squadra in squadre_rows:
        # Recuperiamo i dati dei giocatori
        giocatore1 = conn.execute('SELECT * FROM giocatori WHERE id = ?', (squadra['giocatore1_id'],)).fetchone()
        giocatore2 = conn.execute('SELECT * FROM giocatori WHERE id = ?', (squadra['giocatore2_id'],)).fetchone()
        
        squadre.append({
            'id': squadra['id'],
            'nome_squadra': squadra['nome_squadra'],
            'giocatore1': dict(giocatore1),
            'giocatore2': dict(giocatore2),
            'punteggio_totale': squadra['punteggio_totale']
        })
    
    # Recuperiamo le partite della giornata
    partite_rows = conn.execute('''
        SELECT * FROM partite 
        WHERE giornata_id = ? 
        ORDER BY turno, campo
    ''', (giornata_id,)).fetchall()
    
    partite = []
    for partita in partite_rows:
        # Recuperiamo i dati delle squadre
        squadra1 = next((s for s in squadre if s['id'] == partita['squadra1_id']), None)
        squadra2 = next((s for s in squadre if s['id'] == partita['squadra2_id']), None)
        
        partite.append({
            'id': partita['id'],
            'turno': partita['turno'],
            'campo': partita['campo'],
            'squadra1': squadra1,
            'squadra2': squadra2,
            'punteggio_squadra1': partita['punteggio_squadra1'],
            'punteggio_squadra2': partita['punteggio_squadra2'],
            'stato': partita['stato']
        })
    
    conn.close()
    
    return render_template('visualizza_giornata.html', 
                         giornata=giornata, 
                         torneo=torneo, 
                         squadre=squadre, 
                         partite=partite, 
                         version=VERSION)

@app.route('/elimina-giornata/<int:giornata_id>')
def elimina_giornata(giornata_id):
    conn = get_db_connection()
    
    try:
        # Prima recuperiamo l'ID del torneo per il redirect
        giornata = conn.execute('SELECT torneo_id FROM giornate WHERE id = ?', (giornata_id,)).fetchone()
        if giornata is None:
            flash('Giornata non trovata.', 'error')
            conn.close()
            return redirect(url_for('gestione_tornei'))
            
        torneo_id = giornata['torneo_id']
        
        # Elimina prima le partite associate
        conn.execute('DELETE FROM partite WHERE giornata_id = ?', (giornata_id,))
        
        # Elimina le squadre associate
        conn.execute('DELETE FROM squadre WHERE giornata_id = ?', (giornata_id,))
        
        # Elimina la giornata
        conn.execute('DELETE FROM giornate WHERE id = ?', (giornata_id,))
        
        conn.commit()
        flash('Giornata eliminata con successo.', 'success')
        
        # Redirect alla pagina del torneo invece che alla gestione tornei
        return redirect(url_for('visualizza_torneo', id=torneo_id))
        
    except Exception as e:
        conn.rollback()
        flash('Errore durante l\'eliminazione della giornata.', 'error')
        print(f"Errore: {str(e)}")
        return redirect(url_for('gestione_tornei'))
    finally:
        conn.close()

@app.route('/esporta-pdf/<int:giornata_id>')
def esporta_pdf(giornata_id):
    from weasyprint import HTML
    from io import BytesIO
    
    conn = get_db_connection()
    giornata = conn.execute('SELECT * FROM giornate WHERE id = ?', (giornata_id,)).fetchone()
    
    if giornata is None:
        conn.close()
        return redirect(url_for('gestione_tornei'))
    
    torneo = conn.execute('SELECT * FROM tornei WHERE id = ?', (giornata['torneo_id'],)).fetchone()
    squadre = recupera_squadre(conn, giornata_id)
    partite = recupera_partite(conn, giornata_id)
    
    conn.close()
    
    # Rendiamo il template HTML
    rendered_template = render_template('esporta_pdf.html', giornata=giornata, torneo=torneo,
                          squadre=squadre, partite=partite, version=VERSION)
    
    try:
        # Creo il nome del file
        filename = f"torneotto_{torneo['nome']}_{giornata['data']}.pdf".replace(" ", "_")
        
        # Creazione del PDF con WeasyPrint
        html = HTML(string=rendered_template)
        pdf = html.write_pdf(stylesheets=[])  # Utilizzo un array vuoto per assicurarmi che non vengano applicate altre regole
        
        # Preparo il file per l'invio
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Invio del PDF al client
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print(f"Errore nella creazione del PDF: {str(e)}")
        # Se c'è un errore nella generazione del PDF, mostro il template HTML
        return render_template('esporta_pdf.html', giornata=giornata, torneo=torneo,
                          squadre=squadre, partite=partite, version=VERSION)

# Inizializza il database all'avvio
init_db()

# Rimuovo il blocco if __name__ == '__main__' per usare flask run 