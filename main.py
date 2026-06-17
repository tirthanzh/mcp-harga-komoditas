from source.phips_service import PhipsService, LevelLocation
from source.badanpangan_service import BadanpanganService
from source.mcp_prompts import register_mcp_prompts

from fastmcp import FastMCP
from loguru import logger
from asyncio import sleep, gather


PHIPS_SERVICE = PhipsService()
BADANPANGAN_SERVICE = BadanpanganService()


mcp = FastMCP(name="MCP Comodity Prices", version="1.0.6")
register_mcp_prompts(mcp)

async def schedule_task():
    while True:
        await sleep(6 * 60 * 60)
        logger.info("update schedule trigerred...")
        await PHIPS_SERVICE.update_tables()



@mcp.tool
async def list_price_type(keyword: str | None = None):
    """
    Get a list of available price types (e.g., Retail, Wholesale, Producer).
    Use this to find the correct 'price_type_id' for get_comodity_prices.
    
    Args:
        keyword: Optional string to filter the price types (e.g., "Pasar Tradisional", "Pasar Modern", "Pedagang Besar", "Produsen").
    """


    await PHIPS_SERVICE.ensure_started()
    return await PHIPS_SERVICE.list_price_type(keyword)

@mcp.tool
async def list_comodities(keyword: str | None = None):
    """
    Get a list of supported commodities. 
    
    Args:
        keyword: Optional string to search for specific commodities (e.g., "beras", "cabai", "ayam").
    """
    await PHIPS_SERVICE.ensure_started()
    return await PHIPS_SERVICE.list_comodities(keyword)

@mcp.tool
async def list_location(keyword: str | None = None, level: LevelLocation = "all"):
    """
    Get a list of supported locations (provinces, cities, or districts).
    
    Args:
        keyword: Optional string to search for a specific location (e.g., "Jakarta", "Bandung", "Banten, Kota Tangerang").
        level: The level of the location hierarchy. Valid options: "all", "province", "city"
    """
    await PHIPS_SERVICE.ensure_started()
    return await PHIPS_SERVICE.list_location(keyword, level)

@mcp.tool
async def get_comodity_prices(
    comodity_keyword: str,
    price_type_id: int = 2,
    start_date: str | None = None,
    end_date: str | None = None,
    location_keyword: str | None = None,
    location_level: LevelLocation = "all",
):
    """
    The main tool to fetch historical and current commodity prices. It automatically matches 
    the keywords to the internal IDs and returns a time-series dataset.
    
    Args:
        comodity_keyword: The name of the commodity to search for (e.g., "beras", "gula"). Will return all matched variants.
        price_type_id: The ID for the price type (e.g., 2 for standard retail price). Try to default to 2 if unsure.
        start_date: The start date for the price data in 'YYYY-MM-DD' format (e.g., "2026-04-28"). If None, uses default is today.
        end_date: The end date for the price data in 'YYYY-MM-DD' format. Can be None to get data up to today.
        location_keyword: The name of the region to search for (e.g., "jakarta", "jawa timur"). If None, returns national average if available.
        location_level: Filter location matching by level ("all", "province", "city"). Default is "all".
        
    Returns:
        A JSON object containing 'matched' (the exact commodities and location found) and 'results' (the daily price data).
    """

    await PHIPS_SERVICE.ensure_started()

    comodities, locations = await gather(
        PHIPS_SERVICE.list_comodities(comodity_keyword),
        PHIPS_SERVICE.list_location(location_keyword, location_level)
    )
    if len(comodities) == 0:
        raise Exception("Comodity not found, try view list comodity before.")
    if len(locations) == 0:
        raise Exception("Location not found, try view list location before.")
    location = locations[0]
    results = await PHIPS_SERVICE.get_price_comodity_origin(
        [com["id"] for com in comodities],
        price_type_id,
        start_date,
        end_date,
        location["province_id"],
        location["city_id"],
    )
    return {
        "matched": {
            "comodities": comodities,
            "location": location,
        },
        "results": results
    }

@mcp.tool
async def get_statistik_wilayah_ketahanan_pangan(location_keyword: str, year: int):
    """
    This tool useful to get statistic information for each Desa/Village about food resilience
    Args:
        location_keyword: The name of region to search (e.g., "jakarta", "jawa timur").
        years: Year about timeframe the statistic, usually the data for this year is not yet available.
    """
    await BADANPANGAN_SERVICE.ensure_started()

    return await BADANPANGAN_SERVICE.fetch_statistik_dareah_badan_pangan_origin(location_keyword, [year])

if __name__ == "__main__":
    from asyncio import run, ensure_future
    async def main():
        try:
            ensure_future(schedule_task())
            await mcp.run_async("http", host="0.0.0.0", port=5200)  
        except BaseException as e:
            logger.error(e)
        finally:
            await PHIPS_SERVICE.close()
    run(main())