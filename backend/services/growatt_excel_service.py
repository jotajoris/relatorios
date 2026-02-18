"""
Growatt Excel Parser Service
Parses Excel reports exported from the Growatt portal
"""
import pandas as pd
from io import BytesIO
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def parse_growatt_excel(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse a Growatt Excel report and extract generation data.
    
    The Growatt Excel format has:
    - Row 0-2: Header info (plant name, date range)
    - Row 6: "Plant Data" section
    - Row 8-14: Summary metrics (Energy this Month, Total, Income, CO2, PR)
    - Row 15-19: "Inverter Data" section with daily generation per inverter
    - Columns 3-33: Days 1-31 of the month
    - Last column: Total
    
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
            'summary': {},
            'inverters': [],
            'daily_generation': [],
            'total_generation_kwh': 0
        }
        
        # Extract plant name from first row (column 0)
        first_col = df.columns[0]
        if 'Monthly Report' in str(first_col):
            result['plant_name'] = str(first_col).replace(' Monthly Report', '').strip()
        
        # Find month/year (usually in row 2)
        for idx, row in df.head(5).iterrows():
            first_val = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
            if '-' in first_val and len(first_val) == 7:  # Format like "2026-01"
                result['month_year'] = first_val
                break
        
        # Parse summary data (rows 8-14 based on pattern)
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
                    if pd.notna(row.iloc[5]):
                        result['summary'][result_key] = float(row.iloc[5])
                    break
        
        # Find inverter data rows
        # Look for rows starting with inverter serial numbers (like "FULCD5X001")
        inverter_rows = []
        for idx, row in df.iterrows():
            first_val = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
            # Inverter serial numbers typically start with letters and contain alphanumeric
            if first_val and '(' in first_val and any(c.isdigit() for c in first_val[:8]):
                inverter_rows.append((idx, row))
        
        # Process each inverter
        for idx, row in inverter_rows:
            inverter_name = str(row.iloc[0])
            
            # Extract daily values (columns 3-33 for days 1-31)
            daily_values = []
            for day in range(1, 32):
                col_idx = day + 2  # Column index (day 1 is column 3, etc.)
                if col_idx < len(row):
                    val = row.iloc[col_idx]
                    if pd.notna(val):
                        daily_values.append({'day': day, 'generation_kwh': float(val)})
            
            # Get total from last column
            total_col = df.columns[-1]
            inverter_total = float(row.iloc[-1]) if pd.notna(row.iloc[-1]) else sum(d['generation_kwh'] for d in daily_values)
            
            result['inverters'].append({
                'serial': inverter_name,
                'daily_values': daily_values,
                'total_kwh': inverter_total
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
        
        # Use summary value if available and seems more accurate
        if 'energy_this_month_kwh' in result['summary']:
            summary_total = result['summary']['energy_this_month_kwh']
            if summary_total > 0:
                result['total_generation_kwh'] = summary_total
        
        logger.info(f"Parsed Growatt Excel: {result['plant_name']} - {result['month_year']} - {result['total_generation_kwh']} kWh - {len(result['inverters'])} inverters")
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing Growatt Excel: {str(e)}")
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
