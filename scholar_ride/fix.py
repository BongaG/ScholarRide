import sqlite3
conn = sqlite3.connect('instance/scholarride.db')
conn.execute('UPDATE user SET session_token = NULL')
conn.commit()
conn.close()
print('Done!')