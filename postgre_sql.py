import psycopg2
import psycopg2.extras
import os

# Function to get database connection
def get_connection():
    return psycopg2.connect(
        dbname="glossary_db",
        user="glossary_user",
        password="glossary_pass",
        host= "glossary-postgres" if os.getenv("ENV") == "production" else "localhost",
        port=5432
    )

# Function to check if a source text already exists
def check_duplicate(source_text, source_lang='english', target_lang='chinese'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM glossary WHERE source_text = %s AND source_lang = %s AND target_lang = %s", (source_text, source_lang, target_lang))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

# Function to insert a new translation
def insert_translation(source_text, source_lang, target_text, target_lang):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO glossary (source_text, source_lang, target_text, target_lang)
    VALUES (%s, %s, %s, %s)
    """, (source_text, source_lang, target_text, target_lang))
    conn.commit()
    cur.close()
    conn.close()

# Function to get translation if exists
def get_translation(source_text, source_lang='english', target_lang='chinese'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT target_text FROM glossary WHERE source_text = %s AND source_lang = %s AND target_lang = %s", (source_text, source_lang, target_lang))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def insert_text_nouns(text_hash, source_lang, nouns_list):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO text_nouns (hash, source_lang, nouns)
    VALUES (%s, %s, %s)
    ON CONFLICT (hash, source_lang) DO NOTHING
    """, (text_hash, source_lang, psycopg2.extras.Json(nouns_list)))
    conn.commit()
    cur.close()
    conn.close()

def get_text_nouns(text_hash, source_lang):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nouns FROM text_nouns WHERE hash = %s AND source_lang = %s", (text_hash, source_lang))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def ensure_count_column():
    """Ensure the glossary table has a count column with default 0."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE glossary ADD COLUMN IF NOT EXISTS count INTEGER DEFAULT 0;")
        conn.commit()
    finally:
        cur.close()
        conn.close()

def increment_term_count(source_text: str, source_lang: str, target_lang: str) -> int:
    """Increment usage count for a single term if it exists. Returns affected rows."""
    ensure_count_column()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE glossary SET count = COALESCE(count, 0) + 1 WHERE source_text = %s AND source_lang = %s AND target_lang = %s",
            (source_text, source_lang, target_lang),
        )
        affected = cur.rowcount or 0
        conn.commit()
        return affected
    finally:
        cur.close()
        conn.close()

def increment_terms_count(tokens: list[str], source_lang: str, target_lang: str) -> int:
    """Bulk increment usage count for a list of terms. Returns total attempted updates."""
    if not tokens:
        return 0
    ensure_count_column()
    conn = get_connection()
    cur = conn.cursor()
    try:
        params = [(t, source_lang, target_lang) for t in tokens]
        psycopg2.extras.execute_batch(
            cur,
            "UPDATE glossary SET count = COALESCE(count, 0) + 1 WHERE source_text = %s AND source_lang = %s AND target_lang = %s",
            params,
            page_size=min(100, len(params))
        )
        conn.commit()
        # rowcount after execute_batch may reflect last statement; we return number of tokens instead
        return len(tokens)
    finally:
        cur.close()
        conn.close()

def find_terms_in_text(text: str, source_lang: str = 'english', target_lang: str = 'chinese'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT source_text, target_text, source_type FROM glossary WHERE POSITION(source_text IN %s) > 0 AND source_lang = %s AND target_lang = %s", (text, source_lang, target_lang))
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result

def find_similar_words(word: str, source_lang: str = 'english', target_lang: str = 'chinese', similarity_threshold: float = 0.8):
    """Find similar words in the glossary using similarity matching"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Use ILIKE for case-insensitive partial matching and similarity for fuzzy matching
    # PostgreSQL similarity function requires pg_trgm extension

    cur.execute("""
    SELECT source_text, target_text, similarity(source_text, %s) as sim 
    FROM glossary 
    WHERE source_lang = %s AND target_lang = %s 
    AND (source_text ILIKE %s OR similarity(source_text, %s) > %s)
    ORDER BY sim DESC
    LIMIT 5
    """, (word, source_lang, target_lang, f'%{word}%', word, similarity_threshold))
    result = cur.fetchall()
    
    cur.close()
    conn.close()
    return result

if __name__ == "__main__":
    print(find_terms_in_text("本发明公开了一种马桶防漏水干湿分离机构，包括马桶主体和接水盘，所述马桶主体的上部设有便盆，该便盆的底部具有排泄通道，所述接水盘能够水平方向转动地安装在马桶主体上，从而使接水盘能够沿水平方向在位于排泄通道正下方的第一位置和位于排泄通道以外的第二位置之间来回转动，还包括安装在接水盘和/或排泄通道上的防漏水结构。", "chinese"))