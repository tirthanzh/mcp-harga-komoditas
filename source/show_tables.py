from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlite3 import Connection


def show_all_tables(conn: "Connection"):
    c = conn.cursor()
    
    # Menambahkan filter untuk mengabaikan shadow tables FTS5
    # Serta mengabaikan tabel internal sqlite
    query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        AND name NOT LIKE '%_config'
        AND name NOT LIKE '%_idx'
        AND name NOT LIKE '%_data'
        AND name NOT LIKE '%_content'
        AND name NOT LIKE '%_docsize'
        AND name NOT LIKE '%_segments'
    """
    
    c.execute(query)
    tables = [row[0] for row in c.fetchall()]

    if not tables:
        print("Database kosong atau hanya berisi tabel internal.")
        return

    for table_name in tables:
        print(f"\n[ TABLE: {table_name} ]")
        
        c.execute(f"PRAGMA table_info({table_name});")
        columns_info = c.fetchall()
        column_names = [col[1] for col in columns_info]
        
        # Print Header
        print("\t".join(column_names))
        print("-" * (len(column_names) * 15)) 
        
        c.execute(f"SELECT * FROM {table_name}")
        rows = c.fetchall()
        
        for row in rows:
            # Join dengan tab, handle None/Null
            print("\t".join(str(v) if v is not None else "NULL" for v in row))
            
    c.close()