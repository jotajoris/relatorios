"""
COPEL Invoice PDF Parser Service - Enhanced Version
Extracts billing data from COPEL energy invoices (Grupo A and Grupo B)
Automatically identifies the UC from the invoice
"""

import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    logger.warning("pdfplumber not installed. PDF parsing will not work.")


class CopelInvoiceParser:
    """Parser for COPEL energy invoices - Grupo A and Grupo B"""
    
    def __init__(self):
        if pdfplumber is None:
            raise ImportError("pdfplumber is required for PDF parsing. Install with: pip install pdfplumber")
    
    def parse_invoice(self, pdf_source) -> Dict[str, Any]:
        """
        Parse a COPEL invoice PDF and extract all relevant data
        
        Args:
            pdf_source: Path to the PDF file or file-like object
            
        Returns:
            Dictionary with extracted invoice data including UC number for auto-matching
        """
        try:
            with pdfplumber.open(pdf_source) as pdf:
                # Extract text from all pages
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                
                if not full_text:
                    return {"success": False, "error": "Não foi possível extrair texto do PDF"}
                
                # Determine if it's Group A or B
                tariff_group = self._detect_tariff_group(full_text)
                
                # Extract common data
                data = {
                    "success": True,
                    "tariff_group": tariff_group,
                }
                
                # Extract UC number - CRITICAL for auto-matching
                data["uc_number"] = self._extract_uc_number(full_text)
                
                # Extract holder info
                data["holder_name"] = self._extract_holder_name(full_text)
                data["holder_document"] = self._extract_document(full_text)
                
                # Extract address
                data["address"] = self._extract_address(full_text)
                data["city"] = self._extract_city(full_text)
                
                # Extract classification
                data["classification"] = self._extract_classification(full_text, tariff_group)
                
                # Extract reference period
                data["reference_month"] = self._extract_reference_month(full_text)
                data["billing_cycle_start"], data["billing_cycle_end"] = self._extract_billing_cycle(full_text)
                data["due_date"] = self._extract_due_date(full_text)
                
                # Extract financial data
                data["amount_total_brl"] = self._extract_total_amount(full_text)
                data["public_lighting_brl"] = self._extract_public_lighting(full_text)
                
                # Extract taxes
                data["icms_brl"] = self._extract_tax(full_text, "ICMS")
                data["pis_brl"] = self._extract_tax(full_text, "PIS")
                data["cofins_brl"] = self._extract_tax(full_text, "COFINS")
                
                # Check if this is a generator UC
                data["is_generator"] = self._is_generator(full_text)
                
                # Extract energy data based on group
                if tariff_group == "A":
                    data.update(self._extract_group_a_data(full_text))
                else:
                    data.update(self._extract_group_b_data(full_text))
                
                # Extract credits info (SCEE)
                data.update(self._extract_credits_info(full_text))
                
                # Extract tariff info
                data["tariff_values"] = self._extract_tariffs(full_text)
                data["tariff_flag"] = self._extract_tariff_flag(full_text)
                
                # Calculate saved amount
                data["amount_saved_brl"] = self._calculate_savings(data)
                
                return data
                
        except Exception as e:
            logger.error(f"Error parsing invoice PDF: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": f"Erro ao processar PDF: {str(e)}"}
    
    def _detect_tariff_group(self, text: str) -> str:
        """Detect if invoice is Group A or B"""
        text_upper = text.upper()
        
        # Group A indicators - has demand and peak/off-peak tariffs
        group_a_indicators = [
            'A4 INDUSTRIAL', 'A4 COMERCIAL', 'A3 ', 'A2 ', 
            'DEMANDA USD', 'DEMANDA PONTA', 'DEMANDA FORA PONTA',
            'ENERGIA ELETRICA TE PONTA', 'ENERGIA ELETRICA USD PONTA',
            'TARIFA BINÔMIA', 'TARIFA BINOMIA'
        ]
        
        if any(ind in text_upper for ind in group_a_indicators):
            return "A"
        
        # Group B indicators
        group_b_indicators = ['B1 ', 'B2 ', 'B3 ', 'CONVENCIONAL', 'MONÔMIA']
        if any(ind in text_upper for ind in group_b_indicators):
            return "B"
        
        return "B"  # Default to B
    
    def _extract_uc_number(self, text: str) -> Optional[str]:
        """Extract UC number from invoice - 9 digit number"""
        # Clean text for better matching
        text_clean = re.sub(r'\s+', ' ', text)
        
        # Pattern 1: UC in address line (very common in COPEL invoices)
        # Format: "Endereço: ... - XXXXXXXXX" or after "Rod Br 116"
        patterns = [
            r'Endereço[:\s]*[^-]*-[^-]*-\s*(\d{9})',  # UC number at end of address
            r'(?:UC\s+UC\s*)?(\d{9})\s+(?:NF|Nota|NOTA)',  # Before "NF"
            r'(?:UNIDADE\s*CONSUMIDORA|UC)\s*[:\s]*(\d{9})',  # Explicit UC label
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Pattern 2: Look for 9-digit numbers in the first 800 chars
        # Skip invoice numbers (usually start with 21XXXXXXX for NF)
        first_section = text[:800]
        numbers = re.findall(r'\b(\d{9})\b', first_section)
        
        # Filter out NF numbers (series 210, etc)
        valid_ucs = [n for n in numbers if not n.startswith('210') and not n.startswith('310')]
        
        if valid_ucs:
            return valid_ucs[0]
        
        # Fallback: any 9-digit number
        if numbers:
            return numbers[0]
        
        return None
    
    def _extract_holder_name(self, text: str) -> Optional[str]:
        """Extract holder name"""
        patterns = [
            r'(?:Nome|Titular)[:\s]*([A-Z][A-Z\s]+?(?:LTDA|S\.?A\.?|ME|EPP|EIRELI)?)\s*(?:\n|Endereço|CPF|CNPJ)',
            r'(DISTRIBUIDORA\s+DE\s+BANANAS\s+PORTAO\s+LTDA)',
            r'([A-Z][A-Z\s]+?LTDA)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up
                name = re.sub(r'\s+', ' ', name)
                if len(name) > 5:
                    return name
        
        return None
    
    def _extract_document(self, text: str) -> Optional[str]:
        """Extract CNPJ/CPF"""
        # CNPJ pattern: XX.XXX.XXX/XXXX-XX
        cnpj_match = re.search(r'(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})', text)
        if cnpj_match:
            return cnpj_match.group(1)
        
        # CPF pattern: XXX.XXX.XXX-XX
        cpf_match = re.search(r'(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2})', text)
        if cpf_match:
            return cpf_match.group(1)
        
        return None
    
    def _extract_address(self, text: str) -> Optional[str]:
        """Extract address"""
        patterns = [
            r'Endereço[:\s]*(.+?)(?:\n|CEP|Cidade)',
            r'(?:^|\n)([A-Z][a-z]+\s+[A-Z][a-z]+.+?(?:CEP|$))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                addr = match.group(1).strip()
                addr = re.sub(r'\s+', ' ', addr)
                if len(addr) > 10:
                    return addr[:200]  # Limit length
        
        return None
    
    def _extract_city(self, text: str) -> Optional[str]:
        """Extract city"""
        patterns = [
            r'Cidade[:\s]*([^-\n,]+)',
            r',\s*([A-Za-z\s]+)\s*-\s*PR',
            r'([A-Za-z\s]+)\s*-\s*(?:Estado\s*:?\s*)?PR',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                city = match.group(1).strip()
                if len(city) > 2 and len(city) < 50:
                    return city
        
        return None
    
    def _extract_classification(self, text: str, tariff_group: str) -> Optional[str]:
        """Extract classification (A4 Industrial, B3 Comercial, etc)"""
        text_upper = text.upper()
        
        if tariff_group == "A":
            patterns = [
                r'(A[1-4]\s*(?:INDUSTRIAL|COMERCIAL|RURAL)[^,\n]*)',
                r'(A[1-4]\s+\w+)',
            ]
        else:
            patterns = [
                r'(B[1-3]\s*(?:RESIDENCIAL|COMERCIAL|RURAL|SERVIÇOS)[^,\n]*)',
                r'(B[1-3]\s+\w+)',
            ]
        
        for pattern in patterns:
            match = re.search(pattern, text_upper)
            if match:
                return match.group(1).strip()
        
        return f"{tariff_group}3 Comercial" if tariff_group else None
    
    def _extract_reference_month(self, text: str) -> Optional[str]:
        """Extract reference month (MM/YYYY or YYYY-MM)"""
        patterns = [
            r'REF[:\s]*(?:MÊS/ANO|MES/ANO)?[:\s]*(\d{2})[/\-](\d{4})',
            r'(?:REFERENTE|REFERÊNCIA)[:\s]*(\d{2})[/\-](\d{4})',
            r'(\d{2})/(\d{4})\s+\d{2}/\d{2}/\d{4}',  # Before due date
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}/{match.group(2)}"
        
        return None
    
    def _extract_billing_cycle(self, text: str) -> tuple:
        """Extract billing cycle start and end dates"""
        # Look for reading dates pattern: anterior DD/MM/YYYY atual DD/MM/YYYY
        date_pattern = r'(\d{2}/\d{2}/\d{4})'
        dates = re.findall(date_pattern, text)
        
        if len(dates) >= 2:
            return dates[0], dates[1]
        
        return None, None
    
    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract due date (VENCIMENTO)"""
        patterns = [
            r'VENCIMENTO[:\s]*(\d{2}/\d{2}/\d{4})',
            r'VENC(?:IMT)?[:\s]*(\d{2}/\d{2}/\d{4})',
            r'(\d{2}/\d{2}/\d{4})\s+R\$\s*[\d.,]+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_total_amount(self, text: str) -> float:
        """Extract total amount to pay"""
        patterns = [
            r'TOTAL\s+(?:A\s+)?PAGAR[:\s]*R?\$?\s*([\d.,]+)',
            r'VALOR\s+TOTAL[:\s]*R?\$?\s*([\d.,]+)',
            r'TOTAL[:\s]*R?\$?\s*([\d.,]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                value = self._parse_brazilian_number(match)
                if value and value > 0:
                    return value
        
        return 0.0
    
    def _extract_public_lighting(self, text: str) -> float:
        """Extract public lighting tax"""
        patterns = [
            r'(?:CONT\.?\s*)?ILUMIN(?:AÇÃO|ACAO)?\s*PUBLICA[:\s]*([\d.,]+)',
            r'CIP[:\s]*([\d.,]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_brazilian_number(match.group(1))
        
        return 0.0
    
    def _extract_tax(self, text: str, tax_name: str) -> float:
        """Extract specific tax value"""
        pattern = rf'{tax_name}[:\s]*([\d.,]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return self._parse_brazilian_number(match.group(1))
        return 0.0
    
    def _is_generator(self, text: str) -> bool:
        """Check if UC is a generator (has energy injection)"""
        generator_indicators = [
            'GERAÇÃO', 'GERACAO', 'GERADORA', 
            'ENERGIA INJETADA', 'INJETADA',
            'GD', 'GDII', 'GD-II',
            'SCEE'
        ]
        text_upper = text.upper()
        return any(ind in text_upper for ind in generator_indicators)
    
    def _extract_group_a_data(self, text: str) -> Dict[str, Any]:
        """Extract Group A specific data (with demand and peak/off-peak)"""
        data = {}
        
        # Energy Registered (consumed)
        data["energy_registered_p_kwh"] = self._extract_energy_value(text, 
            [r'ENERGIA\s+ELET(?:RICA)?\s+(?:TE\s+)?PONTA[:\s]*([\d.,]+)\s*kWh',
             r'ENERGIA\s+ELET(?:RICA)?\s+USD?\s+PONTA[:\s]*([\d.,]+)'])
        
        data["energy_registered_fp_kwh"] = self._extract_energy_value(text,
            [r'ENERGIA\s+ELET(?:RICA)?\s+(?:TE\s+)?F(?:ORA)?\s*PONTA[:\s]*([\d.,]+)\s*kWh',
             r'ENERGIA\s+ELET(?:RICA)?\s+USD?\s+F(?:ORA)?\s*PONTA[:\s]*([\d.,]+)'])
        
        # Energy Injected
        data["energy_injected_p_kwh"] = abs(self._extract_energy_value(text,
            [r'ENERGIA\s+INJETADA\s+P(?:ON)?T(?:A)?\s+TE[:\s]*-?([\d.,]+)',
             r'ENERGIA\s+INJ(?:ETADA)?\s+P(?:ON)?T[:\s]*-?([\d.,]+)']))
        
        data["energy_injected_fp_kwh"] = abs(self._extract_energy_value(text,
            [r'ENERGIA\s+INJETADA\s+FP\s+TE[:\s]*-?([\d.,]+)',
             r'ENERGIA\s+INJ(?:ETADA)?\s+FP[:\s]*-?([\d.,]+)']))
        
        # Demand
        data["demand_contracted_kw"] = self._extract_energy_value(text,
            [r'DEMANDA\s+CONTRATADA[:\s]*([\d.,]+)\s*kW'])
        
        data["demand_measured_kw"] = self._extract_energy_value(text,
            [r'DEMANDA\s+(?:MEDIDA|USD)[:\s]*([\d.,]+)\s*kW',
             r'DEMANDA\s+USD[:\s]*([\d.,]+)'])
        
        data["demand_injected_kw"] = self._extract_energy_value(text,
            [r'DEMANDA\s+INJETADA[:\s]*([\d.,]+)'])
        
        # Calculate compensated and billed
        data["energy_compensated_p_kwh"] = min(data.get("energy_registered_p_kwh", 0), 
                                                data.get("energy_injected_p_kwh", 0))
        data["energy_compensated_fp_kwh"] = min(data.get("energy_registered_fp_kwh", 0),
                                                 data.get("energy_injected_fp_kwh", 0))
        
        data["energy_billed_p_kwh"] = max(0, data.get("energy_registered_p_kwh", 0) - 
                                          data.get("energy_compensated_p_kwh", 0))
        data["energy_billed_fp_kwh"] = max(0, data.get("energy_registered_fp_kwh", 0) -
                                           data.get("energy_compensated_fp_kwh", 0))
        
        return data
    
    def _extract_group_b_data(self, text: str) -> Dict[str, Any]:
        """Extract Group B specific data (without demand, simpler)"""
        data = {}
        
        # Energy Registered (consumed) - single value, not split by peak
        data["energy_registered_fp_kwh"] = self._extract_energy_value(text,
            [r'ENERGIA\s+ELET(?:RICA)?\s+CONSUMO[:\s]*([\d.,]+)\s*kWh',
             r'CONSUMO[:\s]*([\d.,]+)\s*kWh',
             r'kWh[:\s]*([\d.,]+)'])
        data["energy_registered_p_kwh"] = 0  # Group B doesn't have peak
        
        # Energy Injected (if generator/beneficiary)
        injected = self._extract_energy_value(text,
            [r'ENERGIA\s+INJ(?:ETADA)?[:\s]*-?([\d.,]+)',
             r'INJ(?:ETADA)?[:\s]*-?([\d.,]+)\s*kWh'])
        data["energy_injected_fp_kwh"] = abs(injected)
        data["energy_injected_p_kwh"] = 0
        
        # Energy Compensated
        compensated = self._extract_energy_value(text,
            [r'ENERGIA\s+COMPENSADA[:\s]*([\d.,]+)',
             r'COMPENSAD[AO][:\s]*([\d.,]+)\s*kWh'])
        
        if compensated == 0:
            compensated = min(data.get("energy_registered_fp_kwh", 0),
                             data.get("energy_injected_fp_kwh", 0))
        
        data["energy_compensated_fp_kwh"] = compensated
        data["energy_compensated_p_kwh"] = 0
        
        # Energy Billed
        billed = self._extract_energy_value(text,
            [r'ENERGIA\s+FATURADA[:\s]*([\d.,]+)',
             r'FATURAD[AO][:\s]*([\d.,]+)\s*kWh'])
        
        if billed == 0:
            billed = max(0, data.get("energy_registered_fp_kwh", 0) - 
                        data.get("energy_compensated_fp_kwh", 0))
        
        data["energy_billed_fp_kwh"] = billed
        data["energy_billed_p_kwh"] = 0
        
        return data
    
    def _extract_credits_info(self, text: str) -> Dict[str, Any]:
        """Extract credit balance info (SCEE)"""
        data = {}
        
        # Previous credits
        data["credits_balance_fp_kwh"] = self._extract_energy_value(text,
            [r'CREDITO\s+ANTERIOR[:\s]*([\d.,]+)',
             r'SALDO\s+ANTERIOR[:\s]*([\d.,]+)',
             r'CR[ÉE]DITO[:\s]*([\d.,]+)\s*kWh'])
        
        data["credits_balance_p_kwh"] = self._extract_energy_value(text,
            [r'CREDITO\s+(?:ANTERIOR\s+)?PONTA[:\s]*([\d.,]+)'])
        
        # Accumulated credits
        data["credits_accumulated_fp_kwh"] = self._extract_energy_value(text,
            [r'CREDITO\s+ACUMULADO[:\s]*([\d.,]+)',
             r'SALDO\s+ATUAL[:\s]*([\d.,]+)',
             r'SALDO\s+FP[:\s]*([\d.,]+)'])
        
        data["credits_accumulated_p_kwh"] = self._extract_energy_value(text,
            [r'CREDITO\s+ACUMULADO\s+PONTA[:\s]*([\d.,]+)',
             r'SALDO\s+P(?:ONTA)?[:\s]*([\d.,]+)'])
        
        return data
    
    def _extract_tariffs(self, text: str) -> Dict[str, float]:
        """Extract tariff values"""
        tariffs = {}
        
        # TE (Tarifa de Energia)
        te_ponta = self._extract_energy_value(text,
            [r'TE\s+PONTA[:\s]*([\d.,]+)',
             r'TARIFA\s+TE\s+PONTA[:\s]*([\d.,]+)'])
        if te_ponta:
            tariffs["te_ponta"] = te_ponta
        
        te_fp = self._extract_energy_value(text,
            [r'TE\s+F(?:ORA)?\s*PONTA[:\s]*([\d.,]+)',
             r'TARIFA\s+TE\s+FP[:\s]*([\d.,]+)'])
        if te_fp:
            tariffs["te_fp"] = te_fp
        
        # TUSD
        tusd_ponta = self._extract_energy_value(text,
            [r'TUSD\s+PONTA[:\s]*([\d.,]+)'])
        if tusd_ponta:
            tariffs["tusd_ponta"] = tusd_ponta
        
        tusd_fp = self._extract_energy_value(text,
            [r'TUSD\s+F(?:ORA)?\s*PONTA[:\s]*([\d.,]+)'])
        if tusd_fp:
            tariffs["tusd_fp"] = tusd_fp
        
        return tariffs
    
    def _extract_tariff_flag(self, text: str) -> Optional[str]:
        """Extract tariff flag (Bandeira)"""
        text_upper = text.upper()
        
        if 'VERMELHA' in text_upper:
            return 'Vermelha'
        elif 'AMARELA' in text_upper:
            return 'Amarela'
        elif 'VERDE' in text_upper:
            return 'Verde'
        
        return None
    
    def _extract_energy_value(self, text: str, patterns: List[str]) -> float:
        """Extract energy value using multiple patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = self._parse_brazilian_number(match.group(1))
                if value is not None:
                    return value
        return 0.0
    
    def _parse_brazilian_number(self, value: str) -> Optional[float]:
        """Parse Brazilian number format (1.234,56) to float"""
        if not value:
            return None
        try:
            # Remove spaces
            value = value.strip()
            # Brazilian format: 1.234,56 -> 1234.56
            value = value.replace('.', '').replace(',', '.')
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _calculate_savings(self, data: Dict[str, Any]) -> float:
        """Calculate estimated savings from solar compensation"""
        # Get compensated energy
        compensated_p = data.get("energy_compensated_p_kwh", 0)
        compensated_fp = data.get("energy_compensated_fp_kwh", 0)
        total_compensated = compensated_p + compensated_fp
        
        if total_compensated <= 0:
            return 0.0
        
        # Estimate average tariff
        tariffs = data.get("tariff_values", {})
        avg_tariff = tariffs.get("te_fp", 0.5)  # Default to R$0.50/kWh
        
        if avg_tariff == 0:
            avg_tariff = 0.5
        
        # Calculate savings
        savings = total_compensated * avg_tariff
        
        return round(savings, 2)


# Convenience function
def parse_copel_invoice(pdf_source) -> Dict[str, Any]:
    """
    Parse a COPEL invoice PDF
    
    Args:
        pdf_source: Path to PDF file or file-like object (BytesIO)
        
    Returns:
        Dictionary with all extracted invoice data
    """
    parser = CopelInvoiceParser()
    return parser.parse_invoice(pdf_source)
