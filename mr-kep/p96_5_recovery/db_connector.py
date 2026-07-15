import sqlite3

class DBConnector:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
    def load_lexicon(self):
        # Load canonical whisky names and aliases
        cursor = self.conn.cursor()
        lexicon = {}
        
        # Load Whiskies
        cursor.execute("SELECT whisky_id, name, original_name FROM whiskies")
        for row in cursor.fetchall():
            w_id = row["whisky_id"]
            if row["name"]: lexicon[row["name"].lower().strip()] = w_id
            if row["original_name"]: lexicon[row["original_name"].lower().strip()] = w_id
            
        # Load Aliases
        cursor.execute("SELECT alias_name, entity_id FROM entity_aliases WHERE entity_type='whisky'")
        for row in cursor.fetchall():
            lexicon[row["alias_name"].lower().strip()] = row["entity_id"]
            
        return lexicon
