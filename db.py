import dbm
import json

DB_FILE = "session_store.db"

def save_token(uuid: str, data: dict):
    with dbm.open(DB_FILE, 'c') as db:
        db[uuid] = json.dumps(data)

def get_token(uuid: str) -> dict:
    with dbm.open(DB_FILE, 'c') as db:
        if uuid.encode() not in db:
            return None
        return json.loads(db[uuid].decode())
