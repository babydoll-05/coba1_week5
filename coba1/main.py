import streamlit as st
import pandas as pd
import json
from io import BytesIO
import csv
import io

# --- 1. Konfigurasi Awal dan Data Default CSV ---
st.set_page_config(layout="wide", page_title="Warung Makan Pintar")

# Data Menu Default (menggunakan format CSV dengan pemisah ';')
SAMPLE_CSV = """kategori;nama;harga
Makanan;Ayam Bakar;25000
Makanan;Nasi Goreng;18000
Minuman;Es Teh;5000
Minuman;Jus Alpukat;12000
""" 

# 3. Definisikan fungsi untuk membaca CSV
def load_csv(file_like):
    try:
        # Untuk kasus file upload atau string (jika ada getvalue)
        text = io.StringIO(file_like.getvalue().decode("utf-8"))
    except AttributeError:
        # Untuk kasus string langsung (seperti SAMPLE_CSV)
        text = io.StringIO(file_like)
        
    # Menggunakan DictReader untuk membaca data dengan pemisah ';'
    reader = csv.DictReader(text, delimiter=';')
    rows = []
    
    for row in reader:
        # Membersihkan spasi di sekitar nilai dan memastikan harga adalah integer
        try:
            # Menggunakan _to_number untuk validasi awal saat memuat data default
            # Meskipun Data Editor akan memvalidasi ulang
            harga = int((row.get("harga") or "0").strip())
        except ValueError:
            harga = 0
            
        rows.append({
            # Pastikan kunci yang digunakan sesuai dengan data editor
            "kategori": (row.get("kategori") or "").strip(),
            "nama": (row.get("nama") or "").strip(),
            "harga": harga,
        })
        
    return rows

# --- 2. Inisialisasi Session State untuk Persistensi Data ---

# Memuat data default ke dalam rows
initial_rows = load_csv(SAMPLE_CSV)

# Menggunakan session state untuk menyimpan data agar data tidak hilang saat diedit
if 'menu_rows' not in st.session_state:
    st.session_state.menu_rows = initial_rows

# Konversi list of dicts (rows) ke DataFrame agar mudah diproses oleh Pandas
# Ini dilakukan sekali saat aplikasi pertama kali dimuat (Digunakan untuk Ekspor CSV)
if 'menu_df' not in st.session_state:
    st.session_state.menu_df = pd.DataFrame(st.session_state.menu_rows)

# --- Fungsi Konversi dan Perhitungan Totals ---

def _to_number(x):
    """Mengkonversi nilai ke float, mengabaikan nilai non-numerik atau negatif."""
    try:
        # Menggunakan str(x) untuk menangani input dari Data Editor (yang bisa berupa int atau float)
        v = float(str(x).strip())
        # Pastikan harga tidak negatif
        return v if v >= 0 else None 
    except:
        # Mengabaikan string kosong, None, atau teks non-numerik
        return None

def compute_totals(rows):
    """Menghitung total harga per kategori dan total keseluruhan."""
    totals = {}
    total_all = 0.0
    for r in rows:
        # Mendapatkan kategori, menggunakan "Tidak diketahui" jika kosong
        cat = (r.get("kategori") or "").strip() or "Tidak diketahui"
        
        # Mendapatkan harga menggunakan fungsi konversi
        val = _to_number(r.get("harga"))
        
        if val is None:
            # Abaikan baris yang harga-nya tidak valid
            continue
            
        # Akumulasi total per kategori
        totals[cat] = totals.get(cat, 0.0) + val
        # Akumulasi total keseluruhan
        total_all += val
        
    return totals, total_all

# --- 3. Fungsi Utility untuk Ekspor ---

@st.cache_data
def convert_df_to_csv(df):
    # Konversi DataFrame ke format CSV (untuk menu) dengan pemisah ';'
    return df.to_csv(index=False, sep=';').encode('utf-8')

@st.cache_data
def convert_summary_to_json(summary_dict):
    """Konversi dictionary hasil perhitungan (totals) ke JSON string."""
    # Menggunakan json.dumps untuk format JSON yang lebih fleksibel
    json_string = json.dumps(summary_dict, indent=4)
    return json_string.encode('utf-8')


# --- APLIKASI UTAMA ---
st.title('Warung Makan "Pintar"')
st.caption("Pengelolaan Daftar Menu dan Ekspor CSV/JSON.")

# 4. Data Editor Configuration
st.subheader("📝 Data Menu (Editable)")

# Mapping semua kolom pada data editor
column_config = {
    # Selectbox untuk kategori dengan opsi terbatas
    "kategori": st.column_config.SelectboxColumn(
        "kategori", 
        options=["Makanan", "Minuman", "Lainnya"], 
        required=True
    ),
    # Text input untuk nama menu
    "nama": st.column_config.TextColumn("nama", required=True),
    # Number input untuk harga
    "harga": st.column_config.NumberColumn(
        "harga", 
        min_value=0, 
        step=1000, 
        format="Rp %d"
    ),
}

# Tampilkan Data Editor
edited_rows = st.data_editor(
    st.session_state.menu_rows,
    num_rows="dynamic", # Memungkinkan penambahan/penghapusan baris
    key="data_editor",
    use_container_width=True,
    column_config=column_config
)

# Update Session State dengan hasil edit dari Data Editor
st.session_state.menu_rows = edited_rows
# Konversi kembali ke DataFrame untuk ekspor CSV
current_df = pd.DataFrame(st.session_state.menu_rows)


# --- 5. Ringkasan Total Harga per Kategori ---
st.divider()
st.header("📊 Ringkasan Harga")

# Jalankan fungsi perhitungan total
totals, total_all = compute_totals(edited_rows)

col_a, col_b = st.columns(2)

with col_a:
    st.write("**Total harga per kategori:**")
    if totals:
        # Konversi hasil dictionary totals ke list of dicts untuk st.table
        summary_list = [{"kategori": k, "total": v} for k, v in totals.items()]
        
        # Menampilkan tabel ringkasan
        st.table(summary_list)
        
    else:
        st.info("Belum ada data menu yang valid.")

with col_b:
    # Menampilkan total keseluruhan menggunakan st.metric
    # Menggunakan format yang diminta: 2 desimal dengan pemisah ribuan
    st.metric(
        "Total semua", 
        f"Rp {round(total_all, 2):,.2f}" 
    )

# --- 6. Bagian Ekspor ---
st.divider()
st.header("📤 Ekspor Data")
col1, col2 = st.columns(2)

# Cek apakah ada data yang berhasil dikonversi
data_valid = not current_df.empty and (total_all > 0 or not totals)

if data_valid:
    # EKSPOR MENU (CSV)
    csv_file = convert_df_to_csv(current_df)
    with col1:
        st.subheader("Ekspor Menu dan Ringkasan")
        st.download_button(
            label="⬇️ Unduh CSV (hasil edit)",
            data=csv_file,
            file_name='menu_warung_teredit.csv',
            mime='text/csv',
            use_container_width=True
        )

    # EKSPOR RINGKASAN (JSON) menggunakan data totals
    json_file = convert_summary_to_json(totals)
    with col2:
        st.subheader("Ekspor Ringkasan")
        st.download_button(
            label="⬇️ Unduh JSON (ringkasan)",
            data=json_file,
            file_name='ringkasan_harga_kategori.json',
            mime='application/json',
            use_container_width=True
        )
else:
    st.warning("Tidak ada data menu yang valid untuk diekspor.")

st.info("Catatan: Aplikasi ini menghitung total akumulasi Harga dari semua menu yang ada di setiap kategori.")
