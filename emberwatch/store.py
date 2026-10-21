"""SQLite persistence. All ingest and review operations are transactional."""
import json
import sqlite3
from datetime import datetime, timezone
from .core import parse_csv, distance, priority, TRANSITIONS

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS incidents (
          id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'new',
          anchor TEXT NOT NULL, source TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS detections (
          id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id), payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id),
          kind TEXT NOT NULL, detail TEXT NOT NULL, created TEXT NOT NULL);
        ''')

    def close(self):
        self.db.close()

    def event(self, incident_id, kind, detail):
        self.db.execute('INSERT INTO events(incident_id,kind,detail,created) VALUES(?,?,?,?)',
                        (incident_id, kind, detail, now()))

    def ingest(self, text, source):
        if source not in {'synthetic-demo', 'firms-csv'}:
            raise ValueError('Unknown source')
        rows = sorted(parse_csv(text), key=lambda x: (x['acquired'], x['id']))
        inserted = 0
        with self.db:
            for d in rows:
                if self.db.execute('SELECT 1 FROM detections WHERE id=?', (d['id'],)).fetchone():
                    continue
                candidates = []
                for incident in self.db.execute('SELECT * FROM incidents WHERE source=?', (source,)):
                    anchor = json.loads(incident['anchor'])
                    hours = abs((datetime.fromisoformat(d['acquired'])-datetime.fromisoformat(anchor['acquired'])).total_seconds())/3600
                    km = distance(d, anchor)
                    if hours <= 24 and km <= 10:
                        candidates.append((km, incident['id']))
                incident_id = min(candidates)[1] if candidates else d['id']
                if not candidates:
                    self.db.execute('INSERT INTO incidents(id,anchor,source,created) VALUES(?,?,?,?)',
                                    (incident_id, json.dumps(d), source, now()))
                    self.event(incident_id, 'created', 'Incident opened from satellite-style detection')
                self.db.execute('INSERT INTO detections VALUES(?,?,?)', (d['id'], incident_id, json.dumps(d)))
                self.event(incident_id, 'ingested', 'Detection ' + d['id'])
                inserted += 1
        return {'inserted': inserted, 'duplicates': len(rows)-inserted}

    def incidents(self):
        result = []
        for row in self.db.execute('SELECT * FROM incidents'):
            d = dict(row)
            points = [json.loads(x['payload']) for x in self.db.execute('SELECT payload FROM detections WHERE incident_id=? ORDER BY id', (d['id'],))]
            anchor = json.loads(d.pop('anchor'))
            ranked = [(priority(p), p) for p in points]
            score, representative = max(ranked, key=lambda x: (x[0]['score'], x[1]['id']))
            d.update(score)
            d.update(latitude=anchor['latitude'], longitude=anchor['longitude'], count=len(points),
                     latest=max(p['acquired'] for p in points), representative=representative, detections=points)
            d['events'] = [dict(e) for e in self.db.execute('SELECT * FROM events WHERE incident_id=? ORDER BY id DESC', (d['id'],))]
            result.append(d)
        return sorted(result, key=lambda d: (-d['score'], d['id']))

    def review(self, incident_id, action, note):
        if not isinstance(note, str) or not 3 <= len(note.strip()) <= 1000:
            raise ValueError('Provide a note of 3–1000 characters')
        with self.db:
            row = self.db.execute('SELECT status FROM incidents WHERE id=?', (incident_id,)).fetchone()
            if not row:
                raise ValueError('Incident not found')
            if action == 'report':
                self.event(incident_id, 'unverified-report', note.strip())
            else:
                if action not in TRANSITIONS[row['status']]:
                    raise ValueError(f'Invalid transition from {row["status"]} to {action}')
                self.db.execute('UPDATE incidents SET status=? WHERE id=?', (action, incident_id))
                self.event(incident_id, 'status', f'{row["status"]} → {action}: {note.strip()}')

    def geojson(self):
        return {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [d['longitude'], d['latitude']]},
             'properties': {k: d[k] for k in ['id', 'status', 'score', 'band', 'source', 'count', 'latest']}}
            for d in self.incidents()]}
