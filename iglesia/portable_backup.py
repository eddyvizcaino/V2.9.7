"""Respaldo lógico consistente y restauración transaccional en una base vacía."""
import json
from .db import connect, now_iso
TABLES = ['Ministries','Members','Events','Users','AuditLog','LoginLog','MemberHistory','Alerts','Photos',
          'FStudents','FSubjects','FPeriods','FRecords','FHistory','MemberRegistration']

def export_backup(database):
    conn=connect(database)
    try:
        if getattr(conn,'is_postgres',False):
            conn.rollback()
            conn.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        else: conn.execute('BEGIN')
        tables={name:[dict(r) for r in conn.execute(f'SELECT * FROM {name} ORDER BY Id').fetchall()] for name in TABLES}
        return json.dumps({'format':'iglesia-271','created_at':now_iso(),'tables':tables},ensure_ascii=False).encode('utf-8')
    finally:conn.close()

def restore_empty(database, content, *, replace_existing=False):
    data=json.loads(content)
    if data.get('format')!='iglesia-271' or set(data.get('tables',{})) not in (set(TABLES), set(TABLES)-{'MemberRegistration'}):
        raise ValueError('Formato de respaldo no compatible.')
    data['tables'].setdefault('MemberRegistration', [])
    conn=connect(database)
    try:
        if getattr(conn,'is_postgres',False):
            conn.execute('LOCK TABLE '+','.join(TABLES)+' IN ACCESS EXCLUSIVE MODE')
        else:conn.execute('BEGIN IMMEDIATE')
        if not replace_existing:
            for table in TABLES:
                if table in ('Users','FSubjects'):continue
                if conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]:
                    raise ValueError('La base destino debe estar vacía. Restaure en otra base y después cambie DATABASE_URL.')
            if conn.execute('SELECT COUNT(*) FROM Users').fetchone()[0]>1:
                raise ValueError('La base destino ya tiene usuarios.')
        # Validar todas las columnas antes de borrar el primer registro.
        for table in TABLES:
            if getattr(conn,'is_postgres',False):
                columns={r[0].lower() for r in conn.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=?',(table.lower(),)).fetchall()}
            else:columns={r['name'].lower() for r in conn.execute(f'PRAGMA table_info({table})')}
            for row in data['tables'][table]:
                if not isinstance(row,dict) or not row or any(k.lower() not in columns for k in row):
                    raise ValueError('Columnas no compatibles en '+table)
        if replace_existing and not data['tables']['Users']:
            raise ValueError('El respaldo no contiene usuarios; se rechazó la restauración.')
        for table in reversed(TABLES):conn.execute(f'DELETE FROM {table}')
        for table in TABLES:
            for row in data['tables'][table]:
                names=list(row)
                # Quote validated column identifiers; PostgreSQL schema uses lowercase.
                cols=','.join('"'+k.lower()+'"' for k in names)
                conn.execute(f'INSERT INTO {table}({cols}) VALUES({",".join("?" for _ in names)})',list(row.values()))
            if getattr(conn,'is_postgres',False):
                conn.execute(f"SELECT setval(pg_get_serial_sequence('{table.lower()}','id'),COALESCE((SELECT MAX(Id) FROM {table}),1),EXISTS(SELECT 1 FROM {table}))")
        conn.commit()
    except Exception:
        conn.rollback();raise
    finally:conn.close()
