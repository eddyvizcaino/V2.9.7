import sqlite3
from test_app import Base, token_from

class TestIdentity(Base):
    def check(self, cl, value, exclude=None):
        token=token_from(cl.get('/members/new').get_data(as_text=True))
        return cl.post('/api/members/check-cedula', json={'cedula':value,'exclude':exclude}, headers={'X-CSRFToken':token})

    def test_duplicate_formats_server_and_lookup(self):
        cl=self.client('admin')
        self.member(cl, Cedula='00112345678')
        result=self.check(cl,'001-1234567-8').json
        self.assertTrue(result['exists'])
        self.assertEqual(result['url'],'/members/1')
        self.member(cl,Cedula='001 1234567 8')
        self.assertEqual(self.q('SELECT count(*) FROM Members')[0][0],1)
        self.assertFalse(self.check(cl,'00112345678',1).json['exists'])
        self.member(cl,Cedula='00212345678')
        result=self.post(cl,'/members/2/edit',{'FirstName':'B','LastName':'C','Cedula':'00112345678'},page='/members/2/edit')
        self.assertIn('ya está registrada',result.get_data(as_text=True))
        self.assertEqual(self.q('SELECT Cedula FROM Members WHERE Id=2')[0][0],'002-1234567-8')

    def test_database_guards_legacy_formats_and_races(self):
        cl=self.client('admin'); self.member(cl,Cedula='00112345678')
        db=sqlite3.connect(self.db_path)
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO Members(FullName,Cedula,CreatedAt) VALUES('Otro','00112345678','x')")
        db.rollback();db.close()

    def test_permissions_csrf_and_cross_ministry(self):
        admin=self.client('admin');self.member(admin,Cedula='00112345678',MinistryId='2')
        cl=self.client('jovenes1');res=self.check(cl,'00112345678').json
        self.assertTrue(res['exists']);self.assertIsNone(res['url'])
        self.assertEqual(self.check(cl,'00112345678',1).status_code,403)
        self.assertEqual(cl.post('/api/members/check-cedula',json={}).status_code,400)
        self.assertEqual(self.client().get('/members/new').status_code,302)

    def test_trash_reserves_cedula_and_preserves_history(self):
        cl=self.client('admin');self.member(cl,Cedula='00112345678')
        self.post(cl,'/members/1/delete',page='/members')
        self.assertTrue(self.check(cl,'00112345678').json['deleted'])
        self.assertTrue(self.q('SELECT * FROM MemberHistory WHERE MemberId=1'))
        self.assertNotIn('Ana Pérez',cl.get('/members').get_data(as_text=True))
        self.post(cl,'/trash/1/restore',page='/trash')
        self.assertIsNone(self.q('SELECT DeletedAt FROM Members')[0][0])

    def test_secretary_preserved_and_manual_flow(self):
        db=sqlite3.connect(self.db_path);db.execute("UPDATE Users SET Role='Secretaria', MinistryId=NULL WHERE Username='jovenes1'");db.commit();db.close()
        cl=self.client('jovenes1');self.member(cl,MinistryId='2',BirthDate='1990-02-01')
        self.assertEqual(self.q('SELECT MinistryId,BirthDate FROM Members')[0],(2,'1990-02-01'))
        self.assertEqual(cl.get('/users').status_code,403)
        html=cl.get('/members/new').get_data(as_text=True)
        self.assertIn('ESCANEAR FRENTE DE CÉDULA',html)
        self.assertNotIn('name="identity_image"',html)
