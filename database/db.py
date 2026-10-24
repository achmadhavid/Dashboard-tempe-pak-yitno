import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tempe.db")

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS pelanggan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL UNIQUE,
        bulat_default INTEGER DEFAULT 0,
        kecil_default INTEGER DEFAULT 0,
        kotak_default INTEGER DEFAULT 0,
        is_tetap INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS pesanan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL,
        pelanggan_id INTEGER,
        nama_pelanggan TEXT NOT NULL,
        bulat INTEGER DEFAULT 0,
        kecil INTEGER DEFAULT 0,
        kotak INTEGER DEFAULT 0,
        total_harga INTEGER DEFAULT 0,
        status_bayar TEXT DEFAULT 'belum',
        is_tetap INTEGER DEFAULT 1,
        catatan TEXT DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS keuangan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL,
        jenis TEXT NOT NULL,
        kategori TEXT NOT NULL,
        keterangan TEXT DEFAULT '',
        jumlah INTEGER NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS karyawan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL UNIQUE,
        gaji_harian INTEGER DEFAULT 0,
        aktif INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS absensi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        karyawan_id INTEGER NOT NULL,
        tanggal TEXT NOT NULL,
        hadir INTEGER DEFAULT 1,
        UNIQUE(karyawan_id, tanggal)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS gaji_terbayar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        karyawan_id INTEGER NOT NULL,
        minggu_mulai TEXT NOT NULL,
        minggu_selesai TEXT NOT NULL,
        jumlah_hadir INTEGER DEFAULT 0,
        total_gaji INTEGER DEFAULT 0,
        tanggal_bayar TEXT,
        status TEXT DEFAULT 'belum'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ampas_kontrak (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier TEXT NOT NULL,
        tanggal_mulai TEXT NOT NULL,
        uang_kontrak INTEGER NOT NULL DEFAULT 0,
        sisa_uang INTEGER NOT NULL DEFAULT 0,
        harga_per_ambil INTEGER DEFAULT 0,
        satuan TEXT DEFAULT 'karung',
        status TEXT DEFAULT 'aktif'
    )""")

    # Migrasi kolom baru jika tabel lama sudah ada
    for col_def in [
        "uang_kontrak INTEGER NOT NULL DEFAULT 0",
        "sisa_uang INTEGER NOT NULL DEFAULT 0",
        "harga_per_ambil INTEGER DEFAULT 0",
    ]:
        try:
            c.execute(f"ALTER TABLE ampas_kontrak ADD COLUMN {col_def}")
        except Exception:
            pass

    c.execute("""CREATE TABLE IF NOT EXISTS ampas_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kontrak_id INTEGER NOT NULL,
        tanggal TEXT NOT NULL,
        jumlah_ambil INTEGER NOT NULL,
        biaya_ambil INTEGER DEFAULT 0,
        keterangan TEXT DEFAULT ''
    )""")

    try:
        c.execute("ALTER TABLE ampas_log ADD COLUMN biaya_ambil INTEGER DEFAULT 0")
    except Exception:
        pass

    c.execute("""CREATE TABLE IF NOT EXISTS bahan_baku (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL,
        nama_bahan TEXT NOT NULL,
        jumlah INTEGER NOT NULL,
        satuan TEXT DEFAULT 'unit',
        harga_satuan INTEGER DEFAULT 0,
        total_harga INTEGER DEFAULT 0,
        keterangan TEXT DEFAULT ''
    )""")

    conn.commit()
    conn.close()

def seed_pelanggan():
    pelanggan_tetap = [
        ("Yono",        90,  0,   0),
        ("Pak Mukhtar", 120, 100, 288),
        ("Rofiq",       80,  200, 0),
        ("Saras",       500, 0,   0),
        ("Bandongan",   150, 0,   0),
        ("Mas No",      150, 0,   0),
        ("Marsih",      0,   150, 0),
        ("Sargo",       250, 0,   0),
        ("Sus",         300, 0,   0),
        ("Yuli",        250, 0,   0),
        ("Yeyen",       50,  0,   0),
        ("Iqbal",       50,  0,   0),
        ("Hartanti",    100, 30,  0),
        ("Rika",        50,  0,   0),
        ("Nur Tri",     25,  0,   0),
        ("Umi",         75,  0,   0),
        ("Pak Roto",    125, 0,   0),
        ("Pak Bero",    100, 0,   0),
        ("Jarkoni",     100, 0,   0),
    ]
    conn = get_conn()
    for p in pelanggan_tetap:
        conn.execute(
            "INSERT OR IGNORE INTO pelanggan (nama, bulat_default, kecil_default, kotak_default, is_tetap) VALUES (?,?,?,?,1)",
            p
        )
    conn.commit()
    conn.close()

def seed_karyawan():
    karyawan_default = [
        ("Pak Mono",  50000),
        ("Mbok Yah",  50000),
        ("Mbak Jum",  50000),
    ]
    conn = get_conn()
    for k in karyawan_default:
        conn.execute(
            "INSERT OR IGNORE INTO karyawan (nama, gaji_harian) VALUES (?,?)",
            k
        )
    conn.commit()
    conn.close()
