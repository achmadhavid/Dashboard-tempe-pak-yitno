import streamlit as st
import pandas as pd
from datetime import date
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from database.db import init_db, seed_pelanggan, seed_karyawan, get_conn
from utils.helpers import format_rupiah

st.set_page_config(
    page_title="Dashboard Tempe Pak Yitno",
    page_icon="🫘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Inisialisasi database ──────────────────────────────────────────────────
init_db()
seed_pelanggan()
seed_karyawan()

# ── CSS kustom ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 18px 20px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 10px;
    }
    .metric-card.orange { border-left-color: #FF9800; }
    .metric-card.red    { border-left-color: #F44336; }
    .metric-card.blue   { border-left-color: #2196F3; }
    .metric-label { font-size: 13px; color: #666; margin-bottom: 4px; }
    .metric-value { font-size: 24px; font-weight: 700; color: #212121; }
    .metric-sub   { font-size: 12px; color: #999; margin-top: 2px; }
    .stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────
st.title("🫘 Dashboard Pabrik Tempe Pak Yitno")
st.markdown(f"**{date.today().strftime('%A, %d %B %Y')}** &nbsp;|&nbsp; Selamat datang!")
st.divider()

# ── KPI Hari Ini ───────────────────────────────────────────────────────────
today_str = date.today().isoformat()
conn = get_conn()

# Total pesanan hari ini
df_pesanan = pd.read_sql(
    "SELECT * FROM pesanan WHERE tanggal = ?", conn, params=(today_str,)
)
total_pesanan_hari = len(df_pesanan)
total_pcs_bulat    = int(df_pesanan["bulat"].sum()) if not df_pesanan.empty else 0
total_pcs_kecil    = int(df_pesanan["kecil"].sum()) if not df_pesanan.empty else 0
total_pcs_kotak    = int(df_pesanan["kotak"].sum()) if not df_pesanan.empty else 0
total_omset_hari   = int(df_pesanan["total_harga"].sum()) if not df_pesanan.empty else 0
sudah_bayar        = len(df_pesanan[df_pesanan["status_bayar"] == "sudah"]) if not df_pesanan.empty else 0

# Total pengeluaran hari ini
df_keluar = pd.read_sql(
    "SELECT * FROM keuangan WHERE tanggal = ? AND jenis = 'pengeluaran'",
    conn, params=(today_str,)
)
total_keluar_hari = int(df_keluar["jumlah"].sum()) if not df_keluar.empty else 0

# Kontrak ampas aktif
df_ampas = pd.read_sql(
    "SELECT * FROM ampas_kontrak WHERE status = 'aktif' ORDER BY id DESC LIMIT 1",
    conn
)

# Total karyawan aktif
df_karyawan = pd.read_sql("SELECT * FROM karyawan WHERE aktif = 1", conn)
jml_karyawan = len(df_karyawan)

conn.close()

laba_hari = total_omset_hari - total_keluar_hari

# ── Baris KPI ─────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 Omset Hari Ini",
        value=format_rupiah(total_omset_hari),
        delta=f"{total_pesanan_hari} pelanggan hari ini"
    )

with col2:
    st.metric(
        label="📦 Total Produksi",
        value=f"{total_pcs_bulat + total_pcs_kecil + total_pcs_kotak} pcs",
        delta=f"Bulat: {total_pcs_bulat} | Kecil: {total_pcs_kecil} | Kotak: {total_pcs_kotak}"
    )

with col3:
    st.metric(
        label="💸 Pengeluaran Hari Ini",
        value=format_rupiah(total_keluar_hari),
        delta=format_rupiah(laba_hari) + " laba bersih",
        delta_color="normal" if laba_hari >= 0 else "inverse"
    )

with col4:
    st.metric(
        label="✅ Pembayaran Lunas",
        value=f"{sudah_bayar} / {total_pesanan_hari}",
        delta=f"{total_pesanan_hari - sudah_bayar} belum lunas"
    )

st.divider()

# ── Produksi Hari Ini ──────────────────────────────────────────────────────
col_l, col_r = st.columns([2, 1])

with col_l:
    st.subheader("📋 Rekap Pesanan Hari Ini")
    if df_pesanan.empty:
        st.info("Belum ada pesanan hari ini. Silakan input di menu **Pesanan**.")
    else:
        df_tampil = df_pesanan[["nama_pelanggan", "bulat", "kecil", "kotak",
                                 "total_harga", "status_bayar"]].copy()
        df_tampil["total_harga"] = df_tampil["total_harga"].apply(format_rupiah)
        df_tampil["status_bayar"] = df_tampil["status_bayar"].map(
            {"sudah": "✅ Lunas", "belum": "❌ Belum", "cicilan": "🔄 Cicilan"}
        )
        df_tampil.columns = ["Pelanggan", "Bulat", "Kecil", "Kotak", "Total", "Status"]
        st.dataframe(df_tampil, use_container_width=True, hide_index=True)

with col_r:
    st.subheader("🔔 Notifikasi")

    # Cek kontrak ampas
    if df_ampas.empty:
        st.warning("⚠️ Belum ada kontrak ampas aktif!")
    else:
        ampas = df_ampas.iloc[0]
        sisa_uang = int(ampas["sisa_uang"])
        total_uang = int(ampas["uang_kontrak"])
        persen = (sisa_uang / total_uang * 100) if total_uang > 0 else 0
        if persen <= 15:
            st.error(f"🚨 Kontrak ampas hampir habis!\nSisa: **{format_rupiah(sisa_uang)}** ({persen:.0f}%)")
        elif persen <= 30:
            st.warning(f"⚠️ Kontrak ampas tinggal {persen:.0f}%\nSisa: {format_rupiah(sisa_uang)}")
        else:
            st.success(f"✅ Stok ampas aman\nSisa: {format_rupiah(sisa_uang)} ({persen:.0f}%)")

    st.markdown("---")

    # Belum bayar
    belum = total_pesanan_hari - sudah_bayar
    if belum > 0:
        st.warning(f"💳 {belum} pelanggan belum bayar hari ini")
    else:
        if total_pesanan_hari > 0:
            st.success("💳 Semua pelanggan sudah bayar!")

    st.markdown("---")
    st.info(f"👷 Karyawan aktif: **{jml_karyawan} orang**")

# ── Navigasi Cepat ─────────────────────────────────────────────────────────
st.divider()
st.subheader("🗂️ Menu Cepat")
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.page_link("pages/1_Pesanan.py",      label="📋 Pesanan",     icon="📋")
with m2:
    st.page_link("pages/2_Keuangan.py",     label="💰 Keuangan",    icon="💰")
with m3:
    st.page_link("pages/3_Gaji_Karyawan.py",label="👷 Gaji",        icon="👷")
with m4:
    st.page_link("pages/4_Bahan_Baku.py",   label="🌾 Bahan Baku",  icon="🌾")
with m5:
    st.page_link("pages/5_Laporan.py",      label="📊 Laporan",     icon="📊")
