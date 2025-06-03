import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Configurazione del database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://neondb_owner:npg_Ty5lY2xHCkeK@ep-silent-cloud-a9is9gil-pooler.gwc.azure.neon.tech/neondb?sslmode=require'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurazione dell'applicazione
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # Configurazione del logging
    LOG_LEVEL = 'DEBUG'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'app.log'
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Configurazione del server
    PORT = 5001
    HOST = '0.0.0.0'

    # Configurazione per il pool di connessioni
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,  # Ridotto per evitare troppe connessioni simultanee
        'max_overflow': 10,  # Ridotto per limitare le connessioni extra
        'pool_timeout': 60,  # Aumentato per dare più tempo alle connessioni
        'pool_recycle': 300,  # Ridotto per riciclare le connessioni più frequentemente
        'pool_pre_ping': True,  # Aggiunto per verificare la connessione prima dell'uso
        'echo': False,  # Disabilitato il logging SQL per ridurre il rumore
    }

    # Configurazione dei tornei
    TOURNAMENT_TYPES = {
        'torneotto30': {
            'name': "TorneOtto 30'",
            'num_squadre': 4,
            'num_giocatori': 8,
            'tempo_partita': 30
        },
        'torneotto45': {
            'name': "TorneOtto 45'",
            'num_squadre': 8,
            'tempo_partita': 45,
            'finali': 1
        },
        'gironi': {
            'name': "A Gironi",
            'min_gironi': 2,
            'max_gironi': 8,
            'min_squadre_per_girone': 3,
            'max_squadre_per_girone': 6,
            'metodi_sorteggio': [
                {'id': 'random', 'name': 'Casuale'},
                {'id': 'elo', 'name': 'ELO'},
                {'id': 'seeded', 'name': 'Teste di Serie'},
                {'id': 'manual', 'name': 'Manuale'}
            ],
            'k_factor': {
                'gironi': 32,
                'semifinali': 40,
                'finale_1_2': 50,
                'finale_3_4': 40
            }
        },
        'eliminazione': {
            'name': "Eliminazione Diretta",
            'num_partecipanti': [8, 16, 32],
            'teste_di_serie': [2, 4, 8],
            'consolazione': True
        }
    }

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 