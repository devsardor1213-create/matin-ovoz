"""
Bot database ni to'liq tozalash va yangidan boshlash uchun script.
Bu faylni bir marta ishga tushiring, keyin o'chirishingiz mumkin.
"""
import sqlite3
import os

print("=" * 50)
print("  BOT DATABASE RESET QILINMOQDA...")
print("=" * 50)

# --- bot_data.db ni tozalash ---
conn = sqlite3.connect('bot_data.db')
c = conn.cursor()

# Barcha kanallarni o'chirish
c.execute("DELETE FROM channels")
print(f"✅ Channels jadvali tozalandi")

# Barcha active adminlarni o'chirish (faqat asosiy admin qoladi)
c.execute("DELETE FROM active_admins")
print(f"✅ Active admins tozalandi")

# Foydalanuvchilarni o'chirish (ixtiyoriy)
c.execute("SELECT COUNT(*) FROM users")
user_count = c.fetchone()[0]
c.execute("DELETE FROM users")
print(f"✅ {user_count} ta foydalanuvchi o'chirildi")

conn.commit()
conn.close()

# --- users.db ni tozalash ---
if os.path.exists('users.db'):
    conn2 = sqlite3.connect('users.db')
    c2 = conn2.cursor()
    # Barcha jadvallarni ko'rish va tozalash
    c2.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c2.fetchall()
    for (table_name,) in tables:
        c2.execute(f"DELETE FROM {table_name}")
        print(f"✅ users.db/{table_name} tozalandi")
    conn2.commit()
    conn2.close()

# --- database.db ni tozalash ---
if os.path.exists('database.db'):
    conn3 = sqlite3.connect('database.db')
    c3 = conn3.cursor()
    c3.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c3.fetchall()
    for (table_name,) in tables:
        c3.execute(f"DELETE FROM {table_name}")
        print(f"✅ database.db/{table_name} tozalandi")
    conn3.commit()
    conn3.close()

print("\n" + "=" * 50)
print("  ✅ HAMMASI TOZALANDI! BOT YANGI BOSHLAYDI.")
print("=" * 50)
