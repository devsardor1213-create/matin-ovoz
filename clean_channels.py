import sqlite3

conn = sqlite3.connect('bot_data.db')
c = conn.cursor()

# Barcha kanallarni ko'rish
c.execute("SELECT * FROM channels")
channels = c.fetchall()
print("Mavjud kanallar:")
for ch in channels:
    print(f"  ID: {ch[0]}, channel_id: {ch[1]}, url: {ch[2]}")

# Begona kanallarni o'chirish
c.execute("DELETE FROM channels")
conn.commit()

print("\n✅ Barcha begona kanallar o'chirildi!")
print("Endi /start bosganida kanal talab qilinmaydi.")

conn.close()
