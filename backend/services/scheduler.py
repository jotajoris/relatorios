"""
Scheduled Jobs - Run at midnight Brasília time (UTC-3)
- Download missing invoices from COPEL for all plants with credentials
- Sync Growatt generation data every X minutes (configurable)
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

logger = logging.getLogger(__name__)
BRT = timezone(timedelta(hours=-3))

# Global scheduler reference for dynamic updates
_scheduler = None
_current_sync_interval = 30  # Default 30 minutes


async def get_sync_interval_from_db():
    """Get the sync interval from database settings."""
    try:
        client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
        db = client[os.environ.get('DB_NAME', 'test_database')]
        settings = await db.app_settings.find_one({'key': 'growatt_sync_interval'})
        client.close()
        if settings:
            return int(settings.get('value', 30))
    except Exception as e:
        logger.warning(f"Could not get sync interval from DB: {e}")
    return 30  # Default


async def set_sync_interval(minutes: int):
    """Set the sync interval in database and update scheduler."""
    global _scheduler, _current_sync_interval
    
    try:
        client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
        db = client[os.environ.get('DB_NAME', 'test_database')]
        await db.app_settings.update_one(
            {'key': 'growatt_sync_interval'},
            {'$set': {'key': 'growatt_sync_interval', 'value': minutes, 'updated_at': datetime.now(BRT).isoformat()}},
            upsert=True
        )
        client.close()
        
        _current_sync_interval = minutes
        
        # Update the scheduler job
        if _scheduler:
            try:
                _scheduler.remove_job('sync_all_plants')
            except:
                pass
            
            from apscheduler.triggers.interval import IntervalTrigger
            _scheduler.add_job(
                sync_all_plants,
                trigger=IntervalTrigger(minutes=minutes),
                id='sync_all_plants',
                name=f'Sync TODAS usinas (cada {minutes} min)',
                replace_existing=True,
            )
            logger.info(f"Scheduler atualizado: Sync todas usinas a cada {minutes} minutos")
        
        return True
    except Exception as e:
        logger.error(f"Error setting sync interval: {e}")
        return False


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
        # Get all active plants
        all_plants = await db.plants.find(
            {'is_active': True},
            {'_id': 0, 'id': 1, 'name': 1, 'growatt_username': 1, 'growatt_password': 1, 'growatt_plant_name': 1}
        ).to_list(200)
        
        if not all_plants:
            logger.info("Nenhuma usina ativa encontrada")
            return
        
        # Separate plants with credentials and without
        plants_with_creds = [p for p in all_plants if p.get('growatt_username') and p.get('growatt_password')]
        plants_without_creds = [p for p in all_plants if not p.get('growatt_username') or not p.get('growatt_password')]
        
        logger.info(f"Usinas com credenciais: {len(plants_with_creds)}, sem credenciais: {len(plants_without_creds)}")
        
        # Get installer login from client_logins to use for plants without credentials
        installer_login = await db.client_logins.find_one(
            {'inverter_app': 'Growatt', 'is_installer': True},
            {'_id': 0, 'login': 1, 'password': 1}
        )
        
        # Group by username to login once per account
        from collections import defaultdict
        by_user = defaultdict(list)
        
        # Add plants with their own credentials
        for p in plants_with_creds:
            by_user[p.get('growatt_username','')].append(p)
        
        # Add plants without credentials to installer account
        if installer_login and plants_without_creds:
            installer_user = installer_login.get('login', '')
            if installer_user:
                for p in plants_without_creds:
                    # Add temporary credentials for sync
                    p['_temp_username'] = installer_user
                    p['_temp_password'] = installer_login.get('password', '')
                    by_user[installer_user].append(p)
        
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
        from services.growatt_service import GrowattOSSService
        import uuid
        
        total_synced = 0
        total_errors = 0
        
        for username, user_plants in by_user.items():
            # Get password from first plant (or temp credentials)
            password = user_plants[0].get('growatt_password') or user_plants[0].get('_temp_password', '')
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
                        
                        # Update plant info including growatt_plant_id
                        update_fields = {
                            'last_growatt_sync': datetime.now(BRT).isoformat(),
                            'growatt_status': gplant.get('status', 'unknown'),
                        }
                        # Save the Growatt plantId if available
                        growatt_id = gplant.get('plant_id') or gplant.get('id', '')
                        if growatt_id:
                            update_fields['growatt_plant_id'] = str(growatt_id)
                        
                        await db.plants.update_one({'id': plant_id}, {'$set': update_fields})
                        total_synced += 1
                        logger.info(f"  {plant.get('name')}: {gen_kwh} kWh ({gplant.get('status')}) [ID:{growatt_id}]")
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
        return total_synced, total_errors
        
    except Exception as e:
        logger.error(f"Growatt sync job error: {e}")
        return 0, 1
    finally:
        client.close()


async def _sync_solarman_plants(db):
    """Internal function to sync Solarman plants. Called by sync_all_plants."""
    logger.info("--- Sincronizando usinas Solarman ---")
    
    total_synced = 0
    total_errors = 0
    
    try:
        # Check if Solarman session is valid
        session = await db.solarman_sessions.find_one({'type': 'pro', 'logged_in': True}, {'_id': 0})
        
        if not session or not session.get('auth_token'):
            logger.info("Sessão Solarman não encontrada ou expirada. Pulando.")
            return 0, 0
        
        # Get all plants with solarman_id
        plants = await db.plants.find(
            {'solarman_id': {'$exists': True, '$ne': None, '$ne': ''}, 'is_active': True},
            {'_id': 0, 'id': 1, 'name': 1, 'solarman_id': 1}
        ).to_list(200)
        
        if not plants:
            logger.info("Nenhuma usina com solarman_id encontrada")
            return 0, 0
        
        logger.info(f"Encontradas {len(plants)} usinas Solarman")
        
        # Build solarman_id to plant_id mapping
        solarman_to_plant = {str(p.get('solarman_id')): p for p in plants}
        
        # Fetch all plants from Solarman API
        from services.solarman_service import SolarmanSessionService
        service = SolarmanSessionService(db)
        
        result = await service.fetch_plants()
        
        if not result.get('success'):
            logger.warning(f"Falha ao buscar usinas do Solarman: {result.get('error')}")
            return 0, 1
        
        solarman_plants = result.get('plants', [])
        import uuid
        
        for sp in solarman_plants:
            solarman_id = str(sp.get('id', ''))
            
            if solarman_id not in solarman_to_plant:
                continue
            
            our_plant = solarman_to_plant[solarman_id]
            plant_id = our_plant['id']
            
            try:
                today_kwh = sp.get('today_energy_kwh') or sp.get('generationValue') or 0
                total_kwh = sp.get('total_energy_kwh') or sp.get('generationTotal') or 0
                status = sp.get('status', 'offline')
                network_status = sp.get('networkStatus', 'UNKNOWN')
                
                today_str = datetime.now(BRT).strftime('%Y-%m-%d')
                
                if today_kwh > 0:
                    existing = await db.generation_data.find_one({'plant_id': plant_id, 'date': today_str})
                    if existing:
                        await db.generation_data.update_one(
                            {'plant_id': plant_id, 'date': today_str},
                            {'$set': {'generation_kwh': today_kwh, 'source': 'solarman_auto'}}
                        )
                    else:
                        await db.generation_data.insert_one({
                            'id': str(uuid.uuid4()), 'plant_id': plant_id,
                            'date': today_str, 'generation_kwh': today_kwh,
                            'source': 'solarman_auto', 'created_at': datetime.now(BRT).isoformat()
                        })
                
                await db.plants.update_one({'id': plant_id}, {'$set': {
                    'last_sync': datetime.now(BRT).isoformat(),
                    'solarman_status': status,
                    'solarman_network_status': network_status,
                    'solarman_total_kwh': total_kwh,
                }})
                
                total_synced += 1
                logger.info(f"  {our_plant.get('name')}: {today_kwh} kWh ({status})")
                
            except Exception as e:
                logger.error(f"  Erro {our_plant.get('name')}: {e}")
                total_errors += 1
        
        return total_synced, total_errors
        
    except Exception as e:
        logger.error(f"Solarman sync error: {e}")
        return 0, 1


async def sync_all_plants():
    """
    Sync generation data from ALL portals (Growatt, Solarman, etc) for all monitored plants.
    This is the main sync job that runs at the configured interval.
    """
    logger.info("========================================")
    logger.info("=== JOB: Sincronização de TODAS as usinas ===")
    logger.info("========================================")
    
    start_time = datetime.now(BRT)
    
    # Sync Growatt plants
    growatt_synced, growatt_errors = await sync_all_growatt_plants()
    
    # Sync Solarman plants
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'test_database')]
    try:
        solarman_synced, solarman_errors = await _sync_solarman_plants(db)
    finally:
        client.close()
    
    # Summary
    total_synced = growatt_synced + solarman_synced
    total_errors = growatt_errors + solarman_errors
    duration = (datetime.now(BRT) - start_time).total_seconds()
    
    logger.info("========================================")
    logger.info(f"=== SYNC COMPLETO em {duration:.1f}s ===")
    logger.info(f"    Growatt: {growatt_synced} usinas")
    logger.info(f"    Solarman: {solarman_synced} usinas")
    logger.info(f"    Total: {total_synced} sincronizadas, {total_errors} erros")
    logger.info("========================================")


def start_scheduler():
    """Start the APScheduler with scheduled jobs."""
    global _scheduler, _current_sync_interval
    
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    
    _scheduler = AsyncIOScheduler()
    
    # Faturas COPEL: midnight Brasília (03:00 UTC)
    _scheduler.add_job(
        download_missing_invoices,
        trigger=CronTrigger(hour=3, minute=0, timezone='America/Sao_Paulo'),
        id='download_invoices',
        name='Download faturas COPEL automatico',
        replace_existing=True,
    )
    
    # Sync ALL plants (Growatt + Solarman + future portals): every X minutes
    _scheduler.add_job(
        sync_all_plants,
        trigger=IntervalTrigger(minutes=_current_sync_interval),
        id='sync_all_plants',
        name=f'Sync TODAS usinas (cada {_current_sync_interval} min)',
        replace_existing=True,
    )
    
    _scheduler.start()
    logger.info(f"Scheduler iniciado: faturas COPEL (meia-noite) + Sync todas usinas (cada {_current_sync_interval} min)")
    
    # Load interval from DB after scheduler starts
    async def load_interval():
        global _current_sync_interval
        interval = await get_sync_interval_from_db()
        if interval != _current_sync_interval:
            await set_sync_interval(interval)
    
    asyncio.get_event_loop().create_task(load_interval())
    
    return _scheduler


def get_scheduler():
    """Get the scheduler instance."""
    global _scheduler
    return _scheduler


def get_current_interval():
    """Get the current sync interval in minutes."""
    global _current_sync_interval
    return _current_sync_interval
