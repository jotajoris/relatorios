"""
PDF Report Generator v4 - ON Soluções Energéticas
Palette: Yellow #FFD600 + Black #1A1A1A (NO orange)
Features: Pagination, footer on all pages, energy flow diagram, colored tables
"""
import os, io, logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, Image, PageBreak, HRFlowable, NextPageTemplate
)
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from reportlab.graphics.charts.barcharts import VerticalBarChart

logger = logging.getLogger(__name__)

# ON Brand Colors - NO orange
Y = colors.HexColor('#FFD600')
YL = colors.HexColor('#FFF9D4')
YD = colors.HexColor('#D4B300')
BK = colors.HexColor('#1A1A1A')
BK2 = colors.HexColor('#333333')
GL = colors.HexColor('#F7F7F7')
GM = colors.HexColor('#9CA3AF')
GD = colors.HexColor('#555555')
GR = colors.HexColor('#16A34A')
W = colors.white

PW, PH = A4
MG = 10 * mm
CW = PW - 2 * MG
BRT = timezone(timedelta(hours=-3))
LOGO = '/app/backend/assets/logo_on.png'

MESES = {'01':'JANEIRO','02':'FEVEREIRO','03':'MARCO','04':'ABRIL','05':'MAIO','06':'JUNHO',
         '07':'JULHO','08':'AGOSTO','09':'SETEMBRO','10':'OUTUBRO','11':'NOVEMBRO','12':'DEZEMBRO'}

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
            ('Brand', 11, 'Helvetica-Bold', Y, TA_LEFT),
            ('Period', 18, 'Helvetica-Bold', W, TA_LEFT),
            ('Sub', 9, 'Helvetica', colors.HexColor('#CCCCCC'), TA_LEFT),
            ('Sec', 11, 'Helvetica-Bold', BK, TA_LEFT),
            ('SecW', 11, 'Helvetica-Bold', W, TA_LEFT),
            ('KL', 7, 'Helvetica', GM, TA_CENTER),
            ('KV', 13, 'Helvetica-Bold', BK, TA_CENTER),
            ('KY', 13, 'Helvetica-Bold', Y, TA_CENTER),
            ('KG', 13, 'Helvetica-Bold', GR, TA_CENTER),
            ('Bd', 8, 'Helvetica', BK, TA_LEFT),
            ('Sm', 7, 'Helvetica', GD, TA_LEFT),
            ('SmC', 7, 'Helvetica', GD, TA_CENTER),
            ('Ft', 6.5, 'Helvetica', GM, TA_CENTER),
            ('FlL', 7, 'Helvetica', GD, TA_CENTER),
            ('FlV', 9, 'Helvetica-Bold', BK, TA_CENTER),
            ('InfoL', 8, 'Helvetica', GD, TA_LEFT),
            ('InfoV', 10, 'Helvetica-Bold', BK, TA_LEFT),
        ]:
            self.st.add(ParagraphStyle(name=nm, fontSize=sz, fontName=fn, textColor=cl, alignment=al, leading=sz*1.3))

    def _header_block(self, d):
        """Dark header bar with logo, plant name, period."""
        parts = d.get('month_year','').split('-')
        period = f"{MESES.get(parts[1],parts[1])} {parts[0]}" if len(parts)==2 else d.get('month_year','')
        logo = _img(LOGO, 48, 48)

        title = [
            Paragraph("ON SOLUCOES ENERGETICAS", self.st['Brand']),
            Paragraph(f"{d.get('plant_name','')} - {period}", self.st['Period']),
            Paragraph(f"{d.get('company_name','')} | {_n(d.get('capacity_kwp',0),2)} kWp", self.st['Sub']),
        ]
        cells = []
        ws = []
        if logo:
            cells.append(logo); ws.append(56)
        cells.append(title)
        ws.append(CW - sum(ws) - 4)

        t = Table([cells], colWidths=ws)
        t.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),6),
            ('BACKGROUND',(0,0),(-1,-1),BK),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ]))
        return [t, Spacer(1,4*mm)]

    def _sec(self, title, dark=False):
        st = self.st['SecW'] if dark else self.st['Sec']
        bg = BK if dark else Y
        t = Table([[Paragraph(title, st)]], colWidths=[CW])
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),bg),
            ('LEFTPADDING',(0,0),(-1,-1),8),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ]))
        return t

    def _kpi(self, label, value, style='KV'):
        data = [[Paragraph(label, self.st['KL'])],[Paragraph(f"<nobr>{value}</nobr>", self.st[style])]]
        c = Table(data, colWidths=[88])
        border_color = Y if style in ('KY','KG') else colors.HexColor('#E5E7EB')
        c.setStyle(TableStyle([
            ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('BACKGROUND',(0,0),(-1,-1),W),
            ('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#E5E7EB')),
            ('LINEABOVE',(0,0),(-1,0),3,border_color),
        ]))
        return c

    def _kpi_row(self, items):
        cards = [self._kpi(k['l'],k['v'],k.get('s','KV')) for k in items]
        w = CW/len(items)
        r = Table([cards], colWidths=[w]*len(items))
        r.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER')]))
        return r

    def _energy_flow(self, d):
        """Energy flow diagram in a styled box."""
        gen = d.get('total_generation_kwh',0) or 0
        inj_p = d.get('energy_injected_p',0) or 0
        inj_fp = d.get('energy_injected_fp',0) or 0
        cons_p = d.get('consumption_p',0) or 0
        cons_fp = d.get('consumption_fp',0) or 0

        def _box(lines):
            paras = []
            for lbl, val in lines:
                paras.append(Paragraph(lbl, self.st['FlL']))
                paras.append(Paragraph(f"<b>{val}</b>", self.st['FlV']))
                paras.append(Spacer(1,1.5*mm))
            return paras

        left = _box([
            ("Unidade Geradora", f"{_n(gen,0)} kWh"),
            ("C. Registrado Ponta", f"{_n(cons_p,0)} kWh"),
            ("C. Registrado F.Ponta", f"{_n(cons_fp,0)} kWh"),
        ])
        mid = _box([
            ("E. Injetada Ponta", f"{_n(inj_p,0)} kWh"),
            ("E. Injetada F.Ponta", f"{_n(inj_fp,0)} kWh"),
            ("Geracao Total", f"{_n(gen,0)} kWh"),
        ])
        right = _box([
            ("Consumo F.Ponta", f"{_n(cons_fp,0)} kWh"),
            ("Consumo Ponta", f"{_n(cons_p,0)} kWh"),
        ])

        data = [[left, mid, right]]
        t = Table(data, colWidths=[CW/3]*3)
        t.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('BACKGROUND',(0,0),(-1,-1),GL),
            ('BOX',(0,0),(-1,-1),1.5,Y),
            ('LINEBEFORE',(1,0),(1,-1),0.5,colors.HexColor('#E5E7EB')),
            ('LINEBEFORE',(2,0),(2,-1),0.5,colors.HexColor('#E5E7EB')),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),10),
        ]))
        return t

    def _chart(self, daily, prog_daily):
        dw = Drawing(CW, 155)
        dw.add(Rect(0,0,CW,155,fillColor=W,strokeColor=colors.HexColor('#E5E7EB')))
        vals = [dd.get('generation_kwh',0) for dd in daily[:31]]
        if not vals: return dw
        bc = VerticalBarChart()
        bc.x,bc.y,bc.width,bc.height = 38,22,CW-55,115
        bc.data = [vals]
        bc.strokeColor = colors.transparent
        bc.valueAxis.valueMin = 0
        mx = max(max(vals) if vals else 100, prog_daily)*1.15
        bc.valueAxis.valueMax = mx
        bc.valueAxis.valueStep = mx/5
        bc.valueAxis.labels.fontSize = 6
        bc.valueAxis.strokeColor = GM
        bc.valueAxis.gridStrokeColor = colors.Color(0.93,0.93,0.93)
        bc.valueAxis.visibleGrid = True
        bc.categoryAxis.labels.fontSize = 5
        bc.categoryAxis.categoryNames = [str(i+1) for i in range(len(vals))]
        bc.categoryAxis.strokeColor = GM
        bc.bars[0].fillColor = colors.HexColor('#BDBDBD')
        bc.bars[0].strokeColor = None
        dw.add(bc)
        if prog_daily > 0:
            ly = bc.y + (prog_daily/mx)*bc.height
            ln = Line(bc.x,ly,bc.x+bc.width,ly)
            ln.strokeColor = Y; ln.strokeWidth = 2; ln.strokeDashArray = [6,3]
            dw.add(ln)
        return dw

    def _nice_table(self, headers, rows, widths, has_total=False, yellow_values=False):
        hdr_s = ParagraphStyle('TH', fontSize=6.5, fontName='Helvetica-Bold', textColor=Y, alignment=TA_CENTER, leading=8)
        td_s = ParagraphStyle('TD', fontSize=7, fontName='Helvetica', textColor=BK, alignment=TA_CENTER, leading=9)
        td_l = ParagraphStyle('TDL', fontSize=6.5, fontName='Helvetica', textColor=BK, alignment=TA_LEFT, leading=8.5)
        td_b = ParagraphStyle('TDB', fontSize=7, fontName='Helvetica-Bold', textColor=BK, alignment=TA_CENTER, leading=9)
        td_y = ParagraphStyle('TDY', fontSize=7, fontName='Helvetica-Bold', textColor=Y, alignment=TA_CENTER, leading=9)

        pdata = [[Paragraph(h, hdr_s) for h in headers]]
        for i, row in enumerate(rows):
            is_total = has_total and i == len(rows)-1
            prow = []
            for j, cell in enumerate(row):
                if is_total:
                    prow.append(Paragraph(str(cell), td_b))
                elif j == 0:
                    prow.append(Paragraph(str(cell), td_l))
                elif yellow_values:
                    prow.append(Paragraph(str(cell), td_y))
                else:
                    prow.append(Paragraph(str(cell), td_s))
            pdata.append(prow)

        t = Table(pdata, colWidths=widths, repeatRows=1)
        cmds = [
            ('BACKGROUND',(0,0),(-1,0),BK),
            ('ALIGN',(0,0),(-1,0),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,0),5),('BOTTOMPADDING',(0,0),(-1,0),5),
            ('TOPPADDING',(0,1),(-1,-1),4),('BOTTOMPADDING',(0,1),(-1,-1),4),
            ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[W,GL]),
            ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#D1D5DB')),
        ]
        if has_total:
            cmds += [('BACKGROUND',(0,-1),(-1,-1),Y),('TEXTCOLOR',(0,-1),(-1,-1),BK)]
        t.setStyle(TableStyle(cmds))
        return t

    def _footer_text(self):
        return 'ON Solucoes Energeticas | onsolucoesenergeticas.com.br | @on.solucoes'

    def generate_report(self, d):
        buf = io.BytesIO()

        # Custom doc with page numbers
        footer_text = self._footer_text()
        class NumberedCanvas:
            pass

        doc = BaseDocTemplate(buf, pagesize=A4, rightMargin=MG, leftMargin=MG, topMargin=MG, bottomMargin=18*mm)
        frame = Frame(MG, 18*mm, CW, PH - MG - 18*mm, id='main')

        def _on_page(canvas, doc_obj):
            canvas.saveState()
            # Yellow bottom bar
            canvas.setFillColor(Y)
            canvas.rect(0, 0, PW, 14*mm, fill=1, stroke=0)
            # Footer text with clickable links
            canvas.setFont('Helvetica-Bold', 7)
            canvas.setFillColor(BK)
            canvas.drawString(MG + 22, 8*mm, "ON Solucoes Energeticas")
            canvas.setFont('Helvetica', 7)
            canvas.drawString(MG + 22, 4*mm, "onsolucoesenergeticas.com.br | @on.solucoes")
            # Clickable link areas
            canvas.linkURL("https://onsolucoesenergeticas.com.br",
                          (MG + 22, 3*mm, MG + 160, 6*mm))
            canvas.linkURL("https://instagram.com/on.solucoes",
                          (MG + 165, 3*mm, MG + 250, 6*mm))
            # Page number
            canvas.setFont('Helvetica-Bold', 7)
            page_text = f"Pagina {doc_obj.page}"
            canvas.drawRightString(PW - MG, 6*mm, page_text)
            # ON logo in footer
            if os.path.exists(LOGO):
                try:
                    canvas.drawImage(LOGO, MG, 3*mm, width=18, height=18, preserveAspectRatio=True, mask='auto')
                except: pass
            canvas.restoreState()

        doc.addPageTemplates([PageTemplate(id='all', frames=[frame], onPage=_on_page)])

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
        ann_prog = d.get('prognosis_annual_kwh', prog*12) or 0

        # ═══ PAGE 1: DASHBOARD ═══
        el.extend(self._header_block(d))

        # Top KPIs
        el.append(self._kpi_row([
            {'l':'Potencia','v':f"{_n(cap,2)} kWp",'s':'KV'},
            {'l':'Geracao do Mes','v':f"{_n(gen,0)} kWh",'s':'KY'},
            {'l':'Desempenho','v':f"{_n(perf,1)} %",'s':'KG' if perf>=100 else 'KY'},
        ]))
        el.append(Spacer(1,3*mm))

        # Energy Flow
        el.append(self._sec("Fluxo de Energia"))
        el.append(Spacer(1,2*mm))
        el.append(self._energy_flow(d))
        el.append(Spacer(1,3*mm))

        # Financial section with yellow accent
        el.append(self._sec("Financeiro", dark=True))
        el.append(Spacer(1,2*mm))
        fin_data = [
            ['Faturado', _brl(billed), 'Economia', _brl(saved)],
            ['Retorno Mensal', f"{_n(roi_m,2)} %", 'Economia Total', _brl(total_sav)],
            ['Retorno Total', f"{_n(roi_t,2)} %", '', ''],
        ]
        ft = Table(fin_data, colWidths=[80,CW/2-80,80,CW/2-80])
        ft.setStyle(TableStyle([
            ('FONTSIZE',(0,0),(-1,-1),9),
            ('TEXTCOLOR',(0,0),(0,-1),GD),('TEXTCOLOR',(2,0),(2,-1),GD),
            ('FONTNAME',(1,0),(1,-1),'Helvetica-Bold'),('FONTNAME',(3,0),(3,-1),'Helvetica-Bold'),
            ('TEXTCOLOR',(1,0),(1,-1),BK),('TEXTCOLOR',(3,0),(3,0),GR),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
            ('BACKGROUND',(0,0),(-1,-1),GL),
            ('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#E5E7EB')),
        ]))
        el.append(ft)
        el.append(Spacer(1,3*mm))

        # Meses Anteriores - with more columns like the reference
        hist = d.get('historical',[])
        if hist:
            el.append(self._sec("Meses Anteriores"))
            el.append(Spacer(1,2*mm))
            rows = []
            for h in hist[:6]:
                my = h.get('month',h.get('month_year',''))
                gk = h.get('generation_kwh',0)
                pk = h.get('prognosis_kwh',0)
                pf = f"{gk/pk*100:.0f}%" if pk>0 else "-"
                rows.append([my, f"{_n(gk,0)} kWh", pf])
            el.append(self._nice_table(
                ['Mes/Ano','Geracao','Desempenho'],
                rows, [80,120,80], yellow_values=True))

        # ═══ PAGE 2: GENERATION CHART + PROGNOSIS + ENVIRONMENTAL ═══
        el.append(PageBreak())
        el.extend(self._header_block(d))

        el.append(self._kpi_row([
            {'l':'Potencia','v':f"{_n(cap,2)} kWp",'s':'KV'},
            {'l':'Geracao','v':f"{_n(gen,0)} kWh",'s':'KY'},
            {'l':'Desempenho','v':f"{_n(perf,1)} %",'s':'KG' if perf>=100 else 'KY'},
        ]))
        el.append(Spacer(1,2*mm))

        # Month title
        parts = d.get('month_year','').split('-')
        month_name = MESES.get(parts[1],'') if len(parts)==2 else ''
        el.append(Paragraph(f"<font color='#FFD600'><b>{month_name}</b></font>",
                  ParagraphStyle('MT',fontSize=14,fontName='Helvetica-Bold',textColor=Y,alignment=TA_CENTER)))
        el.append(Spacer(1,2*mm))

        daily = d.get('daily_generation',[])
        days = len(daily) if daily else 30
        dp = prog/days if days>0 else 0
        el.append(self._chart(daily, dp))
        el.append(Paragraph(
            "<font color='#BDBDBD'>&#9632;</font> Geracao &nbsp;&nbsp;"
            "<font color='#FFD600'>&#8212; &#8212;</font> Prognostico",
            self.st['SmC']))
        el.append(Spacer(1,3*mm))

        # Gen/Prog/Perf summary
        gen_mwh = gen/1000
        prog_mwh = prog/1000
        el.append(self._kpi_row([
            {'l':'Geracao','v':f"{_n(gen_mwh,2)} MWh",'s':'KV'},
            {'l':'Prognostico','v':f"{_n(prog_mwh,2)} MWh",'s':'KV'},
            {'l':'Desempenho','v':f"{_n(perf,1)} %",'s':'KG' if perf>=100 else 'KY'},
        ]))
        el.append(Spacer(1,4*mm))

        # Prognosis section (image 3)
        el.append(self._sec("Prognostico e Impacto Ambiental"))
        el.append(Spacer(1,2*mm))
        prog_data = [
            [Paragraph("Geracao acordada mensal", self.st['InfoL']),
             Paragraph(f"<b>{_n(prog,0)} kWh</b>", self.st['InfoV']),
             Paragraph("Geracao acordada anual", self.st['InfoL']),
             Paragraph(f"<b>{_n(ann_prog/1000,2)} MWh</b>", self.st['InfoV'])],
            [Paragraph("Prognostico mensal", self.st['InfoL']),
             Paragraph(f"<b>{_n(prog,0)} kWh</b>", self.st['InfoV']),
             Paragraph("Prognostico anual", self.st['InfoL']),
             Paragraph(f"<b>{_n(ann_prog/1000,2)} MWh</b>", self.st['InfoV'])],
        ]
        pt = Table(prog_data, colWidths=[95,CW/2-95,95,CW/2-95])
        pt.setStyle(TableStyle([
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('BACKGROUND',(0,0),(-1,-1),GL),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#E5E7EB')),
        ]))
        el.append(pt)
        el.append(Spacer(1,3*mm))

        # Environmental (image 3 bottom)
        co2t = (env.get('co2_avoided_kg',0) or 0)/1000
        trees = int(env.get('trees_saved',0) or 0)
        env_data = [[
            Paragraph(f"Deixados de produzir<br/><b><font size='12'>{_n(co2t,2)}t de CO2</font></b><br/>(Ultimos 12 meses)",
                      ParagraphStyle('EL',fontSize=8,fontName='Helvetica',textColor=GD,alignment=TA_CENTER,leading=12)),
            Paragraph(f"Total de<br/><b><font size='12' color='#16A34A'>{trees} arvores salvas</font></b><br/>(Ultimos 12 meses)",
                      ParagraphStyle('ER',fontSize=8,fontName='Helvetica',textColor=GD,alignment=TA_CENTER,leading=12)),
        ]]
        et = Table(env_data, colWidths=[CW/2]*2)
        et.setStyle(TableStyle([
            ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
            ('BACKGROUND',(0,0),(-1,-1),GL),
            ('BOX',(0,0),(-1,-1),1,Y),
            ('LINEBEFORE',(1,0),(1,-1),0.5,colors.HexColor('#E5E7EB')),
        ]))
        el.append(et)

        # ═══ PAGE 3+: CONSUMER UNITS ═══
        cu = d.get('consumer_units',[])
        if cu:
            el.append(PageBreak())
            el.extend(self._header_block(d))
            el.append(self._sec("INFORMACOES CONCESSIONARIA", dark=True))
            el.append(Spacer(1,3*mm))

            hdr = ['UC / Contrato','Ciclo','Consumo\nRegistrado','Energia\nCompensada',
                   'Energia\nFaturada','Credito\nAnterior','Credito\nAcumulado',
                   'Faturado\n(R$)','Economizado\n(R$)']
            rows = []
            t_cons=t_comp=t_fat=t_ca=t_cacc=t_bill=t_sav=0
            for c in cu:
                cons=c.get('consumption_registered',0) or 0
                comp=c.get('energy_compensated',0) or 0
                fat=c.get('energy_billed',0) or 0
                ca=c.get('credit_previous',0) or 0
                cacc=c.get('credit_accumulated',0) or 0
                bill=c.get('amount_billed',0) or 0
                sav=c.get('amount_saved',0) or 0
                t_cons+=cons;t_comp+=comp;t_fat+=fat;t_ca+=ca;t_cacc+=cacc;t_bill+=bill;t_sav+=sav
                name = (c.get('name') or c.get('address') or '')
                uc = c.get('uc_number','')
                label = f"{name[:22]}\n{uc}" if uc else name[:25]
                rows.append([label,c.get('cycle',''),_n(cons,0),_n(comp,0),_n(fat,0),_n(ca,0),_n(cacc,0),_n(bill,2),_n(sav,2)])
            rows.append(['TOTAL','',_n(t_cons,0),_n(t_comp,0),_n(t_fat,0),_n(t_ca,0),_n(t_cacc,0),_n(t_bill,2),_n(t_sav,2)])

            el.append(self._nice_table(hdr, rows, [78,52,42,42,40,36,36,46,46], has_total=True))
            el.append(Spacer(1,4*mm))
            el.append(Paragraph(
                f"<b>Resumo:</b> Consumo: {_n(t_cons,0)} kWh | Compensado: {_n(t_comp,0)} kWh | "
                f"Faturado: {_brl(t_bill)} | <font color='#16A34A'><b>Economizado: {_brl(t_sav)}</b></font>",
                self.st['Bd']))

        doc.build(el)
        res = buf.getvalue()
        buf.close()
        return res


def generate_plant_report(data, report_type='complete'):
    return SolarReportGenerator().generate_report(data)
