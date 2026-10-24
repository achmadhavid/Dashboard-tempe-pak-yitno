# 🫘 Dashboard Pabrik Tempe Pak Yitno

Dashboard analitik berbasis web untuk manajemen pabrik tempe.

## Fitur Utama
- **📋 Pesanan & Pelanggan** – Input pesanan harian, 19 pelanggan tetap + tidak tetap, status tagihan
- **💰 Keuangan** – Pemasukan, pengeluaran, laba rugi, grafik bulanan
- **👷 Gaji Karyawan** – Absensi harian, kalkulasi gaji mingguan, riwayat pembayaran
- **🌾 Bahan Baku & Ampas** – Manajemen kontrak ampas, notifikasi hampir habis, pembelian bahan
- **📊 Laporan** – Grafik produksi, keuangan, analisis pelanggan, export Excel & CSV

## Cara Menjalankan

### 1. Install Python (versi 3.9 ke atas)
Download di https://python.org

### 2. Install dependensi
Buka terminal/command prompt di folder ini, lalu ketik:
```
pip install -r requirements.txt
```

### 3. Jalankan aplikasi
```
streamlit run app.py
```

### 4. Buka di browser
Secara otomatis akan terbuka di http://localhost:8501

## Struktur Folder
```
dashboard_tempe_pakyitno/
├── app.py                    ← Halaman utama (home)
├── requirements.txt          ← Daftar library
├── database/
│   └── db.py                 ← Koneksi & fungsi database SQLite
├── pages/
│   ├── 1_Pesanan.py          ← Modul pesanan & pelanggan
│   ├── 2_Keuangan.py         ← Modul keuangan
│   ├── 3_Gaji_Karyawan.py    ← Modul gaji karyawan
│   ├── 4_Bahan_Baku.py       ← Modul bahan baku & ampas
│   └── 5_Laporan.py          ← Modul laporan & grafik
├── utils/
│   └── helpers.py            ← Fungsi pembantu (format Rupiah, hitung total, dll)
└── data/
    └── tempe.db              ← Database SQLite (dibuat otomatis)
```

## Harga Tempe
- Bulat : Rp 800/pcs
- Kecil : Rp 200/pcs  
- Kotak : Rp 300/pcs

## Catatan
- Database tersimpan lokal di file `data/tempe.db`
- Data 19 pelanggan tetap sudah otomatis terisi saat pertama dijalankan
- Backup rutin folder `data/` untuk keamanan data
