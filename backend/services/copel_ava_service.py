"""
COPEL AVA Portal Integration - Download invoices automatically
Portal: https://www.copel.com/avaweb/paginaLogin/login.jsf
"""
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

COPEL_LOGIN_URL = "https://www.copel.com/avaweb/paginaLogin/login.jsf"
COPEL_SEGUNDA_VIA_URL = "https://www.copel.com/avaweb/paginas/segundaViaFatura.jsf"


class CopelAVAService:
    def __init__(self):
        self.browser = None
        self.page = None
        self.logged_in = False

    async def _init_browser(self):
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
        pw = await async_playwright().start()
        self.browser = await pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        ctx = await self.browser.new_context(accept_downloads=True)
        self.page = await ctx.new_page()

    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
            self.logged_in = False

    async def login(self, cnpj: str, password: str) -> Dict[str, Any]:
        """Login to COPEL AVA portal."""
        try:
            if not self.browser:
                await self._init_browser()

            await self.page.goto(COPEL_LOGIN_URL, timeout=30000)
            await self.page.wait_for_timeout(3000)

            await self.page.fill('#formulario\\:numDoc', cnpj)
            await self.page.fill('#formulario\\:pass', password)
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_timeout(8000)

            # Check if login succeeded by looking for UC list
            body = await self.page.inner_text('body')
            # The UC list page has 7-9 digit UC numbers
            import re
            ucs_found = re.findall(r'\b\d{7,9}\b', body)
            ucs_found = list(set(ucs_found))

            if len(ucs_found) > 0:
                self.logged_in = True
                return {"success": True, "ucs": ucs_found, "total": len(ucs_found)}
            else:
                # Check for error message
                if 'inválid' in body.lower() or 'incorret' in body.lower():
                    return {"success": False, "error": "Login ou senha invalidos"}
                return {"success": False, "error": "Login nao retornou UCs. Tente novamente."}

        except Exception as e:
            logger.error(f"COPEL login error: {e}")
            return {"success": False, "error": str(e)}

    async def list_available_invoices(self, uc_number: str) -> List[Dict[str, Any]]:
        """Select a UC and list available invoices for download."""
        if not self.logged_in or not self.page:
            return []

        try:
            # Click the UC row to select it
            rows = await self.page.query_selector_all('table tbody tr')
            uc_selected = False
            for row in rows:
                txt = await row.inner_text()
                if uc_number in txt:
                    links = await row.query_selector_all('a')
                    if links:
                        await links[-1].click()  # Last link is "Selecionar"
                        await self.page.wait_for_timeout(5000)
                        uc_selected = True
                    break

            if not uc_selected:
                return []

            # Navigate to Segunda Via page
            # First go to "Todos os Servicos"
            try:
                await self.page.click('a:has-text("ACESSAR TODOS OS SERVIÇOS")', timeout=5000)
                await self.page.wait_for_timeout(3000)
            except:
                pass

            # Click "Emitir Segunda Via"
            try:
                await self.page.click('a:has-text("Emitir Segunda Via")', timeout=5000)
                await self.page.wait_for_timeout(5000)
            except:
                return []

            # Extract invoices from table
            invoices = []
            table_rows = await self.page.query_selector_all('table tbody tr')
            for row in table_rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 5:
                    ref = (await cells[0].inner_text()).strip()
                    venc = (await cells[1].inner_text()).strip()
                    fatura = (await cells[2].inner_text()).strip()
                    valor = (await cells[3].inner_text()).strip()
                    if ref and '/' in ref:
                        invoices.append({
                            'reference_month': ref,
                            'due_date': venc,
                            'invoice_number': fatura,
                            'amount': valor,
                            'uc_number': uc_number,
                        })

            # Go back to UC list for next UC
            try:
                await self.page.goto(
                    "https://www.copel.com/avaweb/paginas/listarUcsDoc.jsf",
                    timeout=15000
                )
                await self.page.wait_for_timeout(3000)
            except:
                pass

            return invoices

        except Exception as e:
            logger.error(f"COPEL list invoices error for UC {uc_number}: {e}")
            return []

    async def download_invoice(self, uc_number: str, reference_month: str) -> Optional[bytes]:
        """Download a specific invoice PDF for a UC and month."""
        if not self.logged_in or not self.page:
            return None

        try:
            # Select the UC
            rows = await self.page.query_selector_all('table tbody tr')
            for row in rows:
                txt = await row.inner_text()
                if uc_number in txt:
                    links = await row.query_selector_all('a')
                    if links:
                        await links[-1].click()
                        await self.page.wait_for_timeout(5000)
                    break

            # Navigate to Segunda Via
            try:
                await self.page.click('a:has-text("ACESSAR TODOS OS SERVIÇOS")', timeout=5000)
                await self.page.wait_for_timeout(3000)
                await self.page.click('a:has-text("Emitir Segunda Via")', timeout=5000)
                await self.page.wait_for_timeout(5000)
            except:
                return None

            # Find and click the "2 via" link for the matching month
            table_rows = await self.page.query_selector_all('table tbody tr')
            for row in table_rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 5:
                    ref = (await cells[0].inner_text()).strip()
                    if ref == reference_month:
                        via_link = await cells[4].query_selector('a')
                        if via_link:
                            try:
                                async with self.page.expect_download(timeout=30000) as dl_info:
                                    await via_link.click()
                                dl = await dl_info.value
                                path = f"/tmp/copel_{uc_number}_{reference_month.replace('/', '_')}.pdf"
                                await dl.save_as(path)
                                with open(path, 'rb') as f:
                                    return f.read()
                            except:
                                logger.warning(f"Download timeout for UC {uc_number} {reference_month}")
                                return None
            return None
        except Exception as e:
            logger.error(f"COPEL download error: {e}")
            return None
