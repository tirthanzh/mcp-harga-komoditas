from source.base_service import BaseService, dict_factory, Lock
from typing import Any, Literal
from time import time
from datetime import datetime
from loguru import logger
from asyncio import gather


def epoch() -> int:
    return int(time() * 1000)

type LevelLocation = Literal["province", "city", "all"]

class PhipsService(BaseService):
    def __init__(self):
        super().__init__(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.0.0 Safari/537.36"
                ),
                "X-Requested-With": "XMLHttpRequest",
                # "XSRF-TOKEN": "CfDJ8G-QVzELtjBMsytlF7fKM_MF2HCgQMxm1GQPmvZc0wtztRtCHdE1Bxu-z7b4PPLkUZuZTWYNfDqrUXLywR73JShUDcabuH9mk6UqHgLTTwx2f56bX-hbRVd3OWDUpjYSEN0gDoBJBS25gP-EmR0YQ4Q",
                "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            },
            # {
            #     "WSAntiforgeryCookie": "CfDJ8G-QVzELtjBMsytlF7fKM_PV3BodAWihARWeB9Donop4Qt5A4H7uBEzjX_oczu1sKq6EXdEIU0BR5TAWBA2QzxJANKG5QzVPy76Q2cXJcdLBhIc_hOBUEd4utRG7zSHIGsBBRjvSEWys8KGAZzPS2CU",
            #     "TS01a661ae": "0199782b6f39c2b0a2268000ab5a3486e8642e8e8efdd181688510679c0795972c2376f0f3f25884a40d5b7714dfdf69c319025cec605eab1e0ef14018fac413bbadcfd4e9",
            #     "TS0dddebd2027": "08f7caa0deab2000b82cec9eef7e7769b0245a3be3e3dc1c66659bf45a0bf88b03cf230a25dfd15108ace41e51113000a2d7b79ab158cd4d807379c126ebc4c9eb410beebe8d61b31c719e6b3540e5672b2365ab573057e6c400b28813ee3dc0",
            #     "TS01441bdb": "0199782b6fd297ada34fe8f7882388430a94109ae0abf01ea4ced549cfb278fd93eb4e94457b3c9b2ff0fa46482e4071de75732882",
            # }
        )

        self.base_url = "https://www.bi.go.id/hargapangan/WebSite/TabelHarga"


    @logger.catch(onerror=lambda e: exec('raise e'))
    async def list_price_type_origin(self) -> list[dict[str, Any]]:
        return (await self.client_get(self.base_url + "/GetRefPriceType", {
            "_": epoch()
        })).json()["data"]
    
    @logger.catch(onerror=lambda e: exec('raise e'))
    async def list_provice_origin(self) -> list[dict[str, Any]]:
        return (await self.client_get(self.base_url + "/GetRefProvince", {
            "_": epoch()
        })).json()["data"]
    
    @logger.catch(onerror=lambda e: exec('raise e'))
    async def list_city_origin(self, province_id: int, price_type_id: int) -> list[dict[str, Any]]:
        return (await self.client_get(self.base_url + "/GetRefRegency", {
            "price_type_id": price_type_id,
            "ref_prov_id": province_id,
            "_": epoch()
        })).json()["data"]
    
    @logger.catch(onerror=lambda e: exec('raise e'))
    async def list_comodities_origin(self) -> list[dict[str, Any]]:
        return (await self.client_get(self.base_url + "/GetRefCommodityAndCategory", {
            "_": epoch()
        })).json()["data"]
    
    @logger.catch(onerror=lambda e: exec('raise e'))
    async def get_price_comodity_origin(
        self,
        comodity_ids: list[str],
        price_type_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        province_id: int | None = None,
        city_id: int | None = None
    ) -> list[dict[str, Any]]:
        today = datetime.now().strftime("%Y-%m-%d")
        start_date = start_date or today
        end_date = end_date or today
        return (await self.client_get(self.base_url + "/GetGridDataDaerah", {
            "price_type_id": price_type_id or "",
            "comcat_id": ",".join(comodity_ids) or "",
            "province_id": province_id or "",
            "regency_id": city_id or "",
            "market_id": "",
            "tipe_laporan": "1",
            "start_date": start_date,
            "end_date": end_date,
            "_": epoch()
        })).json()["data"]
    
    @logger.catch(onerror=lambda e: exec('raise e'))
    async def init_sqlite(self):
        from sqlite3 import connect
        self.sqlite = connect(":memory:")
        self.sqlite.row_factory = dict_factory

        c = self.sqlite.cursor()
        with open("sqlite_script.sql") as f:
            c.executescript(f.read())
        
        self.sqlite.commit()
        c.close()
    
    @logger.catch(onerror=lambda e: exec('raise e'))
    async def update_list_comodity_table(self):
        comodities = await self.list_comodities_origin()
        column = ("id", "cat_id", "denomination", "sort", "name")

        sql = f"INSERT INTO comodity ({', '.join(column)}) VALUES ({', '.join('?' for _ in range(len(column)))}) ON CONFLICT(id) DO UPDATE SET {', '.join(f'{c}=excluded.{c}' for c in tuple(column)[1:])}"
        values = [tuple(row[k] for k in column) for row in comodities]
        c = self.sqlite.cursor()
        c.execute("DELETE FROM comodity_search")
        c.executemany(sql, values)
        self.sqlite.commit()
        c.executemany("INSERT INTO comodity_search (id, name) VALUES (?, ?)", [(row[0], row[4]) for row in values])
        self.sqlite.commit()
        c.close()

    @logger.catch(onerror=lambda e: exec('raise e'))
    async def update_list_location_table(self):
        from asyncio import gather

        locations_fulltext: list[tuple[str, str]] = list()
        tasks = list()
        conflict_sql = f"ON CONFLICT(province_id, city_id) DO NOTHING"
        c = self.sqlite.cursor()
        async def merge_province_and_city(province: dict):
            c.execute(
                f"INSERT INTO location (province_id, province_name, city_id, city_name) VALUES (?, ?, ?, ?) {conflict_sql}",
                (province["id"], province["name"], -1, "-")
            )
            locations_fulltext.append((f"{province['id']}", province["name"]))
            cities = await self.list_city_origin(province_id=province["id"], price_type_id=1)
            if cities:
                c.executemany(
                    f"INSERT INTO location (province_id, province_name, city_id, city_name) VALUES (?, ?, ?, ?) {conflict_sql}",
                    [(province["id"], province["name"], city["id"], city["name"]) for city in cities]
                )
                locations_fulltext.extend((f"{province['id']}:{city['id']}", f"{province['name']}, {city['name']}") for city in cities)
            

        for province in await self.list_provice_origin():
            tasks.append(merge_province_and_city(province))
        
        await gather(*tasks)

        c.execute("DELETE FROM location_search")
        self.sqlite.commit()
        c.executemany("INSERT INTO location_search (id, name) VALUES (?, ?)", locations_fulltext)

        self.sqlite.commit()
        c.close()
    
    @logger.catch(onerror=lambda e: exec('raise e'))
    async def update_price_type_table(self):
        c = self.sqlite.cursor()
        price_types = [(ty["id"], ty["name"]) for ty in await self.list_price_type_origin()]
        c.execute("DELETE FROM price_type_search")
        self.sqlite.commit()
        c.executemany("INSERT INTO price_type_search (id, name) VALUES (?, ?)", price_types)
        self.sqlite.commit()
        c.close()
    
    @logger.catch(onerror=lambda e: exec('raise e'))
    async def start(self):
        await gather(super().start(), self.init_sqlite())
        await gather(self.update_list_comodity_table(), self.update_list_location_table(), self.update_price_type_table())

    @logger.catch()
    async def update_tables(self):
        await self.ensure_started()
        
        async with self._lock:
            await gather(self.update_list_comodity_table(), self.update_list_location_table(), self.update_price_type_table())

    async def close(self):
        try:
            self.sqlite.close()
            await super().close()
        except: pass
    
    # Master method

    async def list_price_type(self, keyword: str | None = None):
        c = self.sqlite.cursor()
        c.execute("SELECT * FROM price_type_search WHERE price_type_search MATCH ? ORDER BY rank", (keyword.strip(),)) if keyword and keyword.strip() else c.execute("SELECT * FROM price_type_search")
        return c.fetchall()
    
    async def list_location(self, keyword: str | None = None, level: LevelLocation = "all"):
        if not level:
            level = "all"
        c = self.sqlite.cursor()
        c.execute("SELECT * FROM location_search WHERE location_search MATCH ? ORDER BY rank", (keyword.strip(),)) if keyword and keyword.strip() else c.execute("SELECT * FROM location_search")
        result = list()
        for row in c.fetchall():
            res = {}
            if ":" in row["id"]:
                pid, cid = row["id"].split(":")
                pn, cn = row["name"].split(", ")
                res = {
                    "province_id": int(pid),
                    "province_name": pn,
                    "city_id": int(cid),
                    "city_name": cn,
                }
            else:
                res = {
                    "province_id": row["id"],
                    "province_name": row["name"],
                    "city_id": None,
                    "city_name": None,
                }
            match level:
                case "province":
                    if res["city_id"] is None:
                        result.append(res)
                case "city":
                    if res["city_id"] != None:
                        result.append(res)
                case "all":
                    result.append(res)

        return result
    
    async def list_comodities(self, keyword: str | None = None):
        c = self.sqlite.cursor()
        c.execute("SELECT * FROM comodity_search WHERE comodity_search MATCH ? ORDER BY rank", (keyword.strip(),)) if keyword and keyword.strip() else c.execute("SELECT * FROM comodity_search")
        return c.fetchall()