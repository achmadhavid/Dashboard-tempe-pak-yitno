import streamlit as st
import pandas as pd
from datetime import date
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db import get_conn
from utils.helpers import format_rupiah

st.set_page_config(page_title="Keuangan - Tempe Pak Yitno", page_icon="💰", layout="wide")
st.title("💰 Keuangan")

KATEGORI_KELUAR = [
    "Bahan Baku - Ragi",
    "Bahan Baku - Plastik",
    "Bahan Baku - Kayu Bakar",
    "Gaji Karyawan",
    "Lain-lain"
]

KATEGORI_MASUK = [
    "Penjualan Tempe",
    "Lain-lain"
]

today_str = date.today().isoformat()

# Hanya menyisakan 2 tab
tab1, tab2 = st.tabs([
    "📥 Input Transaksi",
    "🔴 Piutang Pelanggan"
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 – Input Transaksi
# ════════════════════════════════════════════════════════════════════
with tab1:

    st.subheader("Tambah Transaksi Baru")

    col_jenis, col_form = st.columns([1, 2])

    with col_jenis:
        jenis = st.radio(
            "Jenis Transaksi",
            ["💸 Pengeluaran", "💰 Pemasukan"],
            horizontal=False
        )

    with col_form:

        with st.form("form_transaksi", clear_on_submit=True):

            tgl_trans = st.date_input(
                "Tanggal",
                value=date.today()
            )

            if "Pengeluaran" in jenis:
                kat = st.selectbox("Kategori", KATEGORI_KELUAR)
                jen = "pengeluaran"
            else:
                kat = st.selectbox("Kategori", KATEGORI_MASUK)
                jen = "pemasukan"

            ket = st.text_input("Keterangan")

            jml = st.number_input(
                "Jumlah (Rp)",
                min_value=0,
                step=1000,
                value=0
            )

            if st.form_submit_button(
                "💾 Simpan Transaksi",
                type="primary"
            ):

                if jml <= 0:
                    st.error("Jumlah harus lebih dari 0!")

                else:
                    conn = get_conn()

                    conn.execute(
                        """
                        INSERT INTO keuangan
                        (tanggal, jenis, kategori, keterangan, jumlah)
                        VALUES (?,?,?,?,?)
                        """,
                        (
                            tgl_trans.isoformat(),
                            jen,
                            kat,
                            ket,
                            jml
                        )
                    )

                    conn.commit()
                    conn.close()

                    st.success(
                        f"✅ Transaksi {jen} "
                        f"{format_rupiah(jml)} berhasil disimpan!"
                    )

                    st.rerun()

    st.markdown("---")

    st.markdown("#### ⚡ Import Pemasukan dari Pesanan Hari Ini")

    tgl_import = st.date_input(
        "Tanggal import",
        value=date.today(),
        key="tgl_import"
    )

    if st.button("📥 Import Otomatis dari Data Pesanan"):

        conn = get_conn()

        df_p = pd.read_sql(
            """
            SELECT *
            FROM pesanan
            WHERE tanggal=? AND status_bayar='sudah'
            """,
            conn,
            params=(tgl_import.isoformat(),)
        )

        existing = conn.execute(
            """
            SELECT COUNT(*) as c
            FROM keuangan
            WHERE tanggal=? AND kategori='Penjualan Tempe'
            """,
            (tgl_import.isoformat(),)
        ).fetchone()

        if existing["c"] > 0:

            st.warning(
                "⚠️ Pemasukan hari ini sudah pernah di-import!"
            )

        elif df_p.empty:

            st.warning(
                "Tidak ada pesanan lunas untuk tanggal tersebut."
            )

        else:

            total_import = int(df_p["total_harga"].sum())

            conn.execute(
                """
                INSERT INTO keuangan
                (tanggal, jenis, kategori, keterangan, jumlah)
                VALUES (?,?,?,?,?)
                """,
                (
                    tgl_import.isoformat(),
                    "pemasukan",
                    "Penjualan Tempe",
                    f"Import dari {len(df_p)} pesanan lunas",
                    total_import
                )
            )

            conn.commit()

            st.success(
                f"✅ Berhasil import "
                f"{format_rupiah(total_import)} "
                f"dari {len(df_p)} pesanan lunas!"
            )

        conn.close()
        st.rerun()

    # ── Riwayat transaksi ────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🗒️ Riwayat Transaksi Terbaru")

    conn = get_conn()

    df_riwayat = pd.read_sql(
        """
        SELECT *
        FROM keuangan
        ORDER BY tanggal DESC, id DESC
        LIMIT 30
        """,
        conn
    )

    conn.close()

    if not df_riwayat.empty:

        for _, row in df_riwayat.iterrows():

            cols = st.columns([1, 1, 2, 2, 2, 1])

            cols[0].write(row["tanggal"])

            cols[1].write(
                "💰 Masuk"
                if row["jenis"] == "pemasukan"
                else "💸 Keluar"
            )

            cols[2].write(row["kategori"])

            cols[3].write(row["keterangan"] or "-")

            cols[4].write(
                ("+" if row["jenis"] == "pemasukan" else "-")
                + format_rupiah(row["jumlah"])
            )

            if cols[5].button(
                "🗑️",
                key=f"del_keu_{row['id']}"
            ):

                conn = get_conn()

                conn.execute(
                    "DELETE FROM keuangan WHERE id=?",
                    (row["id"],)
                )

                conn.commit()
                conn.close()

                st.rerun()

    else:
        st.info("Belum ada transaksi.")

# ════════════════════════════════════════════════════════════════════
# TAB 2 – PIUTANG PELANGGAN
# ════════════════════════════════════════════════════════════════════
with tab2:

    st.subheader("🔴 Total Piutang per Pelanggan")

    st.caption(
        "Piutang = total tagihan pesanan yang berstatus "
        "**Belum Bayar** dari semua tanggal."
    )

    conn = get_conn()

    df_piutang = pd.read_sql(
        """
        SELECT nama_pelanggan,
               COUNT(*) as jumlah_transaksi,
               SUM(total_harga) as total_piutang,
               MIN(tanggal) as transaksi_pertama,
               MAX(tanggal) as transaksi_terakhir
        FROM pesanan
        WHERE status_bayar = 'belum'
        GROUP BY nama_pelanggan
        ORDER BY total_piutang DESC
        """,
        conn
    )

    df_cicilan = pd.read_sql(
        """
        SELECT nama_pelanggan,
               COUNT(*) as jumlah_transaksi,
               SUM(total_harga) as total_cicilan,
               MIN(tanggal) as transaksi_pertama,
               MAX(tanggal) as transaksi_terakhir
        FROM pesanan
        WHERE status_bayar = 'cicilan'
        GROUP BY nama_pelanggan
        ORDER BY total_cicilan DESC
        """,
        conn
    )

    conn.close()

    total_piutang_semua = (
        int(df_piutang["total_piutang"].sum())
        if not df_piutang.empty else 0
    )

    total_cicilan_semua = (
        int(df_cicilan["total_cicilan"].sum())
        if not df_cicilan.empty else 0
    )

    total_tunggakan = (
        total_piutang_semua + total_cicilan_semua
    )

    k1, k2, k3 = st.columns(3)

    k1.metric(
        "❌ Total Piutang (Belum Bayar)",
        format_rupiah(total_piutang_semua),
        delta=(
            f"{len(df_piutang)} pelanggan"
            if not df_piutang.empty
            else "0 pelanggan"
        )
    )

    k2.metric(
        "🔄 Total Cicilan",
        format_rupiah(total_cicilan_semua),
        delta=(
            f"{len(df_cicilan)} pelanggan"
            if not df_cicilan.empty
            else "0 pelanggan"
        )
    )

    k3.metric(
        "⚠️ Total Tunggakan Keseluruhan",
        format_rupiah(total_tunggakan)
    )

    st.divider()

    # ── Piutang belum bayar ─────────────────────────────────────
    st.markdown("#### ❌ Pelanggan dengan Tagihan Belum Bayar")

    if df_piutang.empty:

        st.success(
            "✅ Tidak ada piutang! Semua tagihan sudah lunas."
        )

    else:

        df_p_show = df_piutang.copy()

        df_p_show["total_piutang"] = (
            df_p_show["total_piutang"]
            .apply(format_rupiah)
        )

        df_p_show.columns = [
            "Nama Pelanggan",
            "Jml Transaksi",
            "Total Piutang",
            "Tgl Pertama",
            "Tgl Terakhir"
        ]

        st.dataframe(
            df_p_show,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    # ── Cicilan ────────────────────────────────────────────────
    st.markdown("#### 🔄 Pelanggan dengan Status Cicilan")

    if df_cicilan.empty:

        st.info(
            "Tidak ada transaksi dengan status cicilan."
        )

    else:

        df_c_show = df_cicilan.copy()

        df_c_show["total_cicilan"] = (
            df_c_show["total_cicilan"]
            .apply(format_rupiah)
        )

        df_c_show.columns = [
            "Nama Pelanggan",
            "Jml Transaksi",
            "Total Cicilan",
            "Tgl Pertama",
            "Tgl Terakhir"
        ]

        st.dataframe(
            df_c_show,
            use_container_width=True,
            hide_index=True
        )