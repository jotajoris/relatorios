"""
COPEL Portal Automation Service
Uses Playwright to automate login and invoice download from COPEL customer portal
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# COPEL Portal URLs
COPEL_LOGIN_URL = "https://www.copel.com/avaweb/paginaLogin/login.jsf"
COPEL_BASE_URL = "https://www.copel.com/avaweb"

# Set Playwright browsers path
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'


class CopelService:
    """Service class for COPEL portal automation"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
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
            
            # Try to find login form fields
            # The COPEL portal uses JSF, so field IDs might vary
            
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
            
            # Check for error messages
            error_indicators = ['erro', 'inválid', 'incorret', 'falha', 'error']
            for indicator in error_indicators:
                if indicator.lower() in page_content.lower():
                    # Check if it's an actual error message (not just page text)
                    error_elements = await self.page.query_selector_all('[class*="error"], [class*="alert"], .mensagem-erro')
                    for elem in error_elements:
                        error_text = await elem.text_content()
                        if error_text and len(error_text.strip()) > 0:
                            return {"success": False, "error": f"Erro de login: {error_text.strip()}"}
            
            # Check if we're on a different page (logged in)
            if 'login' not in current_url.lower() or 'home' in current_url.lower() or 'dashboard' in current_url.lower():
                self.logged_in = True
                logger.info("COPEL login successful")
                return {
                    "success": True,
                    "message": "Login realizado com sucesso",
                    "url": current_url
                }
            
            # Check for successful login indicators in page content
            success_indicators = ['bem-vindo', 'faturas', 'unidades', 'consumo', 'histórico']
            for indicator in success_indicators:
                if indicator.lower() in page_content.lower():
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
            # Find the row with this UC number
            rows = await self.page.query_selector_all('table tbody tr')
            
            for row in rows:
                cells = await row.query_selector_all('td')
                if cells:
                    first_cell_text = await cells[0].text_content()
                    if first_cell_text and uc_number in first_cell_text:
                        # Find and click the select button/link in this row
                        select_btn = await row.query_selector('a, button, [onclick]')
                        if select_btn:
                            await select_btn.click()
                            await asyncio.sleep(3)
                            
                            logger.info(f"Selected UC: {uc_number}")
                            return {
                                "success": True,
                                "uc_number": uc_number,
                                "url": self.page.url
                            }
            
            return {"success": False, "error": f"UC {uc_number} não encontrada"}
            
        except Exception as e:
            logger.error(f"Error selecting UC: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def download_invoice(self, uc_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Download the latest invoice PDF for a consumer unit
        
        Args:
            uc_number: Consumer unit number (optional if only one UC)
            
        Returns:
            Download result with file path
        """
        if not self.logged_in or not self.page:
            return {"success": False, "error": "Não está logado no portal COPEL"}
        
        try:
            # Navigate to invoices page
            invoice_links = [
                'a:has-text("Fatura")',
                'a:has-text("Segunda Via")',
                'a:has-text("Conta")',
                '[href*="fatura"]',
                '[href*="conta"]'
            ]
            
            for selector in invoice_links:
                try:
                    link = await self.page.wait_for_selector(selector, timeout=5000)
                    if link:
                        await link.click()
                        await asyncio.sleep(3)
                        break
                except:
                    continue
            
            # Look for PDF download button/link
            pdf_selectors = [
                'a:has-text("PDF")',
                'a:has-text("Download")',
                'a:has-text("Baixar")',
                '[href*=".pdf"]',
                'button:has-text("Baixar")'
            ]
            
            async with self.page.expect_download(timeout=30000) as download_info:
                for selector in pdf_selectors:
                    try:
                        btn = await self.page.wait_for_selector(selector, timeout=3000)
                        if btn:
                            await btn.click()
                            break
                    except:
                        continue
                
            download = await download_info.value
            
            # Save the file
            filename = f"fatura_copel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.download_path, filename)
            await download.save_as(filepath)
            
            logger.info(f"COPEL invoice downloaded: {filepath}")
            
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename
            }
            
        except PlaywrightTimeout:
            return {"success": False, "error": "Timeout ao baixar a fatura"}
        except Exception as e:
            logger.error(f"Error downloading invoice: {str(e)}")
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
