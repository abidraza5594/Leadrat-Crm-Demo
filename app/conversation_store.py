"""Project-scoped durable state and knowledge. PostgreSQL in deployment;
SQLite is an explicit local-development option, not an in-memory fallback.
"""
import asyncio
import json
import os
import sqlite3
import threading
from pathlib import Path
from .config import ROOT


class ConversationStore:
    def __init__(self,dsn=None,path=None):
        self.dsn=dsn if dsn is not None else os.getenv('BEACON_DATABASE_URL','')
        self.path=Path(path or os.getenv('BEACON_STATE_PATH',ROOT/'.state/conversations.sqlite3'))
        self.lock=threading.RLock();self.pool=None;self.connection=None

    @property
    def backend(self):return 'postgresql' if self.dsn else 'sqlite-development'

    def _run(self,sql,args=(),fetch=False):
        with self.lock:
            if self.pool:
                with self.pool.connection() as c:
                    rows=c.execute(sql,args)
                    return rows.fetchall() if fetch else None
            rows=self.connection.execute(sql.replace('%s','?'),args)
            self.connection.commit()
            return rows.fetchall() if fetch else None

    async def start(self):
        def setup():
            if self.dsn:
                from psycopg_pool import ConnectionPool
                self.pool=ConnectionPool(self.dsn,min_size=1,max_size=3,kwargs={'autocommit':True},timeout=5)
                self.pool.wait(timeout=10)
                self._run('CREATE EXTENSION IF NOT EXISTS vector')
            else:
                self.path.parent.mkdir(parents=True,exist_ok=True)
                self.connection=sqlite3.connect(self.path,check_same_thread=False)
                self.connection.execute('PRAGMA journal_mode=WAL')
            self._run('''CREATE TABLE IF NOT EXISTS beacon_conversations (
                project TEXT NOT NULL, session_id TEXT NOT NULL, state TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(project,session_id))''')
            self._run('''CREATE TABLE IF NOT EXISTS beacon_knowledge (
                project TEXT NOT NULL, entry_id TEXT NOT NULL, version TEXT NOT NULL,
                document TEXT NOT NULL, embedding TEXT NOT NULL,
                PRIMARY KEY(project,entry_id))''')
            if self.pool:self._run('ALTER TABLE beacon_knowledge ADD COLUMN IF NOT EXISTS search_vector vector(384)')
            retention="CURRENT_TIMESTAMP - INTERVAL '7 days'" if self.pool else "datetime('now','-7 days')"
            self._run('DELETE FROM beacon_conversations WHERE updated_at < '+retention)
        await asyncio.to_thread(setup)

    async def load(self,project,session_id):
        rows=await asyncio.to_thread(self._run,'SELECT state FROM beacon_conversations WHERE project=%s AND session_id=%s',(project,session_id),True)
        return json.loads(rows[0][0]) if rows else {}

    async def save(self,project,session_id,state):
        # No session tokens, CRM credentials, browser cookies or model weights.
        await asyncio.to_thread(self._run,'''INSERT INTO beacon_conversations(project,session_id,state) VALUES(%s,%s,%s)
            ON CONFLICT(project,session_id) DO UPDATE SET state=excluded.state, updated_at=CURRENT_TIMESTAMP''',
            (project,session_id,json.dumps(state,ensure_ascii=False)))

    async def knowledge(self,project,version):
        rows=await asyncio.to_thread(self._run,'SELECT document,embedding FROM beacon_knowledge WHERE project=%s AND version=%s',(project,version),True)
        return [(json.loads(d),json.loads(e)) for d,e in rows]

    async def put_knowledge(self,project,version,rows):
        def write():
            for document,embedding in rows:
                values=(project,str(document['id']),version,json.dumps(document,ensure_ascii=False),json.dumps(embedding))
                self._run('''INSERT INTO beacon_knowledge(project,entry_id,version,document,embedding) VALUES(%s,%s,%s,%s,%s)
                    ON CONFLICT(project,entry_id) DO UPDATE SET version=excluded.version, document=excluded.document, embedding=excluded.embedding''',values)
                if self.pool:self._run('UPDATE beacon_knowledge SET search_vector=%s::vector WHERE project=%s AND entry_id=%s',(values[-1],project,values[1]))
        await asyncio.to_thread(write)

    async def nearest(self,project,version,vector,topic,k=4):
        if not self.pool:return None
        rows=await asyncio.to_thread(self._run,'''SELECT document, 1-(search_vector <=> %s::vector) AS similarity
            FROM beacon_knowledge WHERE project=%s AND version=%s AND document::jsonb->>'module'=%s
            ORDER BY search_vector <=> %s::vector LIMIT %s''',
            (json.dumps(vector),project,version,topic,json.dumps(vector),k),True)
        return [(float(score),json.loads(document)) for document,score in rows]

    async def close(self):
        if self.pool:await asyncio.to_thread(self.pool.close)
        if self.connection:await asyncio.to_thread(self.connection.close)
