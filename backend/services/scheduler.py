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


def start_scheduler():
    """Start the APScheduler with midnight BRT job."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    
    scheduler = AsyncIOScheduler()
    
    # Run at midnight Brasília time (UTC-3) = 03:00 UTC
    scheduler.add_job(
        download_missing_invoices,
        trigger=CronTrigger(hour=3, minute=0, timezone='America/Sao_Paulo'),
        id='download_invoices',
        name='Download faturas COPEL automatico',
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Scheduler iniciado: download de faturas todo dia a meia-noite (Brasilia)")
    return scheduler
