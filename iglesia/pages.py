"""Inicio (panel), calendario/eventos, cumpleaños y alertas internas."""
import datetime

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .db import audit, get_db, now_iso, today_dr
from .security import NAME_SQL, clean, event_scope, is_admin, is_staff, login_required, parse_date, scope, where

bp = Blueprint('pages', __name__)

PRIORITIES = ['Normal', 'Alta', 'Urgente']



@bp.route('/')
@login_required
def home():
    db = get_db()
    sc, sp = scope()

    esc, esp = event_scope()

    def count(table, *extra):
        return db.execute(f'SELECT COUNT(*) FROM {table}' + where(sc, *extra), sp).fetchone()[0]

    stats = {
        'total': count('Members'),
        'inactive': count('Members', "Status='Inactivo'"),
        'baptized': count('Members', "BaptismDate IS NOT NULL AND BaptismDate<>''"),
        'active': count('Members', "Status='Activo'"),
        'ministries': (db.execute('SELECT COUNT(*) FROM Ministries').fetchone()[0] if is_staff() else 1),
        'upcoming': db.execute('SELECT COUNT(*) FROM Events' + where(esc, "date(EventDate)>='" + today_dr().isoformat() + "'"), esp).fetchone()[0],
        'new_month': count('Members', "substr(JoinDate,1,7)='" + today_dr().strftime('%Y-%m') + "'"),
        'conversions_month': db.execute("SELECT COUNT(*) FROM Conversions WHERE substr(ConversionDate,1,7)=?", (today_dr().strftime('%Y-%m'),)).fetchone()[0],
    }
    # Solo eventos de hoy en adelante (antes se mostraban también los ya pasados).
    events = db.execute('SELECT Name,EventDate,EventTime,Venue FROM Events'
                        + where(esc, "date(EventDate)>='" + today_dr().isoformat() + "'") + ' ORDER BY EventDate,EventTime LIMIT 6',
                        esp).fetchall()
    sql = ('SELECT m.Id,m.Name,COUNT(mem.Id) AS Total FROM Ministries m '
           'LEFT JOIN Members mem ON mem.MinistryId=m.Id AND mem.DeletedAt IS NULL')
    if is_staff():
        per_ministry = db.execute(sql + ' GROUP BY m.Id,m.Name ORDER BY m.Name COLLATE NOCASE').fetchall()
    else:
        per_ministry = db.execute(sql + ' WHERE m.Id=? GROUP BY m.Id,m.Name', (g.user['MinistryId'],)).fetchall()
    today=today_dr();celebrations=[]
    for person in db.execute('SELECT FullName,BirthDate,BaptismDate FROM Members'+where(sc),sp).fetchall():
        for field,label in [('BirthDate','Cumpleaños')]:
            try:
                original=datetime.date.fromisoformat(person[field])
                def occurrence(year):
                    try:return original.replace(year=year)
                    except ValueError:return datetime.date(year,2,28)
                nxt=occurrence(today.year)
                if nxt<today:nxt=occurrence(today.year+1)
                delta=(nxt-today).days
                if delta<=30:celebrations.append((delta,person['FullName'],label,nxt.isoformat()))
            except (ValueError,TypeError):pass
    return render_template('home.html', title='INICIO', stats=stats, events=events, per_ministry=per_ministry,celebrations=sorted(celebrations)[:10])


@bp.route('/birthdays')
@login_required
def birthdays():
    db = get_db()
    sc, sp = scope()
    rows = db.execute(
        f'SELECT {NAME_SQL} AS Name,BirthDate,GroupName,Phone,MinistryId FROM Members'
        + where(sc, "BirthDate IS NOT NULL AND BirthDate<>''"), sp).fetchall()
    today = today_dr()

    def occurrence(value, year):
        born = datetime.date.fromisoformat(value)
        try:
            return born.replace(year=year)
        except ValueError:  # 29 de febrero en año no bisiesto
            return datetime.date(year, 2, 28)

    def birthday_info(row):
        try:
            born = datetime.date.fromisoformat(row['BirthDate'])
            this_year = occurrence(row['BirthDate'], today.year)
            nxt = this_year if this_year >= today else occurrence(row['BirthDate'], today.year + 1)
            prev = this_year if this_year <= today else occurrence(row['BirthDate'], today.year - 1)
            return {
                'row': row,
                'born': born,
                'next': nxt,
                'days': (nxt - today).days,
                'since': (today - prev).days,
                'day_month': nxt.strftime('%d/%m'),
                'month': nxt.month,
            }
        except (ValueError, TypeError):
            return None

    info = [x for x in (birthday_info(r) for r in rows) if x]
    info.sort(key=lambda x: x['days'])
    today_birthdays = [x for x in info if x['days'] == 0]
    recent = sorted([x for x in info if 1 <= x['since'] <= 7], key=lambda x: x['since'])
    next7 = [x for x in info if 1 <= x['days'] <= 7]
    current_month = [x for x in info if x['born'].month == today.month]
    current_month.sort(key=lambda x: x['born'].day)

    month_names = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    annual = []
    for month in range(1, 13):
        members = []
        for x in info:
            try:
                born = datetime.date.fromisoformat(x['row']['BirthDate'])
                if born.month == month:
                    members.append(x)
            except (ValueError, TypeError):
                pass
        members.sort(key=lambda x: int(x['row']['BirthDate'][8:10]))
        annual.append((month, month_names[month-1], members))

    return render_template('birthdays.html', title='CUMPLEAÑOS', today_birthdays=today_birthdays,
                           recent=recent, next7=next7, current_month=current_month, annual=annual,
                           month_names=month_names)


@bp.route('/alerts', methods=['GET', 'POST'])
@login_required
def alerts():
    db = get_db()
    if request.method == 'POST':
        title = clean(request.form.get('Title'), 150)
        due, err = parse_date(request.form.get('DueDate'))
        priority = request.form.get('Priority', 'Normal')
        if not title:
            flash('El título es obligatorio.')
        elif err:
            flash('La fecha no es válida.')
        elif priority not in PRIORITIES:
            flash('Prioridad no válida.')
        else:
            db.execute('INSERT INTO Alerts(Title,Message,DueDate,Priority,CreatedBy,CreatedAt) VALUES(?,?,?,?,?,?)',
                       (title, clean(request.form.get('Message'), 2000), due, priority, g.user['Id'], now_iso()))
            audit('Crear', 'Alerta', details=title)
            db.commit()
            flash('Alerta creada.')
            return redirect(url_for('pages.alerts'))
    rows = db.execute('SELECT Title,Message,DueDate,Priority FROM Alerts WHERE Active=1 ORDER BY DueDate').fetchall()
    return render_template('alerts.html', title='ALERTAS INTERNAS', rows=rows, priorities=PRIORITIES)
