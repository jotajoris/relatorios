"""
COPEL AVA Portal Integration - Download invoices automatically
Portal: https://www.copel.com/avaweb/paginaLogin/login.jsf

Flow (based on actual portal UI):
1. Login with CNPJ/password
2. Page shows list of UCs - click blue icon (portinha) to select UC
3. UC services page - click "Segunda via online" icon
4. "Segunda via de fatura" page - shows "Débitos Pendentes" table with "2 via" link
5. Click "2 via" link opens modal with "Fazer download da 2ª via" button
6. To change UC, click blue arrow next to UC number in header
"""
import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

COPEL_LOGIN_URL = "https://www.copel.com/avaweb/paginaLogin/login.jsf"
COPEL_UC_LIST_URL = "https://www.copel.com/avaweb/paginas/listarUcsDoc.jsf"
COPEL_SEGUNDA_VIA_URL = "https://www.copel.com/avaweb/paginas/segundaViaFatura.jsf"

# Increased timeout for slow connections
DEFAULT_TIMEOUT = 120000  # 120 seconds


class CopelAVAService:
    def __init__(self):
        self.browser = None
        self.page = None
        self.logged_in = False
        self.pw = None

    async def _init_browser(self):
        logger.info("[COPEL] Initializing browser...")
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        ctx = await self.browser.new_context(
            accept_downloads=True,
            viewport={'width': 1280, 'height': 900}
        )
        self.page = await ctx.new_page()
        self.page.set_default_timeout(DEFAULT_TIMEOUT)
        logger.info("[COPEL] Browser initialized successfully")

    async def close(self):
        if self.browser:
            logger.info("[COPEL] Closing browser...")
            await self.browser.close()
            self.browser = None
            self.page = None
            self.logged_in = False
        if self.pw:
            await self.pw.stop()
            self.pw = None

    async def login(self, cnpj: str, password: str) -> Dict[str, Any]:
        """Login to COPEL AVA portal."""
        try:
            logger.info(f"[COPEL] Starting login for CNPJ: {cnpj[:8]}***")
            
            if not self.browser:
                await self._init_browser()

            logger.info(f"[COPEL] Navigating to login page: {COPEL_LOGIN_URL}")
            await self.page.goto(COPEL_LOGIN_URL, timeout=60000, wait_until='networkidle')
            await self.page.wait_for_timeout(3000)
            logger.info("[COPEL] Login page loaded")

            # Take screenshot for debugging
            await self.page.screenshot(path='/tmp/copel_login_page.png')

            logger.info("[COPEL] Filling credentials...")
            # Try multiple selectors for CPF/CNPJ field
            cpf_field = await self.page.query_selector('#formulario\\:numDoc')
            if not cpf_field:
                cpf_field = await self.page.query_selector('input[id*="numDoc"]')
            if not cpf_field:
                cpf_field = await self.page.query_selector('input[name*="numDoc"]')
            
            if cpf_field:
                await cpf_field.fill(cnpj)
            else:
                logger.error("[COPEL] Could not find CPF/CNPJ field")
                return {"success": False, "error": "Campo CPF/CNPJ não encontrado"}
            
            # Try multiple selectors for password field
            pass_field = await self.page.query_selector('#formulario\\:pass')
            if not pass_field:
                pass_field = await self.page.query_selector('input[type="password"]')
            
            if pass_field:
                await pass_field.fill(password)
            else:
                logger.error("[COPEL] Could not find password field")
                return {"success": False, "error": "Campo senha não encontrado"}
            
            logger.info("[COPEL] Clicking submit button...")
            submit_btn = await self.page.query_selector('button[type="submit"]')
            if not submit_btn:
                submit_btn = await self.page.query_selector('input[type="submit"]')
            if submit_btn:
                await submit_btn.click()
            else:
                await self.page.keyboard.press('Enter')
            
            logger.info("[COPEL] Waiting for login response...")
            await self.page.wait_for_timeout(8000)

            # Dismiss any inactivity modal that might have appeared (from previous session)
            try:
                inactivity_modal = await self.page.query_selector('.ui-dialog:has-text("Inatividade")')
                if inactivity_modal:
                    logger.info("[COPEL] Found stale inactivity modal after login, dismissing via JS...")
                    await self.page.evaluate('''() => {
                        const btn = document.querySelector('.ui-dialog button');
                        if (btn) btn.click();
                    }''')
                    await self.page.wait_for_timeout(3000)
                    
                    # Force navigate to UC list page to clear any modal state
                    logger.info("[COPEL] Force navigating to UC list to clear modal...")
                    await self.page.goto(COPEL_UC_LIST_URL, timeout=30000, wait_until='networkidle')
                    await self.page.wait_for_timeout(3000)
            except:
                pass

            # Take screenshot after login
            await self.page.screenshot(path='/tmp/copel_after_login.png')

            # Check if login succeeded by looking for UC list
            body = await self.page.inner_text('body')
            current_url = self.page.url
            logger.info(f"[COPEL] Current URL after login: {current_url}")
            
            # The UC list page has 7-9 digit UC numbers
            import re
            ucs_found = re.findall(r'\b\d{7,9}\b', body)
            ucs_found = list(set(ucs_found))
            
            # Check for specific UC list page indicators
            is_uc_list = 'listarUcs' in current_url or 'Selecione uma unidade consumidora' in body

            if len(ucs_found) > 0 or is_uc_list:
                self.logged_in = True
                logger.info(f"[COPEL] Login successful! Found {len(ucs_found)} UCs")
                return {"success": True, "ucs": ucs_found, "total": len(ucs_found)}
            else:
                # Check for error message
                if 'inválid' in body.lower() or 'incorret' in body.lower():
                    return {"success": False, "error": "Login ou senha invalidos"}
                if 'captcha' in body.lower():
                    return {"success": False, "error": "CAPTCHA detectado. Tente novamente mais tarde."}
                return {"success": False, "error": "Login nao retornou UCs. Tente novamente."}

        except Exception as e:
            logger.error(f"[COPEL] Login error: {e}")
            return {"success": False, "error": str(e)}

    async def _ensure_uc_list_page(self):
        """Ensure we're on the UC list page."""
        try:
            current_url = self.page.url
            if 'listarUcs' not in current_url:
                logger.info("[COPEL] Navigating back to UC list...")
                await self.page.goto(COPEL_UC_LIST_URL, timeout=30000, wait_until='networkidle')
                await self.page.wait_for_timeout(3000)
            return True
        except Exception as e:
            logger.warning(f"[COPEL] Failed to navigate to UC list: {e}")
            return False

    async def _select_uc(self, uc_number: str) -> bool:
        """
        Select a UC from the UC list table by clicking the blue icon (portinha).
        Returns True if successful.
        """
        try:
            await self._ensure_uc_list_page()
            await self.page.wait_for_timeout(2000)
            
            logger.info(f"[COPEL] Looking for UC {uc_number} in table...")
            
            # Find the UC row and click the blue "portinha" icon (selection link)
            rows = await self.page.query_selector_all('table tbody tr')
            logger.info(f"[COPEL] Found {len(rows)} rows in UC table")
            
            for row in rows:
                row_text = await row.inner_text()
                if uc_number in row_text:
                    logger.info(f"[COPEL] Found UC {uc_number} in row")
                    
                    # The select button is the last cell with an icon/link
                    # It's a blue door/arrow icon with aria-label="Selecionar"
                    select_btn = await row.query_selector('a[aria-label="Selecionar"]')
                    if not select_btn:
                        # Try finding any link in the last cell
                        cells = await row.query_selector_all('td')
                        if cells and len(cells) > 0:
                            last_cell = cells[-1]
                            select_btn = await last_cell.query_selector('a')
                    
                    if select_btn:
                        logger.info(f"[COPEL] Clicking select button for UC {uc_number}")
                        await select_btn.click()
                        await self.page.wait_for_timeout(5000)
                        
                        # Verify we're on the UC services page
                        body = await self.page.inner_text('body')
                        if 'Serviços' in body or 'Segunda via' in body or uc_number in body:
                            logger.info(f"[COPEL] Successfully selected UC {uc_number}")
                            await self.page.screenshot(path=f'/tmp/copel_uc_selected_{uc_number}.png')
                            return True
                    else:
                        logger.warning(f"[COPEL] UC {uc_number} found but no select button (may be disconnected)")
                        return False
            
            logger.warning(f"[COPEL] UC {uc_number} not found in table")
            return False
            
        except Exception as e:
            logger.error(f"[COPEL] Error selecting UC {uc_number}: {e}")
            return False

    async def _navigate_to_segunda_via(self) -> bool:
        """
        From UC services page, navigate to "Segunda via de fatura" page.
        Click on "Segunda via online" icon.
        """
        try:
            logger.info("[COPEL] Looking for 'Segunda via online' option...")
            await self.page.wait_for_timeout(2000)
            
            # Take screenshot of services page
            await self.page.screenshot(path='/tmp/copel_services_page.png')
            
            # Try clicking the "Segunda via online" option
            # It could be an icon/link with various selectors
            selectors_to_try = [
                'a:has-text("Segunda via online")',
                'a:has-text("Segunda via")',
                'div:has-text("Segunda via online") >> xpath=ancestor::a',
                'span:has-text("Segunda via") >> xpath=ancestor::a',
                '[title*="Segunda via"]',
                'a[href*="segundaVia"]',
            ]
            
            clicked = False
            for selector in selectors_to_try:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        await element.click()
                        clicked = True
                        logger.info(f"[COPEL] Clicked 'Segunda via online' using selector: {selector}")
                        break
                except:
                    continue
            
            if not clicked:
                # Try finding by image/icon alt text or nearby text
                links = await self.page.query_selector_all('a')
                for link in links:
                    try:
                        text = await link.inner_text()
                        if 'segunda via' in text.lower():
                            await link.click()
                            clicked = True
                            logger.info(f"[COPEL] Clicked link with text: {text}")
                            break
                    except:
                        continue
            
            if clicked:
                await self.page.wait_for_timeout(5000)
                await self.page.screenshot(path='/tmp/copel_segunda_via_page.png')
                
                # Verify we're on the segunda via page
                body = await self.page.inner_text('body')
                if 'Segunda via de fatura' in body or 'Débitos Pendentes' in body or 'Mês Ref' in body:
                    logger.info("[COPEL] Successfully navigated to Segunda via de fatura page")
                    return True
            
            logger.warning("[COPEL] Could not navigate to Segunda via page")
            return False
            
        except Exception as e:
            logger.error(f"[COPEL] Error navigating to Segunda via: {e}")
            return False

    async def _dismiss_inactivity_modal(self) -> bool:
        """
        Try to dismiss inactivity modal if present. 
        Returns True only if modal is VISIBLE and contains inactivity warning.
        """
        try:
            # Check for the inactivity dialog specifically - must be visible
            inactivity_modal = await self.page.query_selector('.ui-dialog[aria-hidden="false"]:has-text("Tela inativa")')
            if inactivity_modal:
                # Double check it's really visible
                is_visible = await inactivity_modal.is_visible()
                if not is_visible:
                    return False
                    
                logger.info("[COPEL] Inactivity modal VISIBLE, attempting to dismiss...")
                await self.page.screenshot(path='/tmp/copel_inactivity_modal.png')
                
                # Try to dismiss via JavaScript
                await self.page.evaluate('''() => {
                    const btn = document.querySelector('.ui-dialog button');
                    if (btn) btn.click();
                }''')
                await self.page.wait_for_timeout(2000)
                
                # Force navigate to UC list to clear any modal state
                await self.page.goto(COPEL_UC_LIST_URL, timeout=30000, wait_until='networkidle')
                await self.page.wait_for_timeout(2000)
                
                # Check if modal is still there and visible
                still_there = await self.page.query_selector('.ui-dialog[aria-hidden="false"]:has-text("Tela inativa")')
                if still_there:
                    is_still_visible = await still_there.is_visible()
                    if is_still_visible:
                        logger.warning("[COPEL] Inactivity modal still visible after dismiss attempt")
                        return True  # Still expired
                
                logger.info("[COPEL] Inactivity modal dismissed successfully")
                return False  # Modal dismissed, can continue
            return False  # No visible modal
        except Exception as e:
            logger.warning(f"[COPEL] Error handling inactivity modal: {e}")
            return False

    async def download_invoice(self, uc_number: str, reference_month: str) -> Optional[bytes]:
        """
        Download a specific invoice PDF for a UC and month.
        
        Flow:
        1. Select UC from list
        2. Click "Segunda via online"
        3. Find invoice in "Débitos Pendentes" table
        4. Click "2 via" link
        5. In modal, click "Fazer download da 2ª via"
        """
        logger.info(f"[COPEL] Starting download for UC {uc_number}, month {reference_month}")
        
        if not self.logged_in or not self.page:
            logger.error("[COPEL] Not logged in or no page available")
            return None

        try:
            # Check for inactivity before starting
            if await self._dismiss_inactivity_modal():
                logger.warning("[COPEL] Session expired before starting - need new login")
                return None
            
            # Step 1: Select the UC
            if not await self._select_uc(uc_number):
                logger.error(f"[COPEL] Failed to select UC {uc_number}")
                return None
            
            # Step 2: Navigate to Segunda via online
            if not await self._navigate_to_segunda_via():
                logger.error("[COPEL] Failed to navigate to Segunda via page")
                return None
            
            # Step 3 & 4: Find and click the "2 via" link for the matching month
            logger.info(f"[COPEL] Looking for invoice {reference_month} in Débitos Pendentes...")
            
            # The table has columns: Mês Ref., Vencimento, Fatura, Valor (R$), Via
            table_rows = await self.page.query_selector_all('table tbody tr')
            logger.info(f"[COPEL] Found {len(table_rows)} rows in invoice table")
            
            found_invoice = False
            for row in table_rows:
                row_text = await row.inner_text()
                logger.info(f"[COPEL] Row text: {row_text[:100]}...")
                
                cells = await row.query_selector_all('td')
                if len(cells) >= 5:
                    ref = (await cells[0].inner_text()).strip()
                    logger.info(f"[COPEL] Checking month: {ref} vs {reference_month}")
                    
                    if ref == reference_month:
                        logger.info(f"[COPEL] Found matching invoice for {reference_month}")
                        found_invoice = True
                        
                        # The "via" link is in the last column (Via)
                        # Can be "1 via" (first issue) or "2 via" (second issue)
                        via_cell = cells[4]  # 5th column (index 4)
                        via_link = await via_cell.query_selector('a')
                        
                        if via_link:
                            via_text = await via_link.inner_text()
                            logger.info(f"[COPEL] Clicking '{via_text}' link...")
                            await via_link.click()
                            await self.page.wait_for_timeout(3000)
                            
                            # Check for inactivity modal - if present, session expired
                            if await self._dismiss_inactivity_modal():
                                logger.warning("[COPEL] Session expired during download - will retry with new session")
                                return None
                            
                            # Step 5: Modal opens - click download button
                            await self.page.screenshot(path='/tmp/copel_modal.png')
                            
                            # Log modal content for debugging
                            try:
                                modal_html = await self.page.evaluate('() => document.querySelector(".ui-dialog")?.innerHTML || "No modal found"')
                                logger.info(f"[COPEL] Modal HTML (first 500 chars): {modal_html[:500]}...")
                            except:
                                pass
                            
                            # Wait for modal and find download button
                            download_btn_selectors = [
                                'button:has-text("Fazer download da 2ª via")',
                                'button:has-text("Fazer download da 1ª via")',
                                'button:has-text("Fazer download")',
                                'a:has-text("Fazer download da 2ª via")',
                                'a:has-text("Fazer download da 1ª via")',
                                'a:has-text("Fazer download")',
                                '.ui-dialog-content button',
                                '.ui-dialog button',
                                'button:has-text("download")',
                                'button.ui-button',
                            ]
                            
                            download_btn = None
                            for selector in download_btn_selectors:
                                try:
                                    download_btn = await self.page.wait_for_selector(selector, timeout=2000)
                                    if download_btn:
                                        btn_text = await download_btn.inner_text()
                                        logger.info(f"[COPEL] Found button with selector '{selector}': {btn_text}")
                                        if 'download' in btn_text.lower():
                                            break
                                        download_btn = None  # Reset if not a download button
                                except:
                                    continue
                            
                            if download_btn:
                                try:
                                    logger.info("[COPEL] Clicking download button...")
                                    async with self.page.expect_download(timeout=60000) as dl_info:
                                        await download_btn.click()
                                    
                                    dl = await dl_info.value
                                    path = f"/tmp/copel_{uc_number}_{reference_month.replace('/', '_')}.pdf"
                                    await dl.save_as(path)
                                    logger.info(f"[COPEL] Invoice downloaded successfully: {path}")
                                    
                                    with open(path, 'rb') as f:
                                        return f.read()
                                        
                                except Exception as dl_error:
                                    logger.warning(f"[COPEL] Download error: {dl_error}")
                                    # Try closing modal if download failed
                                    try:
                                        close_btn = await self.page.query_selector('button[aria-label="Close"]')
                                        if close_btn:
                                            await close_btn.click()
                                    except:
                                        pass
                                    return None
                            else:
                                logger.warning("[COPEL] Download button not found in modal")
                                return None
                        else:
                            logger.warning(f"[COPEL] No '2 via' link found for {reference_month}")
                        break
            
            if not found_invoice:
                logger.warning(f"[COPEL] Invoice {reference_month} not found in Débitos Pendentes")
                
                # Try alternative: use the "Segunda Via" section with month selector
                logger.info("[COPEL] Trying alternative method with month selector...")
                return await self._download_via_month_selector(uc_number, reference_month)
            
            return None
            
        except Exception as e:
            logger.error(f"[COPEL] Download error: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # Return to UC list for next download
            await self._ensure_uc_list_page()

    async def _download_via_month_selector(self, uc_number: str, reference_month: str) -> Optional[bytes]:
        """
        Alternative download method using the month selector field.
        Used when invoice is not in Débitos Pendentes table.
        """
        try:
            logger.info(f"[COPEL] Trying month selector for {reference_month}...")
            
            # Find the month input field and fill it
            month_input = await self.page.query_selector('input[id*="mesReferencia"]')
            if not month_input:
                month_input = await self.page.query_selector('input[placeholder*="Mês"]')
            
            if month_input:
                await month_input.fill(reference_month)
                await self.page.wait_for_timeout(1000)
                
                # Click "Listar fatura" button
                list_btn = await self.page.query_selector('button:has-text("Listar fatura")')
                if not list_btn:
                    list_btn = await self.page.query_selector('a:has-text("Listar fatura")')
                
                if list_btn:
                    await list_btn.click()
                    await self.page.wait_for_timeout(5000)
                    
                    # Now look for the invoice in the table again
                    table_rows = await self.page.query_selector_all('table tbody tr')
                    for row in table_rows:
                        cells = await row.query_selector_all('td')
                        if len(cells) >= 5:
                            ref = (await cells[0].inner_text()).strip()
                            if ref == reference_month:
                                via_link = await cells[4].query_selector('a')
                                if via_link:
                                    await via_link.click()
                                    await self.page.wait_for_timeout(3000)
                                    
                                    # Click download button in modal
                                    download_btn = await self.page.wait_for_selector(
                                        'button:has-text("Fazer download")', timeout=5000
                                    )
                                    if download_btn:
                                        async with self.page.expect_download(timeout=60000) as dl_info:
                                            await download_btn.click()
                                        dl = await dl_info.value
                                        path = f"/tmp/copel_{uc_number}_{reference_month.replace('/', '_')}.pdf"
                                        await dl.save_as(path)
                                        with open(path, 'rb') as f:
                                            return f.read()
            
            logger.warning(f"[COPEL] Alternative method also failed for {reference_month}")
            return None
            
        except Exception as e:
            logger.error(f"[COPEL] Alternative download error: {e}")
            return None


    async def list_available_invoices(self, uc_number: str) -> List[Dict[str, Any]]:
        """
        Select a UC and list all available invoices (both pending and historical).
        """
        if not self.logged_in or not self.page:
            return []

        try:
            # Select the UC
            if not await self._select_uc(uc_number):
                return []
            
            # Navigate to Segunda via online
            if not await self._navigate_to_segunda_via():
                return []
            
            # Extract invoices from "Débitos Pendentes" table
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

            # Return to UC list for next UC
            await self._ensure_uc_list_page()
            
            return invoices

        except Exception as e:
            logger.error(f"[COPEL] Error listing invoices for UC {uc_number}: {e}")
            return []
