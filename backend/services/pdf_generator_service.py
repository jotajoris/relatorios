"""
PDF Report Generator - Unified Solar Plant Report
ON Soluções Energéticas
Combines generation dashboard + consumer unit billing details
Brand: Yellow #FFD600, Black #1A1A1A
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from reportlab.graphics.charts.barcharts import VerticalBarChart

logger = logging.getLogger(__name__)

Y = colors.HexColor('#FFD600')
YL = colors.HexColor('#FFF8D6')
BK = colors.HexColor('#1A1A1A')
BK2 = colors.HexColor('#2D2D2D')
GL = colors.HexColor('#F4F4F5')
GM = colors.HexColor('#9CA3AF')
GD = colors.HexColor('#4B5563')
GR = colors.HexColor('#10B981')
W = colors.white
PW, PH = A4
MG = 11 * mm
CW = PW - 2 * MG

MONTHS_PT = {
    '01': 'JANEIRO', '02': 'FEVEREIRO', '03': 'MARCO', '04': 'ABRIL',
    '05': 'MAIO', '06': 'JUNHO', '07': 'JULHO', '08': 'AGOSTO',
    '09': 'SETEMBRO', '10': 'OUTUBRO', '11': 'NOVEMBRO', '12': 'DEZEMBRO'
}

ON_LOGO = '/app/backend/assets/logo_on_sem_fundo.png'


def _n(v, d=2):
    if v is None: return "0"
    s = f"{v:,.{d}f}"
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def _brl(v):
    return f"R$ {_n(v, 2)}"


def _img(path, w, h):
    if path and os.path.exists(path):
        try:
            return Image(path, width=w, height=h)
        except Exception:
            pass
    return None


class SolarReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._add()

    def _add(self):
        for name, sz, fn, clr, al in [
            ('HdBrand', 9, 'Helvetica-Bold', Y, TA_LEFT),
            ('HdPeriod', 22, 'Helvetica-Bold', BK, TA_LEFT),
            ('HdSub', 9, 'Helvetica', GM, TA_LEFT),
            ('Sect', 11, 'Helvetica-Bold', BK, TA_LEFT),
            ('KLbl', 7, 'Helvetica', GM, TA_CENTER),
            ('KVal', 13, 'Helvetica-Bold', BK, TA_CENTER),
            ('KHi', 13, 'Helvetica-Bold', Y, TA_CENTER),
            ('Bod', 8, 'Helvetica', BK, TA_LEFT),
            ('Sm', 7, 'Helvetica', GD, TA_LEFT),
            ('Ft', 7, 'Helvetica', GM, TA_CENTER),
            ('TH', 6, 'Helvetica-Bold', W, TA_CENTER),
            ('TD', 7, 'Helvetica', BK, TA_CENTER),
        ]:
            self.styles.add(ParagraphStyle(name=name, fontSize=sz, fontName=fn,
                                           textColor=clr, alignment=al, leading=sz * 1.35))

    # ── Header ──
    def _header(self, d):
        parts = d.get('month_year', '').split('-')
        if len(parts) == 2:
            period = f"{MONTHS_PT.get(parts[1], parts[1])} {parts[0]}"
        else:
            period = d.get('month_year', '')

        logo = _img(ON_LOGO, 28, 28)
        cl = None
        lu = d.get('logo_url')
        if lu:
            lp = f"/tmp/logos/{lu.split('/')[-1]}" if lu.startswith('/api/logos/') else lu
            cl = _img(lp, 36, 36)

        title = [
            Paragraph("ON SOLUCOES ENERGETICAS", self.styles['HdBrand']),
            Paragraph(period, self.styles['HdPeriod']),
            Paragraph(f"{d.get('plant_name', '')} | {d.get('company_name', '')} | {d.get('capacity_kwp', 0)} kWp",
                       self.styles['HdSub']),
        ]
        cells = []
        widths = []
        if logo:
            cells.append(logo); widths.append(34)
        cells.append(title)
        rem = CW - sum(widths) - 4
        if cl:
            widths.append(rem - 42); cells.append(cl); widths.append(42)
        else:
            widths.append(rem)

        t = Table([cells], colWidths=widths)
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return [t, Spacer(1, 2 * mm),
                HRFlowable(width="100%", thickness=2, color=Y),
                Spacer(1, 4 * mm)]

    # ── Section title ──
    def _sect(self, title):
        t = Table([[Paragraph(title, self.styles['Sect'])]],
                  colWidths=[CW])
        t.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('LINEBEFORE', (0, 0), (0, -1), 3, Y),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        return t

    # ── KPI card ──
    def _kpi(self, label, value, hi=False):
        st = self.styles['KHi'] if hi else self.styles['KVal']
        data = [
            [Paragraph(label, self.styles['KLbl'])],
            [Paragraph(f"<nobr>{value}</nobr>", st)]
        ]
        c = Table(data, colWidths=[82])
        c.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), W),
            ('BOX', (0, 0), (-1, -1), 0.5, GL),
            ('LINEABOVE', (0, 0), (-1, 0), 2, Y if hi else GL),
        ]))
        return c

    def _kpi_row(self, items, his=None):
        if his is None: his = []
        cards = [self._kpi(k['l'], k['v'], i in his) for i, k in enumerate(items)]
        w = CW / len(items)
        r = Table([cards], colWidths=[w] * len(items))
        r.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        return r

    # ── Chart ──
    def _chart(self, daily, prog_daily):
        dw = Drawing(CW, 130)
        dw.add(Rect(0, 0, CW, 130, fillColor=GL, strokeColor=None))
        vals = [d.get('generation_kwh', 0) for d in daily[:31]]
        if not vals: return dw
        bc = VerticalBarChart()
        bc.x, bc.y, bc.width, bc.height = 32, 18, CW - 45, 95
        bc.data = [vals]
        bc.strokeColor = colors.transparent
        bc.valueAxis.valueMin = 0
        mx = max(max(vals) if vals else 100, prog_daily) * 1.15
        bc.valueAxis.valueMax = mx
        bc.valueAxis.valueStep = mx / 4
        bc.valueAxis.labels.fontSize = 5
        bc.valueAxis.strokeColor = GM
        bc.valueAxis.gridStrokeColor = colors.Color(0.92, 0.92, 0.92)
        bc.valueAxis.visibleGrid = True
        bc.categoryAxis.labels.fontSize = 5
        bc.categoryAxis.categoryNames = [str(i + 1) for i in range(len(vals))]
        bc.categoryAxis.strokeColor = GM
        bc.bars[0].fillColor = BK2
        bc.bars[0].strokeColor = None
        dw.add(bc)
        if prog_daily > 0:
            ly = bc.y + (prog_daily / mx) * bc.height
            ln = Line(bc.x, ly, bc.x + bc.width, ly)
            ln.strokeColor = Y; ln.strokeWidth = 1.5; ln.strokeDashArray = [5, 3]
            dw.add(ln)
            dw.add(String(bc.x + bc.width + 2, ly - 3,
                          f'Meta: {_n(prog_daily, 0)}', fontSize=5, fillColor=Y))
        return dw

    # ── Styled table ──
    def _table(self, headers, rows, widths=None):
        data = [headers] + rows
        if not widths:
            widths = [CW / len(headers)] * len(headers)
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BK),
            ('TEXTCOLOR', (0, 0), (-1, 0), Y),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('FONTSIZE', (0, 1), (-1, -1), 6.5),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [W, YL]),
            ('GRID', (0, 0), (-1, -1), 0.4, GM),
        ]))
        return t

    def _footer(self):
        return Paragraph(
            f"Relatorio gerado em {datetime.now().strftime('%d/%m/%Y as %H:%M')} | "
            f"<b>ON Solucoes Energeticas</b> | www.onsolucoes.com.br",
            self.styles['Ft'])

    # ══════════════ GENERATE ══════════════
    def generate_report(self, d: Dict[str, Any]) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                rightMargin=MG, leftMargin=MG,
                                topMargin=MG, bottomMargin=MG)
        el = []

        prog = d.get('prognosis_kwh', 0) or 0
        gen = d.get('total_generation_kwh', 0) or 0
        perf = (gen / prog * 100) if prog > 0 else 0
        fin = d.get('financial', {})
        env = d.get('environmental', {})
        cap = d.get('capacity_kwp', 0)

        # ════════ PAGE 1: DASHBOARD ════════
        el.extend(self._header(d))

        # Row 1: Main KPIs
        el.append(self._kpi_row([
            {'l': 'Potencia', 'v': f"{_n(cap, 2)} kWp"},
            {'l': 'Geracao do Mes', 'v': f"{_n(gen, 0)} kWh"},
            {'l': 'Desempenho', 'v': f"{_n(perf, 1)} %"},
        ], [1]))
        el.append(Spacer(1, 3 * mm))

        # Daily Chart
        el.append(self._sect("Geracao Diaria"))
        el.append(Spacer(1, 2 * mm))
        daily = d.get('daily_generation', [])
        days = len(daily) if daily else 30
        dp = prog / days if days > 0 else 0
        el.append(self._chart(daily, dp))
        el.append(Paragraph(
            "<font color='#2D2D2D'>&#9632;</font> Geracao Real &nbsp;&nbsp;"
            "<font color='#FFD600'>- - -</font> Prognostico",
            self.styles['Sm']))
        el.append(Spacer(1, 3 * mm))

        # Row 2: Generation summary
        gen_mwh = gen / 1000
        prog_mwh = prog / 1000
        el.append(self._kpi_row([
            {'l': 'Geracao', 'v': f"{_n(gen_mwh, 2)} MWh"},
            {'l': 'Prognostico', 'v': f"{_n(prog_mwh, 2)} MWh"},
            {'l': 'Desempenho', 'v': f"{_n(perf, 1)} %"},
        ], [0]))
        el.append(Spacer(1, 3 * mm))

        # Row 3: Financial
        saved = fin.get('saved_brl', 0) or 0
        billed = fin.get('billed_brl', 0) or 0
        total_sav = fin.get('total_savings', 0) or 0
        roi_m = fin.get('roi_monthly', 0) or 0
        roi_t = fin.get('roi_total', 0) or 0

        el.append(self._sect("Financeiro"))
        el.append(Spacer(1, 2 * mm))
        el.append(self._kpi_row([
            {'l': 'Faturado', 'v': _brl(billed)},
            {'l': 'Economia Mes', 'v': _brl(saved)},
            {'l': 'Economia Total', 'v': _brl(total_sav)},
            {'l': 'Retorno Mensal', 'v': f"{_n(roi_m, 2)} %"},
            {'l': 'Retorno Total', 'v': f"{_n(roi_t, 2)} %"},
        ], [1, 2]))
        el.append(Spacer(1, 3 * mm))

        # Prognosis & Energy Flow
        ann_prog = d.get('prognosis_annual_kwh', prog * 12) or 0
        inj_p = d.get('energy_injected_p', 0) or 0
        inj_fp = d.get('energy_injected_fp', 0) or 0
        cons_p = d.get('consumption_p', 0) or 0
        cons_fp = d.get('consumption_fp', 0) or 0

        info_data = [
            ['Ger. Acordada Mensal', f"{_n(prog, 0)} kWh",
             'Ger. Acordada Anual', f"{_n(ann_prog / 1000, 2)} MWh"],
            ['Cons. Registrado FP', f"{_n(cons_fp, 0)} kWh",
             'Cons. Registrado PT', f"{_n(cons_p, 0)} kWh"],
            ['E. Injetada FP', f"{_n(inj_fp, 0)} kWh",
             'E. Injetada PT', f"{_n(inj_p, 0)} kWh"],
        ]
        it = Table(info_data, colWidths=[95, 80, 95, 80])
        it.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), GD),
            ('TEXTCOLOR', (2, 0), (2, -1), GD),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        el.append(it)
        el.append(Spacer(1, 3 * mm))

        # Environmental
        co2t = (env.get('co2_avoided_kg', 0) or 0) / 1000
        trees = int(env.get('trees_saved', 0) or 0)
        el.append(self._sect("Impacto Ambiental (12 meses)"))
        el.append(Spacer(1, 2 * mm))
        el.append(self._kpi_row([
            {'l': 'CO2 Evitado', 'v': f"{_n(co2t, 2)} t"},
            {'l': 'Arvores Salvas', 'v': f"{trees}"},
        ], [0, 1]))
        el.append(Spacer(1, 3 * mm))

        # Historical table
        hist = d.get('historical', [])
        if hist:
            el.append(self._sect("Meses Anteriores"))
            el.append(Spacer(1, 2 * mm))
            rows = []
            for h in hist[:6]:
                my = h.get('month', h.get('month_year', ''))
                gkwh = h.get('generation_kwh', 0)
                pkwh = h.get('prognosis_kwh', 0)
                pf = f"{gkwh / pkwh * 100:.1f}%" if pkwh > 0 else "-"
                rows.append([my, f"{_n(pkwh, 0)} kWh", f"{_n(gkwh, 0)} kWh", pf])
            el.append(self._table(
                ['Mes/Ano', 'Prognostico', 'Geracao', 'Desempenho'],
                rows, [60, 100, 100, 60]))

        # ════════ PAGE 2+: CONSUMER UNITS ════════
        cu = d.get('consumer_units', [])
        if cu:
            el.append(PageBreak())
            el.extend(self._header(d))
            el.append(self._sect("INFORMACOES CONCESSIONARIA"))
            el.append(Spacer(1, 3 * mm))

            hdr = ['Contrato', 'Ciclo', 'Consumo\nRegistrado', 'Energia\nCompensada',
                   'Energia\nFaturada', 'Credito\nAnterior', 'Credito\nAcumulado',
                   'Faturado\n(R$)', 'Economizado\n(R$)']
            rows = []
            t_cons = t_comp = t_fat = t_cred_ant = t_cred_acc = t_bill = t_sav = 0
            for c in cu:
                cons = c.get('consumption_registered', 0)
                comp = c.get('energy_compensated', 0)
                fat = c.get('energy_billed', 0)
                ca = c.get('credit_previous', 0)
                cacc = c.get('credit_accumulated', 0)
                bill = c.get('amount_billed', 0)
                sav = c.get('amount_saved', 0)
                t_cons += cons; t_comp += comp; t_fat += fat
                t_cred_ant += ca; t_cred_acc += cacc
                t_bill += bill; t_sav += sav
                rows.append([
                    (c.get('name') or c.get('uc_number') or '')[:20],
                    c.get('cycle', ''),
                    _n(cons, 0),
                    _n(comp, 0),
                    _n(fat, 0),
                    _n(ca, 0),
                    _n(cacc, 0),
                    _n(bill, 2),
                    _n(sav, 2),
                ])
            # TOTAL row
            rows.append([
                'TOTAL', '',
                _n(t_cons, 0), _n(t_comp, 0), _n(t_fat, 0),
                _n(t_cred_ant, 0), _n(t_cred_acc, 0),
                _n(t_bill, 2), _n(t_sav, 2),
            ])

            wds = [72, 48, 42, 42, 42, 38, 38, 48, 48]
            tbl = self._table(hdr, rows, wds)
            # Bold the TOTAL row
            tbl.setStyle(TableStyle([
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), Y),
                ('TEXTCOLOR', (0, -1), (-1, -1), BK),
            ]))
            el.append(tbl)
            el.append(Spacer(1, 4 * mm))

            # Summary below table
            el.append(Paragraph(
                f"<b>Resumo:</b> Consumo Total: {_n(t_cons, 0)} kWh | "
                f"Compensado: {_n(t_comp, 0)} kWh | "
                f"Faturado: {_brl(t_bill)} | "
                f"<font color='#10B981'><b>Economizado: {_brl(t_sav)}</b></font>",
                self.styles['Bod']))

        # Footer
        el.append(Spacer(1, 6 * mm))
        el.append(HRFlowable(width="100%", thickness=1, color=Y))
        el.append(Spacer(1, 2 * mm))
        el.append(self._footer())

        doc.build(el)
        res = buf.getvalue()
        buf.close()
        return res


def generate_plant_report(data: Dict[str, Any], report_type: str = 'complete') -> bytes:
    gen = SolarReportGenerator()
    return gen.generate_report(data)
