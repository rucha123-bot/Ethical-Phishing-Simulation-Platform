import sqlite3

# Connect to the SQLite database (it will be created if it doesn't exist)
conn = sqlite3.connect('phishing.db')
cursor = conn.cursor()

# --- Create campaigns table ---
# Stores information about each phishing campaign
cursor.execute('''
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    template_name TEXT NOT NULL,
    target_emails TEXT NOT NULL, -- Comma-separated list of emails
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# --- Create results table ---
# Tracks the outcome for each email sent
cursor.execute('''
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    tracking_id TEXT NOT NULL UNIQUE, -- Unique ID for tracking link and pixel
    target_email TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    opened_at TIMESTAMP NULL,
    clicked_at TIMESTAMP NULL,
    submitted_at TIMESTAMP NULL,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
)
''')

print("Database 'phishing.db' initialized successfully.")

# Commit changes and close the connection
conn.commit()
conn.close()
