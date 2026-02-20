"""
Scheduled Jobs - Run at midnight Brasília time (UTC-3)
- Download missing invoices from COPEL for all plants with credentials
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

logger = logging.getLogger(__name__)
BRT = timezone(timedelta(hours=-3))


async def download_missing_invoices():
    """Download all missing invoices from COPEL for plants with credentials configured."""
    logger.info("=== JOB: Iniciando download automatico de faturas ===")
    
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'test_database')]
    
    try:
        # Find all plants with COPEL credentials
        plants = await db.plants.find(
            {'copel_cnpj': {'$exists': True, '$ne': ''}, 'copel_password': {'$exists': True, '$ne': ''}, 'is_active': True},
            {'_id': 0}
        ).to_list(100)
        
        if not plants:
            logger.info("Nenhuma usina com credenciais COPEL configuradas")
            return
        
        logger.info(f"Encontradas {len(plants)} usinas com credenciais COPEL")
        
        from services.copel_ava_service import CopelAVAService
        from services.pdf_parser_service import parse_copel_invoice
        from io import BytesIO
        import uuid
        
        now = datetime.now(BRT)
        # Check last 3 months of invoices
        months_to_check = []
        for i in range(3):
            d = now - timedelta(days=30 * i)
            months_to_check.append(f"{d.month:02d}/{d.year}")
        
        total_downloaded = 0
        total_errors = 0
        
        for plant in plants:
            plant_id = plant['id']
            cnpj = plant.get('copel_cnpj', '')
            password = plant.get('copel_password', '')
            
            logger.info(f"Processando: {plant.get('name', '?')} (CNPJ: {cnpj[:8]}...)")
            
            # Get UCs for this plant
            units = await db.consumer_units.find(
                {'plant_id': plant_id, 'is_active': True},
                {'_id': 0, 'id': 1, 'uc_number': 1}
            ).to_list(100)
            
            if not units:
                continue
            
            # Check which invoices are missing
            missing = []
            for unit in units:
                uc = unit.get('uc_number', '')
                if not uc:
                    continue
                for ref_month in months_to_check:
                    existing = await db.invoices.find_one({
                        'consumer_unit_id': unit['id'],
                        'reference_month': ref_month
                    })
                    if not existing:
                        # Also check by uc_number across plants
                        all_ucs = await db.consumer_units.find(
                            {'uc_number': uc}, {'_id': 0, 'id': 1}
                        ).to_list(10)
                        all_ids = [u['id'] for u in all_ucs]
                        existing2 = await db.invoices.find_one({
                            'consumer_unit_id': {'$in': all_ids},
                            'reference_month': ref_month
                        })
                        if not existing2:
                            missing.append({'uc': uc, 'ref': ref_month, 'unit_id': unit['id']})
            
            if not missing:
                logger.info(f"  Todas as faturas ja estao no sistema para {plant.get('name')}")
                continue
            
            logger.info(f"  {len(missing)} faturas faltando. Tentando baixar...")
            
            # Login to COPEL
            service = CopelAVAService()
            try:
                login_result = await service.login(cnpj, password)
                if not login_result.get('success'):
                    logger.warning(f"  Login COPEL falhou: {login_result.get('error')}")
                    total_errors += 1
                    continue
                
                for item in missing:
                    try:
                        pdf_data = await service.download_invoice(item['uc'], item['ref'])
                        if pdf_data:
                            # Parse the PDF
                            parsed = parse_copel_invoice(BytesIO(pdf_data))
                            if parsed.get('success'):
                                # Save invoice
                                invoice_doc = {
                                    'id': str(uuid.uuid4()),
                                    'consumer_unit_id': item['unit_id'],
                                    'plant_id': plant_id,
                                    'reference_month': item['ref'],
                                    'source': 'copel_auto',
                                    'created_at': datetime.now(BRT).isoformat(),
                                }
                                # Add parsed fields
                                for key in ['tariff_group', 'is_generator', 'is_beneficiary', 'uc_number',
                                           'amount_total_brl', 'amount_saved_brl', 'billing_cycle_start',
                                           'billing_cycle_end', 'energy_registered_fp_kwh', 'energy_registered_p_kwh',
                                           'energy_compensated_fp_kwh', 'energy_compensated_p_kwh',
                                           'energy_injected_fp_kwh', 'energy_injected_p_kwh',
                                           'energy_billed_fp_kwh', 'energy_billed_p_kwh',
                                           'credits_balance_fp_kwh', 'credits_balance_p_kwh',
                                           'credits_accumulated_fp_kwh', 'credits_accumulated_p_kwh',
                                           'public_lighting_brl', 'tariff_flag']:
                                    if key in parsed:
                                        invoice_doc[key] = parsed[key]
                                
                                await db.invoices.insert_one(invoice_doc)
                                total_downloaded += 1
                                logger.info(f"    Fatura baixada: UC {item['uc']} ref {item['ref']}")
                            else:
                                logger.warning(f"    Parse falhou: UC {item['uc']} ref {item['ref']}")
                        else:
                            logger.info(f"    Fatura nao disponivel: UC {item['uc']} ref {item['ref']}")
                    except Exception as e:
                        logger.warning(f"    Erro UC {item['uc']}: {e}")
                        total_errors += 1
            finally:
                await service.close()
        
        logger.info(f"=== JOB CONCLUIDO: {total_downloaded} faturas baixadas, {total_errors} erros ===")
        
    except Exception as e:
        logger.error(f"Job error: {e}")
    finally:
        client.close()


async def sync_all_growatt_plants():
    """Sync generation data from Growatt for ALL plants with credentials."""
    logger.info("=== JOB: Sincronizacao Growatt automatica ===")
    
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'test_database')]
    
    try:
        plants = await db.plants.find(
            {'growatt_username': {'$exists': True, '$ne': ''}, 'is_active': True},
            {'_id': 0, 'id': 1, 'name': 1, 'growatt_username': 1, 'growatt_password': 1, 'growatt_plant_name': 1}
        ).to_list(200)
        
        if not plants:
            logger.info("Nenhuma usina com credenciais Growatt")
            return
        
        logger.info(f"Encontradas {len(plants)} usinas com credenciais Growatt")
        
        # Group by username to login once per account
        from collections import defaultdict
        by_user = defaultdict(list)
        for p in plants:
            by_user[p.get('growatt_username','')].append(p)
        
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
        from services.growatt_service import GrowattOSSService
        import uuid
        
        total_synced = 0
        total_errors = 0
        
        for username, user_plants in by_user.items():
            password = user_plants[0].get('growatt_password', '')
            if not password:
                continue
            
            logger.info(f"Login Growatt: {username} ({len(user_plants)} usinas)")
            service = GrowattOSSService()
            
            try:
                login_result = await service.login(username, password)
                if not login_result.get('success'):
                    logger.warning(f"  Login falhou: {login_result.get('error')}")
                    total_errors += len(user_plants)
                    continue
                
                # Get all plants from Growatt
                growatt_plants = await service.get_plants()
                growatt_map = {p['name'].lower(): p for p in growatt_plants}
                
                for plant in user_plants:
                    plant_id = plant['id']
                    gname = plant.get('growatt_plant_name') or plant.get('name', '')
                    
                    # Find matching Growatt plant
                    gplant = growatt_map.get(gname.lower())
                    if not gplant:
                        # Try partial match
                        gplant = next((gp for gp in growatt_plants if gname.lower() in gp['name'].lower()), None)
                    
                    if gplant and gplant.get('today_energy_kwh', 0) > 0:
                        today_str = datetime.now(BRT).strftime('%Y-%m-%d')
                        gen_kwh = gplant['today_energy_kwh']
                        
                        existing = await db.generation_data.find_one({'plant_id': plant_id, 'date': today_str})
                        if existing:
                            await db.generation_data.update_one(
                                {'plant_id': plant_id, 'date': today_str},
                                {'$set': {'generation_kwh': gen_kwh, 'source': 'growatt_auto'}}
                            )
                        else:
                            await db.generation_data.insert_one({
                                'id': str(uuid.uuid4()), 'plant_id': plant_id,
                                'date': today_str, 'generation_kwh': gen_kwh,
                                'source': 'growatt_auto', 'created_at': datetime.now(BRT).isoformat()
                            })
                        
                        await db.plants.update_one({'id': plant_id}, {'$set': {
                            'last_growatt_sync': datetime.now(BRT).isoformat(),
                            'growatt_status': gplant.get('status', 'unknown'),
                        }})
                        total_synced += 1
                        logger.info(f"  {plant.get('name')}: {gen_kwh} kWh ({gplant.get('status')})")
                    else:
                        status = gplant.get('status', 'offline') if gplant else 'not_found'
                        await db.plants.update_one({'id': plant_id}, {'$set': {
                            'last_growatt_sync': datetime.now(BRT).isoformat(),
                            'growatt_status': status,
                        }})
                        logger.info(f"  {plant.get('name')}: 0 kWh ({status})")
                
            except Exception as e:
                logger.error(f"  Erro Growatt {username}: {e}")
                total_errors += 1
            finally:
                await service.close()
        
        logger.info(f"=== GROWATT SYNC CONCLUIDO: {total_synced} usinas sincronizadas, {total_errors} erros ===")
        
    except Exception as e:
        logger.error(f"Growatt sync job error: {e}")
    finally:
        client.close()


def start_scheduler():
    """Start the APScheduler with scheduled jobs."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    
    scheduler = AsyncIOScheduler()
    
    # Faturas COPEL: midnight Brasília (03:00 UTC)
    scheduler.add_job(
        download_missing_invoices,
        trigger=CronTrigger(hour=3, minute=0, timezone='America/Sao_Paulo'),
        id='download_invoices',
        name='Download faturas COPEL automatico',
        replace_existing=True,
    )
    
    # Growatt sync: 6AM Brasília (09:00 UTC) - after sunrise, has yesterday's data
    scheduler.add_job(
        sync_all_growatt_plants,
        trigger=CronTrigger(hour=9, minute=0, timezone='America/Sao_Paulo'),
        id='sync_growatt',
        name='Sync Growatt automatico (diario)',
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Scheduler iniciado: faturas COPEL (meia-noite) + Growatt sync (6h Brasilia)")
    return scheduler
