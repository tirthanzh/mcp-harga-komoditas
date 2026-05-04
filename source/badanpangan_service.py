from source.base_service import BaseService, RawResponse
from source.badanpangan_utilities import BASE_URL, INDICATOR_FIELDS, FIELD_LABELS, DEFAULT_IND, decompress_njson, parse_core_i_blocks, parse_data_years, parse_opt_area_names, build_rows, extract_core_names, find_kabupaten_by_name
import re
from datetime import datetime, timedelta
from loguru import logger
from asyncio import sleep

class BadanpanganService(BaseService):
    def __init__(self):
        super().__init__({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
            "Referer": BASE_URL + "/",
        }, timeout=120)
        # self._cached_main_page: tuple[RawResponse, datetime] = None
    
    async def fetch_main_page(self) -> RawResponse:
        # if self._cached_main_page and (self._cached_main_page[1] + timedelta(hours=1)) > datetime.now():
        #     return self._cached_main_page[0]
        # self._cached_main_page = (await self.client_get(BASE_URL), datetime.now())
        # await sleep(0.5)
        # return self._cached_main_page[0]
        return await self.client_get(BASE_URL)
        
    async def get_rand_link(self) -> str:
        html = (await self.fetch_main_page()).text()
        m = re.search(r'var\s+randLink\s*=\s*["\']([a-f0-9]{32})["\']', html)
        if not m:
            m = re.search(r'\?([a-f0-9]{32})', html)
        if not m:
            raise RuntimeError("randLink tidak ditemukan")
        return m.group(1)
    
    async def fetch_js(self, rand: str, sip: int, dip: int, tip: int, ind: str) -> str:
        """Fetch data dari micro_draw endpoint."""
        url = f"{BASE_URL}/micro_draw.php?rand={rand}&sip={sip}&dip={dip}&tip={tip}&ind={ind}"
        return (await self.client_get(url)).text()
    
    # Master method

    @logger.catch(onerror=lambda e: exec('raise e'))
    async def process_kabupaten(
        self,
        kab_kode: str,
        years: list[int],
        available_years: set[int],
        ind: str
    ) -> list[dict]:
        """
        Proses data untuk satu kabupaten.
        Return list of rows data.
        """
        all_rows = []

        for year in years:
            if year not in available_years:
                logger.error(f"[{year}] tidak ada data → skip")
                continue

            # Refresh rand link sebelum tiap request
            try:
                rand = await self.get_rand_link()
            except Exception as e:
                logger.error(f"[{year}] ERROR refresh rand: {e}")
                continue

            try:
                js_text = await self.fetch_js(rand, int(kab_kode), 3, year, ind)
                await sleep(0.5)
            except Exception as e:
                logger.error(f"[{year}] ERROR fetch: {e}")
                continue

            if "Key Invalid" in js_text or (len(js_text) < 300 and "alert" in js_text.lower()):
                logger.warning(f"[{year}] Server reject → skip")
                continue

            if "coreData" not in js_text:
                logger.warning(f"[{year}] coreData tidak ada → skip")
                continue

            # coreNames dari blob
            njson = decompress_njson(js_text)
            core_names = extract_core_names(njson) if njson else {}

            # coreData
            core_data = parse_core_i_blocks(js_text)
            if not core_data:
                logger.warning(f"[{year}] parse coreData gagal → skip")
                continue

            rows = build_rows(core_data, core_names, year, INDICATOR_FIELDS, FIELD_LABELS)
            logger.info(f"[{year}] {len(rows)} baris (dari {len(core_data)} kode area)")
            all_rows.extend(rows)
        
        return all_rows
    

    @logger.catch(onerror=lambda e: exec('raise e'))
    async def fetch_statistik_dareah_badan_pangan_origin(self, province: str, years: list[int]):
        html = (await self.fetch_main_page()).text()
        data_years = parse_data_years(html, years)
        kab_codes = {k: yrs for k, yrs in data_years.items() if len(k) == 6}
        logger.info(f"[+] Total kabupaten/kota dengan data: {len(kab_codes)}")
        
        opt_names = parse_opt_area_names(html)
        logger.info(f"[*] Mencari kabupaten/kota dengan provinsi: '{province}'")
        logger.info(f"[*] Mencari kabupaten/kota dengan nama: '{province}'")
        matched_kab = find_kabupaten_by_name(kab_codes, opt_names, province)

        if not matched_kab:
            logger.info(f"ERROR: Tidak ditemukan kabupaten/kota dengan nama '{province}'")
            logger.info(f"\nKabupaten/kota yang tersedia:")
            for kode, nama in sorted(opt_names.items()):
                if len(kode) == 6:  # Hanya kabupaten/kota
                    logger.info(f"  - {nama} ({kode})")
            raise Exception("not found")

        logger.info(f"[+] Ditemukan {len(matched_kab)} kabupaten/kota yang cocok:")
        # for kode in sorted(matched_kab.keys()):
        #     nama = opt_names.get(kode, f"Kode_{kode}")
        #     logger.info(f"  - {nama} ({kode})")
        
        all_data = []
        total_processed = 0
        total_skipped = 0

        for kab_kode, available_years in sorted(matched_kab.items()):
            kab_name = opt_names.get(kab_kode, f"Kode_{kab_kode}")
            total_processed += 1

            logger.info(f"\n  [{total_processed}/{len(matched_kab)}] {kab_kode} — {kab_name}")
            logger.info(f"Tahun tersedia: {sorted(available_years)}")

            # Proses data untuk kabupaten ini
            try:
                rows = await self.process_kabupaten(
                    kab_kode, years, available_years, DEFAULT_IND
                )
            except Exception as e:
                logger.error(f"ERROR: Gagal memproses {kab_name}: {e}")
                total_skipped += 1
                continue

            if rows:
                all_data.extend(rows)
                logger.info(f"[+] Berhasil: {len(rows)} baris")
            else:
                logger.warning(f"[WARN] Tidak ada baris untuk {kab_name}")
                total_skipped += 1

        # ── Step 4: simpan hasil ke JSON ───────────────────────────────
        if not all_data:
            logger.error("ERROR: Tidak ada data yang berhasil diambil")
            raise Exception("not found")
            

        # Buat structure JSON yang rapi
        result = {
            "metadata": {
                "daerah_pencarian": province,
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

        logger.info(f"[DONE] Crawling selesai!")
        logger.info(f"  - Total kabupaten diproses: {total_processed}")
        logger.info(f"  - Total kabupaten dilewati: {total_skipped}")
        logger.info(f"  - Total baris data: {len(all_data)}")

        return result







    

    