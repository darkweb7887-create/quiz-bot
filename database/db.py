#!/usr/bin/env python3
"""Database module - SQLite"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'quiz_bot.db')

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        with self.get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT DEFAULT '',
                    first_name TEXT DEFAULT '',
                    last_name TEXT DEFAULT '',
                    is_banned INTEGER DEFAULT 0,
                    is_admin INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    creator_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    approved INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id)
                );
                
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    options TEXT NOT NULL,
                    correct_answer INTEGER NOT NULL,
                    explanation TEXT DEFAULT '',
                    order_num INTEGER DEFAULT 0,
                    FOREIGN KEY (test_id) REFERENCES tests(id)
                );
                
                CREATE TABLE IF NOT EXISTS game_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    test_id INTEGER NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    correct_answers INTEGER DEFAULT 0,
                    total_questions INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (test_id) REFERENCES tests(id)
                );
                
                CREATE TABLE IF NOT EXISTS user_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    chosen_answer INTEGER NOT NULL,
                    is_correct INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES game_sessions(id)
                );
                
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
    
    # ==================== USERS ====================
    
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        with self.get_conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, last_name))
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None
    
    def get_all_users(self, limit: int = 100) -> List[Dict]:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM users ORDER BY joined_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
    
    def ban_user(self, user_id: int):
        with self.get_conn() as conn:
            conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    
    def unban_user(self, user_id: int):
        with self.get_conn() as conn:
            conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    
    def is_banned(self, user_id: int) -> bool:
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT is_banned FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            return bool(row['is_banned']) if row else False
    
    def is_admin(self, user_id: int) -> bool:
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT user_id FROM admins WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row is not None
    
    def get_users_by_period(self, period: str) -> List[Dict]:
        start_date = self._get_start_date(period)
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE joined_at >= ? ORDER BY joined_at DESC",
                (start_date,)
            ).fetchall()
            return [dict(r) for r in rows]
    
    # ==================== TESTS ====================
    
    def save_test(self, creator_id: int, title: str, description: str, 
                  questions: List[Dict], approved: bool = False) -> int:
        with self.get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO tests (creator_id, title, description, approved)
                VALUES (?, ?, ?, ?)
            """, (creator_id, title, description, int(approved)))
            test_id = cursor.lastrowid
            
            for i, q in enumerate(questions):
                options = json.dumps(q['options'], ensure_ascii=False)
                conn.execute("""
                    INSERT INTO questions (test_id, question, options, correct_answer, explanation, order_num)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    test_id, q['question'], options,
                    q['correct_answer'], q.get('explanation', ''), i
                ))
            
            return test_id
    
    def get_tests(self, approved_only: bool = True) -> List[Dict]:
        with self.get_conn() as conn:
            if approved_only:
                rows = conn.execute(
                    "SELECT * FROM tests WHERE approved = 1 ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tests ORDER BY created_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]
    
    def get_all_tests(self) -> List[Dict]:
        return self.get_tests(approved_only=False)
    
    def get_pending_tests(self) -> List[Dict]:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tests WHERE approved = 0 ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
    
    def get_test(self, test_id: int) -> Optional[Dict]:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM tests WHERE id = ?", (test_id,)).fetchone()
            return dict(row) if row else None
    
    def approve_test(self, test_id: int):
        with self.get_conn() as conn:
            conn.execute("UPDATE tests SET approved = 1 WHERE id = ?", (test_id,))
    
    def reject_test(self, test_id: int):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM tests WHERE id = ?", (test_id,))
            conn.execute("DELETE FROM questions WHERE test_id = ?", (test_id,))
    
    def delete_test(self, test_id: int):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM questions WHERE test_id = ?", (test_id,))
            conn.execute("DELETE FROM tests WHERE id = ?", (test_id,))
    
    # ==================== QUESTIONS ====================
    
    def get_questions(self, test_id: int) -> List[Dict]:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM questions WHERE test_id = ? ORDER BY order_num",
                (test_id,)
            ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d['options'] = json.loads(d['options'])
                result.append(d)
            return result
    
    def get_question_count(self, test_id: int) -> int:
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM questions WHERE test_id = ?", (test_id,)
            ).fetchone()
            return row['cnt']
    
    # ==================== SESSIONS & RESULTS ====================
    
    def start_session(self, user_id: int, test_id: int) -> int:
        with self.get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO game_sessions (user_id, test_id)
                VALUES (?, ?)
            """, (user_id, test_id))
            return cursor.lastrowid
    
    def save_result(self, session_id: int, user_id: int, test_id: int, 
                    correct: int, total: int):
        with self.get_conn() as conn:
            conn.execute("""
                UPDATE game_sessions 
                SET finished_at = CURRENT_TIMESTAMP, correct_answers = ?, total_questions = ?
                WHERE id = ?
            """, (correct, total, session_id))
    
    def get_user_results(self, user_id: int) -> List[Dict]:
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT gs.*, t.title as test_title,
                       gs.correct_answers as correct,
                       gs.total_questions as total,
                       gs.started_at as taken_at
                FROM game_sessions gs
                JOIN tests t ON gs.test_id = t.id
                WHERE gs.user_id = ? AND gs.finished_at IS NOT NULL
                ORDER BY gs.started_at DESC
                LIMIT 20
            """, (user_id,)).fetchall()
            return [dict(r) for r in rows]
    
    def get_test_attempts(self, test_id: int) -> int:
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM game_sessions WHERE test_id = ? AND finished_at IS NOT NULL",
                (test_id,)
            ).fetchone()
            return row['cnt']
    
    def get_top_users(self, limit: int = 10) -> List[Dict]:
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT u.user_id, u.first_name, u.username,
                       SUM(gs.correct_answers) as total_correct,
                       SUM(gs.total_questions) as total_questions,
                       CASE WHEN SUM(gs.total_questions) > 0 
                            THEN ROUND(SUM(gs.correct_answers) * 100.0 / SUM(gs.total_questions), 1)
                            ELSE 0 END as percentage
                FROM users u
                JOIN game_sessions gs ON u.user_id = gs.user_id
                WHERE gs.finished_at IS NOT NULL
                GROUP BY u.user_id
                ORDER BY percentage DESC, total_correct DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
    
    # ==================== STATISTICS ====================
    
    def _get_start_date(self, period: str) -> str:
        now = datetime.now()
        if period == 'today':
            start = now.replace(hour=0, minute=0, second=0)
        elif period == 'week':
            start = now - timedelta(days=7)
        elif period == 'month':
            start = now - timedelta(days=30)
        elif period == '3months':
            start = now - timedelta(days=90)
        elif period == '6months':
            start = now - timedelta(days=180)
        elif period == 'year':
            start = now - timedelta(days=365)
        else:
            start = datetime(2000, 1, 1)
        return start.strftime('%Y-%m-%d %H:%M:%S')
    
    def get_stats(self) -> Dict:
        with self.get_conn() as conn:
            total_users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()['cnt']
            total_tests = conn.execute("SELECT COUNT(*) as cnt FROM tests WHERE approved = 1").fetchone()['cnt']
            total_games = conn.execute("SELECT COUNT(*) as cnt FROM game_sessions WHERE finished_at IS NOT NULL").fetchone()['cnt']
            pending = conn.execute("SELECT COUNT(*) as cnt FROM tests WHERE approved = 0").fetchone()['cnt']
            banned = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE is_banned = 1").fetchone()['cnt']
            
            return {
                'total_users': total_users,
                'total_tests': total_tests,
                'total_games': total_games,
                'pending_tests': pending,
                'banned_users': banned
            }
    
    def get_stats_by_period(self, period: str) -> Dict:
        start_date = self._get_start_date(period)
        with self.get_conn() as conn:
            new_users = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE joined_at >= ?", (start_date,)
            ).fetchone()['cnt']
            
            games = conn.execute(
                "SELECT COUNT(*) as cnt FROM game_sessions WHERE started_at >= ? AND finished_at IS NOT NULL",
                (start_date,)
            ).fetchone()['cnt']
            
            new_tests = conn.execute(
                "SELECT COUNT(*) as cnt FROM tests WHERE created_at >= ?", (start_date,)
            ).fetchone()['cnt']
            
            return {
                'new_users': new_users,
                'games': games,
                'new_tests': new_tests
            }
    
    def get_stats_custom_range(self, start: str, end: str) -> Dict:
        with self.get_conn() as conn:
            new_users = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE joined_at BETWEEN ? AND ?",
                (start, end)
            ).fetchone()['cnt']
            
            games = conn.execute(
                "SELECT COUNT(*) as cnt FROM game_sessions WHERE started_at BETWEEN ? AND ? AND finished_at IS NOT NULL",
                (start, end)
            ).fetchone()['cnt']
            
            return {'new_users': new_users, 'games': games}
    
    def get_all_users_for_api(self) -> List[Dict]:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT user_id, username, first_name, last_name, is_banned, joined_at FROM users ORDER BY joined_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
    
    def get_all_tests_for_api(self) -> List[Dict]:
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT t.*, u.first_name as creator_name,
                       (SELECT COUNT(*) FROM questions WHERE test_id = t.id) as question_count,
                       (SELECT COUNT(*) FROM game_sessions WHERE test_id = t.id AND finished_at IS NOT NULL) as attempts
                FROM tests t
                LEFT JOIN users u ON t.creator_id = u.user_id
                ORDER BY t.created_at DESC
            """).fetchall()
            return [dict(r) for r in rows]
