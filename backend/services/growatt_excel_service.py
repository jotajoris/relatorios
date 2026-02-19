"""
Growatt Excel Parser Service
Parses Excel reports exported from the Growatt portal

Estrutura do Excel Growatt:
- Cabeçalho: Nome da usina + "Monthly Report"
- Linha 2: Período (YYYY-MM)
- Linhas 6-12: KPIs (Energy, Income, CO2, PR)
- Linha 15: Cabeçalho com dias (1-28/30/31) + Total
- Linhas 16+: Dados dos inversores por dia
- Seções adicionais: Storage Data, Hybrid Inverter, Wit, Microgrid
"""
import pandas as pd
from io import BytesIO
from datetime import datetime
import calendar
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def parse_growatt_excel(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse a Growatt Excel report and extract generation data.
    
    Handles variable month lengths (28, 29, 30, 31 days) automatically
    by detecting which columns have actual data.
    
    Returns:
        Dictionary with parsed data and daily generation
    """
    try:
        # Try to read as old Excel format (.xls)
        try:
            df = pd.read_excel(BytesIO(file_content), engine='xlrd')
        except Exception:
            # Try new format (.xlsx)
            df = pd.read_excel(BytesIO(file_content), engine='openpyxl')
        
        result = {
            'success': True,
            'filename': filename,
            'plant_name': None,
            'month_year': None,
            'days_in_month': None,
            'summary': {},
            'inverters': [],
            'daily_generation': [],
            'total_generation_kwh': 0
        }
        
        # Extract plant name from first column header
        first_col = df.columns[0]
        if 'Monthly Report' in str(first_col):
            result['plant_name'] = str(first_col).replace(' Monthly Report', '').strip()
        
        # Find month/year (usually in row 2, column 0)
        for idx, row in df.head(5).iterrows():
            first_val = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
            if '-' in first_val and len(first_val) == 7:  # Format like "2026-02"
                result['month_year'] = first_val
                # Calculate actual days in this month
                year, month = map(int, first_val.split('-'))
                result['days_in_month'] = calendar.monthrange(year, month)[1]
                break
        
        # Parse summary data (Plant Data section)
        summary_mapping = {
            'Energy this Month(kWh)': 'energy_this_month_kwh',
            'Energy Total(kWh)': 'energy_total_kwh',
            'Income this Month(R$)': 'income_this_month_brl',
            'Income Total(R$)': 'income_total_brl',
            'CO2 Emission Reduced this Month(kg)': 'co2_reduced_month_kg',
            'CO2 Emission Reduced Total(kg)': 'co2_reduced_total_kg',
            'PR this Month': 'pr_this_month'
        }
        
        for idx, row in df.iterrows():
            first_val = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
            for excel_key, result_key in summary_mapping.items():
                if excel_key in first_val:
                    # Value is in column 5 (index 5)
                    if len(row) > 5 and pd.notna(row.iloc[5]):
                        try:
                            result['summary'][result_key] = float(row.iloc[5])
                        except (ValueError, TypeError):
                            pass
                    break
        
        # Find inverter data rows
        # Pattern: Serial number like "FULCD5X002(125k (inv 1))" or similar
        # Must be in the "Inverter Data" section and have alphanumeric serial
        inverter_rows = []
        in_inverter_section = False
        
        for idx, row in df.iterrows():
            first_val = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
            
            # Detect section markers
            if 'Inverter Data' in first_val:
                in_inverter_section = True
                continue
            elif 'Storage Data' in first_val or 'Hybrid Inverter' in first_val or 'Wit Data' in first_val:
                in_inverter_section = False
                continue
            
            # Only process rows in the inverter section
            if not in_inverter_section:
                continue
            
            # Skip header row
            if 'Serial Number' in first_val:
                continue
            
            # Inverter rows have serial numbers like "FULCD5X002(125k (inv 1))"
            # Must start with alphanumeric and contain parentheses
            if first_val and '(' in first_val:
                serial_part = first_val.split('(')[0].strip()
                # Valid serial: alphanumeric, typically 8+ chars
                if serial_part and len(serial_part) >= 6 and any(c.isdigit() for c in serial_part) and any(c.isalpha() for c in serial_part):
                    inverter_rows.append((idx, row))
        
        # Determine actual days with data by checking inverter rows
        max_day_with_data = 0
        if inverter_rows:
            for idx, row in inverter_rows:
                for day in range(1, 32):
                    col_idx = day + 2  # Column index (day 1 is column 3)
                    if col_idx < len(row) and pd.notna(row.iloc[col_idx]):
                        try:
                            val = float(row.iloc[col_idx])
                            if val > 0:
                                max_day_with_data = max(max_day_with_data, day)
                        except (ValueError, TypeError):
                            pass
        
        # Use detected days or fall back to calendar days
        actual_days = max_day_with_data if max_day_with_data > 0 else (result['days_in_month'] or 31)
        logger.info(f"Detected {actual_days} days with data in Excel")
        
        # Process each inverter
        for idx, row in inverter_rows:
            inverter_name = str(row.iloc[0])
            
            # Extract daily values only for days that have data
            daily_values = []
            for day in range(1, actual_days + 1):
                col_idx = day + 2  # Column index (day 1 is column 3)
                if col_idx < len(row):
                    val = row.iloc[col_idx]
                    if pd.notna(val):
                        try:
                            gen_val = float(val)
                            daily_values.append({'day': day, 'generation_kwh': gen_val})
                        except (ValueError, TypeError):
                            pass
            
            # Get total from last column (labeled "Total(kWh)")
            inverter_total = 0
            if pd.notna(row.iloc[-1]):
                try:
                    inverter_total = float(row.iloc[-1])
                except (ValueError, TypeError):
                    inverter_total = sum(d['generation_kwh'] for d in daily_values)
            else:
                inverter_total = sum(d['generation_kwh'] for d in daily_values)
            
            result['inverters'].append({
                'serial': inverter_name,
                'daily_values': daily_values,
                'total_kwh': round(inverter_total, 2),
                'days_with_data': len(daily_values)
            })
        
        # Calculate combined daily generation (sum across all inverters)
        if result['inverters']:
            days_data = {}
            for inv in result['inverters']:
                for daily in inv['daily_values']:
                    day = daily['day']
                    if day not in days_data:
                        days_data[day] = 0
                    days_data[day] += daily['generation_kwh']
            
            # Build daily generation list with dates
            if result['month_year']:
                year, month = result['month_year'].split('-')
                for day, total in sorted(days_data.items()):
                    date_str = f"{year}-{month}-{day:02d}"
                    result['daily_generation'].append({
                        'date': date_str,
                        'day': day,
                        'generation_kwh': round(total, 2)
                    })
            else:
                for day, total in sorted(days_data.items()):
                    result['daily_generation'].append({
                        'day': day,
                        'generation_kwh': round(total, 2)
                    })
            
            result['total_generation_kwh'] = round(sum(d['generation_kwh'] for d in result['daily_generation']), 2)
        
        # Use summary value if available (more accurate as it comes from Growatt)
        if 'energy_this_month_kwh' in result['summary']:
            summary_total = result['summary']['energy_this_month_kwh']
            if summary_total > 0:
                result['total_generation_kwh'] = summary_total
        
        logger.info(
            f"Parsed Growatt Excel: {result['plant_name']} - {result['month_year']} - "
            f"{result['total_generation_kwh']} kWh - {len(result['inverters'])} inverters - "
            f"{len(result['daily_generation'])} days"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing Growatt Excel: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'filename': filename
        }


def extract_generation_records(parsed_data: Dict, plant_id: str) -> List[Dict]:
    """
    Convert parsed Growatt Excel data into generation records for database insertion.
    
    Returns:
        List of generation data records ready for insertion
    """
    if not parsed_data.get('success') or not parsed_data.get('daily_generation'):
        return []
    
    records = []
    for daily in parsed_data['daily_generation']:
        if daily.get('date'):
            records.append({
                'plant_id': plant_id,
                'date': daily['date'],
                'generation_kwh': daily['generation_kwh'],
                'source': 'growatt_excel'
            })
    
    return records
