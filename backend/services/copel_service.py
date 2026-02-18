"""
COPEL Portal Automation Service
Uses Playwright to automate login and invoice download from COPEL customer portal

NOTE: Playwright is imported lazily to allow the app to start without it installed.
The automation features will only work when playwright is available.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List, Any, TYPE_CHECKING

# Lazy import for playwright - will be imported when actually needed
# This allows the app to start even if playwright is not installed
if TYPE_CHECKING:
    from playwright.async_api import Browser, Page

logger = logging.getLogger(__name__)

# COPEL Portal URLs
COPEL_LOGIN_URL = "https://www.copel.com/avaweb/paginaLogin/login.jsf"
COPEL_BASE_URL = "https://www.copel.com/avaweb"

# Flag to track if playwright is available
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
    # Set Playwright browsers path
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
except ImportError:
    logger.warning("Playwright not available. COPEL automation features will be disabled.")
    async_playwright = None
    PlaywrightTimeout = Exception


class CopelService:
    """Service class for COPEL portal automation"""
    
    def __init__(self):
        self.browser: Optional["Browser"] = None
        self.page: Optional["Page"] = None
        self.logged_in = False
        self.download_path = "/tmp/copel_downloads"
        
        # Ensure download directory exists
        os.makedirs(self.download_path, exist_ok=True)
    
    async def _init_browser(self):
        """Initialize Playwright browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        )
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            accept_downloads=True
        )
        self.page = await context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(60000)  # 60 seconds
    
    async def _close_browser(self):
        """Close browser instance"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
            self.logged_in = False
    
    async def login(self, cpf_cnpj: str, password: str) -> Dict[str, Any]:
        """
        Login to COPEL portal
        
        Args:
            cpf_cnpj: CPF or CNPJ (numbers only or formatted)
            password: Portal password
            
        Returns:
            Login result with status
        """
        try:
            if not self.browser:
                await self._init_browser()
            
            logger.info(f"Attempting COPEL login for: {cpf_cnpj[:4]}***")
            
            # Navigate to login page
            await self.page.goto(COPEL_LOGIN_URL, wait_until='networkidle', timeout=90000)
            await asyncio.sleep(2)  # Wait for JS to load
            
            # Take screenshot for debugging
            await self.page.screenshot(path=f"{self.download_path}/login_page.png")
            
            # Check for reCAPTCHA
            captcha_element = await self.page.query_selector('.g-recaptcha, [class*="captcha"]')
            if captcha_element:
                # Check if captcha is visible (not yet solved)
                captcha_visible = await captcha_element.is_visible()
                if captcha_visible:
                    logger.warning("reCAPTCHA detected on COPEL login page")
                    # We'll try to proceed anyway - sometimes captcha is not required
            
            # Wait for the form to be visible
            await self.page.wait_for_selector('form', timeout=30000)
            
            # Try different selectors for CPF/CNPJ field
            cpf_selectors = [
                'input[id*="cpfCnpj"]',
                'input[name*="cpfCnpj"]',
                'input[id*="login"]',
                'input[name*="login"]',
                'input[placeholder*="CPF"]',
                'input[placeholder*="CNPJ"]',
                'input[type="text"]:first-of-type'
            ]
            
            cpf_input = None
            for selector in cpf_selectors:
                try:
                    cpf_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if cpf_input:
                        logger.info(f"Found CPF field with selector: {selector}")
                        break
                except:
                    continue
            
            if not cpf_input:
                # Try to find any text input
                inputs = await self.page.query_selector_all('input[type="text"]')
                if inputs:
                    cpf_input = inputs[0]
                    logger.info("Found CPF field using generic text input")
            
            if not cpf_input:
                return {"success": False, "error": "Campo de CPF/CNPJ não encontrado na página"}
            
            # Clear and fill CPF/CNPJ
            await cpf_input.click()
            await cpf_input.fill('')
            # Remove formatting from CPF/CNPJ
            cpf_clean = ''.join(filter(str.isdigit, cpf_cnpj))
            await cpf_input.type(cpf_clean, delay=50)
            
            # Find password field
            password_selectors = [
                'input[type="password"]',
                'input[id*="senha"]',
                'input[name*="senha"]',
                'input[id*="password"]'
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = await self.page.wait_for_selector(selector, timeout=5000)
                    if password_input:
                        logger.info(f"Found password field with selector: {selector}")
                        break
                except:
                    continue
            
            if not password_input:
                return {"success": False, "error": "Campo de senha não encontrado na página"}
            
            # Fill password
            await password_input.click()
            await password_input.fill('')
            await password_input.type(password, delay=50)
            
            # Take screenshot before clicking login
            await self.page.screenshot(path=f"{self.download_path}/before_login.png")
            
            # Find and click login button
            login_button_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Entrar")',
                'button:has-text("Login")',
                'button:has-text("Acessar")',
                'a:has-text("Entrar")',
                '.btn-login',
                '[id*="btnLogin"]',
                '[id*="btnEntrar"]'
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = await self.page.wait_for_selector(selector, timeout=3000)
                    if login_button:
                        logger.info(f"Found login button with selector: {selector}")
                        break
                except:
                    continue
            
            if not login_button:
                # Try clicking any submit button
                await self.page.keyboard.press('Enter')
            else:
                await login_button.click()
            
            # Wait for navigation or error message
            await asyncio.sleep(5)
            
            # Take screenshot after login attempt
            await self.page.screenshot(path=f"{self.download_path}/after_login.png")
            
            # Check if login was successful
            current_url = self.page.url
            page_content = await self.page.content()
            page_text = await self.page.evaluate('() => document.body.innerText')
            
            # Check for captcha error specifically
            if 'captcha' in page_text.lower():
                logger.warning("CAPTCHA verification required/failed")
                return {
                    "success": False, 
                    "error": "O portal COPEL está exigindo verificação de captcha. Tente novamente mais tarde ou faça login manualmente.",
                    "captcha_required": True
                }
            
            # Check for error messages
            error_indicators = ['erro', 'inválid', 'incorret', 'falha', 'error']
            for indicator in error_indicators:
                if indicator.lower() in page_text.lower():
                    # Check if it's an actual error message (not just page text)
                    error_elements = await self.page.query_selector_all('[class*="error"], [class*="alert"], .mensagem-erro, .ui-messages-error')
                    for elem in error_elements:
                        error_text = await elem.text_content()
                        if error_text and len(error_text.strip()) > 0:
                            return {"success": False, "error": f"Erro de login: {error_text.strip()}"}
            
            # Check if we're on a different page (logged in)
            if 'login' not in current_url.lower() or 'listarUcs' in current_url or 'inicio' in current_url:
                self.logged_in = True
                logger.info("COPEL login successful")
                return {
                    "success": True,
                    "message": "Login realizado com sucesso",
                    "url": current_url
                }
            
            # Check for successful login indicators in page content
            success_indicators = ['bem-vindo', 'faturas', 'unidades', 'consumo', 'histórico', 'selecione']
            for indicator in success_indicators:
                if indicator.lower() in page_text.lower():
                    self.logged_in = True
                    logger.info(f"COPEL login successful (found: {indicator})")
                    return {
                        "success": True,
                        "message": "Login realizado com sucesso",
                        "url": current_url
                    }
            
            return {
                "success": False, 
                "error": "Não foi possível confirmar o login. Verifique as credenciais.",
                "url": current_url
            }
            
        except PlaywrightTimeout as e:
            logger.error(f"COPEL login timeout: {str(e)}")
            return {"success": False, "error": "Timeout ao acessar o portal da COPEL. O site pode estar lento."}
        except Exception as e:
            logger.error(f"COPEL login error: {str(e)}")
            return {"success": False, "error": f"Erro ao fazer login: {str(e)}"}
    
    async def get_consumer_units(self) -> List[Dict[str, Any]]:
        """
        Get list of consumer units (UCs) from logged in account
        
        Returns:
            List of consumer units with details
        """
        if not self.logged_in or not self.page:
            return []
        
        try:
            await asyncio.sleep(2)  # Wait for page to fully render
            
            units = []
            
            # The COPEL portal shows UCs in a table
            # Each row has: UC number, City, Address, Group, Status, Select button
            rows = await self.page.query_selector_all('table tbody tr')
            
            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 5:
                    uc_number = await cells[0].text_content()
                    city = await cells[1].text_content()
                    address = await cells[2].text_content()
                    group = await cells[3].text_content()
                    status = await cells[4].text_content()
                    
                    units.append({
                        "uc_number": uc_number.strip() if uc_number else "",
                        "city": city.strip() if city else "",
                        "address": address.strip() if address else "",
                        "group": group.strip() if group else "",
                        "status": status.strip() if status else "",
                    })
            
            logger.info(f"Found {len(units)} consumer units")
            return units
            
        except Exception as e:
            logger.error(f"Error getting consumer units: {str(e)}")
            return []
    
    async def select_consumer_unit(self, uc_number: str) -> Dict[str, Any]:
        """
        Select a consumer unit to view its details and invoices
        
        Args:
            uc_number: The UC number to select
            
        Returns:
            Selection result
        """
        if not self.logged_in or not self.page:
            return {"success": False, "error": "Não está logado"}
        
        try:
            # Wait for table to be fully loaded
            await asyncio.sleep(2)
            
            # Find the row with this UC number and get its select link
            rows = await self.page.query_selector_all('table tbody tr')
            
            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 1:
                    uc_text = await cells[0].text_content()
                    if uc_text and uc_number in uc_text.strip():
                        # Found the row, now look for the select link
                        # The link is a ui-commandlink with aria-label="Selecionar"
                        select_link = await row.query_selector('a.ui-commandlink, a[aria-label="Selecionar"]')
                        
                        if not select_link:
                            # Check if last cell has any link
                            if len(cells) >= 6:
                                select_link = await cells[-1].query_selector('a')
                        
                        if not select_link:
                            return {
                                "success": False, 
                                "error": f"UC {uc_number} não possui botão de seleção (pode estar desligada ou pendente)"
                            }
                        
                        # Click the select link
                        await select_link.click()
                        logger.info(f"Clicked select for UC {uc_number}")
                        
                        # Wait for page to load
                        await asyncio.sleep(4)
                        
                        # Take screenshot
                        await self.page.screenshot(path=f"{self.download_path}/uc_selected_{uc_number}.png")
                        
                        return {
                            "success": True,
                            "uc_number": uc_number,
                            "url": self.page.url
                        }
            
            return {"success": False, "error": f"UC {uc_number} não encontrada na tabela"}
            
        except Exception as e:
            logger.error(f"Error selecting UC: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def download_invoice(self, uc_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Download the latest invoice PDF for a consumer unit
        
        Args:
            uc_number: Consumer unit number (required to select the UC first)
            
        Returns:
            Download result with file path
        """
        if not self.logged_in or not self.page:
            return {"success": False, "error": "Não está logado no portal COPEL"}
        
        try:
            # If UC number provided, select it first
            if uc_number:
                select_result = await self.select_consumer_unit(uc_number)
                if not select_result.get('success'):
                    return select_result
            
            await asyncio.sleep(2)
            
            # Take screenshot of current page
            await self.page.screenshot(path=f"{self.download_path}/uc_page.png")
            
            # Log current page content for debugging
            page_text = await self.page.evaluate('() => document.body.innerText')
            logger.info(f"UC page content (first 500 chars): {page_text[:500]}")
            
            # Look for invoice/fatura links on UC detail page
            invoice_links = [
                'a:has-text("2ª Via")',
                'a:has-text("Segunda Via")',
                'a:has-text("Fatura")',
                'a:has-text("Conta")',
                'a:has-text("PDF")',
                'a:has-text("Visualizar")',
                '[href*="fatura"]',
                '[href*="conta"]',
                '[href*="pdf"]',
                'button:has-text("Fatura")',
            ]
            
            found_link = None
            for selector in invoice_links:
                try:
                    found_link = await self.page.wait_for_selector(selector, timeout=3000)
                    if found_link:
                        logger.info(f"Found invoice link with selector: {selector}")
                        break
                except:
                    continue
            
            if not found_link:
                # Try to find any clickable element that might lead to invoice
                all_links = await self.page.query_selector_all('a')
                for link in all_links:
                    text = await link.text_content()
                    if text and any(word in text.lower() for word in ['fatura', 'conta', 'pdf', 'via', 'baixar', 'visualizar']):
                        found_link = link
                        logger.info(f"Found invoice link by text: {text}")
                        break
            
            if not found_link:
                return {
                    "success": False, 
                    "error": "Link para fatura não encontrado na página da UC",
                    "screenshot": f"{self.download_path}/uc_page.png"
                }
            
            # Try to download the PDF
            try:
                async with self.page.expect_download(timeout=60000) as download_info:
                    await found_link.click()
                
                download = await download_info.value
                
                # Save the file
                filename = f"fatura_copel_{uc_number or 'unknown'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                filepath = os.path.join(self.download_path, filename)
                await download.save_as(filepath)
                
                logger.info(f"COPEL invoice downloaded: {filepath}")
                
                return {
                    "success": True,
                    "filepath": filepath,
                    "filename": filename
                }
            except PlaywrightTimeout:
                # The link might open a new page instead of downloading
                logger.info("Download timeout - link may have opened a new page")
                await asyncio.sleep(2)
                
                # Take screenshot of result page
                await self.page.screenshot(path=f"{self.download_path}/after_click.png")
                
                return {
                    "success": False, 
                    "error": "Fatura pode ter aberto em nova aba. Verifique screenshot.",
                    "screenshot": f"{self.download_path}/after_click.png"
                }
            
        except PlaywrightTimeout:
            return {"success": False, "error": "Timeout ao baixar a fatura"}
        except Exception as e:
            logger.error(f"Error downloading invoice: {str(e)}")
            return {"success": False, "error": f"Erro ao baixar fatura: {str(e)}"}
            return {"success": False, "error": f"Erro ao baixar fatura: {str(e)}"}
    
    async def close(self):
        """Clean up resources"""
        await self._close_browser()


async def test_copel_login(cpf_cnpj: str, password: str) -> Dict[str, Any]:
    """
    Test COPEL login credentials
    
    Args:
        cpf_cnpj: CPF or CNPJ
        password: Portal password
        
    Returns:
        Test result
    """
    service = CopelService()
    try:
        result = await service.login(cpf_cnpj, password)
        return result
    finally:
        await service.close()


async def download_copel_invoice(cpf_cnpj: str, password: str, uc_number: Optional[str] = None) -> Dict[str, Any]:
    """
    Login and download invoice from COPEL
    
    Args:
        cpf_cnpj: CPF or CNPJ
        password: Portal password
        uc_number: Consumer unit number
        
    Returns:
        Download result
    """
    service = CopelService()
    try:
        login_result = await service.login(cpf_cnpj, password)
        if not login_result.get('success'):
            return login_result
        
        download_result = await service.download_invoice(uc_number)
        return download_result
    finally:
        await service.close()
