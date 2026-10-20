import argparse
from pathlib import Path
from .store import Store
from .server import serve

def main():
    p = argparse.ArgumentParser(description='EmberWatch local wildfire triage prototype')
    p.add_argument('--db', default='emberwatch.db', help='SQLite database path')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('demo', help='Import explicitly synthetic demo observations')
    ingest = sub.add_parser('ingest', help='Import NASA FIRMS-format CSV')
    ingest.add_argument('file', type=Path)
    web = sub.add_parser('serve')
    web.add_argument('--port', type=int, default=8000)
    args = p.parse_args()
    if args.command == 'serve':
        serve(args.db, args.port)
        return
    store = Store(args.db)
    try:
        path = Path(__file__).parent.parent/'data/demo.csv' if args.command == 'demo' else args.file
        if path.stat().st_size > 5_000_000:
            raise ValueError('CSV must be at most 5 MB')
        print(store.ingest(path.read_text(encoding='utf-8-sig'), 'synthetic-demo' if args.command == 'demo' else 'firms-csv'))
    except (ValueError, OSError) as exc:
        p.exit(1, f'Error: {exc}\n')
    finally:
        store.close()

if __name__ == '__main__':
    main()
