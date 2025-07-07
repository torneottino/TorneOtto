--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (Homebrew)
-- Dumped by pg_dump version 16.9 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: mattiaianniello
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO mattiaianniello;

--
-- Name: match; Type: TABLE; Schema: public; Owner: mattiaianniello
--

CREATE TABLE public.match (
    id integer NOT NULL,
    date date NOT NULL,
    player1_id integer NOT NULL,
    player2_id integer NOT NULL,
    player3_id integer NOT NULL,
    player4_id integer NOT NULL,
    team1_elo_pre double precision NOT NULL,
    team2_elo_pre double precision NOT NULL,
    winner_team integer NOT NULL,
    elo_change double precision NOT NULL,
    k_factor double precision NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.match OWNER TO mattiaianniello;

--
-- Name: match_id_seq; Type: SEQUENCE; Schema: public; Owner: mattiaianniello
--

CREATE SEQUENCE public.match_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.match_id_seq OWNER TO mattiaianniello;

--
-- Name: match_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mattiaianniello
--

ALTER SEQUENCE public.match_id_seq OWNED BY public.match.id;


--
-- Name: player; Type: TABLE; Schema: public; Owner: mattiaianniello
--

CREATE TABLE public.player (
    id integer NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    nome character varying(50) NOT NULL,
    cognome character varying(50) NOT NULL,
    posizione character varying(20),
    telefono character varying(20),
    elo_standard double precision DEFAULT 1500.00
);


ALTER TABLE public.player OWNER TO mattiaianniello;

--
-- Name: player_elo_history; Type: TABLE; Schema: public; Owner: mattiaianniello
--

CREATE TABLE public.player_elo_history (
    id integer NOT NULL,
    player_id integer NOT NULL,
    tournament_id integer NOT NULL,
    tournament_day_id integer NOT NULL,
    match_id integer,
    old_elo double precision DEFAULT 1500.00 NOT NULL,
    new_elo double precision DEFAULT 1500.00 NOT NULL,
    elo_change double precision DEFAULT 0.00 NOT NULL,
    date date DEFAULT CURRENT_DATE NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.player_elo_history OWNER TO mattiaianniello;

--
-- Name: player_elo_history_id_seq; Type: SEQUENCE; Schema: public; Owner: mattiaianniello
--

CREATE SEQUENCE public.player_elo_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.player_elo_history_id_seq OWNER TO mattiaianniello;

--
-- Name: player_elo_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mattiaianniello
--

ALTER SEQUENCE public.player_elo_history_id_seq OWNED BY public.player_elo_history.id;


--
-- Name: player_id_seq; Type: SEQUENCE; Schema: public; Owner: mattiaianniello
--

CREATE SEQUENCE public.player_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.player_id_seq OWNER TO mattiaianniello;

--
-- Name: player_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mattiaianniello
--

ALTER SEQUENCE public.player_id_seq OWNED BY public.player.id;


--
-- Name: player_tournament_elo; Type: TABLE; Schema: public; Owner: mattiaianniello
--

CREATE TABLE public.player_tournament_elo (
    id integer NOT NULL,
    player_id integer NOT NULL,
    tournament_id integer NOT NULL,
    elo_rating double precision NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.player_tournament_elo OWNER TO mattiaianniello;

--
-- Name: player_tournament_elo_id_seq; Type: SEQUENCE; Schema: public; Owner: mattiaianniello
--

CREATE SEQUENCE public.player_tournament_elo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.player_tournament_elo_id_seq OWNER TO mattiaianniello;

--
-- Name: player_tournament_elo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mattiaianniello
--

ALTER SEQUENCE public.player_tournament_elo_id_seq OWNED BY public.player_tournament_elo.id;


--
-- Name: tournament; Type: TABLE; Schema: public; Owner: mattiaianniello
--

CREATE TABLE public.tournament (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    tipo_torneo character varying(20) NOT NULL,
    circolo character varying(100),
    note text,
    data_inizio date NOT NULL,
    data_fine date NOT NULL,
    stato character varying(20),
    created_at timestamp without time zone,
    config_json text
);


ALTER TABLE public.tournament OWNER TO mattiaianniello;

--
-- Name: tournament_day; Type: TABLE; Schema: public; Owner: mattiaianniello
--

CREATE TABLE public.tournament_day (
    id integer NOT NULL,
    tournament_id integer NOT NULL,
    data date NOT NULL,
    stato character varying(100),
    created_at timestamp without time zone,
    config_json text,
    tipo_giornata character varying(100) NOT NULL
);


ALTER TABLE public.tournament_day OWNER TO mattiaianniello;

--
-- Name: tournament_day_id_seq; Type: SEQUENCE; Schema: public; Owner: mattiaianniello
--

CREATE SEQUENCE public.tournament_day_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tournament_day_id_seq OWNER TO mattiaianniello;

--
-- Name: tournament_day_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mattiaianniello
--

ALTER SEQUENCE public.tournament_day_id_seq OWNED BY public.tournament_day.id;


--
-- Name: tournament_id_seq; Type: SEQUENCE; Schema: public; Owner: mattiaianniello
--

CREATE SEQUENCE public.tournament_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tournament_id_seq OWNER TO mattiaianniello;

--
-- Name: tournament_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: mattiaianniello
--

ALTER SEQUENCE public.tournament_id_seq OWNED BY public.tournament.id;


--
-- Name: match id; Type: DEFAULT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.match ALTER COLUMN id SET DEFAULT nextval('public.match_id_seq'::regclass);


--
-- Name: player id; Type: DEFAULT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player ALTER COLUMN id SET DEFAULT nextval('public.player_id_seq'::regclass);


--
-- Name: player_elo_history id; Type: DEFAULT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_elo_history ALTER COLUMN id SET DEFAULT nextval('public.player_elo_history_id_seq'::regclass);


--
-- Name: player_tournament_elo id; Type: DEFAULT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_tournament_elo ALTER COLUMN id SET DEFAULT nextval('public.player_tournament_elo_id_seq'::regclass);


--
-- Name: tournament id; Type: DEFAULT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.tournament ALTER COLUMN id SET DEFAULT nextval('public.tournament_id_seq'::regclass);


--
-- Name: tournament_day id; Type: DEFAULT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.tournament_day ALTER COLUMN id SET DEFAULT nextval('public.tournament_day_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: mattiaianniello
--

COPY public.alembic_version (version_num) FROM stdin;
2ab33b518cdc
\.


--
-- Data for Name: match; Type: TABLE DATA; Schema: public; Owner: mattiaianniello
--

COPY public.match (id, date, player1_id, player2_id, player3_id, player4_id, team1_elo_pre, team2_elo_pre, winner_team, elo_change, k_factor, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: player; Type: TABLE DATA; Schema: public; Owner: mattiaianniello
--

COPY public.player (id, created_at, updated_at, nome, cognome, posizione, telefono, elo_standard) FROM stdin;
1	2025-05-24 14:18:38.393309	2025-05-24 14:18:38.393312	Mattia	Ianniello	Indifferente		1500
2	2025-05-24 14:19:22.345115	2025-05-24 14:19:22.345122	Antonio	De Luca	Destra		1500
3	2025-05-24 14:19:30.157264	2025-05-24 14:19:30.157271	Alberto	Ruotolo	Sinistra		1500
4	2025-05-24 14:19:37.098629	2025-05-24 14:19:37.098637	Roberto	Cedrone	Destra		1500
5	2025-05-24 14:19:42.980877	2025-05-24 14:19:42.980882	Marco	Matteuzzi	Destra		1500
6	2025-05-24 14:19:49.10009	2025-05-24 14:19:49.100097	Riccardo	Parentini	Destra		1500
7	2025-05-24 14:19:57.271581	2025-05-24 14:19:57.271586	Cosimo	Graniglia	Indifferente		1500
8	2025-05-24 14:20:08.159856	2025-05-24 14:20:08.159861	Stefano	Rosa	Sinistra		1500
10	2025-05-24 15:30:28.777067	\N	Mario	Rossi	Destra	3331234567	1500
11	2025-05-24 15:30:28.777074	\N	Luigi	Verdi	Sinistra	3332345678	1500
12	2025-05-24 15:30:28.777075	\N	Giovanni	Bianchi	Indifferente	3333456789	1500
13	2025-05-24 15:30:28.777075	\N	Paolo	Neri	Destra	3334567890	1500
14	2025-05-24 15:30:28.777075	\N	Marco	Gialli	Sinistra	3335678901	1500
15	2025-05-24 15:30:28.777076	\N	Andrea	Blu	Indifferente	3336789012	1500
16	2025-05-24 15:30:28.777076	\N	Stefano	Viola	Destra	3337890123	1500
17	2025-05-24 15:30:28.777076	\N	Roberto	Arancione	Sinistra	3338901234	1500
\.


--
-- Data for Name: player_elo_history; Type: TABLE DATA; Schema: public; Owner: mattiaianniello
--

COPY public.player_elo_history (id, player_id, tournament_id, tournament_day_id, match_id, old_elo, new_elo, elo_change, date, created_at) FROM stdin;
89	3	3	6	\N	1500	1494.67	-5.33	2025-05-24	2025-05-24 15:06:28.041716
90	1	3	6	\N	1500	1494.67	-5.33	2025-05-24	2025-05-24 15:06:28.046007
91	4	3	6	\N	1500	1505.33	5.33	2025-05-24	2025-05-24 15:06:28.048674
92	6	3	6	\N	1500	1505.33	5.33	2025-05-24	2025-05-24 15:06:28.051171
93	5	3	6	\N	1500	1500	0	2025-05-24	2025-05-24 15:06:28.053352
94	8	3	6	\N	1500	1500	0	2025-05-24	2025-05-24 15:06:28.05567
95	7	3	6	\N	1500	1500	0	2025-05-24	2025-05-24 15:06:28.059271
96	2	3	6	\N	1500	1500	0	2025-05-24	2025-05-24 15:06:28.061154
97	3	3	7	\N	1494.67	1479	-15.67	2025-05-24	2025-05-24 15:07:20.764025
98	2	3	7	\N	1500	1484.33	-15.67	2025-05-24	2025-05-24 15:07:20.766402
99	8	3	7	\N	1500	1510.67	10.67	2025-05-24	2025-05-24 15:07:20.768614
100	5	3	7	\N	1500	1510.67	10.67	2025-05-24	2025-05-24 15:07:20.772576
101	1	3	7	\N	1494.67	1500	5.33	2025-05-24	2025-05-24 15:07:20.774724
102	4	3	7	\N	1505.33	1510.6599999999999	5.33	2025-05-24	2025-05-24 15:07:20.776654
103	7	3	7	\N	1500	1499.67	-0.33	2025-05-24	2025-05-24 15:07:20.779072
104	6	3	7	\N	1505.33	1505	-0.33	2025-05-24	2025-05-24 15:07:20.781176
105	3	3	8	\N	1479	1481.24	2.24	2025-05-24	2025-05-24 15:08:37.876291
106	2	3	8	\N	1484.33	1486.57	2.24	2025-05-24	2025-05-24 15:08:37.879176
107	8	3	8	\N	1510.67	1515.0500000000002	4.38	2025-05-24	2025-05-24 15:08:37.881573
108	6	3	8	\N	1505	1509.38	4.38	2025-05-24	2025-05-24 15:08:37.88464
109	5	3	8	\N	1510.67	1510.04	-0.63	2025-05-24	2025-05-24 15:08:37.886751
110	7	3	8	\N	1499.67	1499.04	-0.63	2025-05-24	2025-05-24 15:08:37.889013
111	4	3	8	\N	1510.6599999999999	1504.6799999999998	-5.98	2025-05-24	2025-05-24 15:08:37.891781
112	1	3	8	\N	1500	1494.02	-5.98	2025-05-24	2025-05-24 15:08:37.893856
113	4	4	9	\N	1500	1536	36	2025-05-24	2025-05-24 15:36:31.367259
114	12	4	9	\N	1500	1536	36	2025-05-24	2025-05-24 15:36:31.372811
115	15	4	9	\N	1500	1504	4	2025-05-24	2025-05-24 15:36:31.376107
116	1	4	9	\N	1500	1504	4	2025-05-24	2025-05-24 15:36:31.382538
117	17	4	9	\N	1500	1496	-4	2025-05-24	2025-05-24 15:36:31.387149
118	2	4	9	\N	1500	1496	-4	2025-05-24	2025-05-24 15:36:31.390696
119	7	4	9	\N	1500	1464	-36	2025-05-24	2025-05-24 15:36:31.394543
120	14	4	9	\N	1500	1464	-36	2025-05-24	2025-05-24 15:36:31.39798
121	14	3	10	\N	1500	1500.58	0.58	2025-05-24	2025-05-24 15:37:32.755421
122	2	3	10	\N	1486.57	1487.1499999999999	0.58	2025-05-24	2025-05-24 15:37:32.758607
123	17	3	10	\N	1500	1515.47	15.47	2025-05-24	2025-05-24 15:37:32.761761
124	4	3	10	\N	1504.6799999999998	1520.1499999999999	15.47	2025-05-24	2025-05-24 15:37:32.765039
125	1	3	10	\N	1494.02	1494.15	0.13	2025-05-24	2025-05-24 15:37:32.767995
126	15	3	10	\N	1500	1500.13	0.13	2025-05-24	2025-05-24 15:37:32.771108
127	12	3	10	\N	1500	1483.82	-16.18	2025-05-24	2025-05-24 15:37:32.773535
128	7	3	10	\N	1499.04	1482.86	-16.18	2025-05-24	2025-05-24 15:37:32.775692
129	1	4	11	\N	1504	1543.31	39.31	2025-05-24	2025-05-24 17:44:56.013788
130	7	4	11	\N	1464	1503.31	39.31	2025-05-24	2025-05-24 17:44:56.025632
131	15	4	11	\N	1504	1508.37	4.37	2025-05-24	2025-05-24 17:44:56.031268
132	17	4	11	\N	1496	1500.37	4.37	2025-05-24	2025-05-24 17:44:56.03412
133	4	4	11	\N	1536	1531.63	-4.37	2025-05-24	2025-05-24 17:44:56.037227
134	14	4	11	\N	1464	1459.63	-4.37	2025-05-24	2025-05-24 17:44:56.041522
135	12	4	11	\N	1536	1496.69	-39.31	2025-05-24	2025-05-24 17:44:56.044873
136	2	4	11	\N	1496	1456.69	-39.31	2025-05-24	2025-05-24 17:44:56.048647
137	4	4	12	\N	1531.63	1565.7600000000002	34.13	2025-05-24	2025-05-24 18:00:37.53786
138	12	4	12	\N	1496.69	1530.8200000000002	34.13	2025-05-24	2025-05-24 18:00:37.542018
139	15	4	12	\N	1508.37	1514.6599999999999	6.29	2025-05-24	2025-05-24 18:00:37.545064
140	14	4	12	\N	1459.63	1465.92	6.29	2025-05-24	2025-05-24 18:00:37.547692
141	1	4	12	\N	1543.31	1534.6499999999999	-8.66	2025-05-24	2025-05-24 18:00:37.550718
142	17	4	12	\N	1500.37	1491.7099999999998	-8.66	2025-05-24	2025-05-24 18:00:37.553851
143	7	4	12	\N	1503.31	1471.55	-31.76	2025-05-24	2025-05-24 18:00:37.556481
144	2	4	12	\N	1456.69	1424.93	-31.76	2025-05-24	2025-05-24 18:00:37.560214
\.


--
-- Data for Name: player_tournament_elo; Type: TABLE DATA; Schema: public; Owner: mattiaianniello
--

COPY public.player_tournament_elo (id, player_id, tournament_id, elo_rating, created_at, updated_at) FROM stdin;
73	14	3	1500.58	\N	2025-05-24 15:37:32.753834
63	2	3	1487.1499999999999	\N	2025-05-24 15:37:32.757367
74	17	3	1515.47	\N	2025-05-24 15:37:32.76054
58	4	3	1520.1499999999999	\N	2025-05-24 15:37:32.76386
62	1	3	1494.15	\N	2025-05-24 15:37:32.76683
75	15	3	1500.13	\N	2025-05-24 15:37:32.769951
76	12	3	1483.82	\N	2025-05-24 15:37:32.772584
64	7	3	1482.86	\N	2025-05-24 15:37:32.774867
65	4	4	1565.7600000000002	\N	2025-05-24 18:00:37.535357
66	12	4	1530.8200000000002	\N	2025-05-24 18:00:37.540507
67	15	4	1514.6599999999999	\N	2025-05-24 18:00:37.544155
72	14	4	1465.92	\N	2025-05-24 18:00:37.546897
68	1	4	1534.6499999999999	\N	2025-05-24 18:00:37.549494
69	17	4	1491.7099999999998	\N	2025-05-24 18:00:37.552737
71	7	4	1471.55	\N	2025-05-24 18:00:37.555458
70	2	4	1424.93	\N	2025-05-24 18:00:37.559169
59	3	3	1481.24	\N	2025-05-24 15:08:37.874786
57	8	3	1515.0500000000002	\N	2025-05-24 15:08:37.880671
61	6	3	1509.38	\N	2025-05-24 15:08:37.883746
60	5	3	1510.04	\N	2025-05-24 15:08:37.885928
\.


--
-- Data for Name: tournament; Type: TABLE DATA; Schema: public; Owner: mattiaianniello
--

COPY public.tournament (id, nome, tipo_torneo, circolo, note, data_inizio, data_fine, stato, created_at, config_json) FROM stdin;
3	30fri	torneotto30			2025-05-24	2025-05-31	In corso	2025-05-24 14:41:31.506967	{"num_squadre": 4, "num_giocatori": 8, "tempo_partita": 30}
4	45fresh	torneotto45			2025-05-24	2025-05-31	Pianificato	2025-05-24 15:09:21.976617	{"num_squadre": 4, "tempo_partita": 45, "finali": 2}
\.


--
-- Data for Name: tournament_day; Type: TABLE DATA; Schema: public; Owner: mattiaianniello
--

COPY public.tournament_day (id, tournament_id, data, stato, created_at, config_json, tipo_giornata) FROM stdin;
11	4	2025-05-23	Completata	2025-05-24 19:44:40.098624	{"players": [1, 7, 4, 14, 15, 17, 12, 2], "semifinali": [{"squadra_a": [1, 7], "squadra_b": [4, 14], "risultato": {"squadra_a": 6, "squadra_b": 4}}, {"squadra_a": [15, 17], "squadra_b": [12, 2], "risultato": {"squadra_a": 6, "squadra_b": 5}}], "finali": {"primo_posto": {"squadra_a": [1, 7], "squadra_b": [15, 17], "risultato": {"squadra_a": 6, "squadra_b": 2}}, "terzo_posto": {"squadra_a": [4, 14], "squadra_b": [12, 2], "risultato": {"squadra_a": 9, "squadra_b": 4}}}, "classifica": [1, 7, 15, 17, 4, 14, 12, 2]}	torneotto45
6	3	2025-05-25	Completata	2025-05-24 15:06:15.434209	{"players": [3, 1, 4, 6, 5, 8, 7, 2], "teams": [[3, 1], [4, 6], [5, 8], [7, 2]], "schedule": [[[1, 2], [3, 4]], [[1, 3], [2, 4]], [[1, 4], [2, 3]]], "results": {"1-2": "6-2", "3-4": "3-3", "1-3": "4-8", "2-4": "9-2", "1-4": "3-6", "2-3": "5-4"}}	torneotto30
7	3	2025-05-26	Completata	2025-05-24 15:07:08.805665	{"players": [3, 2, 8, 5, 1, 4, 7, 6], "teams": [[3, 2], [8, 5], [1, 4], [7, 6]], "schedule": [[[1, 2], [3, 4]], [[1, 3], [2, 4]], [[1, 4], [2, 3]]], "results": {"1-2": "5-8", "3-4": "7-2", "1-3": "3-6", "2-4": "5-5", "1-4": "4-6", "2-3": "5-2"}}	torneotto30
8	3	2025-06-01	Completata	2025-05-24 15:08:26.442487	{"players": [3, 2, 8, 6, 5, 7, 4, 1], "teams": [[3, 2], [8, 6], [5, 7], [4, 1]], "schedule": [[[1, 2], [3, 4]], [[1, 3], [2, 4]], [[1, 4], [2, 3]]], "results": {"1-2": "6-0", "3-4": "9-4", "1-3": "5-5", "2-4": "6-2", "1-4": "3-9", "2-3": "8-6"}}	torneotto30
9	4	2025-05-14	Completata	2025-05-24 17:36:17.388252	{"players": [15, 1, 17, 2, 4, 12, 7, 14], "semifinali": [{"squadra_a": [15, 1], "squadra_b": [17, 2], "risultato": {"squadra_a": 6, "squadra_b": 5}}, {"squadra_a": [4, 12], "squadra_b": [7, 14], "risultato": {"squadra_a": 7, "squadra_b": 6}}], "finali": {"primo_posto": {"squadra_a": [15, 1], "squadra_b": [4, 12], "risultato": {"squadra_a": 5, "squadra_b": 6}}, "terzo_posto": {"squadra_a": [17, 2], "squadra_b": [7, 14], "risultato": {"squadra_a": 4, "squadra_b": 3}}}, "classifica": [4, 12, 15, 1, 17, 2, 7, 14]}	torneotto45
10	3	2025-05-31	Completata	2025-05-24 15:37:20.905844	{"players": [14, 2, 17, 4, 1, 15, 12, 7], "teams": [[14, 2], [17, 4], [1, 15], [12, 7]], "schedule": [[[1, 2], [3, 4]], [[1, 3], [2, 4]], [[1, 4], [2, 3]]], "results": {"1-2": "5-7", "3-4": "8-2", "1-3": "5-5", "2-4": "6-4", "1-4": "8-7", "2-3": "6-4"}}	torneotto30
12	4	2025-05-10	Completata	2025-05-24 20:00:26.26129	{"players": [1, 17, 4, 12, 15, 14, 7, 2], "semifinali": [{"squadra_a": [1, 17], "squadra_b": [4, 12], "risultato": {"squadra_a": 5, "squadra_b": 6}}, {"squadra_a": [15, 14], "squadra_b": [7, 2], "risultato": {"squadra_a": 5, "squadra_b": 4}}], "finali": {"primo_posto": {"squadra_a": [4, 12], "squadra_b": [15, 14], "risultato": {"squadra_a": 7, "squadra_b": 6}}, "terzo_posto": {"squadra_a": [1, 17], "squadra_b": [7, 2], "risultato": {"squadra_a": 5, "squadra_b": 4}}}, "classifica": [4, 12, 15, 14, 1, 17, 7, 2]}	torneotto45
\.


--
-- Name: match_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mattiaianniello
--

SELECT pg_catalog.setval('public.match_id_seq', 1, false);


--
-- Name: player_elo_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mattiaianniello
--

SELECT pg_catalog.setval('public.player_elo_history_id_seq', 144, true);


--
-- Name: player_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mattiaianniello
--

SELECT pg_catalog.setval('public.player_id_seq', 17, true);


--
-- Name: player_tournament_elo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mattiaianniello
--

SELECT pg_catalog.setval('public.player_tournament_elo_id_seq', 76, true);


--
-- Name: tournament_day_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mattiaianniello
--

SELECT pg_catalog.setval('public.tournament_day_id_seq', 12, true);


--
-- Name: tournament_id_seq; Type: SEQUENCE SET; Schema: public; Owner: mattiaianniello
--

SELECT pg_catalog.setval('public.tournament_id_seq', 4, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: match match_pkey; Type: CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.match
    ADD CONSTRAINT match_pkey PRIMARY KEY (id);


--
-- Name: player_elo_history player_elo_history_pkey; Type: CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_elo_history
    ADD CONSTRAINT player_elo_history_pkey PRIMARY KEY (id);


--
-- Name: player player_pkey; Type: CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player
    ADD CONSTRAINT player_pkey PRIMARY KEY (id);


--
-- Name: player_tournament_elo player_tournament_elo_pkey; Type: CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_tournament_elo
    ADD CONSTRAINT player_tournament_elo_pkey PRIMARY KEY (id);


--
-- Name: tournament_day tournament_day_pkey; Type: CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.tournament_day
    ADD CONSTRAINT tournament_day_pkey PRIMARY KEY (id);


--
-- Name: tournament tournament_pkey; Type: CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.tournament
    ADD CONSTRAINT tournament_pkey PRIMARY KEY (id);


--
-- Name: player_tournament_elo unique_player_tournament; Type: CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_tournament_elo
    ADD CONSTRAINT unique_player_tournament UNIQUE (player_id, tournament_id);


--
-- Name: match match_player1_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.match
    ADD CONSTRAINT match_player1_id_fkey FOREIGN KEY (player1_id) REFERENCES public.player(id);


--
-- Name: match match_player2_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.match
    ADD CONSTRAINT match_player2_id_fkey FOREIGN KEY (player2_id) REFERENCES public.player(id);


--
-- Name: match match_player3_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.match
    ADD CONSTRAINT match_player3_id_fkey FOREIGN KEY (player3_id) REFERENCES public.player(id);


--
-- Name: match match_player4_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.match
    ADD CONSTRAINT match_player4_id_fkey FOREIGN KEY (player4_id) REFERENCES public.player(id);


--
-- Name: player_elo_history player_elo_history_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_elo_history
    ADD CONSTRAINT player_elo_history_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.match(id);


--
-- Name: player_elo_history player_elo_history_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_elo_history
    ADD CONSTRAINT player_elo_history_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.player(id);


--
-- Name: player_elo_history player_elo_history_tournament_day_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_elo_history
    ADD CONSTRAINT player_elo_history_tournament_day_id_fkey FOREIGN KEY (tournament_day_id) REFERENCES public.tournament_day(id) ON DELETE CASCADE;


--
-- Name: player_elo_history player_elo_history_tournament_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_elo_history
    ADD CONSTRAINT player_elo_history_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.tournament(id);


--
-- Name: player_tournament_elo player_tournament_elo_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_tournament_elo
    ADD CONSTRAINT player_tournament_elo_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.player(id);


--
-- Name: player_tournament_elo player_tournament_elo_tournament_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.player_tournament_elo
    ADD CONSTRAINT player_tournament_elo_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.tournament(id);


--
-- Name: tournament_day tournament_day_tournament_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: mattiaianniello
--

ALTER TABLE ONLY public.tournament_day
    ADD CONSTRAINT tournament_day_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.tournament(id);


--
-- PostgreSQL database dump complete
--

