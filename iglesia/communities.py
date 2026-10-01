"""Módulo independiente COMUNIDADES DE ORACIÓN."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from .db import audit, get_db, now_iso
from .security import clean, pastoral_required

bp=Blueprint('communities',__name__)

def _prayer_ministry_id():
    db=get_db()
    row=db.execute("SELECT Id FROM Ministries WHERE lower(Name) IN (lower('Ministerio de Oración'),lower('Oración'),lower('Oracion')) ORDER BY Id LIMIT 1").fetchone()
    if row: return row['Id']
    cur=db.execute("INSERT INTO Ministries(Name,Description,CreatedAt) VALUES(?,?,?)",('Ministerio de Oración','Ministerio base para Comunidades de Oración',now_iso()))
    db.commit(); return cur.lastrowid

def _community(cid):
    c=get_db().execute('SELECT * FROM Communities WHERE Id=?',(cid,)).fetchone()
    if not c: abort(404)
    return c

def _all_members():
    return get_db().execute("SELECT Id,MemberCode,FirstName,LastName,FullName,Phone FROM Members WHERE DeletedAt IS NULL ORDER BY FirstName,LastName,FullName").fetchall()

def _valid_people(*ids):
    ids=[x for x in ids if x]
    if len(ids)!=len(set(ids)): return False
    db=get_db(); return all(db.execute('SELECT 1 FROM Members WHERE Id=? AND DeletedAt IS NULL',(x,)).fetchone() for x in ids)

@bp.route('/communities')
@pastoral_required
def index():
    db=get_db(); mid=_prayer_ministry_id()
    rows=db.execute('''SELECT c.*,
      COALESCE(l1.FirstName||' '||l1.LastName,l1.FullName,'') Leader1Name,
      COALESCE(l2.FirstName||' '||l2.LastName,l2.FullName,'') Leader2Name,
      SUM(CASE WHEN cm.Active=1 THEN 1 ELSE 0 END) Total
      FROM Communities c
      LEFT JOIN Members l1 ON l1.Id=c.LeaderMemberId LEFT JOIN Members l2 ON l2.Id=c.Leader2MemberId
      LEFT JOIN CommunityMembers cm ON cm.CommunityId=c.Id WHERE c.MinistryId=?
      GROUP BY c.Id,l1.Id,l2.Id ORDER BY c.Name''',(mid,)).fetchall()
    return render_template('communities.html',title='COMUNIDADES DE ORACIÓN',rows=rows,can_manage=True)

@bp.route('/communities/new',methods=['GET','POST'])
@pastoral_required
def new():
    db=get_db(); mid=_prayer_ministry_id()
    if request.method=='POST':
        name=clean(request.form.get('Name'),200); status=request.form.get('Status') if request.form.get('Status') in ('Activa','Inactiva') else 'Activa'
        l1=request.form.get('LeaderMemberId',type=int); l2=request.form.get('Leader2MemberId',type=int)
        if not name: flash('El nombre de la comunidad es obligatorio.')
        elif not _valid_people(l1,l2): flash('Líder 1 y Líder 2 deben ser miembros válidos y diferentes.')
        elif db.execute('SELECT 1 FROM Communities WHERE MinistryId=? AND lower(Name)=lower(?)',(mid,name)).fetchone(): flash('Ya existe una comunidad de oración con ese nombre.')
        else:
            cur=db.execute('INSERT INTO Communities(MinistryId,Name,LeaderMemberId,Leader2MemberId,Status,CreatedDate,Notes,CreatedAt) VALUES(?,?,?,?,?,?,?,?)',(mid,name,l1,l2,status,request.form.get('CreatedDate') or None,clean(request.form.get('Notes'),2000),now_iso()))
            audit('Crear','Comunidad de Oración',cur.lastrowid,f'Comunidad {name}'); db.commit(); flash('Comunidad de oración creada.'); return redirect(url_for('communities.index'))
    return render_template('community_form.html',title='CREAR COMUNIDAD DE ORACIÓN',c={},members=_all_members())

@bp.route('/communities/<int:cid>/edit',methods=['GET','POST'])
@pastoral_required
def edit(cid):
    c=_community(cid); db=get_db(); mid=_prayer_ministry_id()
    if c['MinistryId']!=mid: abort(404)
    if request.method=='POST':
        name=clean(request.form.get('Name'),200); status=request.form.get('Status') if request.form.get('Status') in ('Activa','Inactiva') else 'Activa'; l1=request.form.get('LeaderMemberId',type=int); l2=request.form.get('Leader2MemberId',type=int)
        if not name: flash('El nombre de la comunidad es obligatorio.')
        elif not _valid_people(l1,l2): flash('Líder 1 y Líder 2 deben ser miembros válidos y diferentes.')
        elif db.execute('SELECT 1 FROM Communities WHERE MinistryId=? AND lower(Name)=lower(?) AND Id<>?',(mid,name,cid)).fetchone(): flash('Ya existe otra comunidad con ese nombre.')
        else:
            db.execute('UPDATE Communities SET Name=?,LeaderMemberId=?,Leader2MemberId=?,Status=?,CreatedDate=?,Notes=?,UpdatedAt=? WHERE Id=?',(name,l1,l2,status,request.form.get('CreatedDate') or None,clean(request.form.get('Notes'),2000),now_iso(),cid)); audit('Editar','Comunidad de Oración',cid,f'Comunidad actualizada: {name}'); db.commit(); flash('Comunidad actualizada.'); return redirect(url_for('communities.view',cid=cid))
    return render_template('community_form.html',title='EDITAR COMUNIDAD DE ORACIÓN',c=c,members=_all_members())

@bp.route('/communities/<int:cid>',methods=['GET','POST'])
@pastoral_required
def view(cid):
    c=_community(cid); db=get_db()
    if c['MinistryId']!=_prayer_ministry_id(): abort(404)
    if request.method=='POST':
        member_id=request.form.get('member_id',type=int); member=db.execute('SELECT Id FROM Members WHERE Id=? AND DeletedAt IS NULL',(member_id,)).fetchone()
        if not member: flash('Miembro no encontrado.')
        elif db.execute('SELECT Id FROM CommunityMembers WHERE CommunityId=? AND MemberId=? AND Active=1',(cid,member_id)).fetchone(): flash('Ese miembro ya pertenece a esta comunidad.')
        else:
            old=db.execute('SELECT Id FROM CommunityMembers WHERE CommunityId=? AND MemberId=? ORDER BY Id DESC',(cid,member_id)).fetchone()
            if old: db.execute('UPDATE CommunityMembers SET Active=1,JoinedAt=?,LeftAt=NULL WHERE Id=?',(now_iso(),old['Id']))
            else: db.execute('INSERT INTO CommunityMembers(CommunityId,MemberId,Active,JoinedAt) VALUES(?,?,1,?)',(cid,member_id,now_iso()))
            audit('Agregar miembro','Comunidad de Oración',cid,f'Miembro {member_id} agregado'); db.commit(); flash('Miembro agregado a la comunidad.')
    people=db.execute('''SELECT cm.Id cmid,m.Id,m.MemberCode,m.FirstName,m.LastName,m.FullName,m.Phone FROM CommunityMembers cm JOIN Members m ON m.Id=cm.MemberId WHERE cm.CommunityId=? AND cm.Active=1 AND m.DeletedAt IS NULL ORDER BY m.FirstName,m.LastName,m.FullName''',(cid,)).fetchall()
    return render_template('community_view.html',title=c['Name'],c=c,people=people,members=_all_members(),can_manage=True)

@bp.route('/communities/<int:cid>/members/<int:member_id>/remove',methods=['POST'])
@pastoral_required
def remove_member(cid,member_id):
    _community(cid); db=get_db(); db.execute('UPDATE CommunityMembers SET Active=0,LeftAt=? WHERE CommunityId=? AND MemberId=? AND Active=1',(now_iso(),cid,member_id)); audit('Retirar miembro','Comunidad de Oración',cid,f'Miembro {member_id} retirado'); db.commit(); flash('Miembro retirado; su ficha permanece intacta.'); return redirect(url_for('communities.view',cid=cid))
