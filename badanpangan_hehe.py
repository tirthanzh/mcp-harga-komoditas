"""
FSVA Scraper v5 - Dynamic Parameters
=====================================
Output: JSON format dengan parameter dinamis.

Usage:
    python test.py --daerah "Aceh" --tahun 2024,2025
    python test.py -d "Jakarta" -t 2024 -o output.json

pip install requests
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

from helpers import (
    fetch_main_page,
    parse_data_years,
    parse_opt_area_names,
    get_rand_link,
    fetch_js,
    decompress_njson,
    extract_core_names,
    parse_core_i_blocks,
    build_rows,
    safe_filename,
    find_kabupaten_by_name,
)

# Configuration
BASE_URL = "https://fsva.badanpangan.go.id"
DEFAULT_OUTPUT_DIR = "test-out"
DEFAULT_IND = "x_comp18"
REQUEST_DELAY = 2.0  # detik antar request ke micro_draw
PAGE_DELAY = 1.0  # detik setelah ambil halaman utama

INDICATOR_FIELDS = [
    "x_comp18",
    "x_1_p_ncpr",
    "x_2_p_poverty",
    "x_3_p_p_food",
    "x_4_p_electric",
    "x_5_p_water",
    "x_6_p_life",
    "x_7_p_tenkes",
    "x_8_p_fschool",
    "x_9_p_stunting",
    "x_61_p_morb",
    "x_2_p_lahan",
    "x_3_p_sarana",
    "x_4_p_desil_1",
    "x_5_p_jalan",
    "x_ikp",
    "x_ikp_rank",
]

FIELD_LABELS = {
    "x_comp18": "Komposit_FSVA",
    "x_1_p_ncpr": "Rasio_NCPR",
    "x_2_p_poverty": "Persen_Miskin",
    "x_3_p_p_food": "Persen_RT_Pangan65",
    "x_4_p_electric": "Persen_RT_TanpaListrik",
    "x_5_p_water": "Persen_RT_TanpaAirBersih",
    "x_6_p_life": "AHH",
    "x_7_p_tenkes": "Rasio_Tenkes",
    "x_8_p_fschool": "RLS_Perempuan",
    "x_9_p_stunting": "Persen_Stunting",
    "x_61_p_morb": "Persen_Morbiditas",
    "x_2_p_lahan": "Rasio_LahanPertanian",
    "x_3_p_sarana": "Rasio_SaranaPangan",
    "x_4_p_desil_1": "Rasio_Desil1",
    "x_5_p_jalan": "Desa_TanpaAkses",
    "x_ikp": "IKP",
    "x_ikp_rank": "IKP_Ranking",
}


def save_json(data: Dict, filepath: str):
    """Simpan data ke format JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_session() -> requests.Session:
    """Buat dan konfigurasi HTTP session."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
        "Referer": BASE_URL + "/",
    })
    return session


def process_kabupaten(
    session: requests.Session,
    kab_kode: str,
    kab_name: str,
    years: List[int],
    available_years: set[int],
    ind: str
) -> List[Dict]:
    """
    Proses data untuk satu kabupaten.
    Return list of rows data.
    """
    all_rows = []

    for year in years:
        if year not in available_years:
            print(f"    [{year}] tidak ada data → skip")
            continue

        # Refresh rand link sebelum tiap request
        try:
            rand = get_rand_link(session, BASE_URL)
        except Exception as e:
            print(f"    [{year}] ERROR refresh rand: {e}")
            continue
        time.sleep(0.5)

        try:
            js_text = fetch_js(session, BASE_URL, rand, int(kab_kode), 3, year, ind)
        except requests.RequestException as e:
            print(f"    [{year}] ERROR fetch: {e}")
            continue

        if "Key Invalid" in js_text or (len(js_text) < 300 and "alert" in js_text.lower()):
            print(f"    [{year}] Server reject → skip")
            continue

        if "coreData" not in js_text:
            print(f"    [{year}] coreData tidak ada → skip")
            continue

        # coreNames dari blob
        njson = decompress_njson(js_text)
        core_names = extract_core_names(njson) if njson else {}

        # coreData
        core_data = parse_core_i_blocks(js_text)
        if not core_data:
            print(f"    [{year}] parse coreData gagal → skip")
            continue

        rows = build_rows(core_data, core_names, year, INDICATOR_FIELDS, FIELD_LABELS)
        print(f"    [{year}] {len(rows)} baris (dari {len(core_data)} kode area)")
        all_rows.extend(rows)

        time.sleep(REQUEST_DELAY)

    return all_rows


def main():
    parser = argparse.ArgumentParser(
        description="FSVA Scraper - Crawling data pangan dengan parameter dinamis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python test.py --daerah "Aceh" --tahun 2024,2025
  python test.py -d "Jakarta" -t 2024 -o jakarta_2024.json
  python test.py --daerah "Bandung" --tahun 2024,2025,2026
        """
    )

    parser.add_argument(
        "--daerah", "-d",
        type=str,
        required=True,
        help="Nama daerah (kabupaten/kota) yang akan dicari"
    )

    parser.add_argument(
        "--tahun", "-t",
        type=str,
        default="2024,2025,2026",
        help="Tahun yang akan dicari (comma-separated, default: 2024,2025,2026)"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Nama file output JSON (default: <daerah>_<tahun>.json)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Direktori output (default: {DEFAULT_OUTPUT_DIR})"
    )

    parser.add_argument(
        "--ind",
        type=str,
        default=DEFAULT_IND,
        help=f"Indikator utama (default: {DEFAULT_IND})"
    )

    args = parser.parse_args()

    # Parse tahun
    try:
        years = [int(t.strip()) for t in args.tahun.split(",")]
    except ValueError:
        print("ERROR: Format tahun tidak valid. Gunakan format: 2024,2025,2026")
        sys.exit(1)

    # Setup output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Setup output filename
    if args.output:
        output_filename = args.output
        if not output_filename.endswith(".json"):
            output_filename += ".json"
    else:
        daerah_safe = safe_filename(args.daerah)
        years_str = "_".join(map(str, years))
        output_filename = f"{daerah_safe}_{years_str}.json"

    output_path = os.path.join(args.output_dir, output_filename)

    # Setup session
    session = create_session()

    print(f"[*] FSVA Scraper v5 - Dynamic Parameters")
    print(f"[*] Daerah: {args.daerah}")
    print(f"[*] Tahun: {years}")
    print(f"[*] Output: {output_path}")
    print(f"{'='*55}")

    # ── Step 1: ambil info dari halaman utama ──────────────────
    print("[*] Fetch halaman utama ...")
    try:
        html, rand = fetch_main_page(session, BASE_URL)
    except Exception as e:
        print(f"ERROR: Gagal fetch halaman utama: {e}")
        sys.exit(1)

    time.sleep(PAGE_DELAY)

    # Parse dataYears: {kode_kab: {2024, 2025, 2026}}
    data_years = parse_data_years(html, years)
    # Hanya kode 6-digit = kabupaten/kota (dip=3 butuh kode kab)
    kab_codes = {k: yrs for k, yrs in data_years.items() if len(k) == 6}
    print(f"[+] Total kabupaten/kota dengan data: {len(kab_codes)}")

    # Parse nama dari optArea di HTML
    opt_names = parse_opt_area_names(html)

    # ── Step 2: filter kabupaten berdasarkan nama ────────────────
    print(f"[*] Mencari kabupaten/kota dengan nama: '{args.daerah}'")
    matched_kab = find_kabupaten_by_name(kab_codes, opt_names, args.daerah)

    if not matched_kab:
        print(f"ERROR: Tidak ditemukan kabupaten/kota dengan nama '{args.daerah}'")
        print(f"\nKabupaten/kota yang tersedia:")
        for kode, nama in sorted(opt_names.items()):
            if len(kode) == 6:  # Hanya kabupaten/kota
                print(f"  - {nama} ({kode})")
        sys.exit(1)

    print(f"[+] Ditemukan {len(matched_kab)} kabupaten/kota yang cocok:")
    for kode in sorted(matched_kab.keys()):
        nama = opt_names.get(kode, f"Kode_{kode}")
        print(f"  - {nama} ({kode})")

    # ── Step 3: proses data per kabupaten ────────────────────────
    all_data = []
    total_processed = 0
    total_skipped = 0

    for kab_kode, available_years in sorted(matched_kab.items()):
        kab_name = opt_names.get(kab_kode, f"Kode_{kab_kode}")
        total_processed += 1

        print(f"\n  [{total_processed}/{len(matched_kab)}] {kab_kode} — {kab_name}")
        print(f"    Tahun tersedia: {sorted(available_years)}")

        # Proses data untuk kabupaten ini
        try:
            rows = process_kabupaten(
                session, kab_kode, kab_name, years, available_years, args.ind
            )
        except Exception as e:
            print(f"    ERROR: Gagal memproses {kab_name}: {e}")
            total_skipped += 1
            continue

        if rows:
            all_data.extend(rows)
            print(f"    [+] Berhasil: {len(rows)} baris")
        else:
            print(f"    [WARN] Tidak ada baris untuk {kab_name}")
            total_skipped += 1

    # ── Step 4: simpan hasil ke JSON ───────────────────────────────
    if not all_data:
        print(f"\n{'='*55}")
        print("ERROR: Tidak ada data yang berhasil diambil")
        sys.exit(1)

    # Buat structure JSON yang rapi
    result = {
        "metadata": {
            "daerah_pencarian": args.daerah,
            "kabupaten_kota_ditemukan": [
                {
                    "kode": kode,
                    "nama": opt_names.get(kode, f"Kode_{kode}")
                }
                for kode in sorted(matched_kab.keys())
            ],
            "tahun_diproses": years,
            "tanggal_crawling": datetime.now().isoformat(),
            "total_baris": len(all_data),
            "total_kabupaten_diproses": total_processed,
            "total_kabupaten_dilewati": total_skipped
        },
        "data": all_data
    }

    save_json(result, output_path)

    print(f"\n{'='*55}")
    print(f"[DONE] Crawling selesai!")
    print(f"  - Total kabupaten diproses: {total_processed}")
    print(f"  - Total kabupaten dilewati: {total_skipped}")
    print(f"  - Total baris data: {len(all_data)}")
    print(f"  - Output file: {output_path}")


if __name__ == "__main__":
    main()