# 🏆 TorneOtto - Sistema di Gestione Tornei Padel

<div align="center">

![Status](https://img.shields.io/badge/Status-Active-green)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0.2-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Sistema completo per la gestione di tornei di padel con sistema ELO avanzato**

[🚀 Demo](#demo) • [📋 Features](#features) • [🛠️ Installazione](#installazione) • [📚 Documentazione](#documentazione)

</div>

---

## 📋 Indice

- [🎯 Panoramica](#-panoramica)
- [✨ Features](#-features)
- [🏗️ Architettura](#️-architettura)
- [🗄️ Database](#️-database)
- [🛠️ Installazione](#️-installazione)
- [🚀 Utilizzo](#-utilizzo)
- [🎨 Design System](#-design-system)
- [📊 Logging & Debug](#-logging--debug)
- [🔗 API Routes](#-api-routes)
- [🤝 Contributi](#-contributi)
- [📄 Licenza](#-licenza)

---

## 🎯 Panoramica

**TorneOtto** è un sistema completo per la gestione di tornei di padel, sviluppato con Flask e PostgreSQL. Offre una soluzione professionale per organizzare e gestire diversi tipi di tornei con un sistema ELO avanzato per il ranking dei giocatori.

### 🎮 Tipi di Torneo Supportati

- **🏃‍♂️ TorneOtto 30'** - Tornei veloci da 30 minuti
- **⏰ TorneOtto 45'** - Tornei standard da 45 minuti  
- **🔄 Gironi** - Tornei con fase a gironi + eliminazione diretta
- **⚔️ Eliminazione** - Eliminazione diretta e doppia eliminazione
- **🥇 Torneo Americana** - Modalità in cui i giocatori ruotano tra compagni e avversari

---

## ✨ Features

### 🎯 **Gestione Completa**
- ✅ **Gestione Giocatori** - Profili completi con posizione (D/S/I) e ELO
- ✅ **4 Tipi di Torneo** - Supporto completo per tutti i formati
- ✅ **Sistema ELO Avanzato** - Calcolo dinamico con storico completo
- ✅ **Pairing Intelligente** - 4 algoritmi di accoppiamento

### 🎨 **Interface Moderna**
- ✅ **Responsive Design** - Mobile-first approach
- ✅ **UI/UX Moderna** - Design system coerente
- ✅ **Dashboard Interattiva** - Panoramica completa
- ✅ **Export PDF** - Classifiche e risultati

### 🔧 **Funzionalità Avanzate**
- ✅ **Bracket Visualization** - Tabelloni eliminazione interattivi
- ✅ **Real-time Updates** - Aggiornamenti in tempo reale
- ✅ **Logging Professionale** - Sistema debug completo
- ✅ **Error Handling** - Gestione errori avanzata

---

## 🏗️ Architettura

```
TorneOtto/
├── 🐍 Backend (Flask + SQLAlchemy)
│   ├── app.py              # Applicazione principale
│   ├── config.py           # Configurazioni
│   ├── routes/             # Blueprint Routes
│   ├── models/             # Modelli Database
│   └── services/           # Business Logic
├── 🎨 Frontend (Jinja2 + CSS)
│   ├── templates/          # Template HTML
│   └── static/             # CSS, JS, Images
└── 🗄️ Database (PostgreSQL)
    └── 9 Tabelle Ottimizzate
```

### 🏛️ **Design Patterns**
- **MVC Architecture** - Separazione delle responsabilità
- **Blueprint Pattern** - Modularity delle route
- **Repository Pattern** - Astrazione database
- **Service Layer** - Business logic centralizzata

---

## 🗄️ Database

### 📊 **Schema Database (9 Tabelle)**

<details>
<summary><strong>👥 PLAYERS</strong></summary>

```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    nome VARCHAR(50) NOT NULL,
    cognome VARCHAR(50) NOT NULL,
    telefono VARCHAR(20),
    posizione VARCHAR(20) NOT NULL, -- Destra/Sinistra/Indifferente
    elo_standard FLOAT DEFAULT 1500.00,
    created_at DATETIME
);
```
</details>

<details>
<summary><strong>🏆 TOURNAMENTS</strong></summary>

```sql
CREATE TABLE tournaments (
    id INTEGER PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo_torneo VARCHAR(20) NOT NULL, -- torneotto30/45/gironi/eliminazione
    circolo VARCHAR(100),
    note TEXT,
    data_inizio DATE NOT NULL,
    data_fine DATE NOT NULL,
    stato VARCHAR(20) DEFAULT 'Pianificato',
    config_json TEXT, -- Configurazioni specifiche
    created_at DATETIME
);
```
</details>

<details>
<summary><strong>📅 TOURNAMENT_DAY (Polymorphic)</strong></summary>

```sql
CREATE TABLE tournament_day (
    id INTEGER PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id),
    data DATE NOT NULL,
    stato VARCHAR(100),
    config_json TEXT,
    tipo_giornata VARCHAR(100), -- Discriminator
    created_at DATETIME
);
```
</details>

<details>
<summary><strong>⚔️ ELIMINATION SYSTEM</strong></summary>

```sql
-- Tornei Eliminazione
CREATE TABLE elimination_tournaments (
    id INTEGER PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id),
    tipo_eliminazione VARCHAR(20), -- single/double
    num_partecipanti INTEGER,
    num_squadre INTEGER,
    metodo_accoppiamento VARCHAR(20), -- random/seeded/manual
    best_of_three BOOLEAN DEFAULT FALSE,
    data_inizio DATE,
    stato VARCHAR(20) DEFAULT 'Setup',
    config_json TEXT,
    created_at DATETIME
);

-- Squadre Eliminazione
CREATE TABLE elimination_teams (
    id INTEGER PRIMARY KEY,
    tournament_id INTEGER REFERENCES elimination_tournaments(id),
    posizione_seed INTEGER,
    is_bye BOOLEAN DEFAULT FALSE,
    eliminata BOOLEAN DEFAULT FALSE,
    sconfitte INTEGER DEFAULT 0,
    players_json TEXT, -- Array giocatori JSON
    created_at DATETIME
);

-- Partite Eliminazione
CREATE TABLE elimination_matches (
    id INTEGER PRIMARY KEY,
    tournament_id INTEGER REFERENCES elimination_tournaments(id),
    turno INTEGER,
    posizione_turno INTEGER,
    bracket_type VARCHAR(10) DEFAULT 'winner', -- winner/loser
    team1_id INTEGER REFERENCES elimination_teams(id),
    team2_id INTEGER REFERENCES elimination_teams(id),
    team1_score INTEGER,
    team2_score INTEGER,
    winner_team_id INTEGER REFERENCES elimination_teams(id),
    stato VARCHAR(20) DEFAULT 'Pending',
    data_partita DATETIME,
    set_scores_json TEXT, -- Best of 3
    created_at DATETIME
);
```
</details>

<details>
<summary><strong>📈 ELO SYSTEM</strong></summary>

```sql
-- ELO per Torneo
CREATE TABLE player_tournament_elo (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    tournament_id INTEGER REFERENCES tournaments(id),
    elo_rating FLOAT DEFAULT 1500.00,
    updated_at DATETIME,
    UNIQUE(player_id, tournament_id)
);

-- Storico ELO
CREATE TABLE player_elo_history (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    tournament_id INTEGER REFERENCES tournaments(id),
    tournament_day_id INTEGER REFERENCES tournament_day(id),
    old_elo FLOAT NOT NULL,
    new_elo FLOAT NOT NULL,
    elo_change FLOAT NOT NULL,
    created_at DATETIME
);
```
</details>

---

## 🛠️ Installazione

### 📋 **Prerequisiti**
- Python 3.9+
- PostgreSQL
- Git

### 🚀 **Setup Rapido**

```bash
# 1. Clone del repository
git clone https://github.com/tuousername/torneotto.git
cd torneotto

# 2. Installazione dipendenze
python3 -m pip install -r requirements.txt

# 3. Configurazione database
# Aggiorna config.py con le tue credenziali PostgreSQL

# 4. Avvio applicazione
python3 app.py
```

### 🌐 **Accesso**
- **URL**: http://localhost:5001
- **Debug**: Attivo in development mode
- **Logs**: Disponibili in `logs/`

---

## 🚀 Utilizzo

### 1️⃣ **Gestione Giocatori**
```
http://localhost:5001/giocatori
```
- Aggiungi giocatori con nome, cognome, telefono, posizione
- Modifica profili esistenti
- Visualizza ELO e statistiche

### 2️⃣ **Creazione Tornei**
```
http://localhost:5001/tornei/nuovo
```
- Scegli tipo torneo (TorneOtto30/45, Gironi, Eliminazione)  
- Configura parametri specifici
- Imposta date e regole

### 3️⃣ **Gestione Giornate**
```
http://localhost:5001/tornei/{id}
```
- Crea nuove giornate
- Scegli metodo pairing (Random, ELO, Seeded, Manual)
- Inserisci risultati
- Visualizza classifiche

### 4️⃣ **Tornei Eliminazione**
```
http://localhost:5001/tornei/{id}/eliminazione
```
- Seleziona giocatori
- Crea bracket automatico
- Visualizza tabellone interattivo
- Inserisci risultati partite

---

## 🎨 Design System

### 🎯 **Principi Design**
- **Mobile-First** - Design responsive prioritario
- **Consistent Spacing** - Sistema di spaziature coerente
- **Modern UI** - Interface pulita e moderna
- **Accessibility** - Supporto per screen readers

### 🎨 **Variabili CSS**
```css
:root {
  /* Spacing */
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2rem;
  
  /* Colors */
  --accent-primary: #007bff;
  --accent-secondary: #28a745;
  --accent-tertiary: #8b5cf6;
  
  /* Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}
```

### 📱 **Responsive Breakpoints**
- **Mobile**: < 768px
- **Tablet**: 768px - 1024px  
- **Desktop**: > 1024px

---

## 📊 Logging & Debug

### 🔍 **Sistema Log Avanzato**

```
logs/
├── app.log      # Log principale (INFO+)
├── errors.log   # Solo errori (ERROR+)
└── debug.log    # Debug completo (DEBUG+)
```

### 📋 **Features Log**
- ✅ **Rotating Handlers** - Max 10MB, 5 backup files
- ✅ **Structured Logging** - Format consistente con timestamp
- ✅ **Request Tracking** - Log di tutte le richieste HTTP
- ✅ **Exception Handling** - Stack trace completi
- ✅ **Performance Monitoring** - Tempi di risposta
- ✅ **IP & User Agent** - Tracking completo utenti

### 🐛 **Error Handlers**
```python
@app.errorhandler(404)
def not_found_error(error):
    # Log con dettagli completi
    
@app.errorhandler(500)  
def internal_error(error):
    # Rollback DB + logging

@app.errorhandler(Exception)
def handle_exception(error):
    # Catch-all con stack trace
```

---

## 🔗 API Routes

### 🏆 **Tornei (48+ endpoints)**

<details>
<summary><strong>Gestione Generale</strong></summary>

```python
GET  /tornei                    # Lista tornei
GET  /tornei/attivi            # Tornei attivi  
GET  /tornei/nuovo             # Selezione tipo
GET  /tornei/<id>              # Vista torneo
POST /tornei/<id>/delete       # Elimina torneo
GET  /tornei/<id>/classifica   # Classifiche
```
</details>

<details>
<summary><strong>TorneOtto 30'</strong></summary>

```python
GET/POST /tornei/nuovo/torneotto30              # Crea torneo
GET/POST /tornei/torneotto30/new_day           # Nuova giornata
GET      /tornei/torneotto30/choose_method     # Metodo pairing
POST     /tornei/torneotto30/pairing/random    # Pairing casuale
POST     /tornei/torneotto30/pairing/elo       # Pairing ELO
GET/POST /tornei/torneotto30/pairing/seeded    # Pairing seeded
GET/POST /tornei/torneotto30/pairing/manual    # Pairing manuale
POST     /tornei/torneotto30/save_day          # Salva giornata
```
</details>

<details>
<summary><strong>Eliminazione</strong></summary>

```python
GET/POST /tornei/<id>/eliminazione/seleziona-giocatori  # Selezione
GET/POST /tornei/<id>/eliminazione/crea-tabellone       # Crea bracket
GET      /tornei/<id>/eliminazione/tabellone            # Vista bracket
GET/POST /tornei/<id>/eliminazione/inserisci-risultati  # Risultati
```
</details>

### 👥 **Giocatori (5 endpoints)**

```python
GET      /giocatori               # Lista giocatori
GET      /giocatori/catalogo      # Catalogo
GET/POST /giocatori/nuovo         # Crea giocatore
GET/POST /giocatori/modifica/<id> # Modifica
POST     /giocatori/elimina/<id>  # Elimina
```

### 📊 **Utilities**

```python
GET /tornei/giornata/<id>           # Vista giornata
GET/POST /tornei/giornata/<id>/risultati # Inserisci risultati
GET /tornei/giornata/<id>/pdf       # Export PDF
GET /api/tournaments/<id>/players/<id>/stats # Statistiche
```

---

## 🎯 Algoritmi Pairing

### 🎲 **Random Pairing**
- Accoppiamento casuale dei giocatori
- Evita ripetizioni eccessive
- Bilanciamento posizioni (D/S)

### 📈 **ELO-Based Pairing** 
- Accoppiamento basato su rating ELO
- Partite equilibrate per livello
- Calcolo dinamico delle variazioni

### 🏆 **Seeded Pairing**
- Accoppiamento con giocatori "seed"
- Protezione dei top player
- Distribuzione equilibrata

### ✋ **Manual Pairing**
- Controllo completo manuale
- Interface drag & drop
- Validazione automatica

---

## 🔧 Sistema ELO

### 📊 **Caratteristiche**
- **Base Rating**: 1500 punti di partenza
- **K-Factor**: 32 (configurabile)
- **Storico Completo**: Tracking di ogni variazione
- **Per Torneo**: ELO specifico per ogni torneo
- **Progressivo**: Calcolo dinamico durante il torneo

### 🧮 **Formula**
```python
def calculate_elo_change(team1_elo, team2_elo, result, k_factor=32):
    expected_score = 1 / (1 + 10**((team2_elo - team1_elo) / 400))
    actual_score = 1 if result == 'win' else 0
    return k_factor * (actual_score - expected_score)
```

---

## 🎨 Screenshots

<details>
<summary><strong>🏠 Homepage Dashboard</strong></summary>

![Homepage](static/images/screenshots/homepage.png)
*Dashboard principale con panoramica tornei e statistiche*
</details>

<details>
<summary><strong>🏆 Lista Tornei</strong></summary>

![Tornei](static/images/screenshots/tournaments.png)
*Gestione completa dei tornei con stati e date*
</details>

<details>
<summary><strong>⚔️ Bracket Eliminazione</strong></summary>

![Bracket](static/images/screenshots/bracket.png)
*Visualizzazione interattiva del tabellone eliminazione*
</details>

<details>
<summary><strong>👥 Gestione Giocatori</strong></summary>

![Giocatori](static/images/screenshots/players.png)
*Database completo giocatori con ELO e statistiche*
</details>

---

## 🤝 Contributi

### 🙏 **Come Contribuire**

1. **Fork** il repository
2. **Crea** un branch per la tua feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** le tue modifiche (`git commit -m 'Add some AmazingFeature'`)
4. **Push** al branch (`git push origin feature/AmazingFeature`)
5. **Apri** una Pull Request

### 🐛 **Bug Reports**
- Usa le [GitHub Issues](https://github.com/tuousername/torneotto/issues)
- Includi log e step per riprodurre
- Specifica browser e sistema operativo

### 💡 **Feature Requests**
- Descrivi il caso d'uso
- Spiega il beneficio per gli utenti
- Considera l'impatto sulle performance

---

## 📄 Licenza

Questo progetto è rilasciato sotto licenza **MIT License**.

---

## 🙋‍♂️ Supporto

### 📧 **Contatti**
- **Email**: support@torneotto.com
- **GitHub**: [Issues](https://github.com/tuousername/torneotto/issues)

### 📚 **Risorse**
- [📖 Documentazione Completa](docs/)
- [🎥 Video Tutorial](https://youtube.com/torneotto)

---

## 🥇 Torneo Americana

Il torneo all'americana è una modalità in cui i giocatori ruotano tra compagni e avversari, garantendo varietà e bilanciamento. TorneOtto supporta due modalità:

### Modalità Semplice (Coppie Giranti)
- Ogni partita ha 4 giocatori (2 coppie), nessuna coppia si ripete.
- I turni sono simultanei: ogni campo ospita una partita per turno.
- I giocatori ruotano tra attivi e a riposo (se il numero non è multiplo di 4).
- Puoi configurare il numero di turni e di campi.
- Dopo il sorteggio, puoi **confermare la giornata** tramite apposito pulsante: la giornata viene salvata e sarà sempre richiamabile.

### Modalità Completa (Round Robin)
- Ogni giocatore gioca con tutti gli altri e contro tutti gli altri.
- Rotazione automatica delle coppie ad ogni turno.
- Ideale per gruppi piccoli che vogliono la massima copertura.

### Come si usa
1. Crea un torneo di tipo "Americana" dal gestionale.
2. Scegli la modalità (semplice/round robin), il numero di campi e di turni.
3. Avvia il sorteggio: il sistema genera il calendario con rotazione vera.
4. Premi "Conferma Giornata" per salvare la giornata e renderla richiamabile.
5. Inserisci i risultati e consulta la classifica aggiornata.

**Nessuna coppia si ripete, la rotazione è garantita, e la giornata è sempre richiamabile!**

<div align="center">

**⭐ Se TorneOtto ti è utile, lascia una stella!**

Made with ❤️ by TorneOtto Team

</div> 