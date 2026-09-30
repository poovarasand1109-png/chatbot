import sqlite3
from datetime import date


DATABASE_NAME = "macrosnap.db"


# =========================================================
# CREATE DATABASE
# =========================================================

def create_database():

    connection = sqlite3.connect(
        DATABASE_NAME
    )

    cursor = connection.cursor()

    # Table for daily protein
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_protein (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_date TEXT UNIQUE,
            protein REAL DEFAULT 0
        )
    """)

    # Table for user settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY,
            protein_goal REAL DEFAULT 100
        )
    """)

    connection.commit()

    connection.close()


# =========================================================
# GET TODAY'S PROTEIN
# =========================================================

def get_today_protein():

    today = str(date.today())

    connection = sqlite3.connect(
        DATABASE_NAME
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT protein
        FROM daily_protein
        WHERE tracking_date = ?
        """,
        (today,)
    )

    result = cursor.fetchone()

    connection.close()

    if result is None:
        return 0.0

    return result[0]


# =========================================================
# ADD PROTEIN
# =========================================================

def add_protein(protein):

    today = str(date.today())

    connection = sqlite3.connect(
        DATABASE_NAME
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO daily_protein (
            tracking_date,
            protein
        )
        VALUES (?, ?)

        ON CONFLICT(tracking_date)
        DO UPDATE SET
            protein = protein + excluded.protein
        """,
        (today, protein)
    )

    connection.commit()

    connection.close()


# =========================================================
# GET PROTEIN GOAL
# =========================================================

def get_protein_goal():

    connection = sqlite3.connect(
        DATABASE_NAME
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT protein_goal
        FROM user_settings
        WHERE id = 1
        """
    )

    result = cursor.fetchone()

    connection.close()

    # Default goal
    if result is None:
        return 100.0

    return result[0]


# =========================================================
# SAVE PROTEIN GOAL
# =========================================================

def save_protein_goal(protein_goal):

    connection = sqlite3.connect(
        DATABASE_NAME
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO user_settings (
            id,
            protein_goal
        )
        VALUES (1, ?)

        ON CONFLICT(id)
        DO UPDATE SET
            protein_goal = excluded.protein_goal
        """,
        (protein_goal,)
    )

    connection.commit()

    connection.close()