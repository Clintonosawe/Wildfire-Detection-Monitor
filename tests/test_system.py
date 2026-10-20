import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from emberwatch.core import parse_csv, distance, priority
from emberwatch.store import Store

HEADER = 'latitude,longitude,acq_date,acq_time,satellite,confidence,frp,humidity,wind_kmh\n'
ROW = '49,-92,2026-10-18,0030,N,h,100,20,60\n'

class DomainTests(unittest.TestCase):
    def test_confidence_mapping_and_utc(self):
        d = parse_csv(HEADER+ROW)[0]
        self.assertEqual(d['confidence'], 90)
        self.assertEqual(d['acquired'], '2026-10-18T00:30:00+00:00')

    def test_score_components(self):
        result = priority(parse_csv(HEADER+ROW)[0])
        self.assertEqual(result['score'], 93)
        self.assertEqual(sum(result['components'].values()), result['score'])
        self.assertEqual(result['band'], 'high')

    def test_missing_weather(self):
        result = priority(parse_csv(HEADER+ROW.replace(',20,60', ',,'))[0])
        self.assertTrue(result['missing_weather'])
        self.assertEqual(result['score'], 75)

    def test_invalid_values(self):
        for old,new in [('49','91'),('-92','NaN'),('0030','2460'),(',h,',',unknown,'),(',100,',',-1,'),(',20,',',101,')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                parse_csv(HEADER+ROW.replace(old,new))

    def test_missing_columns_and_empty(self):
        for text in ['latitude\n49', HEADER]:
            with self.assertRaises(ValueError): parse_csv(text)

    def test_known_distance(self):
        self.assertAlmostEqual(distance({'latitude':0,'longitude':0}, {'latitude':0,'longitude':1}),111.195,places=2)
        self.assertAlmostEqual(distance({'latitude':0,'longitude':179.99}, {'latitude':0,'longitude':-179.99}),2.224,places=2)

    def test_row_limit(self):
        with self.assertRaises(ValueError): parse_csv(HEADER+ROW*5001)

class PersistenceTests(unittest.TestCase):
    def setUp(self): self.store=Store(':memory:')
    def tearDown(self): self.store.close()
    def ingest(self, rows=ROW): return self.store.ingest(HEADER+rows,'firms-csv')

    def test_idempotency(self):
        self.assertEqual(self.ingest()['inserted'],1)
        self.assertEqual(self.ingest()['duplicates'],1)
        self.assertEqual(len(self.store.incidents()[0]['events']),2)

    def test_nearby_and_distant_grouping(self):
        self.ingest(ROW+ROW.replace('49,','49.01,')+ROW.replace('49,','51,'))
        self.assertEqual(sorted(d['count'] for d in self.store.incidents()),[1,2])

    def test_temporal_boundary(self):
        self.ingest(ROW+ROW.replace('10-18','10-19')+ROW.replace('10-18','10-20'))
        self.assertEqual(sorted(d['count'] for d in self.store.incidents()),[1,2])

    def test_batch_order_is_deterministic(self):
        other=ROW.replace('49,','49.01,')
        self.ingest(other+ROW)
        ids=[d['id'] for d in self.store.incidents()]
        second=Store(':memory:')
        try:
            second.ingest(HEADER+ROW+other,'firms-csv')
            self.assertEqual(ids,[d['id'] for d in second.incidents()])
        finally: second.close()

    def test_malformed_batch_is_atomic(self):
        with self.assertRaises(ValueError): self.ingest(ROW+ROW.replace('49,','999,'))
        self.assertEqual(self.store.incidents(),[])

    def test_validated_transitions(self):
        self.ingest(); ident=self.store.incidents()[0]['id']
        with self.assertRaises(ValueError): self.store.review(ident,'confirmed','Too early')
        for action in ['reviewing','confirmed','resolved','reviewing','dismissed']:
            self.store.review(ident,action,'Test evidence')
        self.assertEqual(self.store.incidents()[0]['status'],'dismissed')
        self.assertEqual(len(self.store.incidents()[0]['events']),7)

    def test_report_does_not_change_score_or_status(self):
        self.ingest(); before=self.store.incidents()[0]
        self.store.review(before['id'],'report','Unverified smoke report')
        after=self.store.incidents()[0]
        self.assertEqual((before['score'],before['status']),(after['score'],after['status']))
        self.assertEqual(after['events'][0]['kind'],'unverified-report')

    def test_invalid_note(self):
        self.ingest(); ident=self.store.incidents()[0]['id']
        for note in ['', '  ', 'x'*1001]:
            with self.assertRaises(ValueError): self.store.review(ident,'reviewing',note)
        self.assertEqual(self.store.incidents()[0]['status'],'new')

    def test_geojson_longitude_first(self):
        self.ingest()
        self.assertEqual(self.store.geojson()['features'][0]['geometry']['coordinates'],[-92,49])

    def test_reopen_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'test.db')
            store=Store(path);store.ingest(HEADER+ROW,'firms-csv');store.close()
            store=Store(path)
            try: self.assertEqual(store.incidents()[0]['count'],1)
            finally: store.close()

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=str(Path(cls.tmp.name)/'http.db')
        store=Store(cls.db);store.ingest(HEADER+ROW,'firms-csv');store.close()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); cls.port=sock.getsockname()[1]
        cls.base=f'http://127.0.0.1:{cls.port}'
        cls.proc=subprocess.Popen([sys.executable,'-m','emberwatch','--db',cls.db,'serve','--port',str(cls.port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                with urlopen(cls.base+'/api/health',timeout=.3): return
            except OSError: time.sleep(.03)
        cls.proc.terminate();cls.proc.wait();cls.tmp.cleanup()
        raise RuntimeError('Server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate();cls.proc.wait(timeout=5);cls.tmp.cleanup()

    def test_assets_and_api(self):
        for path in ['/','/app.js','/style.css','/api/incidents','/api/export']:
            with urlopen(self.base+path) as response:
                self.assertEqual(response.status,200)
                self.assertIn("default-src 'self'",response.headers['Content-Security-Policy'])

    def test_reject_external_origin(self):
        req=Request(self.base+'/api/review',data=b'{}',headers={'Origin':'https://example.com'})
        with self.assertRaises(HTTPError) as ctx: urlopen(req)
        self.assertEqual(ctx.exception.code,403)

    def test_reject_bad_host(self):
        with self.assertRaises(HTTPError) as ctx: urlopen(Request(self.base+'/api/health',headers={'Host':'attacker.example'}))
        self.assertEqual(ctx.exception.code,403)

    def test_review_and_invalid_json(self):
        with urlopen(self.base+'/api/incidents') as response: ident=json.load(response)[0]['id']
        req=Request(self.base+'/api/review',data=json.dumps({'id':ident,'action':'report','note':'HTTP report'}).encode(),headers={'Origin':self.base,'Content-Type':'application/json'})
        with urlopen(req) as response: self.assertTrue(json.load(response)['ok'])
        for body in [b'{',b'[]',b'{"id":4}',b'x'*8193]:
            req=Request(self.base+'/api/review',data=body,headers={'Origin':self.base})
            with self.assertRaises(HTTPError) as ctx: urlopen(req)
            self.assertEqual(ctx.exception.code,400)

if __name__ == '__main__': unittest.main()
