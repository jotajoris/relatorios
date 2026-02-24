"""
PDF Report Generator v5 - ON Soluções Energéticas
Fixes: UC centered, Endereco column, % with 2 decimals on one line,
no text cut, centered summary, better energy flow diagram,
better Meses Anteriores table (dark text, more columns), more color
"""
import os, io, logging, tempfile, requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, Image, PageBreak, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle, Polygon
from reportlab.graphics.charts.barcharts import VerticalBarChart

logger = logging.getLogger(__name__)

Y = colors.HexColor('#FFD600')
YL = colors.HexColor('#FFF9D4')
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
MESES_ABR = {'01':'JAN','02':'FEV','03':'MAR','04':'ABR','05':'MAI','06':'JUN',
             '07':'JUL','08':'AGO','09':'SET','10':'OUT','11':'NOV','12':'DEZ'}

def _n(v, d=2):
    if v is None: return "0"
    s = f"{float(v):,.{d}f}"
    return s.replace(',','X').replace('.',',').replace('X','.')

def _brl(v): return f"R$ {_n(v,2)}"

def _download_image(url: str) -> str:
    """Download image from URL and return local temp file path"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # Get extension from URL or default to .png
            ext = '.png'
            if '.jpg' in url.lower() or '.jpeg' in url.lower():
                ext = '.jpg'
            elif '.webp' in url.lower():
                ext = '.webp'
            
            # Create temp file
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(fd, 'wb') as f:
                f.write(response.content)
            return temp_path
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
    return None

def _img(p, w, h):
    """Load image from local path or URL"""
    if not p:
        return None
    
    # If it's a URL, download it first
    if p.startswith('http://') or p.startswith('https://'):
        local_path = _download_image(p)
        if local_path and os.path.exists(local_path):
            try:
                return Image(local_path, width=w, height=h)
            except Exception as e:
                logger.error(f"Failed to create image from downloaded file: {e}")
        return None
    
    # Local file
    if os.path.exists(p):
        try:
            return Image(p, width=w, height=h)
        except Exception as e:
            logger.error(f"Failed to create image from local file {p}: {e}")
    return None

def _ps(name, sz, fn='Helvetica', cl=BK, al=TA_CENTER, ld=None):
    return ParagraphStyle(name, fontSize=sz, fontName=fn, textColor=cl, alignment=al, leading=ld or sz*1.35)


class SolarReportGenerator:
    def __init__(self):
        self.st = getSampleStyleSheet()

    def _hdr(self, d):
        parts = d.get('month_year','').split('-')
        period = f"{MESES.get(parts[1],parts[1])} {parts[0]}" if len(parts)==2 else d.get('month_year','')
        logo = _img(LOGO, 48, 48)
        # Client logo - can be a Cloudinary URL or a local path
        cl_logo = None
        lu = d.get('logo_url')
        if lu:
            # _img now handles both URLs and local paths
            cl_logo = _img(lu, 40, 40)
            logger.info(f"Loading client logo from: {lu}, result: {'success' if cl_logo else 'failed'}")

        title = []
        title.append(Paragraph("ON SOLUCOES ENERGETICAS", _ps('HB',11,'Helvetica-Bold',Y,TA_LEFT)))
        title.append(Paragraph(f"{d.get('plant_name','')} - {period}", _ps('HP',17,'Helvetica-Bold',W,TA_LEFT)))
        title.append(Paragraph(f"{d.get('company_name','')} | {_n(d.get('capacity_kwp',0),2)} kWp", _ps('HS',9,'Helvetica',colors.HexColor('#BBBBBB'),TA_LEFT)))

        cells = []
        ws = []
        if logo:
            cells.append(logo); ws.append(56)
        cells.append(title)
        remaining = CW - sum(ws) - 4
        if cl_logo:
            ws.append(remaining - 48)
            cells.append(cl_logo)
            ws.append(48)
        else:
            ws.append(remaining)

        t = Table([cells], colWidths=ws)
        t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),8),
            ('BACKGROUND',(0,0),(-1,-1),BK),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        return [t, Spacer(1,4*mm)]

    def _sec(self, title, dark=False):
        bg = BK if dark else Y
        cl = W if dark else BK
        t = Table([[Paragraph(title, _ps('S',11,'Helvetica-Bold',cl,TA_LEFT))]], colWidths=[CW])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('LEFTPADDING',(0,0),(-1,-1),8),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        return t

    def _kpi(self, label, value, accent=False, green=False):
        cl = GR if green else (Y if accent else BK)
        data = [[Paragraph(label, _ps('KL',7,'Helvetica',GM))],
                [Paragraph(f"<nobr>{value}</nobr>", _ps('KV',13,'Helvetica-Bold',cl))]]
        c = Table(data, colWidths=[88])
        bc = Y if (accent or green) else colors.HexColor('#E5E7EB')
        c.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('BACKGROUND',(0,0),(-1,-1),W),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#E5E7EB')),
            ('LINEABOVE',(0,0),(-1,0),3,bc)]))
        return c

    def _kpi_row(self, items):
        cards = [self._kpi(k['l'],k['v'],k.get('a'),k.get('g')) for k in items]
        w = CW/len(items)
        r = Table([cards], colWidths=[w]*len(items))
        r.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER')]))
        return r

    def _energy_flow_diagram(self, d):
        """Energy flow as a clean structured table - no image."""
        gen = d.get('total_generation_kwh',0) or 0
        inj_p = d.get('energy_injected_p',0) or 0
        inj_fp = d.get('energy_injected_fp',0) or 0
        cons_p = d.get('consumption_p',0) or 0
        cons_fp = d.get('consumption_fp',0) or 0

        lbl = _ps('FL2',7,'Helvetica',GD,TA_CENTER,9)
        val = _ps('FV2',9,'Helvetica-Bold',BK,TA_CENTER,11)

        def _cell(label, value):
            return [Paragraph(label, lbl), Paragraph(f"<b>{value}</b>", val)]

        left = _cell("Unidade Geradora", f"{_n(gen,0)} kWh")
        left += [Spacer(1,2*mm)]
        left += _cell("C. Registrado Ponta", f"{_n(cons_p,0)} kWh")
        left += _cell("C. Registrado F.Ponta", f"{_n(cons_fp,0)} kWh")

        mid = _cell("Consumo F.Ponta", f"{_n(cons_fp,0)} kWh")
        mid += _cell("Consumo Ponta", f"{_n(cons_p,0)} kWh")
        mid += [Spacer(1,2*mm)]
        mid += _cell("Geracao Total", f"{_n(gen,0)} kWh")

        right = _cell("E. Injetada Ponta", f"{_n(inj_p,0)} kWh")
        right += [Spacer(1,2*mm)]
        right += _cell("E. Injetada F.Ponta", f"{_n(inj_fp,0)} kWh")

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
        return [t]

    def _chart(self, daily, prog_daily):
        dw = Drawing(CW, 155)
        dw.add(Rect(0,0,CW,155,fillColor=W,strokeColor=colors.HexColor('#E5E7EB'),strokeWidth=0.5))
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

    def _data_table(self, headers, rows, widths, has_total=False):
        """Table with dark headers, white text values, no text cutting."""
        hs = _ps('TH',7,'Helvetica-Bold',W,TA_CENTER,9)
        ts = _ps('TD',7,'Helvetica',BK,TA_CENTER,9)
        tl = _ps('TDL',7,'Helvetica',BK,TA_LEFT,9)
        tc = _ps('TDC',7,'Helvetica',BK,TA_CENTER,9)
        tb = _ps('TDB',7.5,'Helvetica-Bold',BK,TA_CENTER,10)

        pdata = [[Paragraph(h, hs) for h in headers]]
        for i, row in enumerate(rows):
            is_t = has_total and i == len(rows)-1
            prow = []
            for j, cell in enumerate(row):
                if is_t:
                    prow.append(Paragraph(str(cell), tb))
                elif j <= 1:  # UC and Endereco left-aligned
                    prow.append(Paragraph(str(cell), tl if j==1 else tc))
                else:
                    prow.append(Paragraph(str(cell), ts))
            pdata.append(prow)

        t = Table(pdata, colWidths=widths, repeatRows=1)
        cmds = [
            ('BACKGROUND',(0,0),(-1,0),BK),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,0),6),('BOTTOMPADDING',(0,0),(-1,0),6),
            ('TOPPADDING',(0,1),(-1,-1),5),('BOTTOMPADDING',(0,1),(-1,-1),5),
            ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[W,GL]),
            ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#D1D5DB')),
        ]
        if has_total:
            cmds += [('BACKGROUND',(0,-1),(-1,-1),Y),('TEXTCOLOR',(0,-1),(-1,-1),BK)]
        t.setStyle(TableStyle(cmds))
        return t

    def _hist_table(self, hist_data):
        """Meses Anteriores - ON palette (black text, yellow section header)."""
        hs = _ps('HH2',7.5,'Helvetica-Bold',GD,TA_CENTER,10)
        tv = _ps('HV2',8,'Helvetica-Bold',BK,TA_CENTER,10)
        tl = _ps('HL2',8,'Helvetica',BK,TA_LEFT,10)

        headers = ['Mes/Ano','Geracao','Desemp.','Consumo PT','Consumo FP','Economizado','Faturado']
        pdata = [[Paragraph(h, hs) for h in headers]]

        sum_gen = sum_pt = sum_fp = sum_eco = sum_fat = 0
        perf_values = []
        count = 0
        for h in hist_data:
            gk = h.get('generation_kwh',0)
            pk = h.get('prognosis_kwh',0)
            pf = (gk/pk*100) if pk>0 else 0
            pt = h.get('consumption_p',0)
            fp = h.get('consumption_fp',0)
            eco = h.get('economizado',0)
            fat = h.get('faturado',0)
            sum_gen += gk; sum_pt += pt; sum_fp += fp; sum_eco += eco; sum_fat += fat
            if pf > 0:
                perf_values.append(pf)
            count += 1
            pdata.append([
                Paragraph(h.get('month',h.get('month_year','')), tl),
                Paragraph(f"{_n(gk,0)} kWh", tv),
                Paragraph(f"{pf:.0f}%", tv),
                Paragraph(f"{_n(pt,0)} kWh" if pt else "-", tv),
                Paragraph(f"{_n(fp,0)} kWh" if fp else "-", tv),
                Paragraph(_brl(eco) if eco else "-", tv),
                Paragraph(_brl(fat) if fat else "-", tv),
            ])

        # SOMA row - with average desempenho
        avg_perf = sum(perf_values) / len(perf_values) if perf_values else 0
        sb = _ps('SB2',8,'Helvetica-Bold',BK,TA_CENTER,10)
        su = _ps('SU2',6,'Helvetica',GD,TA_CENTER,8)
        pdata.append([Paragraph('',sb)] + [Paragraph(v,sb) for v in [
            'Soma\nGeracao','Media\nDesemp.','Soma Cons.\nPT','Soma Cons.\nFP','Soma\nEconomizado','Soma\nFaturado']])
        pdata.append([Paragraph('',sb)] + [Paragraph(v,sb) for v in [
            f"{_n(sum_gen,0)}", f"{avg_perf:.0f}%", f"{_n(sum_pt,0)}", f"{_n(sum_fp,0)}", f"{_n(sum_eco,2)}", f"{_n(sum_fat,2)}"]])
        pdata.append([Paragraph('',su)] + [Paragraph(v,su) for v in ['kWh','%','kWh','kWh','R$','R$']])

        w = CW / 7
        t = Table(pdata, colWidths=[w]*7)
        n_data = len(hist_data)
        t.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('ROWBACKGROUNDS',(0,0),(-1,n_data),[W,GL]),
            ('LINEBELOW',(0,0),(-1,0),1,colors.HexColor('#D1D5DB')),
            ('LINEBELOW',(0,n_data),(-1,n_data),1,colors.HexColor('#D1D5DB')),
        ]))
        return t

    def generate_report(self, d):
        buf = io.BytesIO()
        parts = d.get('month_year','').split('-')
        mm_aa = f"{parts[1]}/{parts[0][2:]}" if len(parts)==2 else ''
        pdf_title = f"{d.get('company_name','ON')} | {mm_aa} | Relatorio de Energia"

        doc = BaseDocTemplate(buf, pagesize=A4, rightMargin=MG, leftMargin=MG, topMargin=MG, bottomMargin=18*mm,
                              title=pdf_title, author="ON Solucoes Energeticas")
        frame = Frame(MG, 18*mm, CW, PH - MG - 18*mm, id='main')

        def _on_page(canvas, doc_obj):
            canvas.saveState()
            # Yellow footer bar
            canvas.setFillColor(Y)
            canvas.rect(0, 0, PW, 12*mm, fill=1, stroke=0)
            # Footer text - centered
            txt = "ON Solucoes Energeticas | onsolucoesenergeticas.com.br | @on.solucoes"
            canvas.setFont('Helvetica-Bold', 6.5)
            canvas.setFillColor(BK)
            canvas.drawCentredString(PW/2, 5.5*mm, txt)
            # Clickable links over the correct text positions
            # "onsolucoesenergeticas.com.br" is roughly at center - measure text
            tw = canvas.stringWidth(txt, 'Helvetica-Bold', 6.5)
            x_start = PW/2 - tw/2
            # ON Solucoes = ~115pt, then " | " = ~10pt, then site ~135pt, then " | " ~10pt, then insta ~55pt
            site_x = x_start + 130
            insta_x = site_x + 145
            canvas.linkURL("https://onsolucoesenergeticas.com.br", (site_x, 3*mm, site_x+130, 9*mm))
            canvas.linkURL("https://instagram.com/on.solucoes", (insta_x, 3*mm, insta_x+55, 9*mm))
            # Page number - right
            canvas.drawRightString(PW-MG, 5.5*mm, f"Pagina {doc_obj.page}")
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
        el.extend(self._hdr(d))
        el.append(self._kpi_row([
            {'l':'Potencia','v':f"{_n(cap,2)} kWp"},
            {'l':'Geracao do Mes','v':f"{_n(gen,0)} kWh",'a':True},
            {'l':'Desempenho','v':f"{_n(perf,1)} %",'g':perf>=100,'a':perf<100},
        ]))
        el.append(Spacer(1,4*mm))

        # Energy Flow Diagram with background image
        el.append(self._sec("Fluxo de Energia"))
        el.append(Spacer(1,2*mm))
        flow_elements = self._energy_flow_diagram(d)
        el.extend(flow_elements)
        el.append(Spacer(1,4*mm))

        # Financial
        el.append(self._sec("Financeiro", dark=True))
        el.append(Spacer(1,2*mm))
        el.append(self._kpi_row([
            {'l':'Faturado','v':_brl(billed)},
            {'l':'Economia do Mes','v':_brl(saved),'g':True},
            {'l':'Retorno Mensal','v':f"{_n(roi_m,2)} %"},
        ]))
        el.append(Spacer(1,2*mm))
        el.append(self._kpi_row([
            {'l':'Economia Total','v':_brl(total_sav),'g':True},
            {'l':'Retorno Total','v':f"{_n(roi_t,2)} %"},
            {'l':'Ger. Acordada','v':f"{_n(prog,0)} kWh"},
        ]))
        el.append(Spacer(1,4*mm))

        # Meses Anteriores - dark readable text, more columns
        hist = d.get('historical',[])
        if hist:
            el.append(self._sec("Meses Anteriores"))
            el.append(Spacer(1,2*mm))
            el.append(self._hist_table(hist[:6]))

        # ═══ PAGE 2: CHART + PROGNOSIS + ENVIRONMENTAL ═══
        el.append(PageBreak())
        el.extend(self._hdr(d))
        el.append(self._kpi_row([
            {'l':'Potencia','v':f"{_n(cap,2)} kWp"},
            {'l':'Geracao','v':f"{_n(gen,0)} kWh",'a':True},
            {'l':'Desempenho','v':f"{_n(perf,1)} %",'g':perf>=100,'a':perf<100},
        ]))
        el.append(Spacer(1,2*mm))

        month_name = MESES.get(parts[1],'') if len(parts)==2 else ''
        el.append(Paragraph(f"<font color='#FFD600'><b>{month_name}</b></font>",
                  _ps('MT',14,'Helvetica-Bold',Y,TA_CENTER)))
        el.append(Spacer(1,2*mm))

        daily = d.get('daily_generation',[])
        days = len(daily) if daily else 30
        dp = prog/days if days>0 else 0
        el.append(self._chart(daily, dp))
        el.append(Paragraph("<font color='#BDBDBD'>&#9632;</font> Geracao &nbsp;&nbsp;<font color='#FFD600'>&#8212;&#8212;</font> Prognostico",
                  _ps('LG',7,'Helvetica',GD,TA_CENTER)))
        el.append(Spacer(1,3*mm))
        el.append(self._kpi_row([
            {'l':'Geracao','v':f"{_n(gen/1000,2)} MWh"},
            {'l':'Prognostico','v':f"{_n(prog/1000,2)} MWh"},
            {'l':'Desempenho','v':f"{_n(perf,1)} %",'g':perf>=100,'a':perf<100},
        ]))
        el.append(Spacer(1,4*mm))

        # Prognosis section
        el.append(self._sec("Prognostico e Impacto Ambiental"))
        el.append(Spacer(1,2*mm))
        il = _ps('IL',8,'Helvetica',GD,TA_LEFT)
        iv = _ps('IV',10,'Helvetica-Bold',BK,TA_LEFT)
        prog_data = [
            [Paragraph("Geracao acordada mensal",il), Paragraph(f"<b>{_n(prog,0)} kWh</b>",iv),
             Paragraph("Geracao acordada anual",il), Paragraph(f"<b>{_n(ann_prog/1000,2)} MWh</b>",iv)],
            [Paragraph("Prognostico mensal",il), Paragraph(f"<b>{_n(prog,0)} kWh</b>",iv),
             Paragraph("Prognostico anual",il), Paragraph(f"<b>{_n(ann_prog/1000,2)} MWh</b>",iv)],
        ]
        pt = Table(prog_data, colWidths=[95,CW/2-95,95,CW/2-95])
        pt.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('BACKGROUND',(0,0),(-1,-1),GL),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#E5E7EB'))]))
        el.append(pt)
        el.append(Spacer(1,3*mm))

        co2t = (env.get('co2_avoided_kg',0) or 0)/1000
        trees = int(env.get('trees_saved',0) or 0)
        el2 = _ps('EE',8,'Helvetica',GD,TA_CENTER,12)
        env_data = [[
            Paragraph(f"Deixados de produzir<br/><b><font size='12'>{_n(co2t,2)}t de CO2</font></b><br/>(Ultimos 12 meses)",el2),
            Paragraph(f"Total de<br/><b><font size='12' color='#16A34A'>{trees} arvores salvas</font></b><br/>(Ultimos 12 meses)",el2),
        ]]
        et = Table(env_data, colWidths=[CW/2]*2)
        et.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
            ('BACKGROUND',(0,0),(-1,-1),GL),('BOX',(0,0),(-1,-1),1,Y),
            ('LINEBEFORE',(1,0),(1,-1),0.5,colors.HexColor('#E5E7EB'))]))
        el.append(et)

        # ═══ PAGE 3+: CONSUMER UNITS ═══
        cu = d.get('consumer_units',[])
        if cu:
            el.append(PageBreak())
            el.extend(self._hdr(d))
            el.append(self._sec("INFORMACOES CONCESSIONARIA", dark=True))
            el.append(Spacer(1,3*mm))

            hdr = ['UC','Endereco','Ciclo','(%)','Consumo\nRegist.','Energ.\nComp.','Energ.\nFatur.','Cred.\nAnter.','Cred.\nAcum.','Faturado\n(R$)','Economia\n(R$)']
            rows = []
            tc=tp=tf=ta=tac=tb=ts2=0
            for c in cu:
                cons=c.get('consumption_registered',0) or 0
                comp=c.get('energy_compensated',0) or 0
                fat=c.get('energy_billed',0) or 0
                ca=c.get('credit_previous',0) or 0
                cacc=c.get('credit_accumulated',0) or 0
                bill=c.get('amount_billed',0) or 0
                sav=c.get('amount_saved',0) or 0
                tc+=cons;tp+=comp;tf+=fat;ta+=ca;tac+=cacc;tb+=bill;ts2+=sav
                pct_val = c.get('percentage',0) or 0
                pct = f"{_n(pct_val,2)}%"
                rows.append([c.get('uc_number',''),(c.get('name') or '')[:28],c.get('cycle',''),
                    pct,_n(cons,0),_n(comp,0),_n(fat,0),_n(ca,0),_n(cacc,0),_n(bill,2),_n(sav,2)])
            rows.append(['TOTAL','','','',_n(tc,0),_n(tp,0),_n(tf,0),_n(ta,0),_n(tac,0),_n(tb,2),_n(ts2,2)])

            el.append(self._data_table(hdr, rows,
                [52,76,54,28,42,42,40,38,38,46,46], has_total=True))
            el.append(Spacer(1,4*mm))
            el.append(Paragraph(
                f"<b>Resumo:</b> Consumo: {_n(tc,0)} kWh | Compensado: {_n(tp,0)} kWh | "
                f"Faturado: {_brl(tb)} | <font color='#16A34A'><b>Economizado: {_brl(ts2)}</b></font>",
                _ps('RS',8,'Helvetica',BK,TA_CENTER)))

        doc.build(el)
        res = buf.getvalue()
        buf.close()
        return res


def generate_plant_report(data, report_type='complete'):
    return SolarReportGenerator().generate_report(data)
