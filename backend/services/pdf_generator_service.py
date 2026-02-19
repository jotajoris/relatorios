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
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from reportlab.graphics.charts.barcharts import VerticalBarChart

logger = logging.getLogger(__name__)

# ON Soluções brand colors
YELLOW = colors.HexColor('#FFD600')
YELLOW_LIGHT = colors.HexColor('#FFF3B0')
YELLOW_DARK = colors.HexColor('#E5C100')
BLACK = colors.HexColor('#1A1A1A')
BLACK_SOFT = colors.HexColor('#2D2D2D')
GRAY_LIGHT = colors.HexColor('#F4F4F5')
GRAY_MED = colors.HexColor('#9CA3AF')
GRAY_DARK = colors.HexColor('#4B5563')
GREEN = colors.HexColor('#10B981')
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 12 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

ON_LOGO_PATH = '/app/backend/assets/logo_on_fundo_preto.png'
ON_LOGO_LIGHT = '/app/backend/assets/logo_on_sem_fundo.png'

MONTH_NAMES = {
    '01': 'JANEIRO', '02': 'FEVEREIRO', '03': 'MARCO', '04': 'ABRIL',
    '05': 'MAIO', '06': 'JUNHO', '07': 'JULHO', '08': 'AGOSTO',
    '09': 'SETEMBRO', '10': 'OUTUBRO', '11': 'NOVEMBRO', '12': 'DEZEMBRO'
}


def _fmt(value, decimals=2):
    """Format number with Brazilian locale."""
    if value is None:
        return "0"
    try:
        s = f"{value:,.{decimals}f}"
        return s.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "0"


def _brl(value):
    return f"R$ {_fmt(value, 2)}"


def _load_image(path, w, h):
    """Safely load an image."""
    if path and os.path.exists(path):
        try:
            return Image(path, width=w, height=h)
        except Exception:
            pass
    return None


class SolarReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._add_styles()

    def _add_styles(self):
        defs = [
            ('ON_Brand', 9, 'Helvetica-Bold', YELLOW, TA_LEFT),
            ('Period', 10, 'Helvetica', GRAY_DARK, TA_LEFT),
            ('PlantTitle', 18, 'Helvetica-Bold', BLACK, TA_LEFT),
            ('CompSub', 9, 'Helvetica', GRAY_MED, TA_LEFT),
            ('SectTitle', 12, 'Helvetica-Bold', BLACK, TA_LEFT),
            ('KPILabel', 8, 'Helvetica', GRAY_MED, TA_CENTER),
            ('KPIVal', 14, 'Helvetica-Bold', BLACK, TA_CENTER),
            ('KPIHigh', 14, 'Helvetica-Bold', YELLOW_DARK, TA_CENTER),
            ('Body', 9, 'Helvetica', BLACK, TA_LEFT),
            ('Small', 7, 'Helvetica', GRAY_DARK, TA_LEFT),
            ('Footer', 7, 'Helvetica', GRAY_MED, TA_CENTER),
        ]
        for name, size, font, color, align in defs:
            self.styles.add(ParagraphStyle(
                name=name, fontSize=size, fontName=font,
                textColor=color, alignment=align, leading=size * 1.3
            ))

    def _header(self, plant_name, month_year, company_name, logo_url=None):
        """Build header with ON logo + yellow accent bar + plant title + client logo."""
        parts = month_year.split('-') if '-' in month_year else month_year.split('/')
        if len(parts) == 2:
            y, m = (parts[0], parts[1]) if len(parts[0]) == 4 else (parts[1], parts[0])
            period = f"{MONTH_NAMES.get(m, m)} {y}"
        else:
            period = month_year

        on_logo = _load_image(ON_LOGO_LIGHT, 32, 32)

        client_logo = None
        if logo_url:
            if logo_url.startswith('/api/logos/'):
                lpath = f"/tmp/logos/{logo_url.split('/')[-1]}"
                client_logo = _load_image(lpath, 40, 40)
            else:
                client_logo = _load_image(logo_url, 40, 40)

        accent = Drawing(5, 50)
        accent.add(Rect(0, 0, 5, 50, fillColor=YELLOW, strokeColor=None))

        title_parts = [
            Paragraph("ON SOLUCOES ENERGETICAS", self.styles['ON_Brand']),
            Paragraph(period, self.styles['Period']),
            Paragraph(plant_name.upper(), self.styles['PlantTitle']),
        ]
        if company_name and company_name.upper() != 'ON SOLUCOES ENERGETICAS':
            title_parts.append(Paragraph(company_name, self.styles['CompSub']))

        cells = [accent]
        widths = [8]
        if on_logo:
            cells.append(on_logo)
            widths.append(38)

        cells.append(title_parts)
        remaining = CONTENT_W - sum(widths) - 6
        if client_logo:
            widths.append(remaining - 50)
            cells.append(client_logo)
            widths.append(50)
        else:
            widths.append(remaining)

        tbl = Table([cells], colWidths=widths)
        tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return [tbl, Spacer(1, 5 * mm)]

    def _section(self, title):
        accent = Drawing(4, 14)
        accent.add(Rect(0, 0, 4, 14, fillColor=YELLOW, strokeColor=None))
        tbl = Table([[accent, Paragraph(title, self.styles['SectTitle'])]],
                    colWidths=[8, CONTENT_W - 12])
        tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('LEFTPADDING', (1, 0), (1, 0), 6),
        ]))
        return tbl

    def _kpi_card(self, label, value, highlight=False):
        style = self.styles['KPIHigh'] if highlight else self.styles['KPIVal']
        data = [
            [Paragraph(label, self.styles['KPILabel'])],
            [Paragraph(f"<nobr>{value}</nobr>", style)]
        ]
        card = Table(data, colWidths=[90])
        card.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 0), (-1, -1), WHITE),
            ('BOX', (0, 0), (-1, -1), 1, GRAY_LIGHT),
            ('LINEABOVE', (0, 0), (-1, 0), 2, YELLOW if highlight else GRAY_LIGHT),
        ]))
        return card

    def _kpi_row(self, kpis, highlights=None):
        if highlights is None:
            highlights = []
        cards = [self._kpi_card(k['label'], k['value'], i in highlights) for i, k in enumerate(kpis)]
        w = CONTENT_W / len(kpis)
        row = Table([cards], colWidths=[w] * len(kpis))
        row.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        return row

    def _chart(self, daily_data, prognosis_daily):
        drawing = Drawing(CONTENT_W, 140)
        drawing.add(Rect(0, 0, CONTENT_W, 140, fillColor=GRAY_LIGHT, strokeColor=None))
        vals = [d.get('generation_kwh', 0) for d in daily_data[:31]]
        if not vals:
            return drawing

        bc = VerticalBarChart()
        bc.x = 35
        bc.y = 22
        bc.width = CONTENT_W - 50
        bc.height = 100
        bc.data = [vals]
        bc.strokeColor = colors.transparent
        bc.valueAxis.valueMin = 0
        mx = max(max(vals) if vals else 100, prognosis_daily)
        bc.valueAxis.valueMax = mx * 1.15
        bc.valueAxis.valueStep = bc.valueAxis.valueMax / 4
        bc.valueAxis.labels.fontSize = 6
        bc.valueAxis.strokeColor = GRAY_MED
        bc.valueAxis.gridStrokeColor = colors.Color(0.92, 0.92, 0.92)
        bc.valueAxis.visibleGrid = True
        bc.categoryAxis.labels.fontSize = 6
        bc.categoryAxis.categoryNames = [str(i + 1) for i in range(len(vals))]
        bc.categoryAxis.strokeColor = GRAY_MED
        bc.bars[0].fillColor = BLACK_SOFT
        bc.bars[0].strokeColor = None
        drawing.add(bc)

        if prognosis_daily > 0:
            ly = bc.y + (prognosis_daily / bc.valueAxis.valueMax) * bc.height
            line = Line(bc.x, ly, bc.x + bc.width, ly)
            line.strokeColor = YELLOW
            line.strokeWidth = 1.5
            line.strokeDashArray = [5, 3]
            drawing.add(line)
            drawing.add(String(bc.x + bc.width + 3, ly - 3,
                               f'Meta: {_fmt(prognosis_daily, 0)}',
                               fontSize=5, fillColor=YELLOW_DARK))
        return drawing

    def _styled_table(self, headers, rows, col_widths=None):
        data = [headers] + rows
        if not col_widths:
            col_widths = [CONTENT_W / len(headers)] * len(headers)
        tbl = Table(data, colWidths=col_widths)
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BLACK),
            ('TEXTCOLOR', (0, 0), (-1, 0), YELLOW),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
            ('GRID', (0, 0), (-1, -1), 0.5, GRAY_MED),
        ]))
        return tbl

    def _footer(self):
        return Paragraph(
            f"Relatorio gerado em {datetime.now().strftime('%d/%m/%Y as %H:%M')} | "
            f"<b>ON Solucoes Energeticas</b> | www.onsolucoes.com.br",
            self.styles['Footer']
        )

    def generate_report(self, data: Dict[str, Any]) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                rightMargin=MARGIN, leftMargin=MARGIN,
                                topMargin=MARGIN, bottomMargin=MARGIN)
        el = []

        # ============ PAGE 1 ============
        el.extend(self._header(
            data.get('plant_name', 'Usina FV'),
            data.get('month_year', ''),
            data.get('company_name', 'ON Solucoes Energeticas'),
            data.get('logo_url')
        ))

        prognosis = data.get('prognosis_kwh', 0)
        generation = data.get('total_generation_kwh', 0)
        perf = (generation / prognosis * 100) if prognosis > 0 else 0
        fin = data.get('financial', {})

        # KPI Row 1
        el.append(self._kpi_row([
            {'label': 'Potencia Instalada', 'value': f"{_fmt(data.get('capacity_kwp', 0), 2)} kWp"},
            {'label': 'Geracao do Mes', 'value': f"{_fmt(generation, 0)} kWh"},
            {'label': 'Desempenho', 'value': f"{_fmt(perf, 1)} %"},
        ], [1]))
        el.append(Spacer(1, 3 * mm))

        # KPI Row 2 - Financial
        if fin.get('saved_brl', 0) > 0 or fin.get('billed_brl', 0) > 0:
            el.append(self._kpi_row([
                {'label': 'Economia do Mes', 'value': _brl(fin.get('saved_brl', 0))},
                {'label': 'Faturado do Mes', 'value': _brl(fin.get('billed_brl', 0))},
                {'label': 'Retorno Mensal', 'value': f"{_fmt(fin.get('roi_monthly', 0), 2)} %"},
            ], [0]))
            el.append(Spacer(1, 3 * mm))

        # Daily Generation Chart
        el.append(self._section("Geracao Diaria"))
        el.append(Spacer(1, 2 * mm))
        daily = data.get('daily_generation', [])
        days = len(daily) if daily else 30
        dp = prognosis / days if days > 0 else 0
        el.append(self._chart(daily, dp))
        el.append(Paragraph(
            "<font color='#2D2D2D'>&#9632;</font> Geracao Real &nbsp;&nbsp;"
            "<font color='#FFD600'>- - -</font> Prognostico Diario",
            self.styles['Small']
        ))
        el.append(Spacer(1, 4 * mm))

        # Prognosis
        el.append(self._section("Prognostico"))
        el.append(Spacer(1, 2 * mm))
        prog_data = [[
            'Geracao Mensal Acordada', f"{_fmt(prognosis, 0)} kWh",
            'Geracao Anual Acordada', f"{_fmt(data.get('prognosis_annual_kwh', prognosis * 12), 0)} kWh"
        ]]
        ptbl = Table(prog_data, colWidths=[110, 90, 110, 90])
        ptbl.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), GRAY_DARK),
            ('TEXTCOLOR', (2, 0), (2, -1), GRAY_DARK),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        el.append(ptbl)
        el.append(Spacer(1, 4 * mm))

        # Environmental
        env = data.get('environmental', {})
        co2_val = env.get('co2_avoided_kg', 0)
        co2t = (co2_val if co2_val else 0) / 1000
        trees = env.get('trees_saved', 0) or 0  # Handle None
        el.append(self._section("Impacto Ambiental (12 meses)"))
        el.append(Spacer(1, 2 * mm))
        el.append(self._kpi_row([
            {'label': 'CO2 Evitado', 'value': f"{_fmt(co2t, 2)} t"},
            {'label': 'Arvores Salvas', 'value': f"{int(trees)}"},
            {'label': 'Equivalente a', 'value': f"{int(trees * 12)} km rodados"},
        ], [0, 1]))
        el.append(Spacer(1, 4 * mm))

        # Historical
        historical = data.get('historical', [])
        if historical:
            el.append(self._section("Historico de Meses Anteriores"))
            el.append(Spacer(1, 2 * mm))
            rows = []
            for h in historical[:6]:
                my = h.get('month', h.get('month_year', ''))
                pg = f"{_fmt(h.get('prognosis_kwh', 0), 0)} kWh"
                gn = f"{_fmt(h.get('generation_kwh', 0), 0)} kWh"
                pv = h.get('prognosis_kwh', 0)
                gv = h.get('generation_kwh', 0)
                pf = f"{gv / pv * 100:.1f}%" if pv > 0 else "-"
                rows.append([my, pg, gn, pf])
            el.append(self._styled_table(
                ['Mes/Ano', 'Prognostico', 'Geracao', 'Desempenho'],
                rows, [70, 100, 100, 70]
            ))

        # ============ PAGE 2: Consumer Units Detail ============
        consumer_units = data.get('consumer_units', [])
        if consumer_units:
            el.append(PageBreak())
            el.extend(self._header(
                data.get('plant_name', 'Usina FV'),
                data.get('month_year', ''),
                data.get('company_name', 'ON Solucoes Energeticas'),
                data.get('logo_url')
            ))

            # Energy Flow
            el.append(self._section("Fluxo de Energia"))
            el.append(Spacer(1, 2 * mm))
            ef_data = [[
                'Injetada Ponta', f"{_fmt(data.get('energy_injected_p', 0), 0)} kWh",
                'Injetada F.Ponta', f"{_fmt(data.get('energy_injected_fp', 0), 0)} kWh"
            ], [
                'Consumo Ponta', f"{_fmt(data.get('consumption_p', 0), 0)} kWh",
                'Consumo F.Ponta', f"{_fmt(data.get('consumption_fp', 0), 0)} kWh"
            ]]
            ef_tbl = Table(ef_data, colWidths=[100, 80, 120, 80])
            ef_tbl.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (0, -1), GRAY_DARK),
                ('TEXTCOLOR', (2, 0), (2, -1), GRAY_DARK),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            el.append(ef_tbl)
            el.append(Spacer(1, 4 * mm))

            # Consumer Units Table - only show if there's data
            if consumer_units:
                el.append(self._section("Detalhamento por Unidade Consumidora"))
                el.append(Spacer(1, 2 * mm))

                cu_headers = ['Contrato', 'Ciclo', 'Consumo\nRegistrado', 'Energia\nCompensada',
                              'Energia\nFaturada', 'Cred.\nAnterior', 'Cred.\nAcumulado',
                              'Faturado\n(R$)', 'Economizado\n(R$)']
                cu_rows = []
                for c in consumer_units:
                    name = c.get('name') or c.get('uc_number') or 'N/A'
                    cu_rows.append([
                        str(name)[:16],
                        str(c.get('cycle') or ''),
                        _fmt(c.get('consumption_registered') or 0, 0),
                        _fmt(c.get('energy_compensated') or 0, 0),
                        _fmt(c.get('energy_billed') or 0, 0),
                        _fmt(c.get('credit_previous') or 0, 0),
                        _fmt(c.get('credit_accumulated') or 0, 0),
                        _fmt(c.get('amount_billed') or 0, 2),
                        _fmt(c.get('amount_saved') or 0, 2),
                    ])
                
                if cu_rows:
                    el.append(self._styled_table(cu_headers, cu_rows,
                                                  [62, 40, 46, 46, 46, 42, 44, 48, 48]))

                    # Totals - handle None values from get()
                    totals_cons = sum(c.get('consumption_registered') or 0 for c in consumer_units)
                    totals_comp = sum(c.get('energy_compensated') or 0 for c in consumer_units)
                    totals_bill = sum(c.get('amount_billed') or 0 for c in consumer_units)
                    totals_save = sum(c.get('amount_saved') or 0 for c in consumer_units)
                    el.append(Spacer(1, 2 * mm))
                    el.append(Paragraph(
                        f"<b>TOTAIS:</b> Consumo: {_fmt(totals_cons, 0)} kWh | "
                        f"Compensado: {_fmt(totals_comp, 0)} kWh | "
                        f"Faturado: {_brl(totals_bill)} | "
                        f"<font color='#10B981'><b>Economizado: {_brl(totals_save)}</b></font>",
                        self.styles['Body']
                    ))

        # Footer
        el.append(Spacer(1, 8 * mm))
        el.append(HRFlowable(width="100%", thickness=1, color=YELLOW))
        el.append(Spacer(1, 2 * mm))
        el.append(self._footer())

        doc.build(el)
        result = buf.getvalue()
        buf.close()
        return result


def generate_plant_report(data: Dict[str, Any], report_type: str = 'complete') -> bytes:
    gen = SolarReportGenerator()
    return gen.generate_report(data)
