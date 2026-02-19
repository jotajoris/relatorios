"""
PDF Report Generator Service
Generates professional PDF reports for solar plants
Based on the ON Soluções report template style
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
GRAY_DARK = colors.HexColor('#4B5563')
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
            fontSize=22,
            fontName='Helvetica-Bold',
            textColor=BLACK_PRIMARY,
            spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            fontSize=13,
            fontName='Helvetica-Bold',
            textColor=BLACK_PRIMARY,
            spaceBefore=14,
            spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            name='SubTitle',
            fontSize=11,
            fontName='Helvetica',
            textColor=GRAY_MEDIUM,
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name='KPILabel',
            fontSize=9,
            fontName='Helvetica',
            textColor=GRAY_MEDIUM
        ))
        self.styles.add(ParagraphStyle(
            name='KPIValue',
            fontSize=18,
            fontName='Helvetica-Bold',
            textColor=BLACK_PRIMARY
        ))
        self.styles.add(ParagraphStyle(
            name='BodyText',
            fontSize=9,
            fontName='Helvetica',
            textColor=BLACK_PRIMARY,
            leading=12
        ))
        self.styles.add(ParagraphStyle(
            name='SmallText',
            fontSize=8,
            fontName='Helvetica',
            textColor=GRAY_DARK,
            leading=10
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
        elements.append(Spacer(1, 6*mm))
        
        return elements
    
    def _create_kpi_row(self, kpis: List[Dict], col_count: int = None) -> Table:
        """Create a row of KPI cards"""
        if col_count is None:
            col_count = len(kpis)
        
        # Build the data for the table
        labels = []
        values = []
        
        for kpi in kpis:
            labels.append(Paragraph(kpi['label'], self.styles['KPILabel']))
            values.append(Paragraph(kpi['value'], self.styles['KPIValue']))
        
        data = [labels, values]
        
        col_width = (A4[0] - 30*mm) / col_count
        table = Table(data, colWidths=[col_width] * col_count)
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
            ('TOPPADDING', (0, 1), (-1, 1), 2),
        ]))
        
        return table
    
    def _create_generation_chart(self, daily_data: List[Dict], prognosis_daily: float) -> Drawing:
        """Create the daily generation bar chart with prognosis line"""
        drawing = Drawing(500, 160)
        
        # Prepare data
        generation_values = []
        for d in daily_data[:31]:  # Max 31 days
            generation_values.append(d.get('generation_kwh', 0))
        
        if not generation_values:
            return drawing
        
        # Create bar chart
        bc = VerticalBarChart()
        bc.x = 40
        bc.y = 25
        bc.width = 440
        bc.height = 115
        bc.data = [generation_values]
        bc.strokeColor = colors.transparent
        bc.valueAxis.valueMin = 0
        max_val = max(max(generation_values) if generation_values else 100, prognosis_daily)
        bc.valueAxis.valueMax = max_val * 1.15
        bc.valueAxis.valueStep = bc.valueAxis.valueMax / 4
        bc.valueAxis.labels.fontSize = 7
        bc.categoryAxis.labels.boxAnchor = 'ne'
        bc.categoryAxis.labels.dx = -2
        bc.categoryAxis.labels.dy = -2
        bc.categoryAxis.labels.angle = 0
        bc.categoryAxis.labels.fontSize = 7
        bc.categoryAxis.categoryNames = [str(i+1) for i in range(len(generation_values))]
        bc.bars[0].fillColor = GRAY_MEDIUM
        bc.bars[0].strokeColor = None
        
        drawing.add(bc)
        
        # Add prognosis line
        if prognosis_daily > 0:
            line_y = bc.y + (prognosis_daily / bc.valueAxis.valueMax) * bc.height
            line = Line(bc.x, line_y, bc.x + bc.width, line_y)
            line.strokeColor = YELLOW_PRIMARY
            line.strokeWidth = 2
            line.strokeDashArray = [4, 2]
            drawing.add(line)
        
        return drawing
    
    def _create_historical_table(self, historical_data: List[Dict]) -> Table:
        """Create the historical monthly data table"""
        # Header
        data = [['Mês/Ano', 'Prognóstico (kWh)', 'Geração (kWh)', 'Desempenho']]
        
        for hist in historical_data[:6]:  # Show last 6 months
            month_year = hist.get('month', hist.get('month_year', ''))
            prognosis = self._format_number(hist.get('prognosis_kwh', 0), 0)
            generation = self._format_number(hist.get('generation_kwh', 0), 0)
            
            prognosis_val = hist.get('prognosis_kwh', 0)
            generation_val = hist.get('generation_kwh', 0)
            if prognosis_val > 0:
                performance = f"{(generation_val / prognosis_val * 100):.1f}%"
            else:
                performance = "-"
            
            data.append([month_year, prognosis, generation, performance])
        
        table = Table(data, colWidths=[70, 100, 100, 70])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GRAY_LIGHT),
            ('TEXTCOLOR', (0, 0), (-1, 0), BLACK_PRIMARY),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_MEDIUM),
        ]))
        
        return table
    
    def _create_consumer_table(self, consumer_data: List[Dict]) -> Table:
        """Create the consumer units table"""
        # Header
        data = [[
            'Contrato', 'Ciclo', 'Consumo\nRegistrado', 'Energia\nCompensada',
            'Energia\nFaturada', 'Crédito\nAnterior', 'Crédito\nAcumulado',
            'Faturado\n(R$)', 'Economizado\n(R$)'
        ]]
        
        for consumer in consumer_data:
            data.append([
                consumer.get('name', '')[:18],  # Truncate long names
                consumer.get('cycle', ''),
                self._format_number(consumer.get('consumption_registered', 0), 0),
                self._format_number(consumer.get('energy_compensated', 0), 0),
                self._format_number(consumer.get('energy_billed', 0), 0),
                self._format_number(consumer.get('credit_previous', 0), 0),
                self._format_number(consumer.get('credit_accumulated', 0), 0),
                self._format_number(consumer.get('amount_billed', 0), 2),
                self._format_number(consumer.get('amount_saved', 0), 2),
            ])
        
        table = Table(data, colWidths=[65, 38, 48, 48, 48, 45, 48, 48, 52])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BLACK_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_MEDIUM),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ]))
        
        return table
    
    def generate_report(self, data: Dict[str, Any]) -> bytes:
        """
        Generate a complete unified report combining all information.
        
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
        - financial: Dict with 'saved_brl', 'billed_brl', etc (optional)
        - consumer_units: List[Dict] with detailed consumer data (optional)
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=12*mm,
            leftMargin=12*mm,
            topMargin=12*mm,
            bottomMargin=12*mm
        )
        
        elements = []
        
        # ==================== PAGE 1: Overview ====================
        
        # Header
        elements.extend(self._create_header(
            data.get('plant_name', 'Usina FV'),
            data.get('month_year', ''),
            data.get('company_name', 'ON Soluções Energéticas')
        ))
        
        # Calculate key metrics
        prognosis = data.get('prognosis_kwh', 0)
        generation = data.get('total_generation_kwh', 0)
        performance = (generation / prognosis * 100) if prognosis > 0 else 0
        financial = data.get('financial', {})
        
        # Row 1: Main KPIs (Potência, Geração, Desempenho)
        kpis1 = [
            {'label': 'Potência Instalada', 'value': f"{self._format_number(data.get('capacity_kwp', 0), 2)} kWp"},
            {'label': 'Geração do Mês', 'value': f"{self._format_number(generation, 0)} kWh"},
            {'label': 'Desempenho', 'value': f"{self._format_number(performance, 1)} %"},
        ]
        elements.append(self._create_kpi_row(kpis1))
        elements.append(Spacer(1, 4*mm))
        
        # Row 2: Financial KPIs (if available)
        if financial:
            kpis2 = [
                {'label': 'Economia do Mês', 'value': self._format_currency(financial.get('saved_brl', 0))},
                {'label': 'Faturado do Mês', 'value': self._format_currency(financial.get('billed_brl', 0))},
                {'label': 'Retorno Financeiro', 'value': f"{self._format_number(financial.get('roi_monthly', 0), 2)} %"},
            ]
            elements.append(self._create_kpi_row(kpis2))
            elements.append(Spacer(1, 4*mm))
            
            # Row 3: Accumulated
            kpis3 = [
                {'label': 'Economia Acumulada', 'value': self._format_currency(financial.get('total_savings', 0))},
                {'label': 'Retorno Total', 'value': f"{self._format_number(financial.get('roi_total', 0), 2)} %"},
            ]
            elements.append(self._create_kpi_row(kpis3, 3))
            elements.append(Spacer(1, 6*mm))
        
        # Generation Chart Section
        elements.append(Paragraph("Geração Diária", self.styles['SectionTitle']))
        
        daily_data = data.get('daily_generation', [])
        days_in_month = len(daily_data) if daily_data else 30
        daily_prognosis = prognosis / days_in_month if days_in_month > 0 else 0
        
        chart = self._create_generation_chart(daily_data, daily_prognosis)
        elements.append(chart)
        
        # Chart legend
        elements.append(Paragraph(
            "<font color='#9CA3AF'>■</font> Geração Real &nbsp;&nbsp;&nbsp;&nbsp;"
            "<font color='#FFD600'>---</font> Prognóstico Diário",
            self.styles['SmallText']
        ))
        elements.append(Spacer(1, 6*mm))
        
        # Prognosis Info
        elements.append(Paragraph("Prognóstico", self.styles['SectionTitle']))
        prognosis_data = [
            ['Geração Acordada Mensal', f"{self._format_number(prognosis, 0)} kWh"],
            ['Geração Acordada Anual', f"{self._format_number(data.get('prognosis_annual_kwh', prognosis * 12), 0)} kWh"],
        ]
        prognosis_table = Table(prognosis_data, colWidths=[180, 120])
        prognosis_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('TEXTCOLOR', (0, 0), (0, -1), GRAY_DARK),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(prognosis_table)
        elements.append(Spacer(1, 6*mm))
        
        # Environmental Impact
        env = data.get('environmental', {})
        co2_tons = env.get('co2_avoided_kg', 0) / 1000
        trees = env.get('trees_saved', 0)
        
        elements.append(Paragraph("Impacto Ambiental (Últimos 12 meses)", self.styles['SectionTitle']))
        env_kpis = [
            {'label': 'CO2 Evitado', 'value': f"{self._format_number(co2_tons, 2)} t"},
            {'label': 'Árvores Salvas', 'value': f"{int(trees)}"},
        ]
        elements.append(self._create_kpi_row(env_kpis, 3))
        elements.append(Spacer(1, 6*mm))
        
        # Historical Data Table
        historical = data.get('historical', [])
        if historical:
            elements.append(Paragraph("Histórico de Meses Anteriores", self.styles['SectionTitle']))
            elements.append(self._create_historical_table(historical))
        
        # ==================== PAGE 2: Consumer Details (if available) ====================
        
        consumer_units = data.get('consumer_units', [])
        if consumer_units:
            elements.append(PageBreak())
            elements.append(Paragraph("Informações da Concessionária", self.styles['ReportTitle']))
            elements.append(Spacer(1, 4*mm))
            
            # Energy flow section
            elements.append(Paragraph("Fluxo de Energia", self.styles['SectionTitle']))
            energy_data = [
                ['Energia Injetada Ponta', f"{self._format_number(data.get('energy_injected_p', 0), 0)} kWh",
                 'Energia Injetada Fora Ponta', f"{self._format_number(data.get('energy_injected_fp', 0), 0)} kWh"],
                ['Consumo Total Ponta', f"{self._format_number(data.get('consumption_p', 0), 0)} kWh",
                 'Consumo Total Fora Ponta', f"{self._format_number(data.get('consumption_fp', 0), 0)} kWh"],
            ]
            energy_table = Table(energy_data, colWidths=[130, 80, 140, 80])
            energy_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('TEXTCOLOR', (0, 0), (0, -1), GRAY_DARK),
                ('TEXTCOLOR', (2, 0), (2, -1), GRAY_DARK),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ]))
            elements.append(energy_table)
            elements.append(Spacer(1, 6*mm))
            
            # Consumer Units Table
            elements.append(Paragraph("Detalhamento por Unidade Consumidora", self.styles['SectionTitle']))
            elements.append(self._create_consumer_table(consumer_units))
            
            # Totals
            totals = {
                'consumption_registered': sum(c.get('consumption_registered', 0) for c in consumer_units),
                'energy_compensated': sum(c.get('energy_compensated', 0) for c in consumer_units),
                'energy_billed': sum(c.get('energy_billed', 0) for c in consumer_units),
                'amount_billed': sum(c.get('amount_billed', 0) for c in consumer_units),
                'amount_saved': sum(c.get('amount_saved', 0) for c in consumer_units),
            }
            
            elements.append(Spacer(1, 3*mm))
            elements.append(Paragraph(
                f"<b>TOTAIS:</b> Consumo Registrado: {self._format_number(totals['consumption_registered'], 0)} kWh | "
                f"Energia Compensada: {self._format_number(totals['energy_compensated'], 0)} kWh | "
                f"Faturado: {self._format_currency(totals['amount_billed'])} | "
                f"Economizado: {self._format_currency(totals['amount_saved'])}",
                self.styles['BodyText']
            ))
        
        # Footer
        elements.append(Spacer(1, 8*mm))
        elements.append(Paragraph(
            f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} | Powered by ON Soluções Energéticas",
            ParagraphStyle(name='Footer', fontSize=7, textColor=GRAY_MEDIUM, alignment=1)
        ))
        
        # Build PDF
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes


# Convenience function
def generate_plant_report(data: Dict[str, Any], report_type: str = 'complete') -> bytes:
    """
    Generate a PDF report for a solar plant.
    
    Args:
        data: Report data dictionary
        report_type: Ignored (kept for backwards compatibility)
    
    Returns:
        PDF file as bytes
    """
    generator = SolarReportGenerator()
    return generator.generate_report(data)
