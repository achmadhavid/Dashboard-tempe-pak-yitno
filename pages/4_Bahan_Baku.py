import streamlit as st
import pandas as pd
from datetime import date
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db import get_conn
from utils.helpers import format_rupiah

st.set_page_config(page_title="Bahan Baku - Tempe Pak Yitno", page_icon="🌾", layout="wide")
st.title("🌾 Bahan Baku & Ampas Tahu")

# ════════════════════════════════════════════════════════════════════
# TAB – Ampas Tahu (Kontrak)
# ════════════════════════════════════════════════════════════════════

st.subheader("Manajemen Kontrak Ampas Tahu")

conn = get_conn()
df_kontrak = pd.read_sql(
    "SELECT * FROM ampas_kontrak ORDER BY status ASC, id DESC", conn
)
df_kontrak_aktif = df_kontrak[df_kontrak["status"] == "aktif"]
conn.close()

# ── Status kartu kontrak aktif ─────────────────────────────────
if df_kontrak_aktif.empty:
    st.error("🚨 Belum ada kontrak ampas aktif! Segera buat kontrak baru.")
else:
    for _, k in df_kontrak_aktif.iterrows():
        sisa_uang   = int(k["sisa_uang"])
        total_uang  = int(k["uang_kontrak"])
        persen_uang = (sisa_uang / total_uang * 100) if total_uang > 0 else 0
        terpakai    = total_uang - sisa_uang

        if persen_uang <= 15:
            st.error(
                f"🚨 SALDO KONTRAK HAMPIR HABIS!  Supplier: **{k['supplier']}** | "
                f"Sisa: **{format_rupiah(sisa_uang)}** ({persen_uang:.1f}%)"
            )
        elif persen_uang <= 30:
            st.warning(
                f"⚠️ Saldo kontrak perlu diisi ulang.  Supplier: **{k['supplier']}** | "
                f"Sisa: {format_rupiah(sisa_uang)} ({persen_uang:.1f}%)"
            )
        else:
            st.success(
                f"✅ Saldo kontrak aman.  Supplier: **{k['supplier']}** | "
                f"Sisa: {format_rupiah(sisa_uang)} ({persen_uang:.1f}%)"
            )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Uang Kontrak", format_rupiah(total_uang))
        col2.metric("Sisa Uang Kontrak", format_rupiah(sisa_uang))
        col3.metric("Sudah Terpakai", format_rupiah(terpakai))
        col4.metric("Biaya / Pengambilan", format_rupiah(int(k["harga_per_ambil"])))

        st.progress(
            max(0.0, min(1.0, persen_uang / 100)),
            text=f"Sisa saldo: {persen_uang:.1f}% | Mulai: {k['tanggal_mulai']}"
        )
        st.divider()

# ── Catat pengambilan ampas ────────────────────────────────────
st.subheader("📥 Catat Pengambilan Ampas Hari Ini")

if df_kontrak_aktif.empty:
    st.warning("Tidak ada kontrak aktif. Buat kontrak terlebih dahulu.")
else:
    kontrak_pilihan = st.selectbox(
        "Pilih Kontrak (Supplier):",
        df_kontrak_aktif["id"].tolist(),
        format_func=lambda x: (
            f"{df_kontrak_aktif[df_kontrak_aktif['id']==x]['supplier'].values[0]}  "
            f"– sisa {format_rupiah(int(df_kontrak_aktif[df_kontrak_aktif['id']==x]['sisa_uang'].values[0]))}"
        ),
        key="sel_kontrak_ambil"
    )

    row_k       = df_kontrak_aktif[df_kontrak_aktif["id"] == kontrak_pilihan].iloc[0]
    sisa_saldo  = int(row_k["sisa_uang"])
    harga_ambil = int(row_k["harga_per_ambil"])
    max_ambil   = (sisa_saldo // harga_ambil) if harga_ambil > 0 else 999

    st.caption(
        f"Supplier: **{row_k['supplier']}** | "
        f"Saldo: {format_rupiah(sisa_saldo)} | "
        f"Harga/ambil: {format_rupiah(harga_ambil)} | "
        f"Maks ambil: {max_ambil}x"
    )

    with st.form("form_ambil_ampas", clear_on_submit=True):
        tgl_ambil = st.date_input("Tanggal Pengambilan", value=date.today())

        jml_ambil = st.number_input(
            f"Jumlah Pengambilan ({row_k['satuan']})",
            min_value=1,
            max_value=max(1, max_ambil),
            value=1,
            step=1,
            key="input_jml_ambil"
        )

        ket_ambil = st.text_input("Keterangan (opsional)")

        biaya_preview = jml_ambil * harga_ambil

        st.info(
            f"💰 Biaya: **{format_rupiah(biaya_preview)}**  "
            f"({jml_ambil} × {format_rupiah(harga_ambil)})  |  "
            f"Sisa saldo setelah ambil: **{format_rupiah(max(0, sisa_saldo - biaya_preview))}**"
        )

        if st.form_submit_button("💾 Catat Pengambilan", type="primary"):
            biaya_total = jml_ambil * harga_ambil

            if biaya_total > sisa_saldo:
                st.error(
                    f"❌ Saldo tidak cukup! "
                    f"Sisa: {format_rupiah(sisa_saldo)}, dibutuhkan: {format_rupiah(biaya_total)}"
                )
            else:
                sisa_baru = sisa_saldo - biaya_total

                conn = get_conn()

                conn.execute(
                    "UPDATE ampas_kontrak SET sisa_uang=?, status=? WHERE id=?",
                    (
                        sisa_baru,
                        "habis" if sisa_baru <= 0 else "aktif",
                        kontrak_pilihan
                    )
                )

                conn.execute(
                    """
                    INSERT INTO ampas_log
                    (kontrak_id, tanggal, jumlah_ambil, biaya_ambil, keterangan)
                    VALUES (?,?,?,?,?)
                    """,
                    (
                        kontrak_pilihan,
                        tgl_ambil.isoformat(),
                        jml_ambil,
                        biaya_total,
                        ket_ambil
                    )
                )

                conn.commit()
                conn.close()

                st.success(
                    f"✅ Pengambilan {jml_ambil} {row_k['satuan']} dicatat! "
                    f"Biaya: {format_rupiah(biaya_total)} | "
                    f"Sisa saldo: {format_rupiah(sisa_baru)}"
                )

                st.rerun()

# ── Riwayat pengambilan ────────────────────────────────────────
st.markdown("---")
st.markdown("#### 📋 Riwayat Pengambilan Ampas (30 Terakhir)")

conn = get_conn()

df_log = pd.read_sql(
    """
    SELECT l.tanggal, k.supplier, l.jumlah_ambil, k.satuan,
           l.biaya_ambil, l.keterangan
    FROM ampas_log l
    JOIN ampas_kontrak k ON l.kontrak_id = k.id
    ORDER BY l.tanggal DESC, l.id DESC
    LIMIT 30
    """,
    conn
)

conn.close()

if not df_log.empty:
    df_log["Pengambilan"] = (
        df_log["jumlah_ambil"].astype(str)
        + " "
        + df_log["satuan"].astype(str)
    )

    df_log["biaya_ambil"] = df_log["biaya_ambil"].apply(format_rupiah)

    df_show_log = df_log[
        ["tanggal", "supplier", "Pengambilan", "biaya_ambil", "keterangan"]
    ].copy()

    df_show_log.columns = [
        "Tanggal",
        "Supplier",
        "Jumlah Ambil",
        "Biaya",
        "Keterangan"
    ]

    st.dataframe(
        df_show_log,
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("Belum ada riwayat pengambilan ampas.")

# ── Buat kontrak baru ──────────────────────────────────────────
st.markdown("---")
st.markdown("#### ➕ Buat Kontrak Ampas Baru")

with st.form("form_kontrak_baru", clear_on_submit=True):

    c1, c2 = st.columns(2)

    supplier = c1.text_input("Nama Supplier")

    satuan_k = c2.selectbox(
        "Satuan Pengambilan",
        ["karung", "kg", "ton", "ember", "plastik"]
    )

    c3, c4 = st.columns(2)

    tgl_mulai = c3.date_input(
        "Tanggal Mulai Kontrak",
        value=date.today()
    )

    harga_per_amb = c4.number_input(
        "Harga per Pengambilan (Rp)",
        min_value=0,
        step=1000,
        value=0,
        help="Biaya yang dipotong dari saldo setiap kali melakukan 1x pengambilan"
    )

    uang_kontrak = st.number_input(
        "💵 Jumlah Uang Kontrak (Rp)",
        min_value=0,
        step=10000,
        value=0,
        help="Total uang yang dibayarkan ke supplier sebagai kontrak."
    )

    if uang_kontrak > 0 and harga_per_amb > 0:
        est_ambil = uang_kontrak // harga_per_amb

        st.caption(
            f"ℹ️ Estimasi jumlah pengambilan: **{est_ambil}x** "
            f"({format_rupiah(uang_kontrak)} ÷ "
            f"{format_rupiah(harga_per_amb)}/ambil)"
        )

    if st.form_submit_button("➕ Buat Kontrak", type="primary"):

        if not supplier.strip():
            st.error("Nama supplier tidak boleh kosong!")

        elif uang_kontrak <= 0:
            st.error("Jumlah uang kontrak harus lebih dari 0!")

        elif harga_per_amb <= 0:
            st.error("Harga per pengambilan harus lebih dari 0!")

        else:
            conn = get_conn()

            conn.execute(
                """
                INSERT INTO ampas_kontrak
                (
                    supplier,
                    tanggal_mulai,
                    uang_kontrak,
                    sisa_uang,
                    harga_per_ambil,
                    satuan,
                    status
                )
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    supplier.strip(),
                    tgl_mulai.isoformat(),
                    uang_kontrak,
                    uang_kontrak,
                    harga_per_amb,
                    satuan_k,
                    "aktif"
                )
            )

            conn.commit()
            conn.close()

            st.success(
                f"✅ Kontrak dengan **{supplier}** berhasil dibuat! "
                f"Saldo: {format_rupiah(uang_kontrak)}"
            )

            st.rerun()