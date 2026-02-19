"""
COPEL Invoice PDF Parser Service - Rewritten
Extracts billing data from COPEL energy invoices (Grupo A and Grupo B)
Automatically identifies the UC from the invoice.

Tested against real invoices:
- 113577680 (Group A, Generator, A4 Industrial)
- 102480958 (Group B, Beneficiary, B3 Comercial)
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    logger.warning("pdfplumber not installed. PDF parsing will not work.")


def _parse_br_number(value: str) -> float:
    """Parse Brazilian number format (1.234,56) to float."""
    if not value:
        return 0.0
    try:
        value = value.strip()
        value = value.replace('.', '').replace(',', '.')
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _extract_full_text(pdf_source) -> str:
    """Extract all text from PDF pages."""
    with pdfplumber.open(pdf_source) as pdf:
        parts = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n".join(parts)


def _detect_tariff_group(text: str) -> str:
    """Detect if invoice is Group A or B."""
    upper = text.upper()
    group_a = [
        'A4 INDUSTRIAL', 'A4 COMERCIAL', 'A3 ', 'A2 ',
        'TARIFA HORARIA VERDE', 'TARIFA HORARIA AZUL',
        'DEMANDA USD', 'DEMANDA INJETADA',
        'ENERGIA ELETRICA TE PONTA', 'ENERGIA ELETRICA USD PONTA',
        'ENERGIA ELETRICA TE F PONTA', 'ENERGIA ELETRICA USD F PONTA',
    ]
    if any(ind in upper for ind in group_a):
        return "A"
    return "B"


def _extract_uc_number(text: str) -> Optional[str]:
    """Extract UC number (7-9 digits) from COPEL invoice."""
    # Best pattern: UC number followed by MM/YYYY DD/MM/YYYY R$ at bottom of page
    # e.g. "2902567 01/2026 05/02/2026 R$3.122,79"
    # or "113577680 01/2026 01/02/2026 R$3.285,91"
    m = re.search(r'\b(\d{7,9})\s+\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}\s+R\$', text)
    if m:
        uc = m.group(1)
        # Filter out NF numbers (start with 210, 310)
        if not uc.startswith('210') and not uc.startswith('310'):
            return uc

    # Pattern 2: After address line, 7-9 digit number
    m = re.search(r'Endereço[:\s]*.+?(\d{7,9})\b', text, re.DOTALL)
    if m:
        uc = m.group(1)
        if not uc.startswith('210') and not uc.startswith('310') and not uc.startswith('412'):
            return uc

    # Pattern 3: In first 1200 chars, standalone 7-9 digit number
    first_section = text[:1200]
    candidates = re.findall(r'\b(\d{7,9})\b', first_section)
    for c in candidates:
        if not c.startswith('210') and not c.startswith('310') and not c.startswith('412') and not c.startswith('043'):
            return c

    return None


def _extract_reference_month(text: str) -> Optional[str]:
    """Extract reference month MM/YYYY."""
    # Pattern: standalone MM/YYYY near beginning or after "REF"
    m = re.search(r'(?:REF[:\s]*(?:MÊS\s*/\s*ANO)?[:\s]*)?(\d{2})/(\d{4})\s+\d{2}/\d{2}/\d{4}\s+R\$', text)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    # Alternative: MM/YYYY followed by vencimento date
    m = re.search(r'\b(\d{2}/\d{4})\s+\d{2}/\d{2}/\d{4}\s+R\$', text)
    if m:
        return m.group(1)
    # Mês/Ano Consumo line
    m = re.search(r'Mês/Ano\s+Consumo.*?:\s*(\d{2}/\d{4})', text)
    if m:
        return m.group(1)
    return None


def _extract_billing_cycle(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract billing cycle start and end dates."""
    # Pattern on first page: dd/mm/yyyy dd/mm/yyyy dd dd/mm/yyyy
    # The 4 dates in sequence are: leitura anterior, leitura atual, dias, proxima leitura
    dates = re.findall(r'(\d{2}/\d{2}/\d{4})', text[:1500])
    if len(dates) >= 2:
        return dates[0], dates[1]
    return None, None


def _extract_due_date(text: str) -> Optional[str]:
    """Extract due date (VENCIMENTO)."""
    # Pattern: after REF line, the second date is the due date
    m = re.search(r'\d{2}/\d{4}\s+(\d{2}/\d{2}/\d{4})\s+R\$', text)
    if m:
        return m.group(1)
    return None


def _extract_total_amount(text: str) -> float:
    """Extract total amount R$X.XXX,XX."""
    m = re.search(r'R\$\s*([\d.,]+)', text[:2000])
    if m:
        return _parse_br_number(m.group(1))
    return 0.0


def _extract_public_lighting(text: str) -> float:
    """Extract CONT ILUMIN PUBLICA MUNICIPIO value."""
    m = re.search(r'CONT\s+ILUMIN\s+PUBLICA\s+MUNICIPIO\s+(?:UN\s+)?(\d+[.,]\d+)', text, re.IGNORECASE)
    if m:
        return _parse_br_number(m.group(1))
    # Alternative format
    m = re.search(r'CONT\s+ILUMIN\s+PUBLICA\s+MUNICIPIO\s+([\d.,]+)', text, re.IGNORECASE)
    if m:
        return _parse_br_number(m.group(1))
    return 0.0


def _extract_tariff_flag(text: str) -> Optional[str]:
    """Extract tariff flag (Bandeira)."""
    upper = text.upper()
    if 'BAND. VERMELHA' in upper or 'BAND.VERMELHA' in upper or 'BANDEIRA VERMELHA' in upper:
        return 'Vermelha'
    elif 'BAND. AMARELA' in upper or 'BAND.AMARELA' in upper or 'BANDEIRA AMARELA' in upper or 'B.AMARELA' in upper:
        return 'Amarela'
    elif 'BAND. VERDE' in upper or 'BAND.VERDE' in upper or 'BANDEIRA VERDE' in upper:
        return 'Verde'
    return None


def _extract_holder_name(text: str) -> Optional[str]:
    """Extract holder name."""
    m = re.search(r'Nome:\s*(.+?)(?:\n|\d{2}/\d{2}/\d{4})', text, re.DOTALL)
    if m:
        name = m.group(1).strip()
        name = re.sub(r'\s+', ' ', name)
        if len(name) > 3:
            return name
    return None


def _extract_document(text: str) -> Optional[str]:
    """Extract CNPJ. Look for the customer CNPJ, not COPEL's."""
    # Find all CNPJs in text
    cnpjs = re.findall(r'(\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})', text)
    # COPEL's CNPJ is 04.368.898/0001-06, skip it
    for cnpj in cnpjs:
        clean = re.sub(r'[.\s/-]', '', cnpj)
        if clean != '04368898000106':
            return cnpj
    return None


def _extract_classification(text: str) -> Optional[str]:
    """Extract classification (A4 Industrial, B3 Comercial, etc)."""
    m = re.search(r'(A[1-4]\s+Industrial[^/\n]*)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r'(B[1-3]\s+Comercial[^/\n]*)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r'(A[1-4]\s+\w+)', text)
    if m:
        return m.group(1).strip()
    m = re.search(r'(B[1-3]\s+\w+)', text)
    if m:
        return m.group(1).strip()
    return None


def _extract_address(text: str) -> Optional[str]:
    """Extract address."""
    m = re.search(r'Endereço:\s*(.+?)(?:\d{9}|\n)', text, re.DOTALL)
    if m:
        addr = re.sub(r'\s+', ' ', m.group(1).strip())
        if len(addr) > 5:
            return addr[:200]
    return None


def _extract_city(text: str) -> Optional[str]:
    """Extract city."""
    m = re.search(r'Cidade:\s*([^-\n]+)', text)
    if m:
        return m.group(1).strip()
    return None


def _extract_icms(text: str) -> float:
    """Extract ICMS value."""
    m = re.search(r'ICMS\s+([\d.,]+)\s+\d+%\s+([\d.,]+)', text)
    if m:
        return _parse_br_number(m.group(2))
    return 0.0


def _is_generator(text: str) -> bool:
    """Check if UC is a generator."""
    upper = text.upper()
    indicators = [
        'GERACAO DE ENERGIA',
        'ENERGIA GERADA/INJETADA',
        'GERAC KWH',
    ]
    return any(ind in upper for ind in indicators)


def _is_beneficiary(text: str) -> bool:
    """Check if UC is a beneficiary in SCEE."""
    upper = text.upper()
    return 'UC BENEFICIÁRIA SCEE' in upper or 'UC BENEFICIARIA SCEE' in upper or 'ENERGIA INJ. OUC' in upper


def _extract_group_a_data(text: str) -> Dict[str, Any]:
    """
    Extract Group A data from the EXTRATO DE FATURAMENTO section.
    
    Key fields from the 'Grandezas e Valores para Faturamento' table:
    - ENERGIA ELETRICA TE PONTA -> energy_registered_p_kwh
    - ENERGIA ELETRICA TE F PONTA -> energy_registered_fp_kwh
    - ENERGIA GERADA/INJETADA PONTA -> energy_injected_p_kwh (total generation ponta)
    - ENERGIA GERADA/INJETADA FORA P -> energy_injected_fp_kwh (total generation FP)
    - DEMANDA USD -> demand_measured_kw
    - DEMANDA INJETADA TP TUSD -> demand_injected_kw
    """
    data = {}

    # Energy Registered (consumed) - from "Grandezas" table or billing items
    # ENERGIA ELETRICA TE PONTA ... Medido ... Faturado ... Tarifa ... Total
    # Format: ENERGIA ELETRICA TE PONTA 5461 7037 38,00 38,00 0,562895 21,39
    m = re.search(r'ENERGIA\s+ELETRICA\s+TE\s+PONTA\s+\d+\s+\d+\s+([\d.,]+)', text)
    if m:
        data["energy_registered_p_kwh"] = _parse_br_number(m.group(1))
    else:
        # Fallback: from billing items first page
        m = re.search(r'ENERGIA\s+ELET(?:RICA)?\s+(?:TE\s+)?PONTA\s+kWh\s+([\d.,]+)', text)
        if m:
            data["energy_registered_p_kwh"] = _parse_br_number(m.group(1))
        else:
            data["energy_registered_p_kwh"] = 0

    m = re.search(r'ENERGIA\s+ELETRICA\s+TE\s+F\s+PONTA\s+\d+\s+\d+\s+([\d.,]+)', text)
    if m:
        data["energy_registered_fp_kwh"] = _parse_br_number(m.group(1))
    else:
        m = re.search(r'ENERGIA\s+ELET(?:RICA)?\s+TE\s+F\s*PONTA\s+kWh\s+([\d.,]+)', text)
        if m:
            data["energy_registered_fp_kwh"] = _parse_br_number(m.group(1))
        else:
            data["energy_registered_fp_kwh"] = 0

    # Energy Generated/Injected (total from meters) - this is the ACTUAL injection
    # ENERGIA GERADA/INJETADA PONTA 12022 24974 303,00
    m = re.search(r'ENERGIA\s+GERADA/INJETADA\s+PONTA\s+\d+\s+\d+\s+([\d.,]+)', text)
    if m:
        data["energy_injected_p_kwh"] = _parse_br_number(m.group(1))
    else:
        # Alternative: GERAC kWh PT
        m = re.search(r'GERAC\s+kWh\s+PT\s+\d+\s+\d+\s+[\d.]+\s+([\d.,]+)', text)
        if m:
            data["energy_injected_p_kwh"] = _parse_br_number(m.group(1))
        else:
            data["energy_injected_p_kwh"] = 0

    m = re.search(r'ENERGIA\s+GERADA/INJETADA\s+FORA\s+P\s+\d+\s+\d+\s+([\d.,]+)', text)
    if m:
        data["energy_injected_fp_kwh"] = _parse_br_number(m.group(1))
    else:
        # Alternative: GERAC kWh FP
        m = re.search(r'GERAC\s+kWh\s+FP\s+\d+\s+\d+\s+[\d.]+\s+([\d.,]+)', text)
        if m:
            data["energy_injected_fp_kwh"] = _parse_br_number(m.group(1))
        else:
            data["energy_injected_fp_kwh"] = 0

    # Energy compensated
    reg_p = data.get("energy_registered_p_kwh", 0)
    inj_p = data.get("energy_injected_p_kwh", 0)
    reg_fp = data.get("energy_registered_fp_kwh", 0)
    inj_fp = data.get("energy_injected_fp_kwh", 0)

    # For FP: compensated = what was offset locally = min(registered, injected)
    data["energy_compensated_fp_kwh"] = min(reg_fp, inj_fp) if inj_fp > 0 else 0
    # For P: compensated = total injected at ponta (used across all UCs in SCEE)
    data["energy_compensated_p_kwh"] = inj_p if inj_p > 0 else 0

    # Energy billed = registered - compensated (can be negative for generators)
    data["energy_billed_p_kwh"] = reg_p - data["energy_compensated_p_kwh"]
    data["energy_billed_fp_kwh"] = reg_fp - data["energy_compensated_fp_kwh"]

    # Demand
    m = re.search(r'DEMANDA\s+USD\s+(?:kW\s+)?(?:\d+\s+\d+\s+)?([\d.,]+)\s+[\d.,]+\s+([\d.,]+)', text)
    if m:
        data["demand_measured_kw"] = _parse_br_number(m.group(1))
    else:
        data["demand_measured_kw"] = 0

    m = re.search(r'DEMANDA\s+INJETADA\s+TP\s+TUSD\s+(?:kW\s+)?([\d.,]+)', text)
    if m:
        data["demand_injected_kw"] = _parse_br_number(m.group(1))
    else:
        data["demand_injected_kw"] = 0

    # Contracted demand from "Contratado" column
    m = re.search(r'DEMANDA\s+INJETADA\s+TP\s+TUSD\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', text)
    if m:
        data["demand_contracted_kw"] = _parse_br_number(m.group(2))
    else:
        data["demand_contracted_kw"] = 0

    # Tariff values - extract unit prices WITH taxes from extrato section
    tariffs = {}

    # From extrato: ENERGIA ELETRICA TE PONTA ... 38,00 38,00 0,562895 21,39
    # The tariff is the second-to-last number (unit price with taxes)
    m = re.search(r'ENERGIA\s+ELETRICA\s+TE\s+PONTA\s+\d+\s+\d+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)\s+[\d.,]+', text)
    if m:
        tariffs["te_p_unit"] = _parse_br_number(m.group(1))

    m = re.search(r'ENERGIA\s+ELETRICA\s+USD\s+PONTA\s+\d+\s+\d+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)\s+[\d.,]+', text)
    if m:
        tariffs["usd_p_unit"] = _parse_br_number(m.group(1))

    m = re.search(r'ENERGIA\s+ELETRICA\s+TE\s+F\s+PONTA\s+\d+\s+\d+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)\s+[\d.,]+', text)
    if m:
        tariffs["te_fp_unit"] = _parse_br_number(m.group(1))

    m = re.search(r'ENERGIA\s+ELETRICA\s+USD\s+F\s+PONTA\s+\d+\s+\d+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)\s+[\d.,]+', text)
    if m:
        tariffs["usd_fp_unit"] = _parse_br_number(m.group(1))

    # Calculated totals: tariff_total = TE + USD
    tariffs["tariff_total_p"] = tariffs.get("te_p_unit", 0) + tariffs.get("usd_p_unit", 0)
    tariffs["tariff_total_fp"] = tariffs.get("te_fp_unit", 0) + tariffs.get("usd_fp_unit", 0)

    # From Informacoes Suplementares - base tariffs
    m = re.search(r'CONSUMO\s+PTA\s+([\d.,]+)\s+([\d.,]+)', text)
    if m:
        tariffs["tusd_ponta"] = _parse_br_number(m.group(1))
        tariffs["te_ponta"] = _parse_br_number(m.group(2))

    m = re.search(r'CONSUMO\s+F\s+PONTA\s+([\d.,]+)\s+([\d.,]+)', text)
    if m:
        tariffs["tusd_fp"] = _parse_br_number(m.group(1))
        tariffs["te_fp"] = _parse_br_number(m.group(2))

    data["tariff_values"] = tariffs

    return data


def _extract_group_b_data(text: str) -> Dict[str, Any]:
    """
    Extract Group B data.

    For beneficiary UCs:
    - ENERGIA ELET CONSUMO -> energy_registered_fp_kwh
    - ENERGIA INJ. OUC OPT TE/TUS -> energy_compensated (sum of all injections)
    - SCEE section -> credits
    """
    data = {}

    # Energy Registered (consumed)
    # ENERGIA ELET CONSUMO ... kWh 13.579 0,375131 5.093,90
    m = re.search(r'ENERGIA\s+ELET\s+CONSUMO\s+.*?kWh\s+([\d.,]+)', text)
    if m:
        data["energy_registered_fp_kwh"] = _parse_br_number(m.group(1))
    else:
        # Try meter reading: CONSUMO kWh TP XXXXX XXXXX X XXXXX
        m = re.search(r'CONSUMO\s+kWh\s+TP\s+\d+\s+\d+\s+\d+\s+([\d.,]+)', text)
        if m:
            data["energy_registered_fp_kwh"] = _parse_br_number(m.group(1))
        else:
            data["energy_registered_fp_kwh"] = 0

    data["energy_registered_p_kwh"] = 0  # Group B has no peak

    # Energy Injected/Compensated (from OUC - other UC - compensation)
    # Sum all ENERGIA INJ. OUC lines (they appear with TE and TUS, take only TE to avoid double counting)
    # Pattern: ENERGIA INJ. OUC OPT TE MM/YYYY GDII-II kWh -11.270
    te_injections = re.findall(
        r'ENERGIA\s+INJ\.\s+OUC\s+OPT\s+TE\s+\d{2}/\d{4}\s+GDII-II\s+kWh\s+([-\d.,]+)',
        text
    )
    total_compensated = 0
    for val in te_injections:
        total_compensated += abs(_parse_br_number(val))

    data["energy_compensated_fp_kwh"] = total_compensated
    data["energy_compensated_p_kwh"] = 0

    # For beneficiary, the "injected" represents what they received
    data["energy_injected_fp_kwh"] = total_compensated
    data["energy_injected_p_kwh"] = 0

    # Energy billed
    reg = data.get("energy_registered_fp_kwh", 0)
    comp = data.get("energy_compensated_fp_kwh", 0)
    data["energy_billed_fp_kwh"] = max(0, reg - comp)
    data["energy_billed_p_kwh"] = 0

    # No demand for Group B
    data["demand_measured_kw"] = 0
    data["demand_contracted_kw"] = 0
    data["demand_injected_kw"] = 0

    # Tariff values - extract unit prices for TE and TUSD
    tariffs = {}
    consumption = data.get("energy_registered_fp_kwh", 0)

    # ENERGIA ELET USO SISTEMA line is usually clean
    # Pattern: ENERGIA ELET USO SISTEMA kWh 6.744 0,498820 3.364,04
    m = re.search(r'ENERGIA\s+ELET\s+USO\s+SISTEMA\s+kWh\s+[\d.,]+\s+([\d.,]+)', text)
    if m:
        tariffs["usd_fp_unit"] = _parse_br_number(m.group(1))
        tariffs["tusd_fp"] = tariffs["usd_fp_unit"]

    # For TE, try from INJ OUC line (always clean) or garbled CONSUMO line
    m = re.search(r'ENERGIA\s+INJ\.\s+OUC\s+OPT\s+TE.*?kWh\s+-?[\d.,]+\s+(0,\d{5,6})', text)
    if m:
        tariffs["te_fp"] = _parse_br_number(m.group(1))
        tariffs["te_fp_unit"] = tariffs["te_fp"]
    if "te_fp_unit" not in tariffs:
        m = re.search(r'ENERGIA\s+ELET\s+CONSUMO.*?kWh.*?[\d.,]+\s+\w?\s*(0,\d{5,6})', text, re.DOTALL)
        if m:
            tariffs["te_fp_unit"] = _parse_br_number(m.group(1))
            tariffs["te_fp"] = tariffs["te_fp_unit"]

    tariffs["tariff_total_fp"] = round(tariffs.get("te_fp_unit", 0) + tariffs.get("usd_fp_unit", 0), 6)
    data["tariff_values"] = tariffs

    return data


def _extract_scee_credits(text: str) -> Dict[str, Any]:
    """Extract SCEE credit balance info."""
    data = {}

    # Pattern: "Saldo Mês Ponta 74, Saldo Mês F Ponta 10489, Saldo Acumulado Ponta 64, Saldo Acumulado F Ponta 7384"
    m = re.search(r'Saldo\s+Mês\s+Ponta\s+([\d.,]+)', text)
    if m:
        data["credits_balance_p_kwh"] = _parse_br_number(m.group(1))
    else:
        data["credits_balance_p_kwh"] = 0

    m = re.search(r'Saldo\s+Mês\s+F\s+Ponta\s+([\d.,]+)', text)
    if m:
        data["credits_balance_fp_kwh"] = _parse_br_number(m.group(1))
    else:
        data["credits_balance_fp_kwh"] = 0

    m = re.search(r'Saldo\s+Acumulado\s+Ponta\s+([\d.,]+)', text)
    if m:
        data["credits_accumulated_p_kwh"] = _parse_br_number(m.group(1))
    else:
        data["credits_accumulated_p_kwh"] = 0

    m = re.search(r'Saldo\s+Acumulado\s+F\s+Ponta\s+([\d.,]+)', text)
    if m:
        data["credits_accumulated_fp_kwh"] = _parse_br_number(m.group(1))
    else:
        data["credits_accumulated_fp_kwh"] = 0

    # Generator UC reference
    m = re.search(r'Geradora:\s+UC\s+(\d+)', text)
    if m:
        data["generator_uc_number"] = m.group(1)

    return data


def _extract_billing_deductions(text: str, is_beneficiary: bool) -> float:
    """
    Calculate 'Economizado' = sum of injection billing deductions.
    - For generators: sum ALL ENERGIA INJETADA + ENERGIA INJ. BAND lines
    - For beneficiaries: sum only ENERGIA INJ. OUC lines (exclude bandeira)
    """
    total = 0.0

    if is_beneficiary:
        # Beneficiary: sum only OUC injection lines (TE + TUS)
        ouc_lines = re.findall(
            r'ENERGIA\s+INJ\.\s+OUC\s+OPT\s+TE?\w*.*?k\w+h\s+-?[\d.,]+\s+[\d.,]+\s+(-[\d.,]+)',
            text
        )
        for val in ouc_lines:
            total += abs(_parse_br_number(val))
    else:
        # Generator: sum ALL INJETADA lines including bandeira
        inj_lines = re.findall(
            r'ENERGIA\s+INJETAD[A].*?k\w+h\s+-?[\d.,]+\s+[\d.,]+\s+(-[\d.,]+)',
            text
        )
        for val in inj_lines:
            total += abs(_parse_br_number(val))

        band_lines = re.findall(
            r'ENERGIA\s+INJ\.\s+BAND\..*?k\w+h\s+-?[\d.,]+\s+[\d.,]+\s+(-[\d.,]+)',
            text
        )
        for val in band_lines:
            total += abs(_parse_br_number(val))

    return round(total, 2)


def _calculate_savings(data: Dict[str, Any]) -> float:
    """Calculate estimated savings from solar compensation."""
    comp_p = data.get("energy_compensated_p_kwh", 0)
    comp_fp = data.get("energy_compensated_fp_kwh", 0)
    tariffs = data.get("tariff_values", {})

    savings = 0.0
    te_p = tariffs.get("te_ponta", 0)
    tusd_p = tariffs.get("tusd_ponta", 0)
    if te_p > 0:
        savings += comp_p * (te_p + tusd_p)

    te_fp = tariffs.get("te_fp", 0)
    tusd_fp = tariffs.get("tusd_fp", 0)
    if te_fp > 0:
        savings += comp_fp * (te_fp + tusd_fp)
    elif comp_fp > 0:
        savings += comp_fp * 0.50

    return round(savings, 2)


def parse_copel_invoice(pdf_source) -> Dict[str, Any]:
    """
    Parse a COPEL invoice PDF and extract all relevant data.

    Args:
        pdf_source: Path to the PDF file or file-like object

    Returns:
        Dictionary with extracted invoice data including UC number for auto-matching
    """
    if pdfplumber is None:
        return {"success": False, "error": "pdfplumber nao instalado"}

    try:
        full_text = _extract_full_text(pdf_source)
        if not full_text or len(full_text) < 50:
            return {"success": False, "error": "Nao foi possivel extrair texto do PDF"}

        tariff_group = _detect_tariff_group(full_text)
        is_gen = _is_generator(full_text)
        is_ben = _is_beneficiary(full_text)

        data = {
            "success": True,
            "tariff_group": tariff_group,
            "is_generator": is_gen,
            "is_beneficiary": is_ben,
            "uc_number": _extract_uc_number(full_text),
            "holder_name": _extract_holder_name(full_text),
            "holder_document": _extract_document(full_text),
            "address": _extract_address(full_text),
            "city": _extract_city(full_text),
            "classification": _extract_classification(full_text),
            "reference_month": _extract_reference_month(full_text),
            "due_date": _extract_due_date(full_text),
            "amount_total_brl": _extract_total_amount(full_text),
            "public_lighting_brl": _extract_public_lighting(full_text),
            "icms_brl": _extract_icms(full_text),
            "tariff_flag": _extract_tariff_flag(full_text),
        }

        data["billing_cycle_start"], data["billing_cycle_end"] = _extract_billing_cycle(full_text)

        # Extract energy data based on group
        if tariff_group == "A":
            data.update(_extract_group_a_data(full_text))
        else:
            data.update(_extract_group_b_data(full_text))

        # Extract SCEE credits
        data.update(_extract_scee_credits(full_text))

        # Economizado = sum of billing deductions from INJETADA items
        billing_deductions = _extract_billing_deductions(full_text, is_ben)
        if billing_deductions > 0:
            data["amount_saved_brl"] = billing_deductions
        else:
            data["amount_saved_brl"] = _calculate_savings(data)

        return data

    except Exception as e:
        logger.error(f"Error parsing invoice PDF: {e}", exc_info=True)
        return {"success": False, "error": f"Erro ao processar PDF: {str(e)}"}
