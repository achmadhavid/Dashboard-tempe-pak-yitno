from datetime import date, timedelta

HARGA = {
    "bulat": 800,
    "kecil": 200,
    "kotak": 300,
}

def hitung_total(bulat: int, kecil: int, kotak: int) -> int:
    return bulat * HARGA["bulat"] + kecil * HARGA["kecil"] + kotak * HARGA["kotak"]

def format_rupiah(angka: int) -> str:
    return f"Rp {angka:,.0f}".replace(",", ".")

def get_minggu_ini():
    hari_ini = date.today()
    senin = hari_ini - timedelta(days=hari_ini.weekday())
    minggu = senin + timedelta(days=6)
    return senin, minggu

def get_minggu_dari_tanggal(tgl: date):
    senin = tgl - timedelta(days=tgl.weekday())
    minggu = senin + timedelta(days=6)
    return senin, minggu

def status_bayar_badge(status: str) -> str:
    mapping = {
        "sudah": "✅ Lunas",
        "belum": "❌ Belum",
        "cicilan": "🔄 Cicilan",
    }
    return mapping.get(status, status)
