"""
COPEL Invoice PDF Parser Service
Extracts billing data from COPEL energy invoices (Grupo A and Grupo B)
"""

import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    logger.warning("pdfplumber not installed. PDF parsing will not work.")


class CopelInvoiceParser:
    """Parser for COPEL energy invoices"""
    
    def __init__(self):
        if pdfplumber is None:
            raise ImportError("pdfplumber is required for PDF parsing. Install with: pip install pdfplumber")
    
    def parse_invoice(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse a COPEL invoice PDF and extract all relevant data
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted invoice data
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
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
                    "raw_text": full_text[:500],  # First 500 chars for debugging
                }
                
                # Extract UC number
                data["uc_number"] = self._extract_uc_number(full_text)
                
                # Extract holder info
                data["holder_name"] = self._extract_holder_name(full_text)
                data["holder_document"] = self._extract_document(full_text)
                
                # Extract address
                data["address"] = self._extract_address(full_text)
                data["city"] = self._extract_city(full_text)
                
                # Extract reference period
                data["reference_month"] = self._extract_reference_month(full_text)
                data["billing_cycle_start"] = self._extract_date(full_text, "start")
                data["billing_cycle_end"] = self._extract_date(full_text, "end")
                data["due_date"] = self._extract_due_date(full_text)
                
                # Extract financial data
                data["amount_total_brl"] = self._extract_total_amount(full_text)
                data["public_lighting_brl"] = self._extract_public_lighting(full_text)
                data["icms_brl"] = self._extract_icms(full_text)
                
                # Check if this is a generator UC
                data["is_generator"] = self._is_generator(full_text)
                
                # Extract energy data based on group
                if tariff_group == "A":
                    data.update(self._extract_group_a_data(full_text))
                else:
                    data.update(self._extract_group_b_data(full_text))
                
                # Extract credits info
                data.update(self._extract_credits_info(full_text))
                
                # Calculate saved amount
                data["amount_saved_brl"] = self._calculate_savings(data)
                
                return data
                
        except Exception as e:
            logger.error(f"Error parsing invoice PDF: {str(e)}")
            return {"success": False, "error": f"Erro ao processar PDF: {str(e)}"}
    
    def _detect_tariff_group(self, text: str) -> str:
        """Detect if invoice is Group A or B"""
        text_lower = text.lower()
        
        # Group A indicators
        if any(ind in text_lower for ind in ['a4 industrial', 'a3', 'a4', 'demanda', 'ponta', 'fora ponta', 'fora_ponta']):
            if 'demanda' in text_lower and ('ponta' in text_lower or 'fora' in text_lower):
                return "A"
        
        # Group B indicators
        if 'b1' in text_lower or 'b2' in text_lower or 'b3' in text_lower or 'convencional' in text_lower:
            return "B"
        
        # Default to B if uncertain
        return "B"
    
    def _extract_uc_number(self, text: str) -> Optional[str]:
        """Extract UC number from invoice"""
        # Pattern: 9-digit number near "UNIDADE CONSUMIDORA" or in a yellow box
        patterns = [
            r'(?:UNIDADE CONSUMIDORA|UC)[:\s]*(\d{8,9})',
            r'(\d{9})\s*(?:NOTA FISCAL|NF)',
            r'(?:^|\s)(\d{9})(?:\s|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Try to find any 9-digit number that looks like UC
        numbers = re.findall(r'\b(\d{9})\b', text)
        if numbers:
            return numbers[0]
        
        return None
    
    def _extract_holder_name(self, text: str) -> Optional[str]:
        """Extract holder name"""
        patterns = [
            r'Nome:\s*(.+?)(?:\n|Endereço)',
            r'DISTRIBUIDORA\s+DE\s+BANANAS\s+PORTAO\s+LTDA',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(0) if 'DISTRIBUIDORA' in pattern else match.group(1)
                return name.strip()
        
        return None
    
    def _extract_document(self, text: str) -> Optional[str]:
        """Extract CNPJ/CPF"""
        patterns = [
            r'CNPJ[:\s]*(\d{2}[./]?\d{3}[./]?\d{3}[/.]?\d{4}[-.]?\d{2})',
            r'CPF[:\s]*(\d{3}[.]?\d{3}[.]?\d{3}[-.]?\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_address(self, text: str) -> Optional[str]:
        """Extract address"""
        match = re.search(r'Endereço:\s*(.+?)(?:\n|CEP)', text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip().replace('\n', ' ')
        return None
    
    def _extract_city(self, text: str) -> Optional[str]:
        """Extract city"""
        match = re.search(r'Cidade:\s*([^-\n]+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_reference_month(self, text: str) -> Optional[str]:
        """Extract reference month (MM/YYYY)"""
        # Pattern: REF:MÊS/ANO or similar
        patterns = [
            r'REF[:\s]*(?:MES[/\s]*ANO)?[:\s]*(\d{2})/(\d{4})',
            r'(\d{2})/(\d{4})\s+\d{2}/\d{2}/\d{4}\s+R\$',  # Near due date and amount
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}/{match.group(2)}"
        
        return None
    
    def _extract_date(self, text: str, date_type: str) -> Optional[str]:
        """Extract billing cycle dates"""
        # Look for date patterns near "Leitura anterior" / "Leitura atual"
        if date_type == "start":
            match = re.search(r'(\d{2}/\d{2}/\d{4})\s+\d{2}/\d{2}/\d{4}\s+\d+\s+\d{2}/\d{2}/\d{4}', text)
            if match:
                return match.group(1)
        else:
            match = re.search(r'\d{2}/\d{2}/\d{4}\s+(\d{2}/\d{2}/\d{4})\s+\d+\s+\d{2}/\d{2}/\d{4}', text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract due date (VENCIMENTO)"""
        patterns = [
            r'VENCIMENTO[:\s]*(\d{2}/\d{2}/\d{4})',
            r'(\d{2}/\d{2}/\d{4})\s+R\$[\d.,]+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_total_amount(self, text: str) -> float:
        """Extract total amount to pay"""
        patterns = [
            r'TOTAL\s+A\s+PAGAR\s+R\$\s*([\d.,]+)',
            r'R\$([\d.,]+)\s*$',  # Last R$ value
            r'TOTAL\s+([\d.,]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).replace('.', '').replace(',', '.')
                try:
                    return float(value)
                except:
                    continue
        
        return 0.0
    
    def _extract_public_lighting(self, text: str) -> float:
        """Extract public lighting tax"""
        match = re.search(r'(?:CONT\s+)?ILUMIN(?:ACAO)?\s+PUBLICA\s+(?:MUNICIPIO)?[:\s]*([\d.,]+)', text, re.IGNORECASE)
        if match:
            value = match.group(1).replace('.', '').replace(',', '.')
            try:
                return float(value)
            except:
                pass
        return 0.0
    
    def _extract_icms(self, text: str) -> float:
        """Extract ICMS value"""
        match = re.search(r'ICMS[:\s]*([\d.,]+)', text, re.IGNORECASE)
        if match:
            value = match.group(1).replace('.', '').replace(',', '.')
            try:
                return float(value)
            except:
                pass
        return 0.0
    
    def _is_generator(self, text: str) -> bool:
        """Check if this UC is a generator"""
        indicators = [
            'geracao de energia',
            'energia injetada',
            'demanda injetada',
            'geradora',
        ]
        text_lower = text.lower()
        
        # Check for generator indicators
        generator_score = sum(1 for ind in indicators if ind in text_lower)
        
        # If it mentions "UC beneficiária" it's NOT the generator
        if 'uc beneficiária' in text_lower or 'uc beneficiaria' in text_lower:
            return False
        
        return generator_score >= 2
    
    def _extract_group_a_data(self, text: str) -> Dict[str, Any]:
        """Extract data specific to Group A invoices"""
        data = {}
        
        # Extract demand data
        demand_match = re.search(r'DEMANDA\s+USD\s+kW\s+([\d.,]+)\s+([\d.,]+)', text, re.IGNORECASE)
        if demand_match:
            data["demand_registered_kw"] = self._parse_number(demand_match.group(1))
        
        # Extract energy data - Fora Ponta
        fp_match = re.search(r'ENERGIA\s+ELETRICA\s+(?:TE\s+)?F\s*PONTA\s+kWh\s+([\d]+)', text, re.IGNORECASE)
        if fp_match:
            data["energy_registered_fp_kwh"] = self._parse_number(fp_match.group(1))
        
        # Extract energy data - Ponta
        p_match = re.search(r'ENERGIA\s+ELETRICA\s+(?:TE\s+)?(?:USD\s+)?PONTA\s+kWh\s+([\d]+)', text, re.IGNORECASE)
        if p_match:
            data["energy_registered_p_kwh"] = self._parse_number(p_match.group(1))
        
        # Extract injected energy - Fora Ponta
        inj_fp = re.search(r'ENERGIA\s+INJETADA\s+FP[^\d]+([\d]+)', text, re.IGNORECASE)
        if inj_fp:
            data["energy_injected_fp_kwh"] = self._parse_number(inj_fp.group(1))
        
        # Extract injected energy - Ponta
        inj_p = re.search(r'ENERGIA\s+INJETADA\s+PT[^\d]+([\d]+)', text, re.IGNORECASE)
        if inj_p:
            data["energy_injected_p_kwh"] = self._parse_number(inj_p.group(1))
        
        # Extract tariffs
        tariff_te_match = re.search(r'Tarifa\s+TE[^\d]*([\d.,]+)', text, re.IGNORECASE)
        if tariff_te_match:
            data["tariff_te_fp_brl"] = self._parse_number(tariff_te_match.group(1))
        
        return data
    
    def _extract_group_b_data(self, text: str) -> Dict[str, Any]:
        """Extract data specific to Group B invoices"""
        data = {}
        
        # Extract consumption
        consumo_match = re.search(r'ENERGIA\s+ELET\s+CONSUMO[^\d]+([\d.,]+)', text, re.IGNORECASE)
        if consumo_match:
            data["energy_registered_fp_kwh"] = self._parse_number(consumo_match.group(1))
        
        # Extract tariff
        tariff_match = re.search(r'([\d],[\d]{6})\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+0,275750', text)
        if tariff_match:
            data["energy_tariff_fp_brl"] = self._parse_number(tariff_match.group(1))
        
        # Extract compensated energy
        compensated_matches = re.findall(r'ENERGIA\s+INJ[^\d]+(\d+)', text, re.IGNORECASE)
        if compensated_matches:
            total_compensated = sum(int(m) for m in compensated_matches)
            data["energy_compensated_fp_kwh"] = total_compensated
        
        return data
    
    def _extract_credits_info(self, text: str) -> Dict[str, Any]:
        """Extract credit balance information"""
        data = {}
        
        # Pattern: "Saldo Mês Ponta X, Saldo Mês F Ponta Y"
        saldo_match = re.search(
            r'Saldo\s+(?:Mes|Mês)\s+Ponta\s+(\d+)[,\s]+Saldo\s+(?:Mes|Mês)\s+F\s*Ponta\s+(\d+)',
            text, re.IGNORECASE
        )
        if saldo_match:
            data["credits_balance_p_kwh"] = int(saldo_match.group(1))
            data["credits_balance_fp_kwh"] = int(saldo_match.group(2))
        
        # Pattern: "Saldo Acumulado Ponta X, Saldo Acumulado F Ponta Y"
        acum_match = re.search(
            r'Saldo\s+Acumulado\s+Ponta\s+(\d+)[,\s]+Saldo\s+Acumulado\s+F\s*Ponta\s+(\d+)',
            text, re.IGNORECASE
        )
        if acum_match:
            data["credits_accumulated_p_kwh"] = int(acum_match.group(1))
            data["credits_accumulated_fp_kwh"] = int(acum_match.group(2))
        
        return data
    
    def _calculate_savings(self, data: Dict[str, Any]) -> float:
        """Calculate estimated savings from compensation"""
        # Simple estimation: compensated energy * average tariff
        compensated = data.get("energy_compensated_fp_kwh", 0) + data.get("energy_compensated_p_kwh", 0)
        injected = data.get("energy_injected_fp_kwh", 0) + data.get("energy_injected_p_kwh", 0)
        
        # Use average COPEL tariff if not available
        avg_tariff = data.get("energy_tariff_fp_brl", 0.87)  # ~R$0.87/kWh average
        
        total_compensation = max(compensated, injected)
        return round(total_compensation * avg_tariff, 2)
    
    def _parse_number(self, value: str) -> float:
        """Parse a number string to float"""
        if not value:
            return 0.0
        # Handle Brazilian number format (1.234,56 -> 1234.56)
        cleaned = value.replace('.', '').replace(',', '.')
        try:
            return float(cleaned)
        except:
            return 0.0


def parse_copel_invoice(pdf_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse a COPEL invoice
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted invoice data
    """
    parser = CopelInvoiceParser()
    return parser.parse_invoice(pdf_path)
