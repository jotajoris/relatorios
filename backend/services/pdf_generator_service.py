"""
PDF Report Generator - Unified Solar Plant Report v3
ON Soluções Energéticas
Pages: 1) Dashboard + Energy Flow  2) Generation Chart  3+) Consumer Units
"""
import os, io, logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
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

# Colors
Y = colors.HexColor('#FFD600')
YL = colors.HexColor('#FFF8D6')
YD = colors.HexColor('#C5A500')
BK = colors.HexColor('#1A1A1A')
BK2 = colors.HexColor('#333333')
GL = colors.HexColor('#F5F5F5')
GM = colors.HexColor('#9CA3AF')
GD = colors.HexColor('#555555')
GR = colors.HexColor('#10B981')
OR = colors.HexColor('#F97316')
W = colors.white

PW, PH = A4
MG = 10 * mm
CW = PW - 2 * MG

MESES = {'01':'JANEIRO','02':'FEVEREIRO','03':'MARCO','04':'ABRIL','05':'MAIO','06':'JUNHO',
         '07':'JULHO','08':'AGOSTO','09':'SETEMBRO','10':'OUTUBRO','11':'NOVEMBRO','12':'DEZEMBRO'}

ON_LOGO = '/app/backend/assets/logo_on_sem_fundo.png'
BRT = timezone(timedelta(hours=-3))


def _n(v, d=2):
    if v is None: return "0"
    s = f"{float(v):,.{d}f}"
    return s.replace(',','X').replace('.',',').replace('X','.')

def _brl(v): return f"R$ {_n(v,2)}"

def _img(p, w, h):
    if p and os.path.exists(p):
        try: return Image(p, width=w, height=h)
        except: pass
    return None


class SolarReportGenerator:
    def __init__(self):
        self.st = getSampleStyleSheet()
        for nm, sz, fn, cl, al in [
            ('Brand',10,'Helvetica-Bold',Y,TA_LEFT),
            ('Period',20,'Helvetica-Bold',BK,TA_LEFT),
            ('Sub',9,'Helvetica',GM,TA_LEFT),
            ('Sec',11,'Helvetica-Bold',BK,TA_LEFT),
            ('KL',7,'Helvetica',GM,TA_CENTER),
            ('KV',12,'Helvetica-Bold',BK,TA_CENTER),
            ('KH',12,'Helvetica-Bold',OR,TA_CENTER),
            ('KG',12,'Helvetica-Bold',GR,TA_CENTER),
            ('Bd',8,'Helvetica',BK,TA_LEFT),
            ('Sm',7,'Helvetica',GD,TA_LEFT),
            ('SmC',7,'Helvetica',GD,TA_CENTER),
            ('Ft',7,'Helvetica',GM,TA_CENTER),
            ('FlowL',7,'Helvetica',GD,TA_CENTER),
            ('FlowV',9,'Helvetica-Bold',BK,TA_CENTER),
            ('FlowH',9,'Helvetica-Bold',OR,TA_CENTER),
        ]:
            self.st.add(ParagraphStyle(name=nm,fontSize=sz,fontName=fn,textColor=cl,alignment=al,leading=sz*1.3))

    def _hdr(self, d):
        parts = d.get('month_year','').split('-')
        period = f"{MESES.get(parts[1],parts[1])} {parts[0]}" if len(parts)==2 else d.get('month_year','')
        logo = _img(ON_LOGO, 50, 50)
        cl = None
        lu = d.get('logo_url')
        if lu:
            lp = f"/tmp/logos/{lu.split('/')[-1]}" if lu.startswith('/api/') else lu
            cl = _img(lp, 45, 45)

        title = [
            Paragraph("ON SOLUCOES ENERGETICAS", self.st['Brand']),
            Paragraph(period, self.st['Period']),
            Paragraph(f"{d.get('plant_name','')} | {d.get('company_name','')} | {_n(d.get('capacity_kwp',0),2)} kWp", self.st['Sub']),
        ]
        cells = []
        ws = []
        if logo:
            cells.append(logo); ws.append(56)
        cells.append(title)
        rem = CW - sum(ws) - 4
        if cl:
            ws.append(rem-50); cells.append(cl); ws.append(50)
        else:
            ws.append(rem)
        t = Table([cells], colWidths=ws)
        t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),4)]))
        return [t, Spacer(1,2*mm), HRFlowable(width="100%",thickness=2,color=Y), Spacer(1,3*mm)]

    def _sec(self, title):
        t = Table([[Paragraph(title, self.st['Sec'])]], colWidths=[CW])
        t.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),8),('LINEBEFORE',(0,0),(0,-1),3,Y),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
        return t

    def _kpi(self, label, value, style='KV'):
        data = [[Paragraph(label, self.st['KL'])],[Paragraph(f"<nobr>{value}</nobr>", self.st[style])]]
        c = Table(data, colWidths=[85])
        c.setStyle(TableStyle([
            ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('BACKGROUND',(0,0),(-1,-1),W),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#E5E7EB')),
            ('LINEABOVE',(0,0),(-1,0),2, Y if style in ('KH','KG') else GL),
        ]))
        return c

    def _kpi_row(self, items):
        cards = [self._kpi(k['l'],k['v'],k.get('s','KV')) for k in items]
        w = CW/len(items)
        r = Table([cards], colWidths=[w]*len(items))
        r.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER')]))
        return r

    def _energy_flow(self, d):
        """Energy flow diagram using table layout with arrows."""
        fin = d.get('financial',{})
        gen = d.get('total_generation_kwh',0) or 0
        inj_p = d.get('energy_injected_p',0) or 0
        inj_fp = d.get('energy_injected_fp',0) or 0
        cons_p = d.get('consumption_p',0) or 0
        cons_fp = d.get('consumption_fp',0) or 0
        saved = fin.get('saved_brl',0) or 0
        billed = fin.get('billed_brl',0) or 0

        def _fc(label, value, bold=False):
            st = self.st['FlowV'] if bold else self.st['FlowL']
            return [Paragraph(label, self.st['FlowL']), Paragraph(value, self.st['FlowH'] if bold else self.st['FlowV'])]

        # Build flow as a structured table
        left = _fc("Unidade Geradora", f"{_n(gen,0)} kWh")
        left += [Spacer(1,2*mm)]
        left += _fc("C. Registrado Ponta", f"{_n(cons_p,0)} kWh")
        left += _fc("C. Registrado F.Ponta", f"{_n(cons_fp,0)} kWh")

        mid = _fc("E. Injetada Ponta", f"{_n(inj_p,0)} kWh")
        mid += [Spacer(1,2*mm)]
        mid += _fc("E. Injetada F.Ponta", f"{_n(inj_fp,0)} kWh")
        mid += [Spacer(1,2*mm)]
        mid += _fc("Geracao Total", f"{_n(gen,0)} kWh")

        right = _fc("Consumo F.Ponta", f"{_n(cons_fp,0)} kWh")
        right += _fc("Consumo Ponta", f"{_n(cons_p,0)} kWh")
        right += [Spacer(1,2*mm)]
        right += [Paragraph("Economia", self.st['FlowL']),
                  Paragraph(f"<b>{_brl(saved)}</b>", self.st['FlowH'])]

        data = [[left, mid, right]]
        t = Table(data, colWidths=[CW/3]*3)
        t.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('BOX',(0,0),(-1,-1),1,colors.HexColor('#E5E7EB')),
            ('LINEBEFORE',(1,0),(1,-1),0.5,colors.HexColor('#E5E7EB')),
            ('LINEBEFORE',(2,0),(2,-1),0.5,colors.HexColor('#E5E7EB')),
            ('BACKGROUND',(0,0),(-1,-1),GL),
            ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('LEFTPADDING',(0,0),(-1,-1),8),
        ]))
        return t

    def _chart(self, daily, prog_daily):
        dw = Drawing(CW, 145)
        dw.add(Rect(0,0,CW,145,fillColor=GL,strokeColor=None))
        vals = [d.get('generation_kwh',0) for d in daily[:31]]
        if not vals: return dw
        bc = VerticalBarChart()
        bc.x,bc.y,bc.width,bc.height = 35,20,CW-50,108
        bc.data = [vals]
        bc.strokeColor = colors.transparent
        bc.valueAxis.valueMin = 0
        mx = max(max(vals) if vals else 100, prog_daily)*1.15
        bc.valueAxis.valueMax = mx
        bc.valueAxis.valueStep = mx/5
        bc.valueAxis.labels.fontSize = 6
        bc.valueAxis.labels.fontName = 'Helvetica'
        bc.valueAxis.strokeColor = GM
        bc.valueAxis.gridStrokeColor = colors.Color(0.92,0.92,0.92)
        bc.valueAxis.visibleGrid = True
        bc.categoryAxis.labels.fontSize = 6
        bc.categoryAxis.categoryNames = [str(i+1) for i in range(len(vals))]
        bc.categoryAxis.strokeColor = GM
        bc.bars[0].fillColor = colors.HexColor('#BDBDBD')
        bc.bars[0].strokeColor = None
        dw.add(bc)
        if prog_daily > 0:
            ly = bc.y + (prog_daily/mx)*bc.height
            ln = Line(bc.x,ly,bc.x+bc.width,ly)
            ln.strokeColor = OR; ln.strokeWidth = 1.5; ln.strokeDashArray = [5,3]
            dw.add(ln)
        return dw

    def _nice_table(self, headers, rows, widths, has_total=False):
        """Create a well-formatted table with word wrapping."""
        # Convert all to Paragraphs for word wrapping
        hdr_style = ParagraphStyle('TH', fontSize=6.5, fontName='Helvetica-Bold', textColor=W, alignment=TA_CENTER, leading=8)
        td_style = ParagraphStyle('TD', fontSize=7, fontName='Helvetica', textColor=BK, alignment=TA_CENTER, leading=9)
        td_left = ParagraphStyle('TDL', fontSize=6.5, fontName='Helvetica', textColor=BK, alignment=TA_LEFT, leading=8.5)
        td_bold = ParagraphStyle('TDB', fontSize=7, fontName='Helvetica-Bold', textColor=BK, alignment=TA_CENTER, leading=9)

        pdata = [[Paragraph(h, hdr_style) for h in headers]]
        for i, row in enumerate(rows):
            is_total = has_total and i == len(rows)-1
            prow = []
            for j, cell in enumerate(row):
                if is_total:
                    prow.append(Paragraph(str(cell), td_bold))
                elif j == 0:
                    prow.append(Paragraph(str(cell), td_left))
                else:
                    prow.append(Paragraph(str(cell), td_style))
            pdata.append(prow)

        t = Table(pdata, colWidths=widths, repeatRows=1)
        style_cmds = [
            ('BACKGROUND',(0,0),(-1,0),BK),
            ('TEXTCOLOR',(0,0),(-1,0),Y),
            ('ALIGN',(0,0),(-1,0),'CENTER'),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
            ('TOPPADDING',(0,1),(-1,-1),4),('BOTTOMPADDING',(0,1),(-1,-1),4),
            ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[W,colors.HexColor('#FAFAFA')]),
            ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#D1D5DB')),
        ]
        if has_total and len(rows) > 0:
            style_cmds.extend([
                ('BACKGROUND',(0,-1),(-1,-1),Y),
                ('TEXTCOLOR',(0,-1),(-1,-1),BK),
            ])
        t.setStyle(TableStyle(style_cmds))
        return t

    def _footer(self):
        now = datetime.now(BRT)
        return Paragraph(
            f'Relatorio gerado em {now.strftime("%d/%m/%Y as %H:%M")} (Horario de Brasilia) | '
            f'<b>ON Solucoes Energeticas</b> | '
            f'<a href="https://onsolucoesenergeticas.com.br" color="#FFD600">onsolucoesenergeticas.com.br</a> | '
            f'<a href="https://instagram.com/on.solucoes" color="#FFD600">@on.solucoes</a>',
            self.st['Ft'])

    # ══════════════ MAIN ══════════════
    def generate_report(self, d):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=MG, leftMargin=MG, topMargin=MG, bottomMargin=MG)
        el = []

        prog = d.get('prognosis_kwh',0) or 0
        gen = d.get('total_generation_kwh',0) or 0
        perf = (gen/prog*100) if prog>0 else 0
        fin = d.get('financial',{})
        env = d.get('environmental',{})
        cap = d.get('capacity_kwp',0)
        saved = fin.get('saved_brl',0) or 0
        billed = fin.get('billed_brl',0) or 0
        total_sav = fin.get('total_savings',0) or 0
        roi_m = fin.get('roi_monthly',0) or 0
        roi_t = fin.get('roi_total',0) or 0

        # ═══ PAGE 1: DASHBOARD + ENERGY FLOW ═══
        el.extend(self._hdr(d))

        # Top KPIs
        el.append(self._kpi_row([
            {'l':'Potencia','v':f"{_n(cap,2)} kWp",'s':'KV'},
            {'l':'Geracao do Mes','v':f"{_n(gen,0)} kWh",'s':'KH'},
            {'l':'Desempenho','v':f"{_n(perf,1)} %",'s':'KG' if perf>=100 else 'KH'},
        ]))
        el.append(Spacer(1,4*mm))

        # Energy Flow Diagram
        el.append(self._sec("Fluxo de Energia"))
        el.append(Spacer(1,2*mm))
        el.append(self._energy_flow(d))
        el.append(Spacer(1,4*mm))

        # Financial KPIs
        el.append(self._sec("Financeiro"))
        el.append(Spacer(1,2*mm))
        el.append(self._kpi_row([
            {'l':'Faturado','v':_brl(billed),'s':'KV'},
            {'l':'Economia do Mes','v':_brl(saved),'s':'KG'},
            {'l':'Retorno Mensal','v':f"{_n(roi_m,2)} %",'s':'KV'},
        ]))
        el.append(Spacer(1,2*mm))
        el.append(self._kpi_row([
            {'l':'Economia Total','v':_brl(total_sav),'s':'KG'},
            {'l':'Retorno Total','v':f"{_n(roi_t,2)} %",'s':'KV'},
            {'l':'Ger. Acordada Mensal','v':f"{_n(prog,0)} kWh",'s':'KV'},
        ]))
        el.append(Spacer(1,4*mm))

        # Meses Anteriores
        hist = d.get('historical',[])
        if hist:
            el.append(self._sec("Meses Anteriores"))
            el.append(Spacer(1,2*mm))
            rows = []
            for h in hist[:6]:
                my = h.get('month',h.get('month_year',''))
                gk = h.get('generation_kwh',0)
                pk = h.get('prognosis_kwh',0)
                pf = f"{gk/pk*100:.1f}%" if pk>0 else "-"
                rows.append([my, f"{_n(pk,0)} kWh", f"{_n(gk,0)} kWh", pf])
            el.append(self._nice_table(
                ['Mes/Ano','Prognostico (kWh/mes)','Geracao (kWh/mes)','Desempenho'],
                rows, [70,110,110,70]))

        # ═══ PAGE 2: GENERATION CHART ═══
        el.append(PageBreak())
        el.extend(self._hdr(d))

        # KPIs
        el.append(self._kpi_row([
            {'l':'Potencia','v':f"{_n(cap,2)} kWp",'s':'KV'},
            {'l':'Geracao','v':f"{_n(gen,0)} kWh",'s':'KH'},
            {'l':'Desempenho','v':f"{_n(perf,1)} %",'s':'KG' if perf>=100 else 'KH'},
        ]))
        el.append(Spacer(1,3*mm))

        # Chart title
        parts = d.get('month_year','').split('-')
        chart_title = MESES.get(parts[1],'') if len(parts)==2 else ''
        el.append(Paragraph(f"<font color='#F97316'><b>{chart_title}</b></font>", ParagraphStyle('CT',fontSize=12,fontName='Helvetica-Bold',textColor=OR,alignment=TA_CENTER)))
        el.append(Spacer(1,2*mm))

        daily = d.get('daily_generation',[])
        days = len(daily) if daily else 30
        dp = prog/days if days>0 else 0
        el.append(self._chart(daily, dp))
        el.append(Paragraph(
            "<font color='#BDBDBD'>&#9632;</font> Geracao &nbsp;&nbsp;"
            "<font color='#F97316'>&#8212;</font> Prognostico",
            self.st['SmC']))
        el.append(Spacer(1,4*mm))

        # Summary KPIs under chart
        gen_mwh = gen/1000
        prog_mwh = prog/1000
        el.append(self._kpi_row([
            {'l':'Geracao','v':f"{_n(gen_mwh,2)} MWh",'s':'KV'},
            {'l':'Prognostico','v':f"{_n(prog_mwh,2)} MWh",'s':'KV'},
            {'l':'Desempenho','v':f"{_n(perf,1)} %",'s':'KG' if perf>=100 else 'KH'},
        ]))
        el.append(Spacer(1,5*mm))

        # Environmental
        co2t = (env.get('co2_avoided_kg',0) or 0)/1000
        trees = int(env.get('trees_saved',0) or 0)
        el.append(self._sec("Impacto Ambiental (Ultimos 12 meses)"))
        el.append(Spacer(1,2*mm))
        env_data = [[
            f"Deixados de produzir\n{_n(co2t,2)}t de CO2",
            f"Total de\n{trees} arvores salvas"
        ]]
        et = Table(env_data, colWidths=[CW/2]*2)
        et.setStyle(TableStyle([
            ('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTSIZE',(0,0),(-1,-1),9),
            ('FONTNAME',(0,0),(-1,-1),'Helvetica-Bold'),('TEXTCOLOR',(0,0),(0,0),GR),
            ('TEXTCOLOR',(1,0),(1,0),GR),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('BOX',(0,0),(-1,-1),1,colors.HexColor('#D1D5DB')),
            ('LINEBEFORE',(1,0),(1,-1),0.5,colors.HexColor('#D1D5DB')),
            ('BACKGROUND',(0,0),(-1,-1),GL),
        ]))
        el.append(et)

        # ═══ PAGE 3+: CONSUMER UNITS ═══
        cu = d.get('consumer_units',[])
        if cu:
            el.append(PageBreak())
            el.extend(self._hdr(d))
            el.append(self._sec("INFORMACOES CONCESSIONARIA"))
            el.append(Spacer(1,3*mm))

            hdr = ['UC / Contrato','Ciclo','Consumo\nRegistrado','Energia\nCompensada',
                   'Energia\nFaturada','Credito\nAnterior','Credito\nAcumulado',
                   'Faturado\n(R$)','Economizado\n(R$)']
            rows = []
            t_cons=t_comp=t_fat=t_ca=t_cacc=t_bill=t_sav=0
            for c in cu:
                cons = c.get('consumption_registered',0) or 0
                comp = c.get('energy_compensated',0) or 0
                fat = c.get('energy_billed',0) or 0
                ca = c.get('credit_previous',0) or 0
                cacc = c.get('credit_accumulated',0) or 0
                bill = c.get('amount_billed',0) or 0
                sav = c.get('amount_saved',0) or 0
                t_cons+=cons; t_comp+=comp; t_fat+=fat; t_ca+=ca; t_cacc+=cacc; t_bill+=bill; t_sav+=sav
                name = (c.get('name') or c.get('address') or '')
                uc = c.get('uc_number','')
                label = f"{name[:22]}\n{uc}" if uc else name[:25]
                rows.append([label, c.get('cycle',''), _n(cons,0), _n(comp,0), _n(fat,0), _n(ca,0), _n(cacc,0), _n(bill,2), _n(sav,2)])

            rows.append(['TOTAL','', _n(t_cons,0), _n(t_comp,0), _n(t_fat,0), _n(t_ca,0), _n(t_cacc,0), _n(t_bill,2), _n(t_sav,2)])

            el.append(self._nice_table(hdr, rows,
                [78,52,42,42,40,36,36,46,46], has_total=True))
            el.append(Spacer(1,4*mm))

            el.append(Paragraph(
                f"<b>Resumo Financeiro:</b> Consumo Total: {_n(t_cons,0)} kWh | "
                f"Compensado: {_n(t_comp,0)} kWh | "
                f"Faturado: {_brl(t_bill)} | "
                f"<font color='#10B981'><b>Economizado: {_brl(t_sav)}</b></font>",
                self.st['Bd']))

        # Footer on every page
        el.append(Spacer(1,6*mm))
        el.append(HRFlowable(width="100%",thickness=1,color=Y))
        el.append(Spacer(1,2*mm))
        el.append(self._footer())

        doc.build(el)
        res = buf.getvalue()
        buf.close()
        return res


def generate_plant_report(data, report_type='complete'):
    return SolarReportGenerator().generate_report(data)
