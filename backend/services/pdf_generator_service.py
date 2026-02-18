"""
PDF Report Generator Service
Generates professional PDF reports for solar plants
Based on the SOLARZ report template style
"""
import os
import io
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# Colors based on ON Soluções brand
YELLOW_PRIMARY = colors.HexColor('#FFD600')
BLACK_PRIMARY = colors.HexColor('#1A1A1A')
GRAY_LIGHT = colors.HexColor('#F4F4F5')
GRAY_MEDIUM = colors.HexColor('#9CA3AF')
GREEN_SUCCESS = colors.HexColor('#10B981')
WHITE = colors.white


class SolarReportGenerator:
    """Generates PDF reports for solar plants"""
    
    def __init__(self, logo_path: Optional[str] = None):
        self.logo_path = logo_path
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            fontSize=24,
            fontName='Helvetica-Bold',
            textColor=BLACK_PRIMARY,
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=BLACK_PRIMARY,
            spaceBefore=16,
            spaceAfter=8
        ))
        self.styles.add(ParagraphStyle(
            name='SubTitle',
            fontSize=12,
            fontName='Helvetica',
            textColor=GRAY_MEDIUM,
            spaceAfter=16
        ))
        self.styles.add(ParagraphStyle(
            name='KPILabel',
            fontSize=10,
            fontName='Helvetica',
            textColor=GRAY_MEDIUM
        ))
        self.styles.add(ParagraphStyle(
            name='KPIValue',
            fontSize=20,
            fontName='Helvetica-Bold',
            textColor=BLACK_PRIMARY
        ))
        self.styles.add(ParagraphStyle(
            name='BodyText',
            fontSize=10,
            fontName='Helvetica',
            textColor=BLACK_PRIMARY,
            leading=14
        ))
    
    def _format_number(self, value: float, decimals: int = 2) -> str:
        """Format number with Brazilian locale (comma as decimal separator)"""
        if value is None:
            return "0"
        formatted = f"{value:,.{decimals}f}"
        # Convert to Brazilian format
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted
    
    def _format_currency(self, value: float) -> str:
        """Format currency in BRL"""
        return f"R$ {self._format_number(value, 2)}"
    
    def _create_header(self, plant_name: str, month_year: str, company_name: str) -> List:
        """Create the report header section"""
        elements = []
        
        # Company name
        elements.append(Paragraph(company_name.upper(), self.styles['SubTitle']))
        
        # Month and Year + Plant Name
        month_names = {
            '01': 'JANEIRO', '02': 'FEVEREIRO', '03': 'MARÇO', '04': 'ABRIL',
            '05': 'MAIO', '06': 'JUNHO', '07': 'JULHO', '08': 'AGOSTO',
            '09': 'SETEMBRO', '10': 'OUTUBRO', '11': 'NOVEMBRO', '12': 'DEZEMBRO'
        }
        
        parts = month_year.split('-') if '-' in month_year else month_year.split('/')
        if len(parts) == 2:
            if len(parts[0]) == 4:  # YYYY-MM
                year, month = parts[0], parts[1]
            else:  # MM/YYYY
                month, year = parts[0], parts[1]
            month_name = month_names.get(month, month)
            title = f"{month_name} {year}, {plant_name.upper()}"
        else:
            title = f"{month_year}, {plant_name.upper()}"
        
        elements.append(Paragraph(title, self.styles['ReportTitle']))
        elements.append(Spacer(1, 8*mm))
        
        return elements
    
    def _create_kpi_row(self, kpis: List[Dict]) -> Table:
        """Create a row of KPI cards"""
        # Build the data for the table
        data = []
        labels = []
        values = []
        
        for kpi in kpis:
            labels.append(Paragraph(kpi['label'], self.styles['KPILabel']))
            values.append(Paragraph(kpi['value'], self.styles['KPIValue']))
        
        data.append(labels)
        data.append(values)
        
        col_width = (A4[0] - 30*mm) / len(kpis)
        table = Table(data, colWidths=[col_width] * len(kpis))
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 1), (-1, 1), 2),
        ]))
        
        return table
    
    def _create_generation_chart(self, daily_data: List[Dict], prognosis_daily: float) -> Drawing:
        """Create the daily generation bar chart with prognosis line"""
        drawing = Drawing(500, 180)
        
        # Prepare data
        generation_values = []
        for d in daily_data[:31]:  # Max 31 days
            generation_values.append(d.get('generation_kwh', 0))
        
        # Create bar chart
        bc = VerticalBarChart()
        bc.x = 50
        bc.y = 30
        bc.width = 420
        bc.height = 130
        bc.data = [generation_values]
        bc.strokeColor = colors.transparent
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = max(max(generation_values) if generation_values else 100, prognosis_daily) * 1.2
        bc.valueAxis.valueStep = bc.valueAxis.valueMax / 5
        bc.categoryAxis.labels.boxAnchor = 'ne'
        bc.categoryAxis.labels.dx = -2
        bc.categoryAxis.labels.dy = -2
        bc.categoryAxis.labels.angle = 0
        bc.categoryAxis.labels.fontSize = 7
        bc.categoryAxis.categoryNames = [str(i+1) for i in range(len(generation_values))]
        bc.bars[0].fillColor = colors.HexColor('#9CA3AF')
        bc.bars[0].strokeColor = None
        
        drawing.add(bc)
        
        return drawing
    
    def _create_historical_table(self, historical_data: List[Dict]) -> Table:
        """Create the historical monthly data table"""
        # Header
        data = [['Mês/Ano', 'Prognóstico (kWh/mês)', 'Geração (kWh/mês)', 'Desempenho']]
        
        for hist in historical_data[:4]:  # Show last 4 months
            month_year = hist.get('month', hist.get('month_year', ''))
            prognosis = self._format_number(hist.get('prognosis_kwh', 0), 2)
            generation = self._format_number(hist.get('generation_kwh', 0), 2)
            
            prognosis_val = hist.get('prognosis_kwh', 0)
            generation_val = hist.get('generation_kwh', 0)
            if prognosis_val > 0:
                performance = f"{(generation_val / prognosis_val * 100):.2f}%"
            else:
                performance = "0%"
            
            data.append([month_year, prognosis, generation, performance])
        
        table = Table(data, colWidths=[60, 110, 110, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GRAY_LIGHT),
            ('TEXTCOLOR', (0, 0), (-1, 0), BLACK_PRIMARY),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_MEDIUM),
        ]))
        
        return table
    
    def _create_consumer_table(self, consumer_data: List[Dict]) -> Table:
        """Create the consumer units table for complete report"""
        # Header
        data = [[
            'Contrato', 'Ciclo', 'Consumo\nRegistrado', 'Energia\nCompensada',
            'Energia\nFaturada', 'Crédito\nAnterior', 'Crédito\nAcumulado',
            'Faturado\n(R$)', 'Economizado\n(R$)'
        ]]
        
        for consumer in consumer_data:
            data.append([
                consumer.get('name', '')[:20],  # Truncate long names
                consumer.get('cycle', ''),
                self._format_number(consumer.get('consumption_registered', 0), 0),
                self._format_number(consumer.get('energy_compensated', 0), 0),
                self._format_number(consumer.get('energy_billed', 0), 0),
                self._format_number(consumer.get('credit_previous', 0), 0),
                self._format_number(consumer.get('credit_accumulated', 0), 0),
                self._format_number(consumer.get('amount_billed', 0), 2),
                self._format_number(consumer.get('amount_saved', 0), 2),
            ])
        
        table = Table(data, colWidths=[70, 40, 50, 50, 50, 45, 50, 50, 55])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BLACK_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_MEDIUM),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ]))
        
        return table
    
    def generate_basic_report(self, data: Dict[str, Any]) -> bytes:
        """
        Generate a basic report (like the first PDF example)
        
        Required data keys:
        - plant_name: str
        - company_name: str
        - month_year: str (YYYY-MM or MM/YYYY)
        - capacity_kwp: float
        - total_generation_kwh: float
        - prognosis_kwh: float
        - daily_generation: List[Dict] with 'day', 'generation_kwh'
        - environmental: Dict with 'co2_avoided_kg', 'trees_saved'
        - historical: List[Dict] with month data
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header(
            data.get('plant_name', 'Usina FV'),
            data.get('month_year', ''),
            data.get('company_name', 'ON Soluções Energéticas')
        ))
        
        # KPIs Row - Potência, Geração, Desempenho
        prognosis = data.get('prognosis_kwh', 0)
        generation = data.get('total_generation_kwh', 0)
        performance = (generation / prognosis * 100) if prognosis > 0 else 0
        
        kpis = [
            {'label': 'Potência', 'value': f"{self._format_number(data.get('capacity_kwp', 0), 2)} kWp"},
            {'label': 'Geração', 'value': f"{self._format_number(generation, 0)} kWh"},
            {'label': 'Desempenho', 'value': f"{self._format_number(performance, 2)} %"},
        ]
        elements.append(self._create_kpi_row(kpis))
        elements.append(Spacer(1, 12*mm))
        
        # Generation Chart Section
        elements.append(Paragraph("Geração Diária", self.styles['SectionTitle']))
        
        daily_data = data.get('daily_generation', [])
        days_in_month = len(daily_data) if daily_data else 30
        daily_prognosis = prognosis / days_in_month if days_in_month > 0 else 0
        
        chart = self._create_generation_chart(daily_data, daily_prognosis)
        elements.append(chart)
        elements.append(Spacer(1, 8*mm))
        
        # Summary KPIs (Geração, Prognóstico, Desempenho for period)
        summary_kpis = [
            {'label': 'Geração', 'value': f"{self._format_number(generation / 1000, 2)} MWh"},
            {'label': 'Prognóstico', 'value': f"{self._format_number(prognosis / 1000, 2)} MWh"},
            {'label': 'Desempenho', 'value': f"{self._format_number(performance, 2)} %"},
        ]
        elements.append(self._create_kpi_row(summary_kpis))
        elements.append(Spacer(1, 8*mm))
        
        # Environmental Impact
        env = data.get('environmental', {})
        co2_tons = env.get('co2_avoided_kg', 0) / 1000
        trees = env.get('trees_saved', 0)
        
        elements.append(Paragraph("Impacto Ambiental (Últimos 12 meses)", self.styles['SectionTitle']))
        env_text = f"• Deixados de produzir {self._format_number(co2_tons, 2)}t de CO2\n• Total de {int(trees)} árvores salvas"
        elements.append(Paragraph(env_text, self.styles['BodyText']))
        elements.append(Spacer(1, 8*mm))
        
        # Historical Data Table
        historical = data.get('historical', [])
        if historical:
            elements.append(Paragraph("Meses Anteriores", self.styles['SectionTitle']))
            elements.append(self._create_historical_table(historical))
        
        # Footer
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            "Powered by ON Soluções Energéticas",
            ParagraphStyle(name='Footer', fontSize=8, textColor=GRAY_MEDIUM, alignment=1)
        ))
        
        # Build PDF
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def generate_complete_report(self, data: Dict[str, Any]) -> bytes:
        """
        Generate a complete report with consumer details (like the second PDF example)
        
        Additional data keys beyond basic report:
        - financial: Dict with 'saved_brl', 'billed_brl', 'roi_monthly', 'roi_total'
        - consumer_units: List[Dict] with detailed consumer data
        - prognosis_annual_kwh: float
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=10*mm,
            leftMargin=10*mm,
            topMargin=10*mm,
            bottomMargin=10*mm
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header(
            data.get('plant_name', 'Usina FV'),
            data.get('month_year', ''),
            data.get('company_name', 'ON Soluções Energéticas')
        ))
        
        # Main KPIs with financial data
        prognosis = data.get('prognosis_kwh', 0)
        generation = data.get('total_generation_kwh', 0)
        performance = (generation / prognosis * 100) if prognosis > 0 else 0
        financial = data.get('financial', {})
        
        # First KPI row - Generation focused
        kpis1 = [
            {'label': 'Potência', 'value': f"{self._format_number(data.get('capacity_kwp', 0), 2)} kWp"},
            {'label': 'Geração', 'value': f"{self._format_number(generation, 0)} kWh"},
            {'label': 'Desempenho', 'value': f"{self._format_number(performance, 0)} %"},
        ]
        elements.append(self._create_kpi_row(kpis1))
        elements.append(Spacer(1, 6*mm))
        
        # Second KPI row - Financial focused
        kpis2 = [
            {'label': 'Economia do Mês', 'value': self._format_currency(financial.get('saved_brl', 0))},
            {'label': 'Faturado do Mês', 'value': self._format_currency(financial.get('billed_brl', 0))},
            {'label': 'Retorno Financeiro', 'value': f"{self._format_number(financial.get('roi_monthly', 0), 2)} %"},
        ]
        elements.append(self._create_kpi_row(kpis2))
        elements.append(Spacer(1, 6*mm))
        
        # Third KPI row - Accumulated
        kpis3 = [
            {'label': 'Economia Total', 'value': self._format_currency(financial.get('total_savings', 0))},
            {'label': 'Retorno Total', 'value': f"{self._format_number(financial.get('roi_total', 0), 2)} %"},
        ]
        elements.append(self._create_kpi_row(kpis3))
        elements.append(Spacer(1, 8*mm))
        
        # Energy flow section
        elements.append(Paragraph("Fluxo de Energia", self.styles['SectionTitle']))
        
        energy_data = [
            ['Energia Injetada Ponta', f"{self._format_number(data.get('energy_injected_p', 0), 0)} kWh"],
            ['Energia Injetada Fora Ponta', f"{self._format_number(data.get('energy_injected_fp', 0), 0)} kWh"],
            ['Consumo Total Ponta', f"{self._format_number(data.get('consumption_p', 0), 0)} kWh"],
            ['Consumo Total Fora Ponta', f"{self._format_number(data.get('consumption_fp', 0), 0)} kWh"],
        ]
        energy_table = Table(energy_data, colWidths=[200, 100])
        energy_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(energy_table)
        elements.append(Spacer(1, 8*mm))
        
        # Prognosis section
        elements.append(Paragraph("Prognóstico", self.styles['SectionTitle']))
        prognosis_data = [
            ['Geração acordada mensal', f"{self._format_number(prognosis, 0)} kWh"],
            ['Prognóstico de geração mensal', f"{self._format_number(data.get('prognosis_monthly', prognosis), 0)} kWh"],
            ['Geração acordada anual', f"{self._format_number(data.get('prognosis_annual_kwh', 0) / 1000, 2)} MWh"],
        ]
        prognosis_table = Table(prognosis_data, colWidths=[200, 100])
        prognosis_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(prognosis_table)
        elements.append(Spacer(1, 8*mm))
        
        # Environmental impact
        env = data.get('environmental', {})
        co2_tons = env.get('co2_avoided_kg', 0) / 1000
        trees = env.get('trees_saved', 0)
        
        elements.append(Paragraph("Impacto Ambiental (Últimos 12 meses)", self.styles['SectionTitle']))
        env_kpis = [
            {'label': 'CO2 Evitado', 'value': f"{self._format_number(co2_tons, 2)} t"},
            {'label': 'Árvores Salvas', 'value': f"{int(trees)}"},
        ]
        elements.append(self._create_kpi_row(env_kpis))
        elements.append(Spacer(1, 8*mm))
        
        # Historical Data Table
        historical = data.get('historical', [])
        if historical:
            elements.append(Paragraph("Meses Anteriores", self.styles['SectionTitle']))
            elements.append(self._create_historical_table(historical))
            elements.append(Spacer(1, 10*mm))
        
        # Consumer Units Table (Page 2+)
        consumer_units = data.get('consumer_units', [])
        if consumer_units:
            elements.append(PageBreak())
            elements.append(Paragraph("Informações Concessionária", self.styles['ReportTitle']))
            elements.append(Spacer(1, 6*mm))
            elements.append(self._create_consumer_table(consumer_units))
            
            # Totals row
            totals = {
                'consumption_registered': sum(c.get('consumption_registered', 0) for c in consumer_units),
                'energy_compensated': sum(c.get('energy_compensated', 0) for c in consumer_units),
                'energy_billed': sum(c.get('energy_billed', 0) for c in consumer_units),
                'amount_billed': sum(c.get('amount_billed', 0) for c in consumer_units),
                'amount_saved': sum(c.get('amount_saved', 0) for c in consumer_units),
            }
            
            elements.append(Spacer(1, 4*mm))
            elements.append(Paragraph(
                f"<b>TOTAL:</b> Consumo: {self._format_number(totals['consumption_registered'], 0)} kWh | "
                f"Compensado: {self._format_number(totals['energy_compensated'], 0)} kWh | "
                f"Faturado: {self._format_currency(totals['amount_billed'])} | "
                f"Economizado: {self._format_currency(totals['amount_saved'])}",
                self.styles['BodyText']
            ))
        
        # Footer
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            "Powered by ON Soluções Energéticas",
            ParagraphStyle(name='Footer', fontSize=8, textColor=GRAY_MEDIUM, alignment=1)
        ))
        
        # Build PDF
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes


# Convenience function
def generate_plant_report(data: Dict[str, Any], report_type: str = 'basic') -> bytes:
    """
    Generate a PDF report for a solar plant.
    
    Args:
        data: Report data dictionary
        report_type: 'basic' or 'complete'
    
    Returns:
        PDF file as bytes
    """
    generator = SolarReportGenerator()
    
    if report_type == 'complete':
        return generator.generate_complete_report(data)
    else:
        return generator.generate_basic_report(data)
