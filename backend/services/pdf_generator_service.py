"""
PDF Report Generator Service
Generates professional PDF reports for solar plants
ON Soluções Energéticas - Brand colors: Yellow (#FFD600) and Black (#1A1A1A)
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# ON Soluções brand colors
YELLOW_PRIMARY = colors.HexColor('#FFD600')
YELLOW_LIGHT = colors.HexColor('#FFF3B0')
YELLOW_DARK = colors.HexColor('#E5C100')
BLACK_PRIMARY = colors.HexColor('#1A1A1A')
BLACK_SOFT = colors.HexColor('#2D2D2D')
GRAY_LIGHT = colors.HexColor('#F4F4F5')
GRAY_MEDIUM = colors.HexColor('#9CA3AF')
GRAY_DARK = colors.HexColor('#4B5563')
GREEN_SUCCESS = colors.HexColor('#10B981')
RED_ALERT = colors.HexColor('#EF4444')
WHITE = colors.white


class SolarReportGenerator:
    """Generates PDF reports for solar plants with ON Soluções branding"""
    
    def __init__(self, logo_path: Optional[str] = None):
        self.logo_path = logo_path
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for ON branding"""
        # Main title - Big and bold
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            fontSize=24,
            fontName='Helvetica-Bold',
            textColor=BLACK_PRIMARY,
            spaceAfter=4,
            alignment=TA_LEFT
        ))
        
        # Section headers with yellow accent
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=BLACK_PRIMARY,
            spaceBefore=12,
            spaceAfter=6,
            borderPadding=4,
            borderColor=YELLOW_PRIMARY,
            borderWidth=0,
            leftIndent=0
        ))
        
        # Subtitle / Company name
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=YELLOW_PRIMARY,
            spaceAfter=2
        ))
        
        # KPI Labels
        self.styles.add(ParagraphStyle(
            name='KPILabel',
            fontSize=8,
            fontName='Helvetica',
            textColor=GRAY_MEDIUM,
            alignment=TA_CENTER
        ))
        
        # KPI Values - Large and bold
        self.styles.add(ParagraphStyle(
            name='KPIValue',
            fontSize=16,
            fontName='Helvetica-Bold',
            textColor=BLACK_PRIMARY,
            alignment=TA_CENTER
        ))
        
        # KPI Values highlighted (yellow)
        self.styles.add(ParagraphStyle(
            name='KPIValueHighlight',
            fontSize=16,
            fontName='Helvetica-Bold',
            textColor=YELLOW_DARK,
            alignment=TA_CENTER
        ))
        
        # Body text custom
        self.styles.add(ParagraphStyle(
            name='BodyCustom',
            fontSize=9,
            fontName='Helvetica',
            textColor=BLACK_PRIMARY,
            leading=12
        ))
        
        # Small text for details
        self.styles.add(ParagraphStyle(
            name='SmallText',
            fontSize=7,
            fontName='Helvetica',
            textColor=GRAY_DARK,
            leading=9
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='FooterStyle',
            fontSize=7,
            fontName='Helvetica',
            textColor=GRAY_MEDIUM,
            alignment=TA_CENTER
        ))
    
    def _format_number(self, value: float, decimals: int = 2) -> str:
        """Format number with Brazilian locale"""
        if value is None:
            return "0"
        formatted = f"{value:,.{decimals}f}"
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted
    
    def _format_currency(self, value: float) -> str:
        """Format currency in BRL"""
        return f"R$ {self._format_number(value, 2)}"
    
    def _create_header_with_logo(self, plant_name: str, month_year: str, company_name: str, logo_url: str = None) -> List:
        """Create header with logo and title"""
        elements = []
        
        # Month names in Portuguese
        month_names = {
            '01': 'JANEIRO', '02': 'FEVEREIRO', '03': 'MARÇO', '04': 'ABRIL',
            '05': 'MAIO', '06': 'JUNHO', '07': 'JULHO', '08': 'AGOSTO',
            '09': 'SETEMBRO', '10': 'OUTUBRO', '11': 'NOVEMBRO', '12': 'DEZEMBRO'
        }
        
        parts = month_year.split('-') if '-' in month_year else month_year.split('/')
        if len(parts) == 2:
            if len(parts[0]) == 4:
                year, month = parts[0], parts[1]
            else:
                month, year = parts[0], parts[1]
            month_name = month_names.get(month, month)
            period_text = f"{month_name} {year}"
        else:
            period_text = month_year
        
        # Header table with logo and title
        header_data = []
        
        # Try to load logo
        logo_element = None
        if logo_url:
            try:
                # Handle local file path or URL
                if logo_url.startswith('/api/logos/'):
                    logo_path = f"/app/backend/uploads/logos/{logo_url.split('/')[-1]}"
                    if os.path.exists(logo_path):
                        logo_element = Image(logo_path, width=50, height=50)
                elif os.path.exists(logo_url):
                    logo_element = Image(logo_url, width=50, height=50)
            except Exception as e:
                logger.warning(f"Could not load logo: {e}")
        
        # Create yellow accent bar
        accent_bar = Drawing(6, 60)
        accent_bar.add(Rect(0, 0, 6, 60, fillColor=YELLOW_PRIMARY, strokeColor=None))
        
        # Title content
        title_content = [
            Paragraph(company_name.upper(), self.styles['CompanyName']),
            Paragraph(f"<b>{period_text}</b>", ParagraphStyle(
                name='PeriodText',
                fontSize=11,
                fontName='Helvetica',
                textColor=GRAY_DARK,
                spaceBefore=2
            )),
            Paragraph(plant_name.upper(), self.styles['ReportTitle'])
        ]
        
        if logo_element:
            header_data = [[accent_bar, logo_element, title_content]]
            col_widths = [8, 55, A4[0] - 100*mm]
        else:
            header_data = [[accent_bar, title_content]]
            col_widths = [8, A4[0] - 40*mm]
        
        header_table = Table(header_data, colWidths=col_widths)
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('LEFTPADDING', (1, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 8*mm))
        
        return elements
    
    def _create_kpi_card(self, label: str, value: str, highlight: bool = False) -> Table:
        """Create a single KPI card with yellow accent"""
        style = self.styles['KPIValueHighlight'] if highlight else self.styles['KPIValue']
        
        data = [
            [Paragraph(label, self.styles['KPILabel'])],
            [Paragraph(value, style)]
        ]
        
        card = Table(data, colWidths=[80])
        card.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 0), (-1, -1), WHITE),
            ('BOX', (0, 0), (-1, -1), 1, GRAY_LIGHT),
            ('LINEABOVE', (0, 0), (-1, 0), 2, YELLOW_PRIMARY if highlight else GRAY_LIGHT),
        ]))
        
        return card
    
    def _create_kpi_row(self, kpis: List[Dict], highlight_indices: List[int] = None) -> Table:
        """Create a row of KPI cards"""
        if highlight_indices is None:
            highlight_indices = []
        
        cards = []
        for i, kpi in enumerate(kpis):
            is_highlight = i in highlight_indices
            card = self._create_kpi_card(kpi['label'], kpi['value'], is_highlight)
            cards.append(card)
        
        row = Table([cards], colWidths=[(A4[0] - 30*mm) / len(kpis)] * len(kpis))
        row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        return row
    
    def _create_section_header(self, title: str) -> Table:
        """Create a section header with yellow accent bar"""
        accent = Drawing(4, 16)
        accent.add(Rect(0, 0, 4, 16, fillColor=YELLOW_PRIMARY, strokeColor=None))
        
        data = [[accent, Paragraph(title, self.styles['SectionTitle'])]]
        table = Table(data, colWidths=[8, A4[0] - 40*mm])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('LEFTPADDING', (1, 0), (1, 0), 6),
        ]))
        
        return table
    
    def _create_generation_chart(self, daily_data: List[Dict], prognosis_daily: float) -> Drawing:
        """Create daily generation bar chart with ON branding"""
        drawing = Drawing(480, 150)
        
        # Background
        drawing.add(Rect(0, 0, 480, 150, fillColor=GRAY_LIGHT, strokeColor=None))
        
        generation_values = [d.get('generation_kwh', 0) for d in daily_data[:31]]
        
        if not generation_values:
            return drawing
        
        # Create bar chart
        bc = VerticalBarChart()
        bc.x = 35
        bc.y = 25
        bc.width = 430
        bc.height = 105
        bc.data = [generation_values]
        bc.strokeColor = colors.transparent
        bc.valueAxis.valueMin = 0
        max_val = max(max(generation_values) if generation_values else 100, prognosis_daily)
        bc.valueAxis.valueMax = max_val * 1.15
        bc.valueAxis.valueStep = bc.valueAxis.valueMax / 4
        bc.valueAxis.labels.fontSize = 7
        bc.valueAxis.labels.fontName = 'Helvetica'
        bc.valueAxis.strokeColor = GRAY_MEDIUM
        bc.valueAxis.gridStrokeColor = colors.Color(0.9, 0.9, 0.9)
        bc.valueAxis.visibleGrid = True
        bc.categoryAxis.labels.fontSize = 7
        bc.categoryAxis.labels.fontName = 'Helvetica'
        bc.categoryAxis.categoryNames = [str(i+1) for i in range(len(generation_values))]
        bc.categoryAxis.strokeColor = GRAY_MEDIUM
        bc.bars[0].fillColor = BLACK_SOFT
        bc.bars[0].strokeColor = None
        
        drawing.add(bc)
        
        # Add prognosis line (dashed yellow)
        if prognosis_daily > 0:
            line_y = bc.y + (prognosis_daily / bc.valueAxis.valueMax) * bc.height
            line = Line(bc.x, line_y, bc.x + bc.width, line_y)
            line.strokeColor = YELLOW_PRIMARY
            line.strokeWidth = 2
            line.strokeDashArray = [6, 3]
            drawing.add(line)
            
            # Label for prognosis line
            label = String(bc.x + bc.width + 5, line_y - 3, f'Meta: {self._format_number(prognosis_daily, 0)}',
                          fontSize=6, fillColor=YELLOW_DARK)
            drawing.add(label)
        
        return drawing
    
    def _create_historical_table(self, historical_data: List[Dict]) -> Table:
        """Create historical data table with ON styling"""
        data = [['Mês/Ano', 'Prognóstico', 'Geração', 'Desempenho']]
        
        for hist in historical_data[:6]:
            month_year = hist.get('month', hist.get('month_year', ''))
            prognosis = f"{self._format_number(hist.get('prognosis_kwh', 0), 0)} kWh"
            generation = f"{self._format_number(hist.get('generation_kwh', 0), 0)} kWh"
            
            prognosis_val = hist.get('prognosis_kwh', 0)
            generation_val = hist.get('generation_kwh', 0)
            if prognosis_val > 0:
                perf = generation_val / prognosis_val * 100
                performance = f"{perf:.1f}%"
            else:
                performance = "-"
            
            data.append([month_year, prognosis, generation, performance])
        
        table = Table(data, colWidths=[70, 100, 100, 70])
        table.setStyle(TableStyle([
            # Header row - black background with yellow text
            ('BACKGROUND', (0, 0), (-1, 0), BLACK_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), YELLOW_PRIMARY),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            # Data rows
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_MEDIUM),
        ]))
        
        return table
    
    def _create_consumer_table(self, consumer_data: List[Dict]) -> Table:
        """Create consumer units table with ON styling"""
        headers = [
            'Contrato', 'Ciclo', 'Consumo\nRegistrado', 'Energia\nCompensada',
            'Energia\nFaturada', 'Crédito\nAnterior', 'Crédito\nAcumulado',
            'Faturado\n(R$)', 'Economizado\n(R$)'
        ]
        data = [headers]
        
        for consumer in consumer_data:
            data.append([
                consumer.get('name', '')[:16],
                consumer.get('cycle', ''),
                self._format_number(consumer.get('consumption_registered', 0), 0),
                self._format_number(consumer.get('energy_compensated', 0), 0),
                self._format_number(consumer.get('energy_billed', 0), 0),
                self._format_number(consumer.get('credit_previous', 0), 0),
                self._format_number(consumer.get('credit_accumulated', 0), 0),
                self._format_number(consumer.get('amount_billed', 0), 2),
                self._format_number(consumer.get('amount_saved', 0), 2),
            ])
        
        table = Table(data, colWidths=[62, 36, 46, 46, 46, 44, 46, 46, 50])
        table.setStyle(TableStyle([
            # Header - black with yellow
            ('BACKGROUND', (0, 0), (-1, 0), BLACK_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), YELLOW_PRIMARY),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            # Data
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, YELLOW_LIGHT]),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_MEDIUM),
        ]))
        
        return table
    
    def _create_footer(self) -> Paragraph:
        """Create footer with timestamp"""
        return Paragraph(
            f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} | "
            f"<b>ON Soluções Energéticas</b> | www.onsolucoes.com.br",
            self.styles['FooterStyle']
        )
    
    def generate_report(self, data: Dict[str, Any]) -> bytes:
        """Generate complete unified report with ON branding"""
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
        
        # ==================== PAGE 1 ====================
        
        # Header with logo
        elements.extend(self._create_header_with_logo(
            data.get('plant_name', 'Usina FV'),
            data.get('month_year', ''),
            data.get('company_name', 'ON Soluções Energéticas'),
            data.get('logo_url')
        ))
        
        # Calculate metrics
        prognosis = data.get('prognosis_kwh', 0)
        generation = data.get('total_generation_kwh', 0)
        performance = (generation / prognosis * 100) if prognosis > 0 else 0
        financial = data.get('financial', {})
        
        # Row 1: Main KPIs
        kpis1 = [
            {'label': 'Potência Instalada', 'value': f"{self._format_number(data.get('capacity_kwp', 0), 2)} kWp"},
            {'label': 'Geração do Mês', 'value': f"{self._format_number(generation, 0)} kWh"},
            {'label': 'Desempenho', 'value': f"{self._format_number(performance, 1)} %"},
        ]
        elements.append(self._create_kpi_row(kpis1, [1]))  # Highlight generation
        elements.append(Spacer(1, 4*mm))
        
        # Row 2: Financial KPIs (if available)
        if financial.get('saved_brl', 0) > 0 or financial.get('billed_brl', 0) > 0:
            kpis2 = [
                {'label': 'Economia do Mês', 'value': self._format_currency(financial.get('saved_brl', 0))},
                {'label': 'Faturado do Mês', 'value': self._format_currency(financial.get('billed_brl', 0))},
                {'label': 'Retorno Financeiro', 'value': f"{self._format_number(financial.get('roi_monthly', 0), 2)} %"},
            ]
            elements.append(self._create_kpi_row(kpis2, [0]))  # Highlight savings
            elements.append(Spacer(1, 4*mm))
            
            # Row 3: Accumulated
            if financial.get('total_savings', 0) > 0:
                kpis3 = [
                    {'label': 'Economia Acumulada', 'value': self._format_currency(financial.get('total_savings', 0))},
                    {'label': 'Retorno Total', 'value': f"{self._format_number(financial.get('roi_total', 0), 2)} %"},
                    {'label': 'Prognóstico Anual', 'value': f"{self._format_number(data.get('prognosis_annual_kwh', 0)/1000, 1)} MWh"},
                ]
                elements.append(self._create_kpi_row(kpis3, [0]))
                elements.append(Spacer(1, 6*mm))
        
        # Generation Chart
        elements.append(self._create_section_header("Geração Diária"))
        elements.append(Spacer(1, 2*mm))
        
        daily_data = data.get('daily_generation', [])
        days_in_month = len(daily_data) if daily_data else 30
        daily_prognosis = prognosis / days_in_month if days_in_month > 0 else 0
        
        chart = self._create_generation_chart(daily_data, daily_prognosis)
        elements.append(chart)
        
        # Legend
        elements.append(Paragraph(
            "<font color='#2D2D2D'>■</font> Geração Real &nbsp;&nbsp;&nbsp;&nbsp;"
            "<font color='#FFD600'>- - -</font> Prognóstico Diário",
            self.styles['SmallText']
        ))
        elements.append(Spacer(1, 5*mm))
        
        # Prognosis Info
        elements.append(self._create_section_header("Prognóstico"))
        elements.append(Spacer(1, 2*mm))
        
        prognosis_data = [
            ['Geração Acordada Mensal', f"{self._format_number(prognosis, 0)} kWh", 
             'Geração Acordada Anual', f"{self._format_number(data.get('prognosis_annual_kwh', prognosis * 12), 0)} kWh"],
        ]
        prog_table = Table(prognosis_data, colWidths=[110, 90, 110, 90])
        prog_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), GRAY_DARK),
            ('TEXTCOLOR', (2, 0), (2, -1), GRAY_DARK),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(prog_table)
        elements.append(Spacer(1, 5*mm))
        
        # Environmental Impact
        env = data.get('environmental', {})
        co2_tons = env.get('co2_avoided_kg', 0) / 1000
        trees = env.get('trees_saved', 0)
        
        elements.append(self._create_section_header("Impacto Ambiental (12 meses)"))
        elements.append(Spacer(1, 2*mm))
        
        env_kpis = [
            {'label': 'CO₂ Evitado', 'value': f"{self._format_number(co2_tons, 2)} t"},
            {'label': 'Árvores Salvas', 'value': f"{int(trees)}"},
            {'label': 'Equivalente a', 'value': f"{int(trees * 12)} km rodados"},
        ]
        elements.append(self._create_kpi_row(env_kpis, [0, 1]))
        elements.append(Spacer(1, 5*mm))
        
        # Historical Data
        historical = data.get('historical', [])
        if historical:
            elements.append(self._create_section_header("Histórico de Meses Anteriores"))
            elements.append(Spacer(1, 2*mm))
            elements.append(self._create_historical_table(historical))
        
        # ==================== PAGE 2: Consumer Details ====================
        
        consumer_units = data.get('consumer_units', [])
        if consumer_units:
            elements.append(PageBreak())
            
            # Page 2 Header
            elements.extend(self._create_header_with_logo(
                data.get('plant_name', 'Usina FV'),
                data.get('month_year', ''),
                data.get('company_name', 'ON Soluções Energéticas'),
                data.get('logo_url')
            ))
            
            # Energy Flow
            elements.append(self._create_section_header("Fluxo de Energia"))
            elements.append(Spacer(1, 2*mm))
            
            energy_data = [
                ['Energia Injetada Ponta', f"{self._format_number(data.get('energy_injected_p', 0), 0)} kWh",
                 'Energia Injetada Fora Ponta', f"{self._format_number(data.get('energy_injected_fp', 0), 0)} kWh"],
                ['Consumo Total Ponta', f"{self._format_number(data.get('consumption_p', 0), 0)} kWh",
                 'Consumo Total Fora Ponta', f"{self._format_number(data.get('consumption_fp', 0), 0)} kWh"],
            ]
            energy_table = Table(energy_data, colWidths=[120, 80, 140, 80])
            energy_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (0, -1), GRAY_DARK),
                ('TEXTCOLOR', (2, 0), (2, -1), GRAY_DARK),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(energy_table)
            elements.append(Spacer(1, 5*mm))
            
            # Consumer Units Table
            elements.append(self._create_section_header("Detalhamento por Unidade Consumidora"))
            elements.append(Spacer(1, 2*mm))
            elements.append(self._create_consumer_table(consumer_units))
            
            # Totals
            totals = {
                'consumption': sum(c.get('consumption_registered', 0) for c in consumer_units),
                'compensated': sum(c.get('energy_compensated', 0) for c in consumer_units),
                'billed': sum(c.get('amount_billed', 0) for c in consumer_units),
                'saved': sum(c.get('amount_saved', 0) for c in consumer_units),
            }
            
            elements.append(Spacer(1, 3*mm))
            totals_text = (
                f"<b>TOTAIS:</b> Consumo: {self._format_number(totals['consumption'], 0)} kWh | "
                f"Compensado: {self._format_number(totals['compensated'], 0)} kWh | "
                f"Faturado: {self._format_currency(totals['billed'])} | "
                f"<font color='#10B981'><b>Economizado: {self._format_currency(totals['saved'])}</b></font>"
            )
            elements.append(Paragraph(totals_text, self.styles['BodyCustom']))
        
        # Footer
        elements.append(Spacer(1, 10*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=YELLOW_PRIMARY))
        elements.append(Spacer(1, 2*mm))
        elements.append(self._create_footer())
        
        # Build PDF
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes


def generate_plant_report(data: Dict[str, Any], report_type: str = 'complete') -> bytes:
    """Generate a PDF report for a solar plant."""
    generator = SolarReportGenerator()
    return generator.generate_report(data)
