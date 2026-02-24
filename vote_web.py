import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="VoteSchool Web", page_icon="🏛️", layout="centered")

DB_PATH = "vote_school.db"

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# --- INITIALISATION DE LA BASE (Si inexistante) ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Création des tables
    c.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, class TEXT, student_id TEXT UNIQUE, password_hash TEXT, is_admin INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS elections (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT, election_id INTEGER, name TEXT, class TEXT
        );
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, election_id INTEGER, candidate_id INTEGER
        );
    """)
    
    # Ajout des données de démo si la table est vide
    check = c.execute("SELECT count(*) FROM students").fetchone()[0]
    if check == 0:
        # Admin
        c.execute("INSERT INTO students (name, class, student_id, password_hash, is_admin) VALUES (?,?,?,?,?)",
                  ("Administrateur", "Direction", "ADMIN001", hash_pw("admin123"), 1))
        # Élèves
        for i in range(1, 6):
            c.execute("INSERT INTO students (name, class, student_id, password_hash) VALUES (?,?,?,?)",
                      (f"Élève {i}", f"Classe {i}", f"STU00{i}", hash_pw("vote123")))
        
        # Une élection exemple
        c.execute("INSERT INTO elections (title, description) VALUES (?,?)",
                  ("Élections des Délégués 2026", "Votez pour vos représentants."))
        
        # Des candidats
        c.execute("INSERT INTO candidates (election_id, name, class) VALUES (1, 'Cédric Touré', 'Terminale A')")
        c.execute("INSERT INTO candidates (election_id, name, class) VALUES (1, 'Aïcha Koné', 'Terminale B')")
        
        conn.commit()
    conn.close()

# Lancer l'initialisation
init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- INTERFACE ---
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🏛️ VoteSchool Web")
    with st.form("login"):
        sid = st.text_input("Identifiant (ex: STU001)")
        pwd = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter"):
            db = get_db()
            user = db.execute("SELECT * FROM students WHERE student_id=? AND password_hash=?", 
                             (sid, hash_pw(pwd))).fetchone()
            if user:
                st.session_state.user = dict(user)
                st.rerun()
            else:
                st.error("Identifiants incorrects")
else:
    user = st.session_state.user
    st.sidebar.success(f"Connecté : {user['name']}")
    if st.sidebar.button("Déconnexion"):
        st.session_state.user = None
        st.rerun()

    st.header("🗳️ Bulletin de Vote")
    db = get_db()
    elections = db.execute("SELECT * FROM elections WHERE is_active=1").fetchall()

    for elect in elections:
        st.subheader(elect['title'])
        voted = db.execute("SELECT id FROM votes WHERE student_id=? AND election_id=?", 
                          (user['student_id'], elect['id'])).fetchone()
        
        if voted:
            st.info("✅ Vote enregistré pour cette élection.")
            res = db.execute("SELECT c.name, COUNT(v.id) as voix FROM candidates c LEFT JOIN votes v ON v.candidate_id=c.id WHERE c.election_id=? GROUP BY c.id", (elect['id'],)).fetchall()
            st.bar_chart(pd.DataFrame(res, columns=["Candidat", "voix"]).set_index("Candidat"))
        else:
            candidates = db.execute("SELECT * FROM candidates WHERE election_id=?", (elect['id'],)).fetchall()
            choice = st.radio("Candidats :", [c['name'] for c in candidates], key=elect['id'])
            if st.button("Voter"):
                c_id = db.execute("SELECT id FROM candidates WHERE name=? AND election_id=?", (choice, elect['id'])).fetchone()['id']
                db.execute("INSERT INTO votes (student_id, election_id, candidate_id) VALUES (?,?,?)", (user['student_id'], elect['id'], c_id))
                db.commit()
                st.rerun()
