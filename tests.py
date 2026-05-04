from loguru import logger
from source.show_tables import show_all_tables


async def test_philip_service_backend():
    from source.phips_service import PhipsService
    from datetime import datetime, timedelta
    svc = PhipsService()
    await svc.start()
    try:
        await svc.init_sqlite()
        logger.info(await svc.list_price_type_origin())
        logger.info(await svc.list_provice_origin())
        logger.info(await svc.list_city_origin(1, 1))
        logger.info(await svc.list_comodity_origin())
        kemarin = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(await svc.get_price_comodity_origin([], 1, province_id=1, start_date=kemarin, end_date=kemarin))
        logger.info("=" * 15)
        await svc.update_list_comodity_table()
        await svc.update_list_location_table()
        await svc.update_price_type_table()
        show_all_tables(svc.sqlite)
        

    except BaseException as e:
        raise e
    finally:
        await svc.close()
    
async def test_philip_service_frontend():
    from source.phips_service import PhipsService
    from asyncio import gather
    svc = PhipsService()
    await svc.start()
    try:
        await svc.init_sqlite()
        await gather(svc.update_price_type_table(), svc.update_list_comodity_table(), svc.update_list_location_table())
        logger.info(await svc.list_price_type())
        logger.info(await svc.list_price_type("modern"))
        logger.info(await svc.list_price_type("4"))
        logger.info(await svc.list_location())
        logger.info(await svc.list_location("jakarta"))
        logger.info(await svc.list_location("4", "city"))
        logger.info(await svc.list_comodities())
        logger.info(await svc.list_comodities("Kualitas Medium"))
        

    except BaseException as e:
        raise e
    finally:
        await svc.close()

async def test_badanpangan_sevice():
    from source.badanpangan_service import BadanpanganService
    from json import dump
    svc = BadanpanganService()
    await svc.start()
    try:
        result = await svc.fetch_statistik_dareah_badan_pangan_origin("bandung", [2024])
        dump(result, open("xbadanpangan_sample.json", "w"), indent=2)
    except BaseException as e:
        raise e
    finally:
        await svc.close()