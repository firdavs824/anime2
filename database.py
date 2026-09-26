import aiosqlite
from typing import Optional, List, Dict, Any
from config import DB_PATH, ENV_ADMIN_IDS


async def init_db():
    """Ma'lumotlar bazasi jadvallarini yaratish."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                is_admin INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS animes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                genre TEXT DEFAULT 'Jangovar',
                views_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Agarda avvalgi bazada genre ustuni bo'lmasa, qo'shib qo'yamiz
        try:
            await db.execute("ALTER TABLE animes ADD COLUMN genre TEXT DEFAULT 'Jangovar'")
        except Exception:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS anime_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime_id INTEGER NOT NULL,
                episode_num INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT DEFAULT 'video',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(anime_id, episode_num),
                FOREIGN KEY (anime_id) REFERENCES animes(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Majburiy kanallar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT NOT NULL,
                channel_link TEXT NOT NULL
            )
        """)
        # Sevimlilar (Bookmarks) jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                anime_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, anime_id)
            )
        """)
        # Anime kuzatuvchilari (Yangi qism bildirishnomalari uchun)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS anime_subscriptions (
                user_id INTEGER NOT NULL,
                anime_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, anime_id)
            )
        """)
        # Reytinglar jadvali (1-5 yulduz)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER NOT NULL,
                anime_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                PRIMARY KEY (user_id, anime_id)
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_anime_code ON animes(code)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_episodes_anime_id ON anime_episodes(anime_id)")
        await db.commit()


async def get_setting(key: str, default: str = "") -> str:
    """Sozlama qiymatini olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] is not None else default


async def set_setting(key: str, value: str):
    """Sozlama qiymatini saqlash."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))
        await db.commit()



async def add_or_update_user(user_id: int, username: Optional[str], full_name: str):
    """Foydalanuvchini bazaga qo'shish yoki yangilash."""
    async with aiosqlite.connect(DB_PATH) as db:
        is_initial_admin = 1 if user_id in ENV_ADMIN_IDS else 0
        await db.execute("""
            INSERT INTO users (user_id, username, full_name, is_admin)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                is_admin = CASE WHEN users.is_admin = 1 THEN 1 ELSE excluded.is_admin END
        """, (user_id, username, full_name, is_initial_admin))
        await db.commit()


async def is_user_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish."""
    if user_id in ENV_ADMIN_IDS:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return bool(row and row[0] == 1)


async def set_user_admin(user_id: int, status: bool = True):
    """Foydalanuvchiga adminlik huquqini berish yoki olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, full_name, is_admin)
            VALUES (?, 'Admin', ?)
            ON CONFLICT(user_id) DO UPDATE SET is_admin = ?
        """, (user_id, 1 if status else 0, 1 if status else 0))
        await db.commit()


async def get_all_admins() -> List[int]:
    """Barcha adminlar ID ro'yxati."""
    admins = set(ENV_ADMIN_IDS)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE is_admin = 1")
        rows = await cursor.fetchall()
        for r in rows:
            admins.add(r[0])
    return list(admins)


async def get_users_count() -> int:
    """Foydalanuvchilar soni."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_all_user_ids() -> List[int]:
    """Barcha foydalanuvchilar ID lari (xabar yuborish uchun)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


# ================== ANIME VA QISMLAR FUNKSIYALARI ==================

def normalize_code(code: str) -> str:
    """Kodni bir xil ko'rinishga keltirish (kichik harf, bo'sh joylarsiz)."""
    return str(code).strip().lower()


async def add_or_get_anime(code: str, title: str, description: str = "") -> int:
    """Anime yaratish yoki mavjud bo'lsa ID sini qaytarish."""
    norm_code = normalize_code(code)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM animes WHERE code = ?", (norm_code,))
        row = await cursor.fetchone()
        if row:
            return row[0]

        cursor = await db.execute("""
            INSERT INTO animes (code, title, description)
            VALUES (?, ?, ?)
        """, (norm_code, title.strip(), description.strip()))
        await db.commit()
        return cursor.lastrowid


async def add_episode(anime_id: int, episode_num: int, file_id: str, file_type: str = "video") -> bool:
    """Animega qism qo'shish yoki yangilash."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO anime_episodes (anime_id, episode_num, file_id, file_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(anime_id, episode_num) DO UPDATE SET
                file_id = excluded.file_id,
                file_type = excluded.file_type
        """, (anime_id, episode_num, file_id, file_type))
        await db.commit()
        return True


async def check_code_exists(code: str) -> bool:
    """Ushbu kod mavjudligini tekshirish."""
    norm_code = normalize_code(code)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM animes WHERE code = ?", (norm_code,))
        row = await cursor.fetchone()
        return row is not None


async def get_anime_by_code(code: str, increment_views: bool = True) -> Optional[Dict[str, Any]]:
    """Kod orqali anime ma'lumotlarini olish."""
    norm_code = normalize_code(code)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM animes WHERE code = ?", (norm_code,))
        row = await cursor.fetchone()
        if row:
            anime = dict(row)
            if increment_views:
                await db.execute("UPDATE animes SET views_count = views_count + 1 WHERE id = ?", (anime["id"],))
                await db.commit()
                anime["views_count"] += 1
            return anime
        return None


async def get_anime_by_id(anime_id: int) -> Optional[Dict[str, Any]]:
    """ID orqali anime olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM animes WHERE id = ?", (anime_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_anime_episodes(anime_id: int) -> List[Dict[str, Any]]:
    """Animening barcha qismlarini o'sish tartibida olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT id, anime_id, episode_num, file_id, file_type, created_at
            FROM anime_episodes
            WHERE anime_id = ?
            ORDER BY episode_num ASC
        """, (anime_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_episode(anime_id: int, episode_num: int) -> Optional[Dict[str, Any]]:
    """Animening ma'lum bir qismini olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM anime_episodes
            WHERE anime_id = ? AND episode_num = ?
        """, (anime_id, episode_num))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_max_episode_num(anime_id: int) -> int:
    """Animedagi eng oxirgi (eng katta) qism raqamini olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT MAX(episode_num) FROM anime_episodes WHERE anime_id = ?", (anime_id,))
        row = await cursor.fetchone()
        return (row[0] or 0) if row else 0


async def delete_anime_by_code(code: str) -> bool:
    """Kodi bo'yicha animeni va uning barcha qismlarini o'chirish."""
    norm_code = normalize_code(code)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM animes WHERE code = ?", (norm_code,))
        row = await cursor.fetchone()
        if not row:
            return False
        anime_id = row[0]
        await db.execute("DELETE FROM anime_episodes WHERE anime_id = ?", (anime_id,))
        await db.execute("DELETE FROM animes WHERE id = ?", (anime_id,))
        await db.commit()
        return True


async def delete_anime_by_id(anime_id: int) -> bool:
    """ID bo'yicha animeni va qismlarini o'chirish."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM anime_episodes WHERE anime_id = ?", (anime_id,))
        cursor = await db.execute("DELETE FROM animes WHERE id = ?", (anime_id,))
        await db.commit()
        return cursor.rowcount > 0


async def delete_episode(anime_id: int, episode_num: int) -> bool:
    """Alohida bitta qismni o'chirish."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM anime_episodes WHERE anime_id = ? AND episode_num = ?",
            (anime_id, episode_num)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_animes_count() -> int:
    """Jami animelar soni."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM animes")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_total_episodes_count() -> int:
    """Jami yuklangan qismlar soni."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM anime_episodes")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_total_views() -> int:
    """Barcha animelarning jami ko'rishlar soni."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT SUM(views_count) FROM animes")
        row = await cursor.fetchone()
        return (row[0] or 0) if row else 0


async def get_all_animes(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Animelar ro'yxatini qismlar soni bilan birga olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT 
                a.id, a.code, a.title, a.views_count, a.created_at,
                COUNT(e.id) AS episodes_count
            FROM animes a
            LEFT JOIN anime_episodes e ON a.id = e.anime_id
            GROUP BY a.id
            ORDER BY a.id DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def search_animes(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Nomi yoki kodi bo'yicha qidirish."""
    q = f"%{query.strip().lower()}%"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT 
                a.id, a.code, a.title, a.views_count,
                COUNT(e.id) AS episodes_count
            FROM animes a
            LEFT JOIN anime_episodes e ON a.id = e.anime_id
            WHERE LOWER(a.title) LIKE ? OR LOWER(a.code) LIKE ?
            GROUP BY a.id
            ORDER BY a.views_count DESC
            LIMIT ?
        """, (q, q, limit))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_random_anime() -> Optional[Dict[str, Any]]:
    """Tasodifiy bitta anime olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM animes ORDER BY RANDOM() LIMIT 1")
        row = await cursor.fetchone()
        return dict(row) if row else None


# ================== MAJBURIY KANALLAR FUNKSIYALARI ==================

async def add_channel(channel_id: str, channel_name: str, channel_link: str) -> bool:
    """Majburiy kanal qo'shish."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO channels (channel_id, channel_name, channel_link)
            VALUES (?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                channel_name = excluded.channel_name,
                channel_link = excluded.channel_link
        """, (str(channel_id).strip(), channel_name.strip(), channel_link.strip()))
        await db.commit()
        return True


async def remove_channel_by_id(channel_db_id: int) -> bool:
    """Kanalni o'chirish."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM channels WHERE id = ?", (channel_db_id,))
        await db.commit()
        return cursor.rowcount > 0


async def get_all_channels() -> List[Dict[str, Any]]:
    """Barcha majburiy kanallarni olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM channels ORDER BY id ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ================== SEVIMLILAR (BOOKMARKS) FUNKSIYALARI ==================

async def toggle_favorite(user_id: int, anime_id: int) -> bool:
    """Anime ni sevimlilarga qo'shish yoki o'chirish. Qo'shilsa True, o'chirilsa False qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
        if await cursor.fetchone():
            await db.execute("DELETE FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
            await db.commit()
            return False
        else:
            await db.execute("INSERT INTO favorites (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id))
            await db.commit()
            return True


async def is_favorite(user_id: int, anime_id: int) -> bool:
    """Anime foydalanuvchining sevimlilarida bor-yo'qligi."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM favorites WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
        return (await cursor.fetchone()) is not None


async def get_user_favorites(user_id: int) -> List[Dict[str, Any]]:
    """Foydalanuvchining sevimlilar ro'yxatini olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT a.*, COUNT(e.id) as episodes_count
            FROM favorites f
            JOIN animes a ON f.anime_id = a.id
            LEFT JOIN anime_episodes e ON a.id = e.anime_id
            WHERE f.user_id = ?
            GROUP BY a.id
            ORDER BY f.created_at DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ================== BILDIRISHNOMA KUZATUVCHILARI ==================

async def toggle_anime_subscription(user_id: int, anime_id: int) -> bool:
    """Anime yangiliklariga obuna bo'lish/o'chirish. Obuna bo'lsa True qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM anime_subscriptions WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
        if await cursor.fetchone():
            await db.execute("DELETE FROM anime_subscriptions WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
            await db.commit()
            return False
        else:
            await db.execute("INSERT INTO anime_subscriptions (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id))
            await db.commit()
            return True


async def is_anime_subscribed(user_id: int, anime_id: int) -> bool:
    """Anime bildirishnomasiga obuna bor-yo'qligi."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM anime_subscriptions WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
        return (await cursor.fetchone()) is not None


async def get_anime_subscribers(anime_id: int) -> List[int]:
    """Animega obuna bo'lgan foydalanuvchilar ID ro'yxati."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM anime_subscriptions WHERE anime_id = ?", (anime_id,))
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


# ================== REYTING TIZIMI ==================

async def add_rating(user_id: int, anime_id: int, rating: int) -> bool:
    """Animega 1-5 yulduzli baho berish."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO ratings (user_id, anime_id, rating) VALUES (?, ?, ?)
            ON CONFLICT(user_id, anime_id) DO UPDATE SET rating = excluded.rating
        """, (user_id, anime_id, max(1, min(5, rating))))
        await db.commit()
        return True


async def get_anime_rating_stats(anime_id: int) -> Dict[str, Any]:
    """Animening o'rtacha bahosi va ovozlar soni."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT AVG(rating), COUNT(*) FROM ratings WHERE anime_id = ?", (anime_id,))
        row = await cursor.fetchone()
        avg_rating = round(row[0], 1) if row and row[0] is not None else 0.0
        votes_count = row[1] if row else 0
        return {"avg_rating": avg_rating, "votes_count": votes_count}


async def get_top_rated_animes(limit: int = 10) -> List[Dict[str, Any]]:
    """Eng yuqori baholangan Top Animelar."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT 
                a.*,
                AVG(r.rating) AS avg_rating,
                COUNT(r.user_id) AS votes_count,
                COUNT(e.id) AS episodes_count
            FROM animes a
            LEFT JOIN ratings r ON a.id = r.anime_id
            LEFT JOIN anime_episodes e ON a.id = e.anime_id
            GROUP BY a.id
            HAVING votes_count > 0
            ORDER BY avg_rating DESC, votes_count DESC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ================== JANRLAR FUNKSIYASI ==================

async def get_animes_by_genre(genre: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """Janr bo'yicha animelarni olish."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT a.*, COUNT(e.id) AS episodes_count
            FROM animes a
            LEFT JOIN anime_episodes e ON a.id = e.anime_id
            WHERE LOWER(a.genre) LIKE ?
            GROUP BY a.id
            ORDER BY a.id DESC
            LIMIT ? OFFSET ?
        """, (f"%{genre.lower()}%", limit, offset))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

