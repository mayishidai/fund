import sqlite3

DATABASE = "funds.db"

def migrate_db():
    """迁移数据库，添加 amount 列"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # 检查 amount 列是否存在
        cursor.execute("PRAGMA table_info(funds)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "amount" not in columns:
            # 添加 amount 列
            cursor.execute("ALTER TABLE funds ADD COLUMN amount REAL DEFAULT 0")
            print("成功添加 amount 列到 funds 表")
        else:
            print("amount 列已存在")
        
        conn.commit()
    except Exception as e:
        print(f"迁移失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
