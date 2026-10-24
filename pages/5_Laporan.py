import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta
import numpy as np
import io, sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db import get_conn
from utils.helpers import format_rupiah, HARGA

st.set_page_config(page_title="Laporan - Tempe Pak Yitno", page_icon="📊", layout="wide")
st.title("📊 Laporan & Grafik")

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR – Filter periode
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.header("🔍 Filter Laporan")
col_bln, col_thn = st.sidebar.columns(2)
bulan_sel = col_bln.selectbox(
    "Bulan", range(1, 13),
    index=date.today().month - 1,
    format_func=lambda m: date(2000, m, 1).strftime("%B")
)
tahun_sel = col_thn.number_input("Tahun", min_value=2020, max_value=2099,
                                  value=date.today().year)
bln_str  = f"{int(tahun_sel)}-{bulan_sel:02d}"
nama_bln = date(int(tahun_sel), bulan_sel, 1).strftime("%B %Y")

# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
conn = get_conn()
df_pesanan = pd.read_sql(
    "SELECT * FROM pesanan WHERE tanggal LIKE ?", conn, params=(f"{bln_str}%",)
)
df_keu = pd.read_sql(
    "SELECT * FROM keuangan WHERE tanggal LIKE ?", conn, params=(f"{bln_str}%",)
)
df_bahan = pd.read_sql(
    "SELECT * FROM bahan_baku WHERE tanggal LIKE ?", conn, params=(f"{bln_str}%",)
)
df_gaji_bln = pd.read_sql(
    """SELECT g.*, k.nama FROM gaji_terbayar g
       JOIN karyawan k ON g.karyawan_id = k.id
       WHERE g.minggu_mulai LIKE ? OR g.minggu_selesai LIKE ?""",
    conn, params=(f"{bln_str}%", f"{bln_str}%")
)
df_semua_pesanan = pd.read_sql("SELECT * FROM pesanan ORDER BY tanggal", conn)
df_semua_keu     = pd.read_sql("SELECT * FROM keuangan ORDER BY tanggal", conn)
conn.close()

# ══════════════════════════════════════════════════════════════════════════════
# KALKULASI KPI
# ══════════════════════════════════════════════════════════════════════════════
total_bulat = int(df_pesanan["bulat"].sum()) if not df_pesanan.empty else 0
total_kecil = int(df_pesanan["kecil"].sum()) if not df_pesanan.empty else 0
total_kotak = int(df_pesanan["kotak"].sum()) if not df_pesanan.empty else 0
total_pcs   = total_bulat + total_kecil + total_kotak
total_omset = int(df_pesanan["total_harga"].sum()) if not df_pesanan.empty else 0
total_masuk  = int(df_keu[df_keu["jenis"]=="pemasukan"]["jumlah"].sum()) if not df_keu.empty else 0
total_keluar = int(df_keu[df_keu["jenis"]=="pengeluaran"]["jumlah"].sum()) if not df_keu.empty else 0
laba_bersih  = total_masuk - total_keluar
total_gaji_bln = int(df_gaji_bln["total_gaji"].sum()) if not df_gaji_bln.empty else 0
total_bb_bln   = int(df_bahan["total_harga"].sum()) if not df_bahan.empty else 0

# ══════════════════════════════════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════════════════════════════════
st.subheader(f"📅 Periode: {nama_bln}")
k1, k2, k3, k4 = st.columns(4)
k1.metric("📦 Total Produksi",    f"{total_pcs:,} pcs")
k2.metric("💰 Total Omset",       format_rupiah(total_omset))
k3.metric("💸 Total Pengeluaran", format_rupiah(total_keluar))
k4.metric("📊 Laba Bersih",       format_rupiah(laba_bersih),
          delta_color="normal" if laba_bersih >= 0 else "inverse")
k5, k6, k7, k8 = st.columns(4)
k5.metric("🫘 Bulat",         f"{total_bulat:,} pcs")
k6.metric("⭕ Kecil",         f"{total_kecil:,} pcs")
k7.metric("📦 Kotak",         f"{total_kotak:,} pcs")
k8.metric("👷 Gaji Terbayar", format_rupiah(total_gaji_bln))
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Produksi", "💰 Biaya & Pemasukan",
    "👥 Distribusi Pelanggan", "🔮 Prediksi Produksi", "📥 Export"
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 – PRODUKSI HARIAN / MINGGUAN / BULANAN
# ════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Grafik Produksi")

    if df_pesanan.empty and df_semua_pesanan.empty:
        st.info("Tidak ada data produksi.")
    else:
        mode_prod = st.radio(
            "Tampilkan per:", ["Harian", "Mingguan", "Bulanan (tren)"],
            horizontal=True, key="mode_prod"
        )

        if mode_prod == "Harian":
            if df_pesanan.empty:
                st.info("Tidak ada data produksi bulan ini.")
            else:
                df_h = df_pesanan.groupby("tanggal")[["bulat","kecil","kotak"]].sum().reset_index()
                df_h["total"] = df_h["bulat"] + df_h["kecil"] + df_h["kotak"]
                df_melt = df_h.melt(id_vars="tanggal",
                                     value_vars=["bulat","kecil","kotak"],
                                     var_name="Jenis", value_name="Jumlah")
                df_melt["Jenis"] = df_melt["Jenis"].str.capitalize()

                fig = px.bar(df_melt, x="tanggal", y="Jumlah", color="Jenis",
                              title=f"Produksi Harian – {nama_bln}",
                              color_discrete_map={"Bulat":"#4CAF50","Kecil":"#2196F3","Kotak":"#FF9800"},
                              barmode="stack")
                fig.add_trace(go.Scatter(x=df_h["tanggal"], y=df_h["total"],
                                          mode="lines+markers", name="Total",
                                          line=dict(color="#9C27B0", width=2, dash="dot"),
                                          marker=dict(size=5)))
                fig.update_layout(xaxis_title="Tanggal", yaxis_title="Pcs",
                                   legend=dict(orientation="h", y=1.12))
                st.plotly_chart(fig, use_container_width=True)

                avg = df_h["total"].mean()
                c1, c2, c3 = st.columns(3)
                c1.metric("Rata-rata/hari", f"{avg:,.0f} pcs")
                c2.metric("Hari tertinggi", f"{df_h['total'].max():,} pcs ({df_h.loc[df_h['total'].idxmax(),'tanggal']})")
                c3.metric("Hari terendah",  f"{df_h['total'].min():,} pcs ({df_h.loc[df_h['total'].idxmin(),'tanggal']})")

        elif mode_prod == "Mingguan":
            if df_semua_pesanan.empty:
                st.info("Belum ada data.")
            else:
                df_w = df_semua_pesanan.copy()
                df_w["tanggal_dt"] = pd.to_datetime(df_w["tanggal"])
                df_w["periode_w"]  = df_w["tanggal_dt"].dt.to_period("W")
                df_w["minggu_label"] = df_w["periode_w"].apply(
                    lambda p: p.start_time.strftime("%d %b")
                )
                df_w["minggu_sort"] = df_w["periode_w"].apply(
                    lambda p: p.start_time
                )
                df_prod_w = (df_w.groupby(["minggu_label","minggu_sort"])
                             [["bulat","kecil","kotak"]].sum().reset_index()
                             .sort_values("minggu_sort").tail(12))
                df_prod_w["total"] = df_prod_w["bulat"] + df_prod_w["kecil"] + df_prod_w["kotak"]

                df_melt_w = df_prod_w.melt(
                    id_vars="minggu_label",
                    value_vars=["bulat","kecil","kotak"],
                    var_name="Jenis", value_name="Jumlah"
                )
                df_melt_w["Jenis"] = df_melt_w["Jenis"].str.capitalize()

                fig_w = px.bar(df_melt_w, x="minggu_label", y="Jumlah", color="Jenis",
                                title="Produksi Mingguan (12 Minggu Terakhir)",
                                color_discrete_map={"Bulat":"#4CAF50","Kecil":"#2196F3","Kotak":"#FF9800"},
                                barmode="stack")
                fig_w.add_trace(go.Scatter(
                    x=df_prod_w["minggu_label"], y=df_prod_w["total"],
                    mode="lines+markers", name="Total",
                    line=dict(color="#9C27B0", width=2, dash="dot"), marker=dict(size=6)
                ))
                fig_w.update_layout(xaxis_title="Minggu (mulai Senin)",
                                     yaxis_title="Pcs",
                                     legend=dict(orientation="h", y=1.12))
                st.plotly_chart(fig_w, use_container_width=True)

                df_tbl_w = df_prod_w[["minggu_label","bulat","kecil","kotak","total"]].copy()
                df_tbl_w.columns = ["Minggu","Bulat","Kecil","Kotak","Total"]
                st.dataframe(df_tbl_w, use_container_width=True, hide_index=True)

        else:  # Bulanan
            if df_semua_pesanan.empty:
                st.info("Belum ada data.")
            else:
                df_m = df_semua_pesanan.copy()
                df_m["bulan"] = df_m["tanggal"].str[:7]
                df_prod_m = df_m.groupby("bulan")[["bulat","kecil","kotak"]].sum().reset_index()
                df_prod_m["total"] = df_prod_m["bulat"] + df_prod_m["kecil"] + df_prod_m["kotak"]
                df_prod_m["label"] = pd.to_datetime(df_prod_m["bulan"]).dt.strftime("%b %Y")

                df_melt_m = df_prod_m.melt(
                    id_vars="label", value_vars=["bulat","kecil","kotak"],
                    var_name="Jenis", value_name="Jumlah"
                )
                df_melt_m["Jenis"] = df_melt_m["Jenis"].str.capitalize()

                fig_m = px.bar(df_melt_m, x="label", y="Jumlah", color="Jenis",
                                title="Tren Produksi Bulanan (Semua Periode)",
                                color_discrete_map={"Bulat":"#4CAF50","Kecil":"#2196F3","Kotak":"#FF9800"},
                                barmode="stack")
                fig_m.add_trace(go.Scatter(
                    x=df_prod_m["label"], y=df_prod_m["total"],
                    mode="lines+markers", name="Total",
                    line=dict(color="#9C27B0", width=2.5), marker=dict(size=7)
                ))
                fig_m.update_layout(xaxis_title="Bulan", yaxis_title="Pcs",
                                     legend=dict(orientation="h", y=1.12))
                st.plotly_chart(fig_m, use_container_width=True)

        # Pie komposisi
        st.markdown("---")
        if total_pcs > 0:
            col_p1, col_p2 = st.columns(2)
            data_pie = {
                "Jenis":  ["Bulat","Kecil","Kotak"],
                "Jumlah": [total_bulat, total_kecil, total_kotak],
                "Omset":  [total_bulat*HARGA["bulat"],
                            total_kecil*HARGA["kecil"],
                            total_kotak*HARGA["kotak"]]
            }
            with col_p1:
                fig_p1 = px.pie(data_pie, values="Jumlah", names="Jenis",
                                 title=f"Komposisi Produksi (pcs) – {nama_bln}",
                                 color_discrete_sequence=["#4CAF50","#2196F3","#FF9800"])
                fig_p1.update_traces(textinfo="percent+label")
                st.plotly_chart(fig_p1, use_container_width=True)
            with col_p2:
                fig_p2 = px.pie(data_pie, values="Omset", names="Jenis",
                                 title=f"Komposisi Omset per Jenis – {nama_bln}",
                                 color_discrete_sequence=["#66BB6A","#42A5F5","#FFA726"])
                fig_p2.update_traces(textinfo="percent+label")
                st.plotly_chart(fig_p2, use_container_width=True)

        # Tabel ringkasan
        st.markdown("---")
        st.markdown("#### Ringkasan Produksi")
        df_ringkas = pd.DataFrame({
            "Jenis":        ["Bulat","Kecil","Kotak","TOTAL"],
            "Harga Satuan": [format_rupiah(HARGA["bulat"]), format_rupiah(HARGA["kecil"]),
                              format_rupiah(HARGA["kotak"]), "–"],
            "Total Pcs":    [f"{total_bulat:,}", f"{total_kecil:,}",
                              f"{total_kotak:,}", f"{total_pcs:,}"],
            "Total Omset":  [format_rupiah(total_bulat*HARGA["bulat"]),
                              format_rupiah(total_kecil*HARGA["kecil"]),
                              format_rupiah(total_kotak*HARGA["kotak"]),
                              format_rupiah(total_omset)],
        })
        st.dataframe(df_ringkas, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════
# TAB 2 – BIAYA & PEMASUKAN
# ════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Grafik Biaya & Pemasukan")

    mode_keu = st.radio(
        "Tampilkan per:", ["Harian", "Mingguan", "Bulanan (tren)"],
        horizontal=True, key="mode_keu"
    )

    def buat_grafik_keu(df_src, grup_col, x_label, judul):
        if df_src.empty:
            st.info("Tidak ada data keuangan.")
            return
        df_g = df_src.groupby([grup_col, "jenis"])["jumlah"].sum().reset_index()
        df_pv = df_g.pivot(index=grup_col, columns="jenis", values="jumlah").fillna(0).reset_index()
        df_pv.columns.name = None
        for col in ["pemasukan", "pengeluaran"]:
            if col not in df_pv.columns:
                df_pv[col] = 0
        df_pv["laba"] = df_pv["pemasukan"] - df_pv["pengeluaran"]

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=df_pv[grup_col], y=df_pv["pemasukan"],
                              name="Pemasukan", marker_color="#4CAF50"), secondary_y=False)
        fig.add_trace(go.Bar(x=df_pv[grup_col], y=df_pv["pengeluaran"],
                              name="Pengeluaran", marker_color="#F44336"), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_pv[grup_col], y=df_pv["laba"],
                                  mode="lines+markers", name="Laba Bersih",
                                  line=dict(color="#9C27B0", width=2.5),
                                  marker=dict(size=6)), secondary_y=True)
        fig.update_layout(title=judul, barmode="group",
                           legend=dict(orientation="h", y=1.12),
                           xaxis_title=x_label)
        fig.update_yaxes(title_text="Rupiah (Rp)", secondary_y=False, tickformat=",.0f")
        fig.update_yaxes(title_text="Laba Bersih (Rp)", secondary_y=True, tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)

        df_tbl = df_pv[[grup_col, "pemasukan", "pengeluaran", "laba"]].copy()
        df_tbl["pemasukan"]   = df_tbl["pemasukan"].apply(format_rupiah)
        df_tbl["pengeluaran"] = df_tbl["pengeluaran"].apply(format_rupiah)
        df_tbl["laba"]        = df_tbl["laba"].apply(format_rupiah)
        df_tbl.columns        = [x_label, "Pemasukan", "Pengeluaran", "Laba Bersih"]
        st.dataframe(df_tbl, use_container_width=True, hide_index=True)

    if mode_keu == "Harian":
        buat_grafik_keu(df_keu, "tanggal", "Tanggal",
                         f"Pemasukan vs Pengeluaran Harian – {nama_bln}")

    elif mode_keu == "Mingguan":
        if not df_semua_keu.empty:
            df_kw = df_semua_keu.copy()
            df_kw["tgl_dt"] = pd.to_datetime(df_kw["tanggal"])
            df_kw["minggu_sort"]  = df_kw["tgl_dt"].dt.to_period("W").apply(lambda p: p.start_time)
            df_kw["minggu_label"] = df_kw["tgl_dt"].dt.to_period("W").apply(
                lambda p: p.start_time.strftime("%d %b"))
            minggu_list = df_kw.sort_values("minggu_sort")["minggu_label"].unique()[-12:]
            df_kw = df_kw[df_kw["minggu_label"].isin(minggu_list)]
            buat_grafik_keu(df_kw, "minggu_label", "Minggu",
                             "Pemasukan vs Pengeluaran Mingguan (12 Minggu Terakhir)")
        else:
            st.info("Belum ada data keuangan.")

    else:
        if not df_semua_keu.empty:
            df_km = df_semua_keu.copy()
            df_km["bulan_label"] = pd.to_datetime(df_km["tanggal"].str[:7]).dt.strftime("%b %Y")
            buat_grafik_keu(df_km, "bulan_label", "Bulan",
                             "Tren Pemasukan vs Pengeluaran Bulanan")
        else:
            st.info("Belum ada data keuangan.")

    # Pie & ringkasan
    st.markdown("---")
    col_ke1, col_ke2 = st.columns(2)
    with col_ke1:
        if not df_keu.empty:
            df_kel = df_keu[df_keu["jenis"]=="pengeluaran"].groupby("kategori")["jumlah"].sum().reset_index()
            if not df_kel.empty:
                fig_kel = px.pie(df_kel, values="jumlah", names="kategori",
                                  title=f"Rincian Pengeluaran – {nama_bln}",
                                  color_discrete_sequence=px.colors.sequential.Oranges_r)
                fig_kel.update_traces(textinfo="percent+label")
                st.plotly_chart(fig_kel, use_container_width=True)
        else:
            st.info("Tidak ada data pengeluaran.")

    with col_ke2:
        margin_pct = (laba_bersih / total_masuk * 100) if total_masuk > 0 else 0
        st.dataframe(pd.DataFrame({
            "Keterangan": ["Total Pemasukan","Total Pengeluaran","Laba Bersih",
                            "Margin Laba (%)","Gaji Karyawan","Bahan Baku"],
            "Nilai": [format_rupiah(total_masuk), format_rupiah(total_keluar),
                       format_rupiah(laba_bersih), f"{margin_pct:.1f}%",
                       format_rupiah(total_gaji_bln), format_rupiah(total_bb_bln)]
        }), use_container_width=True, hide_index=True)

        if total_masuk > 0:
            fig_wf = go.Figure(go.Waterfall(
                orientation="v",
                x=["Pemasukan", "Pengeluaran", "Laba Bersih"],
                y=[total_masuk, -total_keluar, laba_bersih],
                connector={"line": {"color": "rgb(100,100,100)"}},
                increasing={"marker": {"color": "#4CAF50"}},
                decreasing={"marker": {"color": "#F44336"}},
                totals={"marker": {"color": "#2196F3"}}
            ))
            fig_wf.update_layout(title="Alur Keuangan Bulan Ini",
                                   yaxis_tickformat=",.0f",
                                   showlegend=False, height=300)
            st.plotly_chart(fig_wf, use_container_width=True)


# ════════════════════════════════════════════════════════════════════
# TAB 3 – DISTRIBUSI PELANGGAN
# ════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Distribusi & Analisis Pelanggan")

    if df_pesanan.empty:
        st.info("Tidak ada data pesanan untuk periode ini.")
    else:
        df_per_pl = df_pesanan.groupby("nama_pelanggan").agg(
            total_omset=("total_harga", "sum"),
            total_bulat=("bulat",       "sum"),
            total_kecil=("kecil",       "sum"),
            total_kotak=("kotak",       "sum"),
            jumlah_hari=("id",          "count")
        ).reset_index()
        df_per_pl["total_pcs"] = (df_per_pl["total_bulat"]
                                   + df_per_pl["total_kecil"]
                                   + df_per_pl["total_kotak"])
        df_per_pl = df_per_pl.sort_values("total_omset", ascending=False)
        df_per_pl["total_omset_fmt"] = df_per_pl["total_omset"].apply(format_rupiah)

        # Bar horizontal
        fig_bar = px.bar(
            df_per_pl.sort_values("total_omset"),
            x="total_omset", y="nama_pelanggan",
            orientation="h",
            title=f"Omset per Pelanggan – {nama_bln}",
            color="total_omset",
            color_continuous_scale="Greens",
            labels={"total_omset":"Total Omset (Rp)", "nama_pelanggan":"Pelanggan"}
        )
        fig_bar.update_layout(coloraxis_showscale=False,
                               xaxis_tickformat=",.0f",
                               height=max(400, len(df_per_pl) * 28))
        st.plotly_chart(fig_bar, use_container_width=True)

        # Treemap
        st.markdown("---")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            fig_tree1 = px.treemap(
                df_per_pl, path=["nama_pelanggan"], values="total_pcs",
                color="total_pcs", color_continuous_scale="Greens",
                title="Porsi Produksi per Pelanggan (pcs)"
            )
            fig_tree1.update_traces(
                texttemplate="%{label}<br>%{value:,} pcs",
                textfont_size=12
            )
            fig_tree1.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_tree1, use_container_width=True)

        with col_t2:
            fig_tree2 = px.treemap(
                df_per_pl, path=["nama_pelanggan"], values="total_omset",
                color="total_omset", color_continuous_scale="Blues",
                title="Porsi Omset per Pelanggan (Rp)"
            )
            fig_tree2.update_traces(
                texttemplate="%{label}<br>%{customdata[0]}",
                customdata=df_per_pl[["total_omset_fmt"]].values,
                textfont_size=12
            )
            fig_tree2.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_tree2, use_container_width=True)

        # Stacked bar distribusi jenis per pelanggan
        st.markdown("---")
        df_top15 = df_per_pl.sort_values("total_pcs", ascending=False).head(15)
        df_melt_pl = df_top15.melt(
            id_vars="nama_pelanggan",
            value_vars=["total_bulat","total_kecil","total_kotak"],
            var_name="Jenis", value_name="Jumlah"
        )
        df_melt_pl["Jenis"] = df_melt_pl["Jenis"].str.replace("total_","").str.capitalize()

        fig_stack = px.bar(
            df_melt_pl, x="nama_pelanggan", y="Jumlah", color="Jenis",
            title="Distribusi Jenis Tempe per Pelanggan (Top 15 produksi terbanyak)",
            color_discrete_map={"Bulat":"#4CAF50","Kecil":"#2196F3","Kotak":"#FF9800"},
            barmode="stack",
            labels={"nama_pelanggan":"Pelanggan","Jumlah":"Pcs"}
        )
        fig_stack.update_xaxes(tickangle=-35)
        fig_stack.update_layout(legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig_stack, use_container_width=True)

        # Status pembayaran
        st.markdown("---")
        col_s1, col_s2 = st.columns(2)
        label_map = {"sudah":"✅ Lunas","belum":"❌ Belum","cicilan":"🔄 Cicilan"}
        with col_s1:
            df_byr = df_pesanan.groupby("status_bayar")["total_harga"].sum().reset_index()
            df_byr["status_bayar"] = df_byr["status_bayar"].map(label_map)
            fig_byr1 = px.pie(df_byr, values="total_harga", names="status_bayar",
                               title="Status Pembayaran (Nilai Rp)",
                               color_discrete_sequence=["#4CAF50","#F44336","#FF9800"])
            fig_byr1.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_byr1, use_container_width=True)
        with col_s2:
            df_byr2 = df_pesanan.groupby("status_bayar")["id"].count().reset_index()
            df_byr2["status_bayar"] = df_byr2["status_bayar"].map(label_map)
            fig_byr2 = px.pie(df_byr2, values="id", names="status_bayar",
                               title="Status Pembayaran (Jumlah Transaksi)",
                               color_discrete_sequence=["#4CAF50","#F44336","#FF9800"])
            fig_byr2.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_byr2, use_container_width=True)

        st.markdown("---")
        st.markdown("#### Tabel Detail Per Pelanggan")
        df_tbl_pl = df_per_pl[["nama_pelanggan","total_bulat","total_kecil",
                                 "total_kotak","total_pcs","jumlah_hari",
                                 "total_omset_fmt"]].copy()
        df_tbl_pl.columns = ["Pelanggan","Bulat","Kecil","Kotak",
                              "Total Pcs","Hari Pesan","Total Omset"]
        st.dataframe(df_tbl_pl, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════
# TAB 4 – PREDIKSI PRODUKSI MINGGU DEPAN
# ════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("🔮 Prediksi Produksi Minggu Depan")

    conn = get_conn()
    df_pr = pd.read_sql(
        """SELECT tanggal, SUM(bulat) as bulat, SUM(kecil) as kecil, SUM(kotak) as kotak
           FROM pesanan GROUP BY tanggal ORDER BY tanggal""",
        conn
    )
    conn.close()

    MIN_HARI = 7

    if len(df_pr) < MIN_HARI:
        st.warning(
            f"⚠️ Data historis masih kurang. Dibutuhkan minimal **{MIN_HARI} hari** data pesanan "
            f"untuk membuat prediksi. Saat ini baru ada **{len(df_pr)} hari**."
        )
        st.info("Terus gunakan aplikasi setiap hari, prediksi akan muncul otomatis setelah data cukup.")
    else:
        df_pr["tanggal"] = pd.to_datetime(df_pr["tanggal"])
        df_pr["total"]   = df_pr["bulat"] + df_pr["kecil"] + df_pr["kotak"]
        df_pr["weekday"] = df_pr["tanggal"].dt.weekday

        # Rata-rata global & per hari
        avg_global  = df_pr["total"].mean()
        avg_weekday = df_pr.groupby("weekday")["total"].mean()
        faktor_hari = {
            wd: (avg_weekday[wd] / avg_global if wd in avg_weekday.index and avg_global > 0 else 1.0)
            for wd in range(7)
        }

        # Baseline & trend
        baseline = df_pr["total"].tail(7).mean()
        df_tail  = df_pr.tail(min(14, len(df_pr)))
        if len(df_tail) >= 3:
            slope, _ = np.polyfit(np.arange(len(df_tail)), df_tail["total"].values, 1)
        else:
            slope = 0.0
        slope = float(np.clip(slope, -baseline * 0.03, baseline * 0.03))

        # Proporsi jenis
        prop_b = (df_pr["bulat"].mean() / df_pr["total"].mean()) if df_pr["total"].mean() > 0 else 0.7
        prop_k = (df_pr["kecil"].mean() / df_pr["total"].mean()) if df_pr["total"].mean() > 0 else 0.2
        prop_kt = 1 - prop_b - prop_k

        nama_hari_id = {0:"Senin",1:"Selasa",2:"Rabu",3:"Kamis",
                         4:"Jumat",5:"Sabtu",6:"Minggu"}
        hari_terakhir = df_pr["tanggal"].max()
        prediksi = []
        for i in range(1, 8):
            tgl_p    = hari_terakhir + timedelta(days=i)
            wd       = tgl_p.weekday()
            pred_tot = max(0, round((baseline + slope * i) * faktor_hari.get(wd, 1.0)))
            prediksi.append({
                "Tanggal":      tgl_p.strftime("%d %b %Y"),
                "Hari":         nama_hari_id.get(wd, "–"),
                "Bulat (est)":  max(0, round(pred_tot * prop_b)),
                "Kecil (est)":  max(0, round(pred_tot * prop_k)),
                "Kotak (est)":  max(0, round(pred_tot * prop_kt)),
                "Total (est)":  pred_tot,
                "Est. Omset":   format_rupiah(int(
                    round(pred_tot * prop_b)  * HARGA["bulat"] +
                    round(pred_tot * prop_k)  * HARGA["kecil"] +
                    round(pred_tot * prop_kt) * HARGA["kotak"]
                ))
            })
        df_pred = pd.DataFrame(prediksi)

        # Grafik aktual + prediksi
        df_plot_aktual = df_pr.tail(14).copy()
        df_plot_aktual["tgl_str"] = df_plot_aktual["tanggal"].dt.strftime("%d %b")

        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=df_plot_aktual["tgl_str"], y=df_plot_aktual["total"],
            mode="lines+markers", name="Aktual (14 hari)",
            line=dict(color="#4CAF50", width=2.5), marker=dict(size=7),
            fill="tozeroy", fillcolor="rgba(76,175,80,0.12)"
        ))
        fig_pred.add_trace(go.Scatter(
            x=df_pred["Tanggal"], y=df_pred["Total (est)"],
            mode="lines+markers", name="Prediksi (7 hari)",
            line=dict(color="#FF9800", width=2.5, dash="dash"),
            marker=dict(size=8, symbol="diamond"),
            fill="tozeroy", fillcolor="rgba(255,152,0,0.10)"
        ))
        fig_pred.add_hline(
            y=avg_global, line_dash="dot", line_color="#9E9E9E",
            annotation_text=f"Rata-rata historis: {avg_global:.0f} pcs",
            annotation_position="bottom right"
        )
        n_aktual = len(df_plot_aktual)
        n_total  = n_aktual + len(df_pred)
        vline_x  = (n_aktual - 0.5) / (n_total - 1) if n_total > 1 else 0.5
        fig_pred.add_shape(
            type="line",
            xref="paper", yref="paper",
            x0=vline_x, x1=vline_x,
            y0=0, y1=1,
            line=dict(color="#F44336", width=1.5, dash="dash")
        )
        fig_pred.add_annotation(
            xref="paper", yref="paper",
            x=vline_x, y=1.02,
            text="← Aktual | Prediksi →",
            showarrow=False,
            font=dict(size=11, color="#F44336"),
            xanchor="center"
        )
        fig_pred.update_layout(
            title="Produksi Aktual (14 hari) vs Prediksi (7 hari ke depan)",
            xaxis_title="Tanggal", yaxis_title="Jumlah Produksi (pcs)",
            legend=dict(orientation="h", y=1.12),
            hovermode="x unified"
        )
        st.plotly_chart(fig_pred, use_container_width=True)

        # Tabel & KPI prediksi
        st.markdown("#### Tabel Prediksi Minggu Depan")
        st.dataframe(df_pred, use_container_width=True, hide_index=True)

        total_pred = int(df_pred["Total (est)"].sum())
        omset_pred = sum(
            r["Bulat (est)"] * HARGA["bulat"] +
            r["Kecil (est)"] * HARGA["kecil"] +
            r["Kotak (est)"] * HARGA["kotak"]
            for _, r in df_pred.iterrows()
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Produksi Prediksi (7 hari)", f"{total_pred:,} pcs")
        c2.metric("Estimasi Omset Minggu Depan",      format_rupiah(omset_pred))
        c3.metric("Rata-rata/hari (prediksi)",        f"{total_pred/7:,.0f} pcs")

        # Grafik rata-rata per hari
        st.markdown("---")
        nama_hari_list = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]
        df_fak = pd.DataFrame({
            "Hari":             [nama_hari_list[i] for i in range(7)],
            "Rata-rata (pcs)":  [round(avg_weekday.get(i, avg_global), 1) for i in range(7)]
        })
        fig_fak = px.bar(
            df_fak, x="Hari", y="Rata-rata (pcs)",
            title="Rata-rata Produksi per Hari dalam Seminggu (Data Historis)",
            color="Rata-rata (pcs)", color_continuous_scale="Greens",
            text="Rata-rata (pcs)"
        )
        fig_fak.add_hline(y=avg_global, line_dash="dot", line_color="gray",
                           annotation_text=f"Rata-rata global: {avg_global:.0f} pcs")
        fig_fak.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig_fak.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_fak, use_container_width=True)

        with st.expander("ℹ️ Cara kerja prediksi ini"):
            st.markdown(f"""
**Metode: Rolling Average + Pola Hari + Linear Trend**

Prediksi menggunakan 3 komponen yang digabung:

| Komponen | Penjelasan |
|---|---|
| **Baseline** | Rata-rata produksi 7 hari terakhir sebagai titik awal |
| **Trend** | Kecenderungan naik/turun dari 14 hari terakhir (regresi linear, dibatasi ±3%/hari) |
| **Faktor hari** | Bobot khusus tiap hari berdasarkan pola historis (misal: Senin selalu lebih tinggi) |

Proporsi jenis tempe dihitung dari rata-rata historis:
- Bulat: **{prop_b*100:.1f}%** | Kecil: **{prop_k*100:.1f}%** | Kotak: **{prop_kt*100:.1f}%**

*Prediksi ini bersifat estimasi statistik. Semakin banyak data historis, semakin akurat hasilnya.*
            """)


# ════════════════════════════════════════════════════════════════════
# TAB 5 – EXPORT
# ════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Export Laporan")
    st.markdown(f"#### 📥 Download Laporan {nama_bln}")

    if st.button("📊 Generate & Download Laporan Excel", type="primary"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            margin_pct_exp = (laba_bersih / total_masuk * 100) if total_masuk > 0 else 0
            pd.DataFrame({
                "Keterangan": ["Periode","Total Produksi (pcs)","Total Bulat","Total Kecil",
                                "Total Kotak","Total Omset","Total Pemasukan","Total Pengeluaran",
                                "Laba Bersih","Margin Laba (%)","Gaji Karyawan","Bahan Baku"],
                "Nilai": [nama_bln, f"{total_pcs:,}", f"{total_bulat:,}", f"{total_kecil:,}",
                           f"{total_kotak:,}", format_rupiah(total_omset),
                           format_rupiah(total_masuk), format_rupiah(total_keluar),
                           format_rupiah(laba_bersih), f"{margin_pct_exp:.1f}%",
                           format_rupiah(total_gaji_bln), format_rupiah(total_bb_bln)]
            }).to_excel(writer, sheet_name="Ringkasan", index=False)

            if not df_pesanan.empty:
                df_p = df_pesanan[["tanggal","nama_pelanggan","bulat","kecil","kotak",
                                    "total_harga","status_bayar","catatan"]].copy()
                df_p.columns = ["Tanggal","Pelanggan","Bulat","Kecil","Kotak",
                                 "Total Harga","Status Bayar","Catatan"]
                df_p.to_excel(writer, sheet_name="Pesanan", index=False)

            if not df_keu.empty:
                df_k = df_keu[["tanggal","jenis","kategori","keterangan","jumlah"]].copy()
                df_k.columns = ["Tanggal","Jenis","Kategori","Keterangan","Jumlah (Rp)"]
                df_k.to_excel(writer, sheet_name="Keuangan", index=False)

            if not df_bahan.empty:
                df_b = df_bahan[["tanggal","nama_bahan","jumlah","satuan",
                                  "harga_satuan","total_harga","keterangan"]].copy()
                df_b.columns = ["Tanggal","Bahan","Jumlah","Satuan","Harga/Satuan","Total","Ket"]
                df_b.to_excel(writer, sheet_name="Bahan Baku", index=False)

            if not df_gaji_bln.empty:
                df_g = df_gaji_bln[["nama","minggu_mulai","minggu_selesai",
                                     "jumlah_hadir","total_gaji","tanggal_bayar","status"]].copy()
                df_g.columns = ["Karyawan","Minggu Mulai","Minggu Selesai",
                                 "Hari Hadir","Total Gaji","Tgl Bayar","Status"]
                df_g.to_excel(writer, sheet_name="Gaji Karyawan", index=False)

            # Sheet prediksi (jika data cukup)
            try:
                if "df_pred" in dir() and not df_pred.empty:
                    df_pred.to_excel(writer, sheet_name="Prediksi", index=False)
            except Exception:
                pass

        output.seek(0)
        st.download_button(
            label="📥 Download Laporan Excel",
            data=output.getvalue(),
            file_name=f"laporan_tempe_{bln_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("✅ Laporan siap didownload!")

    st.markdown("---")
    st.markdown("#### 📋 Export CSV per Modul")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        if not df_pesanan.empty:
            st.download_button("📋 CSV Pesanan",
                                data=df_pesanan.to_csv(index=False).encode("utf-8"),
                                file_name=f"pesanan_{bln_str}.csv", mime="text/csv")
        if not df_keu.empty:
            st.download_button("💰 CSV Keuangan",
                                data=df_keu.to_csv(index=False).encode("utf-8"),
                                file_name=f"keuangan_{bln_str}.csv", mime="text/csv")
    with col_e2:
        if not df_bahan.empty:
            st.download_button("🌾 CSV Bahan Baku",
                                data=df_bahan.to_csv(index=False).encode("utf-8"),
                                file_name=f"bahan_baku_{bln_str}.csv", mime="text/csv")
        if not df_gaji_bln.empty:
            st.download_button("👷 CSV Gaji",
                                data=df_gaji_bln.to_csv(index=False).encode("utf-8"),
                                file_name=f"gaji_{bln_str}.csv", mime="text/csv")
