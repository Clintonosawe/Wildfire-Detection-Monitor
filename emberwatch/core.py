"""Validated ingestion, deterministic grouping, and transparent triage scoring."""
import csv
import hashlib
import io
import math
from datetime import datetime, timezone

MAX_ROWS = 5000
TRANSITIONS = {'new': {'reviewing'}, 'reviewing': {'confirmed', 'dismissed'},
               'confirmed': {'resolved'}, 'dismissed': {'reviewing'}, 'resolved': {'reviewing'}}

def number(value, name, low, high):
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{name} must be numeric') from None
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f'{name} must be between {low} and {high}')
    return result

def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    required = {'latitude', 'longitude', 'acq_date', 'acq_time', 'confidence', 'frp', 'satellite'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('Missing CSV columns: ' + ', '.join(sorted(required - set(reader.fieldnames or []))))
    rows = []
    for index, row in enumerate(reader, 2):
        if len(rows) >= MAX_ROWS:
            raise ValueError('CSV exceeds 5000 rows; split into regional batches')
        try:
            lat = number(row['latitude'], 'latitude', -90, 90)
            lon = number(row['longitude'], 'longitude', -180, 180)
            t = row['acq_time'].strip().zfill(4)
            if len(t) != 4 or not t.isdigit():
                raise ValueError('acq_time must be HHMM')
            acquired = datetime.strptime(row['acq_date'] + t, '%Y-%m-%d%H%M').replace(tzinfo=timezone.utc).isoformat()
            confidence = {'l': 20, 'n': 60, 'h': 90}.get(row['confidence'].strip().lower())
            if confidence is None:
                confidence = number(row['confidence'], 'confidence', 0, 100)
            satellite = row['satellite'].strip()
            if not satellite or len(satellite) > 40:
                raise ValueError('satellite must be 1–40 characters')
            item = dict(latitude=lat, longitude=lon, acquired=acquired, confidence=confidence,
                        frp=number(row['frp'], 'frp', 0, 100000), satellite=satellite)
            for name, high in [('humidity', 100), ('wind_kmh', 500)]:
                item[name] = number(row[name], name, 0, high) if row.get(name, '').strip() else None
            key = f'{lat:.6f}|{lon:.6f}|{acquired}|{satellite}'
            item['id'] = hashlib.sha256(key.encode()).hexdigest()[:20]
            rows.append(item)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f'CSV row {index}: {exc}') from None
    if not rows:
        raise ValueError('CSV has no detections')
    return rows

def distance(a, b):
    lat1, lat2 = math.radians(a['latitude']), math.radians(b['latitude'])
    dlat = lat2 - lat1
    dlon = math.radians(b['longitude'] - a['longitude'])
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(h)))

def priority(d):
    parts = {'satellite_confidence': round(d['confidence'] * .5, 1),
             'radiative_power': round(min(d['frp']/100, 1)*30, 1),
             'dryness': round((100-d['humidity'])/100*10, 1) if d['humidity'] is not None else 0,
             'wind': round(min(d['wind_kmh']/60, 1)*10, 1) if d['wind_kmh'] is not None else 0}
    score = round(sum(parts.values()), 1)
    return dict(score=score, band='high' if score >= 65 else 'medium' if score >= 40 else 'low',
                components=parts, missing_weather=d['humidity'] is None or d['wind_kmh'] is None)
