import streamlit as st
import pandas as pd
from datetime import date, timedelta
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db import get_conn
from utils.helpers import format_rupiah, get_minggu_dari_tanggal

st.set_page_config(page_title="Gaji Karyawan - Tempe Pak Yitno", page_icon="👷", layout="wide")
st.title("👷 Gaji Karyawan")

tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Absensi Harian", "💵 Kalkulasi Gaji Mingguan",
    "📋 Riwayat Pembayaran", "⚙️ Kelola Karyawan"
])


# TAB 1 – Absensi Harian
with tab1:
    st.subheader("Catat Absensi Harian")
    tgl_absen = st.date_input("Tanggal", value=date.today(), key="tgl_absen")
    tgl_absen_str = tgl_absen.isoformat()

    conn = get_conn()
    df_kar = pd.read_sql("SELECT * FROM karyawan WHERE aktif=1 ORDER BY nama", conn)
    df_abs_existing = pd.read_sql(
        "SELECT karyawan_id, hadir FROM absensi WHERE tanggal=?",
        conn, params=(tgl_absen_str,)
    )
    conn.close()

    if df_kar.empty:
        st.warning("Belum ada data karyawan. Tambahkan di tab **Kelola Karyawan**.")
    else:
        existing_dict = {}
        if not df_abs_existing.empty:
            existing_dict = dict(zip(df_abs_existing["karyawan_id"], df_abs_existing["hadir"]))

        absen_data = {}
        st.markdown("Centang karyawan yang **hadir** hari ini:")
        cols_per_row = 3
        rows = [df_kar.iloc[i:i+cols_per_row] for i in range(0, len(df_kar), cols_per_row)]
        for row_group in rows:
            cols = st.columns(cols_per_row)
            for idx, (_, kar) in enumerate(row_group.iterrows()):
                default_hadir = bool(existing_dict.get(kar["id"], 1))
                hadir = cols[idx].checkbox(
                    f"**{kar['nama']}**\n_{format_rupiah(kar['gaji_harian'])}/hari_",
                    value=default_hadir,
                    key=f"abs_{kar['id']}_{tgl_absen_str}"
                )
                absen_data[kar["id"]] = hadir

        hadir_count = sum(1 for v in absen_data.values() if v)
        st.info(f"Hadir: **{hadir_count}** / {len(df_kar)} karyawan")

        if st.button("💾 Simpan Absensi", type="primary"):
            conn = get_conn()
            for kar_id, hadir in absen_data.items():
                conn.execute(
                    """INSERT INTO absensi (karyawan_id, tanggal, hadir)
                       VALUES (?,?,?)
                       ON CONFLICT(karyawan_id, tanggal) DO UPDATE SET hadir=excluded.hadir""",
                    (kar_id, tgl_absen_str, 1 if hadir else 0)
                )
            conn.commit(); conn.close()
            st.success(f"✅ Absensi {tgl_absen.strftime('%d %B %Y')} berhasil disimpan!")



# TAB 2 – Kalkulasi Gaji Mingguan
with tab2:
    st.subheader("Kalkulasi & Pembayaran Gaji Mingguan")

    # Pilih rentang minggu
    tgl_ref = st.date_input("Pilih tanggal dalam minggu yang ingin dihitung:",
                             value=date.today(), key="tgl_gaji")
    senin_gaji, minggu_gaji = get_minggu_dari_tanggal(tgl_ref)
    st.info(f"Periode: **{senin_gaji.strftime('%d %B')} – {minggu_gaji.strftime('%d %B %Y')}**")

    conn = get_conn()
    df_gaji_kal = pd.read_sql(
        """SELECT k.id, k.nama, k.gaji_harian,
                  SUM(CASE WHEN a.hadir=1 THEN 1 ELSE 0 END) as total_hadir
           FROM karyawan k
           LEFT JOIN absensi a ON k.id = a.karyawan_id
               AND a.tanggal BETWEEN ? AND ?
           WHERE k.aktif=1
           GROUP BY k.id, k.nama, k.gaji_harian""",
        conn,
        params=(senin_gaji.isoformat(), minggu_gaji.isoformat())
    )
    # Cek apakah sudah dibayar
    df_sudah_bayar = pd.read_sql(
        "SELECT karyawan_id FROM gaji_terbayar WHERE minggu_mulai=? AND status='sudah'",
        conn, params=(senin_gaji.isoformat(),)
    )
    conn.close()

    sudah_bayar_ids = set(df_sudah_bayar["karyawan_id"].tolist()) if not df_sudah_bayar.empty else set()

    if df_gaji_kal.empty:
        st.warning("Belum ada data karyawan.")
    else:
        df_gaji_kal["total_gaji"] = df_gaji_kal["total_hadir"] * df_gaji_kal["gaji_harian"]
        df_gaji_kal["status"]     = df_gaji_kal["id"].apply(
            lambda x: "✅ Sudah Dibayar" if x in sudah_bayar_ids else "❌ Belum Dibayar"
        )
        df_gaji_kal["gaji_fmt"]   = df_gaji_kal["total_gaji"].apply(format_rupiah)
        df_gaji_kal["gaji_h_fmt"] = df_gaji_kal["gaji_harian"].apply(format_rupiah)

        df_show_gaji = df_gaji_kal[["nama","gaji_h_fmt","total_hadir","gaji_fmt","status"]].copy()
        df_show_gaji.columns = ["Nama","Gaji/Hari","Hari Hadir","Total Gaji","Status"]
        st.dataframe(df_show_gaji, use_container_width=True, hide_index=True)

        total_gaji_minggu = int(df_gaji_kal["total_gaji"].sum())
        st.metric("💵 Total Gaji Minggu Ini", format_rupiah(total_gaji_minggu))

        belum_bayar = df_gaji_kal[~df_gaji_kal["id"].isin(sudah_bayar_ids)]
        if not belum_bayar.empty:
            st.markdown("---")
            bayar_ids = st.multiselect(
                "Pilih karyawan yang sudah dibayar:",
                options=belum_bayar["id"].tolist(),
                format_func=lambda x: df_gaji_kal[df_gaji_kal["id"]==x]["nama"].values[0]
            )
            if st.button("✅ Tandai Gaji Terbayar", type="primary", disabled=len(bayar_ids)==0):
                conn = get_conn()
                for kid in bayar_ids:
                    row_k = df_gaji_kal[df_gaji_kal["id"]==kid].iloc[0]
                    conn.execute(
                        """INSERT INTO gaji_terbayar
                           (karyawan_id, minggu_mulai, minggu_selesai, jumlah_hadir, total_gaji, tanggal_bayar, status)
                           VALUES (?,?,?,?,?,?,?)""",
                        (kid, senin_gaji.isoformat(), minggu_gaji.isoformat(),
                         int(row_k["total_hadir"]), int(row_k["total_gaji"]),
                         date.today().isoformat(), "sudah")
                    )
                    # Catat ke keuangan
                    conn.execute(
                        "INSERT INTO keuangan (tanggal, jenis, kategori, keterangan, jumlah) VALUES (?,?,?,?,?)",
                        (date.today().isoformat(), "pengeluaran", "Gaji Karyawan",
                         f"Gaji {row_k['nama']} minggu {senin_gaji.strftime('%d/%m')}-{minggu_gaji.strftime('%d/%m')}",
                         int(row_k["total_gaji"]))
                    )
                conn.commit(); conn.close()
                st.success(f"✅ Gaji {len(bayar_ids)} karyawan berhasil dicatat!")
                st.rerun()
        else:
            st.success("✅ Semua karyawan sudah dibayar minggu ini!")


# TAB 3 – Riwayat Pembayaran Gaji
with tab3:
    st.subheader("Riwayat Pembayaran Gaji")
    conn = get_conn()
    df_riwayat_gaji = pd.read_sql(
        """SELECT g.*, k.nama FROM gaji_terbayar g
           JOIN karyawan k ON g.karyawan_id = k.id
           ORDER BY g.minggu_mulai DESC, k.nama""",
        conn
    )
    conn.close()
    if df_riwayat_gaji.empty:
        st.info("Belum ada riwayat pembayaran gaji.")
    else:
        df_rg = df_riwayat_gaji[["nama","minggu_mulai","minggu_selesai",
                                   "jumlah_hadir","total_gaji","tanggal_bayar","status"]].copy()
        df_rg["total_gaji"] = df_rg["total_gaji"].apply(format_rupiah)
        df_rg.columns = ["Nama","Minggu Mulai","Minggu Selesai","Hadir (hari)","Total Gaji","Tgl Bayar","Status"]
        st.dataframe(df_rg, use_container_width=True, hide_index=True)

        # Total per karyawan
        st.markdown("---")
        st.markdown("#### Total Gaji Per Karyawan (Semua Waktu)")
        df_total_kar = df_riwayat_gaji.groupby("nama")["total_gaji"].sum().reset_index()
        df_total_kar["total_gaji"] = df_total_kar["total_gaji"].apply(format_rupiah)
        df_total_kar.columns = ["Nama","Total Gaji Terbayar"]
        st.dataframe(df_total_kar, use_container_width=True, hide_index=True)

# TAB 4 – Kelola Karyawan
with tab4:
    st.subheader("Data Karyawan")
    conn = get_conn()
    df_all_kar = pd.read_sql("SELECT * FROM karyawan ORDER BY nama", conn)
    conn.close()

    if not df_all_kar.empty:
        df_show_kar = df_all_kar[["nama","gaji_harian","aktif"]].copy()
        df_show_kar["gaji_harian"] = df_show_kar["gaji_harian"].apply(format_rupiah)
        df_show_kar["aktif"] = df_show_kar["aktif"].map({1:"✅ Aktif", 0:"❌ Non-aktif"})
        df_show_kar.columns = ["Nama","Gaji Harian","Status"]
        st.dataframe(df_show_kar, use_container_width=True, hide_index=True)

    st.markdown("---")
    col_tambah, col_edit = st.columns(2)

    with col_tambah:
        st.markdown("#### ➕ Tambah Karyawan")
        with st.form("form_tambah_kar", clear_on_submit=True):
            nm_kar  = st.text_input("Nama Karyawan")
            gj_kar  = st.number_input("Gaji Harian (Rp)", min_value=0, step=5000, value=50000)
            if st.form_submit_button("➕ Tambah"):
                if nm_kar.strip():
                    conn = get_conn()
                    try:
                        conn.execute(
                            "INSERT INTO karyawan (nama, gaji_harian) VALUES (?,?)",
                            (nm_kar.strip(), gj_kar)
                        )
                        conn.commit()
                        st.success(f"Karyawan {nm_kar} berhasil ditambahkan!")
                        st.rerun()
                    except:
                        st.error("Nama sudah ada!")
                    finally:
                        conn.close()
                else:
                    st.error("Nama tidak boleh kosong!")

    with col_edit:
        st.markdown("#### ✏️ Edit Karyawan")
        if not df_all_kar.empty:
            kar_pilih = st.selectbox("Pilih karyawan:", df_all_kar["nama"].tolist(), key="kar_edit_sel")
            if kar_pilih:
                row_ke = df_all_kar[df_all_kar["nama"]==kar_pilih].iloc[0]
                gj_baru = st.number_input("Gaji Harian Baru",
                                           value=int(row_ke["gaji_harian"]),
                                           min_value=0, step=5000, key="gj_baru")
                aktif_baru = st.toggle("Aktif", value=bool(row_ke["aktif"]), key="aktif_toggle")
                if st.button("💾 Simpan Edit"):
                    conn = get_conn()
                    conn.execute(
                        "UPDATE karyawan SET gaji_harian=?, aktif=? WHERE nama=?",
                        (gj_baru, 1 if aktif_baru else 0, kar_pilih)
                    )
                    conn.commit(); conn.close()
                    st.success("Data karyawan diperbarui!")
                    st.rerun()
