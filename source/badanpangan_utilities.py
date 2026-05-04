"""
FSVA Scraper Helper Functions
==============================
Fungsi-fungsi pembantu untuk crawling data FSVA.
"""

import re
import json
import base64
import zlib
from loguru import logger

BASE_URL = "https://fsva.badanpangan.go.id"
DEFAULT_IND = "x_comp18"

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
    "x_comp18": "Komposit",
    "x_1_p_ncpr": "Rasio",
    "x_2_p_poverty": "Persentase Miskin",
    "x_3_p_p_food": "Persentase RT Pangan",
    "x_4_p_electric": "Persentase RT Tanpa Listrik",
    "x_5_p_water": "Persentase RT Tanpa Air Bersih",
    "x_6_p_life": "AHH",
    "x_7_p_tenkes": "Rasio Tenkes",
    "x_8_p_fschool": "RLS Perempuan",
    "x_9_p_stunting": "Persentase Stunting",
    "x_61_p_morb": "Persentase Morbiditas",
    "x_2_p_lahan": "Rasio Lahan Pertanian",
    "x_3_p_sarana": "Rasio Sarana Pangan",
    "x_4_p_desil_1": "Rasio Desil1",
    "x_5_p_jalan": "Desa Tanpa Akses",
    "x_ikp": "IKP",
    "x_ikp_rank": "IKP Ranking",
}


@logger.catch(onerror=lambda e: exec('raise e'))
def parse_data_years(html: str, years: list[int]) -> dict[str, set[int]]:
    """
    Extract dataYears['KODE|YEAR'] = 1 dari HTML.
    Return {kode: {year, ...}}
    """
    result: dict[str, set[int]] = {}
    for m in re.finditer(r"dataYears\['(\d+)\|(\d{4})'\]\s*=\s*1", html):
        kode, year = m.group(1), int(m.group(2))
        if year in years:
            result.setdefault(kode, set()).add(year)
    return result


@logger.catch(onerror=lambda e: exec('raise e'))
def parse_opt_area_names(html: str) -> dict[str, str]:
    """
    Extract: optArea[KODE] = { "nama":" Nama Wilayah" };
    Return {kode_str: "Nama Wilayah"}
    """
    names: dict[str, str] = {}
    for m in re.finditer(r'optArea\[(\d+)\]\s*=\s*\{\s*"nama"\s*:\s*"([^"]+)"\s*\}', html):
        names[m.group(1)] = m.group(2).strip()
    return names

@logger.catch(onerror=lambda e: exec('raise e'))
def decompress_njson(js_text: str) -> dict | None:
    """Decompress NJSON blob dari base64 encoded data."""
    matches = re.findall(r"atob\('([A-Za-z0-9+/=]{100,})'\)", js_text)
    if not matches:
        return None
    for b64 in matches:
        try:
            raw = base64.b64decode(b64)
        except Exception:
            continue
        for wbits in (15, -15, 47, 31):
            try:
                text = zlib.decompress(raw, wbits).decode("utf-8", errors="replace")
                text = re.sub(r'[\r\n]+', ' ', text)
                return json.loads(text)
            except Exception:
                continue
    return None

@logger.catch(onerror=lambda e: exec('raise e'))
def extract_core_names(njson: dict | None) -> dict[str, str]:
    """Extract nama wilayah dari NJSON geometries."""
    names: dict[str, str] = {}
    if not njson:
        return names

    try:
        geoms = njson["objects"]["mapdata"]["geometries"]
    except (KeyError, TypeError):
        return names

    for geom in geoms:
        p = geom.get("properties", {})
        for id_f, (p1_f, p2_f) in [
            ("ID_Kab",  ("Provinsi", "Kabkot")),
            ("ID_Kec",  ("Provinsi", "Kecamatan")),
            ("ID_Desa", ("Provinsi", "Desa")),
        ]:
            id_val = p.get(id_f)
            if id_val is None:
                continue
            p1 = str(p.get(p1_f, "")).lower()
            p2 = str(p.get(p2_f, ""))
            names[str(id_val)] = f"{p1} - {p2}"
    return names

@logger.catch(onerror=lambda e: exec('raise e'))
def parse_core_i_blocks(js_text: str) -> dict[str, dict[str, dict]]:
    """
    Parse core_i blocks dari JavaScript response.
    Return {kode: {year: {field: val}}}
    """
    result: dict[str, dict[str, dict]] = {}

    pat_init   = re.compile(r'coreData\["(\w+)"\]\["(\w+)"\]\s*=\s*\{\}')
    pat_assign = re.compile(r'coreData\["(\w+)"\]\["(\w+)"\]\s*=\s*core_i')
    pat_field  = re.compile(r"core_i\['(\w+)'\]\s*=\s*'([^']*)'")
    pat_field2 = re.compile(r'core_i\["(\w+)"\]\s*=\s*"([^"]*)"')

    cur_kode: str | None = None
    cur_year: str | None = None
    cur_fields: dict = {}

    def flush():
        nonlocal cur_kode, cur_year, cur_fields
        if cur_kode and cur_year and cur_fields:
            result.setdefault(cur_kode, {})[cur_year] = dict(cur_fields)
        cur_fields = {}

    for line in js_text.splitlines():
        line = line.strip()
        if not line:
            continue

        m = pat_init.search(line)
        if m:
            flush()
            cur_kode, cur_year = m.group(1), m.group(2)
            continue

        m = pat_assign.search(line)
        if m:
            k, y = m.group(1), m.group(2)
            if cur_fields:
                result.setdefault(k, {})[y] = dict(cur_fields)
            cur_fields = {}
            cur_kode, cur_year = k, y
            continue

        m = pat_field.search(line) or pat_field2.search(line)
        if m:
            cur_fields[m.group(1)] = m.group(2)

    flush()
    return result

@logger.catch(onerror=lambda e: exec('raise e'))
def build_rows(core_data: dict, core_names: dict, year: int) -> list[dict]:
    """
    Build rows dari coreData untuk satu tahun.
    Return list of dict dengan struktur yang rapi.
    """
    year_str = str(year)
    rows = []
    for kode, year_map in core_data.items():
        chain = year_map.get(year_str)
        if chain is None:
            continue
        nama = core_names.get(kode) or f"Kode_{kode}"

        row = {
            "Wilayah": nama,
            "No": kode, 
            "Tahun": year,
            "Komposit": chain.get("x_comp18", ""),
            "Rasio Luas Lahan Pertanian": chain.get("x_2_lahan", ""),
            "Rasio Sarana Pangan": chain.get("x_3_sarana", ""),
            "Rasio Penduduk Miskin Desil 1": chain.get("x_4_desil_1", ""),
            "Desa Tanpa Akses Penghubung": chain.get("x_5_jalan", ""),
            "Rasio Rumah Tangga Tanpa Air Bersih": chain.get("x_5_water", ""),
            "Rasio Tenaga Kesehatan": chain.get("x_7_tenkes", ""),
            "Indeks Ketahanan Pangan (IKP)": chain.get("x_ikp", ""),
            "IKP Ranking": chain.get("x_ikp_rank", "")
        }

        rows.append(row)
    return rows

@logger.catch(onerror=lambda e: exec('raise e'))
def safe_filename(name: str) -> str:
    """Sanitize string untuk nama file."""
    name = name.strip().replace(" ", "_").replace("/", "-")
    name = re.sub(r'[\\:*?"<>|]', '', name)
    return name[:80]

@logger.catch(onerror=lambda e: exec('raise e'))
def find_kabupaten_by_name(kab_codes: dict, opt_names: dict, search_name: str) -> dict[str, set[int]]:
    """
    Cari kabupaten berdasarkan nama (case-insensitive, partial match).
    Return dict dengan format sama seperti kab_codes.
    """
    search_lower = search_name.lower()
    matched = {}

    for kode, years in kab_codes.items():
        nama = opt_names.get(kode, "")
        print(f"nama_kab: {nama}")
        if search_lower in nama.lower():
            matched[kode] = years

    return matched