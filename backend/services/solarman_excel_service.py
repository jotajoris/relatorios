"""
Service to parse Solarman Excel generation reports.
Solarman Excel format:
- Column 0: Tempo (Date in YYYY/MM/DD format)
- Column 1: Produção de energia solar (kWh)
- Column 2: Clima (Weather)
- Column 3: Horas de pico solar (h)
"""
import pandas as pd
from io import BytesIO
from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def parse_solarman_excel(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse a Solarman Excel report file.
    Returns structured data with daily generation values.
    """
    try:
        # Read Excel file
        df = pd.read_excel(BytesIO(file_content), sheet_name=0, header=None)
        
        logger.info(f"[SolarmanExcel] Lendo arquivo: {filename}, shape: {df.shape}")
        
        # Get sheet name for month/year info
        xl = pd.ExcelFile(BytesIO(file_content))
        sheet_name = xl.sheet_names[0] if xl.sheet_names else ""
        
        # Check if it's a Solarman format
        # First row should have headers like "Tempo", "Produção de energia solar"
        first_row = df.iloc[0].astype(str).tolist()
        is_solarman = any('Tempo' in str(c) or 'Produção' in str(c) or 'energia solar' in str(c).lower() for c in first_row)
        
        if not is_solarman:
            return {
                'success': False,
                'error': 'Formato de arquivo não reconhecido. Esperado formato Solarman com colunas Tempo e Produção.'
            }
        
        # Parse daily data (skip header row)
        daily_generation = []
        total_kwh = 0
        days_count = 0
        
        for idx, row in df.iloc[1:].iterrows():
            try:
                # Column 0: Date (Tempo)
                date_val = row.iloc[0]
                
                # Column 1: Generation (kWh)
                gen_val = row.iloc[1]
                
                # Skip if no date
                if pd.isna(date_val):
                    continue
                
                # Parse date
                if isinstance(date_val, str):
                    # Format: YYYY/MM/DD or YYYY-MM-DD
                    date_str = date_val.replace('/', '-')
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    except:
                        # Try other formats
                        try:
                            date_obj = datetime.strptime(date_val, '%d/%m/%Y')
                        except:
                            continue
                elif isinstance(date_val, datetime):
                    date_obj = date_val
                else:
                    continue
                
                date_str = date_obj.strftime('%Y-%m-%d')
                
                # Parse generation value
                if pd.isna(gen_val) or gen_val == '' or gen_val is None:
                    gen_kwh = 0
                else:
                    try:
                        gen_kwh = float(gen_val)
                    except:
                        gen_kwh = 0
                
                # Get weather if available
                weather = str(row.iloc[2]) if len(row) > 2 and not pd.isna(row.iloc[2]) else None
                
                # Get peak hours if available
                peak_hours = None
                if len(row) > 3 and not pd.isna(row.iloc[3]):
                    try:
                        peak_hours = float(row.iloc[3])
                    except:
                        pass
                
                daily_generation.append({
                    'date': date_str,
                    'generation_kwh': gen_kwh,
                    'weather': weather,
                    'peak_hours': peak_hours
                })
                
                if gen_kwh > 0:
                    total_kwh += gen_kwh
                    days_count += 1
                    
            except Exception as e:
                logger.warning(f"[SolarmanExcel] Erro ao processar linha {idx}: {e}")
                continue
        
        if not daily_generation:
            return {
                'success': False,
                'error': 'Nenhum dado de geração encontrado no arquivo'
            }
        
        # Extract month/year from sheet name or first date
        month_year = sheet_name if sheet_name else ""
        if not month_year and daily_generation:
            first_date = daily_generation[0]['date']
            month_year = first_date[:7]  # YYYY-MM
        
        return {
            'success': True,
            'format': 'solarman',
            'month_year': month_year,
            'total_generation_kwh': round(total_kwh, 2),
            'days_with_data': days_count,
            'daily_generation': daily_generation
        }
        
    except Exception as e:
        logger.error(f"[SolarmanExcel] Erro ao processar arquivo: {e}")
        return {
            'success': False,
            'error': f'Erro ao processar arquivo: {str(e)}'
        }


def extract_solarman_generation_records(parsed_data: Dict[str, Any], plant_id: str) -> List[Dict[str, Any]]:
    """
    Extract generation records from parsed Solarman data.
    Returns list of records ready to be inserted into database.
    """
    records = []
    
    daily_generation = parsed_data.get('daily_generation', [])
    
    for day_data in daily_generation:
        gen_kwh = day_data.get('generation_kwh', 0)
        
        # Only add records with actual generation
        if gen_kwh > 0:
            records.append({
                'plant_id': plant_id,
                'date': day_data['date'],
                'generation_kwh': gen_kwh,
                'source': 'solarman_excel',
                'weather': day_data.get('weather'),
                'peak_hours': day_data.get('peak_hours')
            })
    
    return records
