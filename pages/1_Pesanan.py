import streamlit as st
import pandas as pd
from datetime import date
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db import get_conn
from utils.helpers import hitung_total, format_rupiah, HARGA

st.set_page_config(page_title="Pesanan - Tempe Pak Yitno", page_icon="📋", layout="wide")
st.title("📋 Pesanan & Pelanggan")

# ── Pilih Tanggal ──────────────────────────────────────────────────────────
col_tgl, col_info = st.columns([2, 3])
with col_tgl:
    tgl = st.date_input("📅 Tanggal Pesanan", value=date.today())
tgl_str = tgl.isoformat()

# ── Load pelanggan tetap ───────────────────────────────────────────────────
conn = get_conn()
df_pelanggan = pd.read_sql("SELECT * FROM pelanggan WHERE is_tetap=1 ORDER BY nama", conn)
df_pesanan   = pd.read_sql(
    "SELECT * FROM pesanan WHERE tanggal=? ORDER BY nama_pelanggan",
    conn, params=(tgl_str,)
)
conn.close()

with col_info:
    total_omset = int(df_pesanan["total_harga"].sum()) if not df_pesanan.empty else 0
    st.metric("Total Omset Hari Ini", format_rupiah(total_omset))

tab1, tab2, tab3 = st.tabs(["📥 Input Pesanan", "📊 Rekap Harian", "➕ Kelola Pelanggan"])

# ════════════════════════════════════════════════════════════════════
# TAB 1 – Input Pesanan
# ════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader(f"Input Pesanan – {tgl.strftime('%d %B %Y')}")

    # ── Muat default pelanggan tetap ───────────────────────────────
    col_btn1, col_btn2 = st.columns([2, 3])
    with col_btn1:
        if st.button("🔄 Muat Pesanan Default Pelanggan Tetap", type="primary"):
            conn = get_conn()
            # Hapus pesanan tetap yang sudah ada di tanggal ini, lalu isi ulang
            conn.execute("DELETE FROM pesanan WHERE tanggal=? AND is_tetap=1", (tgl_str,))
            for _, row in df_pelanggan.iterrows():
                total = hitung_total(
                    int(row["bulat_default"]),
                    int(row["kecil_default"]),
                    int(row["kotak_default"])
                )
                conn.execute(
                    """INSERT INTO pesanan
                       (tanggal, pelanggan_id, nama_pelanggan, bulat, kecil, kotak, total_harga, status_bayar, is_tetap)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (tgl_str, int(row["id"]), row["nama"],
                     int(row["bulat_default"]), int(row["kecil_default"]), int(row["kotak_default"]),
                     total, "belum", 1)
                )
            conn.commit(); conn.close()
            st.success("✅ Pesanan default berhasil dimuat!")
            st.rerun()

    # ── Edit pesanan yang sudah ada ────────────────────────────────
    conn = get_conn()
    df_pesanan = pd.read_sql(
        "SELECT * FROM pesanan WHERE tanggal=? ORDER BY is_tetap DESC, nama_pelanggan",
        conn, params=(tgl_str,)
    )
    conn.close()

    if not df_pesanan.empty:
        st.markdown("#### ✏️ Edit Pesanan Pelanggan")
        st.caption("Ubah jumlah dan status bayar, lalu klik Simpan Perubahan.")

        edited_data = []
        for _, row in df_pesanan.iterrows():
            with st.container():
                cols = st.columns([2, 1, 1, 1, 1, 2, 1])
                cols[0].markdown(f"**{row['nama_pelanggan']}**"
                                 + (" 🏷️" if row["is_tetap"] else " 🆕"))
                b = cols[1].number_input("Bulat",  value=int(row["bulat"]),
                                          min_value=0, key=f"b_{row['id']}")
                k = cols[2].number_input("Kecil",  value=int(row["kecil"]),
                                          min_value=0, key=f"k_{row['id']}")
                kt= cols[3].number_input("Kotak",  value=int(row["kotak"]),
                                          min_value=0, key=f"kt_{row['id']}")
                total_row = hitung_total(b, k, kt)
                cols[4].metric("Total", format_rupiah(total_row))
                status = cols[5].selectbox(
                    "Status",
                    ["belum", "sudah", "cicilan"],
                    index=["belum","sudah","cicilan"].index(row["status_bayar"]),
                    key=f"s_{row['id']}"
                )
                hapus = cols[6].checkbox("🗑️", key=f"del_{row['id']}")
                edited_data.append({
                    "id": row["id"], "bulat": b, "kecil": k, "kotak": kt,
                    "total_harga": total_row, "status_bayar": status, "hapus": hapus
                })
            st.divider()

        if st.button("💾 Simpan Perubahan", type="primary"):
            conn = get_conn()
            for item in edited_data:
                if item["hapus"]:
                    conn.execute("DELETE FROM pesanan WHERE id=?", (item["id"],))
                else:
                    conn.execute(
                        """UPDATE pesanan SET bulat=?, kecil=?, kotak=?,
                           total_harga=?, status_bayar=? WHERE id=?""",
                        (item["bulat"], item["kecil"], item["kotak"],
                         item["total_harga"], item["status_bayar"], item["id"])
                    )
            conn.commit(); conn.close()
            st.success("✅ Perubahan tersimpan!")
            st.rerun()
    else:
        st.info("Belum ada pesanan. Klik **Muat Pesanan Default** atau tambah manual di bawah.")

    # ── Tambah pesanan tidak tetap ─────────────────────────────────
    st.markdown("---")
    st.markdown("#### ➕ Tambah Pesanan Manual (Pelanggan Tidak Tetap / Tambahan)")
    with st.form("form_tambah_pesanan", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
        nama_baru  = c1.text_input("Nama Pelanggan")
        b_baru     = c2.number_input("Bulat",  min_value=0, value=0)
        k_baru     = c3.number_input("Kecil",  min_value=0, value=0)
        kt_baru    = c4.number_input("Kotak",  min_value=0, value=0)
        st_baru    = c5.selectbox("Status", ["belum", "sudah", "cicilan"])
        catatan    = st.text_input("Catatan (opsional)")
        submit     = st.form_submit_button("➕ Tambah Pesanan")

        if submit:
            if not nama_baru.strip():
                st.error("Nama pelanggan tidak boleh kosong!")
            elif b_baru + k_baru + kt_baru == 0:
                st.error("Jumlah pesanan tidak boleh 0!")
            else:
                total_baru = hitung_total(b_baru, k_baru, kt_baru)
                conn = get_conn()
                row_p = conn.execute(
                    "SELECT id FROM pelanggan WHERE nama=?", (nama_baru,)
                ).fetchone()
                pid = row_p["id"] if row_p else None
                is_t = 1 if row_p else 0
                conn.execute(
                    """INSERT INTO pesanan
                       (tanggal, pelanggan_id, nama_pelanggan, bulat, kecil, kotak,
                        total_harga, status_bayar, is_tetap, catatan)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (tgl_str, pid, nama_baru.strip(), b_baru, k_baru, kt_baru,
                     total_baru, st_baru, is_t, catatan)
                )
                conn.commit(); conn.close()
                st.success(f"✅ Pesanan {nama_baru} berhasil ditambahkan!")
                st.rerun()

# ════════════════════════════════════════════════════════════════════
# TAB 2 – Rekap Harian
# ════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader(f"Rekap Pesanan – {tgl.strftime('%d %B %Y')}")
    conn = get_conn()
    df_rekap = pd.read_sql(
        "SELECT * FROM pesanan WHERE tanggal=? ORDER BY is_tetap DESC, nama_pelanggan",
        conn, params=(tgl_str,)
    )
    conn.close()

    if df_rekap.empty:
        st.info("Tidak ada data pesanan untuk tanggal ini.")
    else:
        # KPI baris atas
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Pelanggan",  len(df_rekap))
        k2.metric("Total Bulat",  int(df_rekap["bulat"].sum()))
        k3.metric("Total Kecil",  int(df_rekap["kecil"].sum()))
        k4.metric("Total Kotak",  int(df_rekap["kotak"].sum()))
        k5.metric("Total Omset",  format_rupiah(int(df_rekap["total_harga"].sum())))

        st.markdown("---")

        # Tabel tagihan lengkap
        df_show = df_rekap[["nama_pelanggan","bulat","kecil","kotak",
                              "total_harga","status_bayar","catatan"]].copy()
        df_show["total_harga"] = df_show["total_harga"].apply(format_rupiah)
        df_show["status_bayar"] = df_show["status_bayar"].map(
            {"sudah":"✅ Lunas","belum":"❌ Belum","cicilan":"🔄 Cicilan"}
        )
        df_show.columns = ["Pelanggan","Bulat","Kecil","Kotak","Total","Status","Catatan"]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        # Ringkasan pembayaran
        st.markdown("---")
        col_s1, col_s2, col_s3 = st.columns(3)
        lunas   = df_rekap[df_rekap["status_bayar"]=="sudah"]["total_harga"].sum()
        belum   = df_rekap[df_rekap["status_bayar"]=="belum"]["total_harga"].sum()
        cicil   = df_rekap[df_rekap["status_bayar"]=="cicilan"]["total_harga"].sum()
        col_s1.metric("✅ Sudah Bayar", format_rupiah(int(lunas)))
        col_s2.metric("❌ Belum Bayar", format_rupiah(int(belum)))
        col_s3.metric("🔄 Cicilan",     format_rupiah(int(cicil)))

        # Update status pembayaran massal
        st.markdown("---")
        st.markdown("#### 💳 Update Status Pembayaran Massal")
        belum_list = df_rekap[df_rekap["status_bayar"]=="belum"]["nama_pelanggan"].tolist()
        if belum_list:
            selected_bayar = st.multiselect("Pilih pelanggan yang sudah bayar:", belum_list)
            if st.button("✅ Tandai Lunas", disabled=len(selected_bayar)==0):
                conn = get_conn()
                for nm in selected_bayar:
                    conn.execute(
                        "UPDATE pesanan SET status_bayar='sudah' WHERE tanggal=? AND nama_pelanggan=?",
                        (tgl_str, nm)
                    )
                conn.commit(); conn.close()
                st.success(f"{len(selected_bayar)} pelanggan ditandai lunas!")
                st.rerun()
        else:
            st.success("✅ Semua pelanggan sudah membayar!")

# ════════════════════════════════════════════════════════════════════
# TAB 3 – Kelola Pelanggan Tetap
# ════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("👥 Daftar Pelanggan Tetap")
    conn = get_conn()
    df_pl = pd.read_sql("SELECT * FROM pelanggan WHERE is_tetap=1 ORDER BY nama", conn)
    conn.close()

    # Tampilkan & edit
    if not df_pl.empty:
        df_show_pl = df_pl[["nama","bulat_default","kecil_default","kotak_default"]].copy()
        df_show_pl["default_omset"] = df_pl.apply(
            lambda r: format_rupiah(hitung_total(r["bulat_default"], r["kecil_default"], r["kotak_default"])),
            axis=1
        )
        df_show_pl.columns = ["Nama","Bulat/hari","Kecil/hari","Kotak/hari","Omset Default"]
        st.dataframe(df_show_pl, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### ✏️ Edit Default Pesanan Pelanggan Tetap")
    nama_edit = st.selectbox("Pilih pelanggan:", df_pl["nama"].tolist() if not df_pl.empty else [])
    if nama_edit:
        row_e = df_pl[df_pl["nama"] == nama_edit].iloc[0]
        c1e, c2e, c3e = st.columns(3)
        be = c1e.number_input("Bulat default",  value=int(row_e["bulat_default"]),  min_value=0, key="edit_b")
        ke = c2e.number_input("Kecil default",  value=int(row_e["kecil_default"]),  min_value=0, key="edit_k")
        kte= c3e.number_input("Kotak default",  value=int(row_e["kotak_default"]),  min_value=0, key="edit_kt")
        if st.button("💾 Simpan Default"):
            conn = get_conn()
            conn.execute(
                "UPDATE pelanggan SET bulat_default=?, kecil_default=?, kotak_default=? WHERE nama=?",
                (be, ke, kte, nama_edit)
            )
            conn.commit(); conn.close()
            st.success(f"Default pesanan {nama_edit} diperbarui!")
            st.rerun()

    st.markdown("---")
    st.markdown("#### ➕ Tambah Pelanggan Tetap Baru")
    with st.form("form_pl_baru", clear_on_submit=True):
        c1n, c2n, c3n, c4n = st.columns(4)
        nm_baru = c1n.text_input("Nama")
        bb = c2n.number_input("Bulat/hari", min_value=0, value=0)
        kb = c3n.number_input("Kecil/hari", min_value=0, value=0)
        ktb= c4n.number_input("Kotak/hari", min_value=0, value=0)
        if st.form_submit_button("➕ Tambah"):
            if nm_baru.strip():
                conn = get_conn()
                try:
                    conn.execute(
                        "INSERT INTO pelanggan (nama, bulat_default, kecil_default, kotak_default, is_tetap) VALUES (?,?,?,?,1)",
                        (nm_baru.strip(), bb, kb, ktb)
                    )
                    conn.commit()
                    st.success(f"Pelanggan {nm_baru} berhasil ditambahkan!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Nama sudah ada: {e}")
                finally:
                    conn.close()
            else:
                st.error("Nama tidak boleh kosong!")
