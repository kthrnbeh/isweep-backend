import sqlite3

db = sqlite3.connect('isweep.db')
cursor = db.cursor()

# Check current schema
cursor.execute("PRAGMA table_info(preferences)")
columns = cursor.fetchall()
print('Current columns in preferences table:')
for col in columns:
    print(f'  {col[1]} ({col[2]})')

print('\nAdding missing columns...')

# Add missing columns if they don't exist
try:
    cursor.execute("ALTER TABLE preferences ADD COLUMN selected_packs TEXT DEFAULT '{}'")
    print('✓ Added selected_packs column')
except sqlite3.OperationalError as e:
    print(f'selected_packs: {e}')

try:
    cursor.execute("ALTER TABLE preferences ADD COLUMN custom_words TEXT DEFAULT '[]'")
    print('✓ Added custom_words column')
except sqlite3.OperationalError as e:
    print(f'custom_words: {e}')

db.commit()
db.close()
print('\n✓ Database updated successfully!')
