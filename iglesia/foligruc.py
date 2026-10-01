"""FOLIGRUC: pénsum oficial, trimestres, inscripciones e historial permanente."""
import calendar
import datetime
import re
from io import BytesIO
from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for
from .security import clean, is_admin, is_pastoral, is_staff, login_required, parse_date, can_access_member, excel_safe

bp = Blueprint('foligruc', __name__, url_prefix='/foligruc')
SUBJECTS = ['Sanidad Interior', 'Liderazgo Saludable', 'Salud Financiera', 'Ética Cristiana',
 'Auto-Liderazgo, 21 cualidades de un líder', 'Ganador de Almas', 'Un líder como Jesús',
 'Formación de Grupos de Crecimiento', 'Perfil de los Tres Monarcas', 'Los llamados a Enseñar',
 'El Pase', 'Liderazgo, Ministerio y Batalla', 'Iglesia y su Comunidad', 'Mentoreo', 'Misiología']
SCHEMA = '''
CREATE TABLE IF NOT EXISTS FStudents(Id INTEGER PRIMARY KEY AUTOINCREMENT, Code TEXT UNIQUE NOT NULL,
 FullName TEXT NOT NULL, Phone TEXT, Congregation TEXT, JoinDate TEXT, Status TEXT NOT NULL DEFAULT 'Activo',
 MemberId INTEGER UNIQUE, MinistryId INTEGER, Notes TEXT, CreatedAt TEXT,
 FOREIGN KEY(MemberId) REFERENCES Members(Id), FOREIGN KEY(MinistryId) REFERENCES Ministries(Id));
CREATE TABLE IF NOT EXISTS FSubjects(Id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT UNIQUE NOT NULL, Teacher TEXT);
CREATE TABLE IF NOT EXISTS FPeriods(Id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT UNIQUE NOT NULL,
 StartDate TEXT NOT NULL, EndDate TEXT NOT NULL, Closed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS FRecords(Id INTEGER PRIMARY KEY AUTOINCREMENT, StudentId INTEGER NOT NULL,
 SubjectId INTEGER NOT NULL, PeriodId INTEGER, Status TEXT NOT NULL, Grade REAL, ApprovedDate TEXT,
 Previous INTEGER NOT NULL DEFAULT 0, Teacher TEXT, Notes TEXT, CreatedAt TEXT, CreatedBy INTEGER,
 UNIQUE(StudentId,SubjectId,PeriodId), FOREIGN KEY(StudentId) REFERENCES FStudents(Id),
 FOREIGN KEY(SubjectId) REFERENCES FSubjects(Id), FOREIGN KEY(PeriodId) REFERENCES FPeriods(Id),
 FOREIGN KEY(CreatedBy) REFERENCES Users(Id));
CREATE UNIQUE INDEX IF NOT EXISTS frecords_active_subject ON FRecords(StudentId,SubjectId) WHERE Status IN ('Aprobada','En curso');
CREATE TABLE IF NOT EXISTS FHistory(Id INTEGER PRIMARY KEY AUTOINCREMENT, StudentId INTEGER,
 UserId INTEGER, Action TEXT, Details TEXT, CreatedAt TEXT,
 FOREIGN KEY(StudentId) REFERENCES FStudents(Id), FOREIGN KEY(UserId) REFERENCES Users(Id));
'''

def db():
    from .db import get_db
    return get_db()

def record_action(student_id, action, details):
    from .db import audit, now_iso
    db().execute('INSERT INTO FHistory(StudentId,UserId,Action,Details,CreatedAt) VALUES(?,?,?,?,?)',
                 (student_id,g.user['Id'],action,details,now_iso()))
    audit(action,'FOLIGRUC',student_id,details)

def scoped():
    return ('',[]) if is_staff() else (' WHERE MinistryId=?',[g.user['MinistryId']])

def student_or_403(sid):
    student = db().execute('SELECT * FROM FStudents WHERE Id=?',(sid,)).fetchone()
    if not student: abort(404)
    if not is_staff() and (g.user['MinistryId'] is None or student['MinistryId'] != g.user['MinistryId']): abort(403)
    return student

def records(sid):
    return db().execute('SELECT r.*,s.Name AS SubjectName,p.Name AS PeriodName FROM FRecords r JOIN FSubjects s ON s.Id=r.SubjectId LEFT JOIN FPeriods p ON p.Id=r.PeriodId WHERE r.StudentId=? ORDER BY r.Id DESC',(sid,)).fetchall()

@bp.route('/')
@login_required
def home():
    sc, params = scoped()
    students=db().execute('SELECT * FROM FStudents'+sc+' ORDER BY FullName',params).fetchall()
    return render_template('foligruc.html',title='FOLIGRUC',section='home',students=students,
        subjects=db().execute('SELECT * FROM FSubjects ORDER BY Id').fetchall(),
        periods=db().execute('SELECT * FROM FPeriods ORDER BY StartDate DESC').fetchall())

@bp.route('/students',methods=['GET','POST'])
@login_required
def students():
    from .db import now_iso
    if request.method=='POST':
        name=clean(request.form.get('FullName'),160)
        member_id=request.form.get('MemberId',type=int)
        ministry_id=request.form.get('MinistryId',type=int) if is_staff() else g.user['MinistryId']
        problem=None
        joined,err=parse_date(request.form.get('JoinDate'))
        if err: problem='Fecha de ingreso no válida.'
        if ministry_id and not db().execute('SELECT Id FROM Ministries WHERE Id=?',(ministry_id,)).fetchone(): problem='Ministerio no válido.'
        if not is_staff() and not ministry_id: problem='Necesita un ministerio asignado.'
        if member_id:
            member=db().execute('SELECT * FROM Members WHERE Id=?',(member_id,)).fetchone()
            if not can_access_member(member): abort(403)
            name=member['FullName']; ministry_id=member['MinistryId']
        if not name: problem='El nombre es obligatorio.'
        if member_id and db().execute('SELECT Id FROM FStudents WHERE MemberId=?',(member_id,)).fetchone():
            problem='El miembro ya tiene expediente.'
        if problem: flash(problem)
        else:
            connection = db()
            # Serializar asignaciones simultáneas tanto en SQLite como en PostgreSQL.
            if getattr(connection, 'is_postgres', False):
                connection.execute('SELECT pg_advisory_xact_lock(274001)')
            else:
                connection.execute('BEGIN IMMEDIATE')
            used = {row['Code'] for row in connection.execute('SELECT Code FROM FStudents').fetchall()}
            numbers = [int(match.group(1)) for value in used
                       if (match := re.fullmatch(r'FOL-(\d+)', value or ''))]
            number = max(numbers, default=0) + 1
            code = f'FOL-{number:06d}'
            while code in used:
                number += 1
                code = f'FOL-{number:06d}'
            cur=db().execute('INSERT INTO FStudents(Code,FullName,Phone,Congregation,JoinDate,MemberId,MinistryId,Notes,CreatedAt) VALUES(?,?,?,?,?,?,?,?,?)',
                (code,name,clean(request.form.get('Phone'),40),clean(request.form.get('Congregation'),160),joined or datetime.date.today().isoformat(),member_id,ministry_id,clean(request.form.get('Notes'),2000),now_iso()))
            record_action(cur.lastrowid,'Crear estudiante',name);db().commit()
            return redirect(url_for('foligruc.student',sid=cur.lastrowid))
    sc,params=scoped()
    from .security import scope,where
    ms,mp=scope()
    return render_template('foligruc.html',title='FOLIGRUC · ESTUDIANTES',section='students',
        students=db().execute('SELECT * FROM FStudents'+sc+' ORDER BY FullName',params).fetchall(),
        members=db().execute('SELECT * FROM Members'+where(ms)+' ORDER BY FullName',mp).fetchall(),
        ministries=db().execute('SELECT * FROM Ministries ORDER BY Name').fetchall())

@bp.route('/subjects',methods=['GET','POST'])
@login_required
def subjects():
    if request.method=='POST':
        if not is_pastoral(): abort(403)
        sid=request.form.get('SubjectId',type=int)
        if sid not in range(1,16): abort(400)
        db().execute('UPDATE FSubjects SET Teacher=? WHERE Id=?',(clean(request.form.get('Teacher'),160),sid))
        record_action(None,'Editar profesor',f'Materia {sid}');db().commit()
        return redirect(url_for('foligruc.subjects'))
    return render_template('foligruc.html',title='FOLIGRUC · MATERIAS',section='subjects',subjects=db().execute('SELECT * FROM FSubjects ORDER BY Id').fetchall())

@bp.route('/periods',methods=['GET','POST'])
@login_required
def periods():
    if request.method=='POST':
        if not is_pastoral(): abort(403)
        pid=request.form.get('close',type=int)
        if pid:
            if db().execute("SELECT 1 FROM FRecords WHERE PeriodId=? AND Status='En curso'",(pid,)).fetchone():
                flash('Registre todos los resultados antes de cerrar el período.')
            else:
                db().execute('UPDATE FPeriods SET Closed=1 WHERE Id=?',(pid,));record_action(None,'Cerrar período',str(pid));db().commit()
        else:
            name=clean(request.form.get('Name'),100); start,err=parse_date(request.form.get('StartDate'))
            if not name or not start or err: flash('Nombre y fecha de inicio válidos son obligatorios.')
            elif db().execute('SELECT 1 FROM FPeriods WHERE Name=?',(name,)).fetchone(): flash('El período ya existe.')
            else:
                date=datetime.date.fromisoformat(start); month=date.month+3; year=date.year+(month-1)//12; month=(month-1)%12+1
                end=datetime.date(year,month,min(date.day,calendar.monthrange(year,month)[1]))-datetime.timedelta(days=1)
                db().execute('INSERT INTO FPeriods(Name,StartDate,EndDate) VALUES(?,?,?)',(name,start,end.isoformat()))
                record_action(None,'Crear período',name);db().commit()
        return redirect(url_for('foligruc.periods'))
    return render_template('foligruc.html',title='FOLIGRUC · PERÍODOS',section='periods',periods=db().execute('SELECT * FROM FPeriods ORDER BY StartDate DESC').fetchall())

@bp.route('/enrollments',methods=['GET','POST'])
@login_required
def enrollments():
    from .db import now_iso
    if request.method=='POST':
        sid=request.form.get('StudentId',type=int); student_or_403(sid)
        sub=request.form.get('SubjectId',type=int);pid=request.form.get('PeriodId',type=int)
        subject=db().execute('SELECT * FROM FSubjects WHERE Id=?',(sub,)).fetchone()
        period=db().execute('SELECT * FROM FPeriods WHERE Id=? AND Closed=0',(pid,)).fetchone()
        if not subject or not period: flash('Seleccione materia y período abierto.')
        elif db().execute("SELECT 1 FROM FRecords WHERE StudentId=? AND SubjectId=? AND (Status IN ('Aprobada','En curso') OR PeriodId=?)",(sid,sub,pid)).fetchone(): flash('La materia ya está aprobada, en curso o registrada en ese período.')
        else:
            db().execute("INSERT INTO FRecords(StudentId,SubjectId,PeriodId,Status,Teacher,CreatedAt,CreatedBy) VALUES(?,?,?,'En curso',?,?,?)",(sid,sub,pid,subject['Teacher'],now_iso(),g.user['Id']))
            record_action(sid,'Inscribir',subject['Name']);db().commit()
            return redirect(url_for('foligruc.student',sid=sid))
    sc,params=scoped()
    return render_template('foligruc.html',title='FOLIGRUC · INSCRIPCIONES',section='enrollments',students=db().execute('SELECT * FROM FStudents'+sc+' ORDER BY FullName',params).fetchall(),subjects=db().execute('SELECT * FROM FSubjects ORDER BY Id').fetchall(),periods=db().execute('SELECT * FROM FPeriods WHERE Closed=0 ORDER BY StartDate DESC').fetchall())

@bp.route('/students/<int:sid>',methods=['GET','POST'])
@login_required
def student(sid):
    from .db import now_iso
    s=student_or_403(sid)
    if request.method=='POST':
        previous=request.form.get('previous')=='1'
        if previous and not is_admin(): abort(403)
        status='Aprobada' if previous else request.form.get('Status')
        date,err=parse_date(request.form.get('ApprovedDate'));problem=None
        if err or (date and date>datetime.date.today().isoformat()): problem='Fecha de aprobación no válida.'
        if status not in ('Aprobada','Reprobada','En curso'): problem='Estado no válido.'
        if problem: flash(problem)
        elif previous:
            sub=request.form.get('SubjectId',type=int)
            subject=db().execute('SELECT * FROM FSubjects WHERE Id=?',(sub,)).fetchone()
            if not subject: abort(400)
            if db().execute("SELECT 1 FROM FRecords WHERE StudentId=? AND SubjectId=? AND Status IN ('Aprobada','En curso')",(sid,sub)).fetchone(): flash('Esa materia ya está aprobada o en curso.')
            else:
                db().execute("INSERT INTO FRecords(StudentId,SubjectId,Status,ApprovedDate,Previous,Teacher,Notes,CreatedAt,CreatedBy) VALUES(?,?,'Aprobada',?,1,?,?,?,?)",(sid,sub,date,subject['Teacher'],clean(request.form.get('Notes'),2000),now_iso(),g.user['Id']))
                record_action(sid,'Aprobación previa',subject['Name']);db().commit()
        else:
            rid=request.form.get('RecordId',type=int)
            row=db().execute('SELECT r.*,p.Closed FROM FRecords r LEFT JOIN FPeriods p ON p.Id=r.PeriodId WHERE r.Id=? AND r.StudentId=?',(rid,sid)).fetchone()
            if not row or row['Previous'] or row['Closed']: abort(400)
            db().execute('UPDATE FRecords SET Status=?,Grade=NULL,ApprovedDate=? WHERE Id=?',(status,date if status=='Aprobada' else None,rid))
            record_action(sid,'Resultado',f"Registro {rid}: {row['Status']} → {status}");db().commit()
        return redirect(url_for('foligruc.student',sid=sid))
    recs=records(sid); approved={r['SubjectId'] for r in recs if r['Status']=='Aprobada'}
    in_course={r['SubjectId'] for r in recs if r['Status']=='En curso'}
    return render_template('foligruc_student.html',title='EXPEDIENTE FOLIGRUC',s=s,records=recs,approved=approved,in_course=in_course,
        subjects=db().execute('SELECT * FROM FSubjects ORDER BY Id').fetchall(),history=db().execute('SELECT h.*,u.Username FROM FHistory h LEFT JOIN Users u ON u.Id=h.UserId WHERE h.StudentId=? ORDER BY h.Id DESC',(sid,)).fetchall())

@bp.route('/students/<int:sid>/export/<kind>')
@login_required
def export(sid,kind):
    s=student_or_403(sid); rows=records(sid); output=BytesIO()
    headings=['Materia','Período','Resultado','Fecha','Profesor','Anterior']
    values=[[r['SubjectName'],r['PeriodName'] or 'Anterior',r['Status'],r['ApprovedDate'],r['Teacher'],'Sí' if r['Previous'] else 'No'] for r in rows]
    if kind=='xlsx':
        from openpyxl import Workbook
        wb=Workbook();ws=wb.active;ws.title='Historial';ws.append([excel_safe(s['FullName']),excel_safe(s['Code'])]);ws.append(headings)
        for v in values:ws.append([excel_safe(x) for x in v])
        for col in ws.columns:ws.column_dimensions[col[0].column_letter].width=25
        wb.save(output);mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif kind=='pdf':
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4,landscape
        from xml.sax.saxutils import escape
        style=getSampleStyleSheet();data=[[Paragraph(escape(str(x if x is not None else '')),style['BodyText']) for x in v] for v in [headings]+values]
        table=Table(data,colWidths=[200,105,80,80,130,55],repeatRows=1);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.grey)]))
        SimpleDocTemplate(output,pagesize=landscape(A4),leftMargin=30,rightMargin=30).build([Paragraph('FOLIGRUC · Historial académico',style['Title']),Paragraph(escape(s['FullName']+' · '+s['Code']),style['Normal']),Spacer(1,16),table]);mime='application/pdf'
    else:abort(404)
    output.seek(0);return send_file(output,mimetype=mime,as_attachment=True,download_name=f'FOLIGRUC_{sid}.{kind}')


@bp.route('/students/<int:sid>/edit',methods=['GET','POST'])
@login_required
def edit_student(sid):
    s=student_or_403(sid)
    if request.method=='POST':
        status=request.form.get('Status');name=clean(request.form.get('FullName'),160)
        if status not in ('Activo','Inactivo','Graduado') or not name:
            flash('Nombre y estado válidos son obligatorios.')
        elif status=='Graduado' and db().execute("SELECT COUNT(DISTINCT SubjectId) FROM FRecords WHERE StudentId=? AND Status='Aprobada'",(sid,)).fetchone()[0]!=15:
            flash('Para registrar la graduación deben estar aprobadas las 15 materias.')
        else:
            db().execute('UPDATE FStudents SET FullName=?,Phone=?,Congregation=?,Status=?,Notes=? WHERE Id=?',(name,clean(request.form.get('Phone'),40),clean(request.form.get('Congregation'),160),status,clean(request.form.get('Notes'),2000),sid))
            record_action(sid,'Editar expediente',f"Estado {s['Status']} → {status}; datos personales actualizados");db().commit()
            return redirect(url_for('foligruc.student',sid=sid))
    return render_template('foligruc_edit.html',title='EDITAR ESTUDIANTE',s=s)
