"""
Solarman Portal Integration Service
Uses Playwright for web scraping the Solarman portal to fetch plant data
Works with Deye, Sofar, and other inverters using Solarman loggers

NOTE: Playwright is imported lazily to allow the app to start without it installed.
"""

import asyncio
import logging
import os
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright not available. Solarman automation features will be disabled.")
    async_playwright = None


class SolarmanService:
    """Service class for Solarman portal integration using web scraping"""
    
    # Server URLs
    SERVERS = {
        'internacional': 'https://home.solarmanpv.com',
        'china': 'https://home.solarman.cn',
        'business': 'https://pro.solarmanpv.com',
    }
    
    def __init__(self):
        self.browser: Optional["Browser"] = None
        self.context: Optional["BrowserContext"] = None
        self.page: Optional["Page"] = None
        self.logged_in = False
        self.plants_cache: List[Dict] = []
        self.cache_time: Optional[datetime] = None
        self.cache_ttl_seconds = 300  # 5 minutes cache
        self.current_server = 'internacional'
    
    async def _init_browser(self):
        """Initialize browser if not already done"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright não está disponível. A integração Solarman está desativada neste ambiente.")
        
        if self.browser is None:
            playwright = await async_playwright().start()
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
            self.browser = await playwright.chromium.launch(
                headless=True, 
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = await self.context.new_page()
    
    async def close(self):
        """Close browser and cleanup resources"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            self.logged_in = False
    
    async def login(self, email: str, password: str, server: str = 'internacional', group: str = None) -> Dict[str, Any]:
        """
        Login to Solarman portal
        
        Args:
            email: Solarman account email
            password: Solarman account password
            server: Server type ('internacional', 'china', 'business')
            group: Organization/group name (optional)
            
        Returns:
            Login result with success status and plants list
        """
        try:
            await self._init_browser()
            
            self.current_server = server.lower()
            base_url = self.SERVERS.get(self.current_server, self.SERVERS['internacional'])
            
            logger.info(f"Attempting Solarman login for user: {email} on server: {server}")
            
            # Navigate to login page
            login_url = f"{base_url}/login" if 'home' in base_url else base_url
            await self.page.goto(login_url, wait_until="networkidle", timeout=30000)
            await self.page.wait_for_timeout(3000)
            
            # Accept cookie banner if present
            try:
                accept_cookies_selectors = [
                    'button:has-text("Accept All")',
                    'button:has-text("Accept")',
                    'button:has-text("Aceitar")',
                    '.cookie-accept',
                    '#accept-cookies',
                ]
                for sel in accept_cookies_selectors:
                    try:
                        btn = self.page.locator(sel).first
                        if await btn.is_visible(timeout=2000):
                            await btn.click()
                            logger.info(f"Accepted cookies with: {sel}")
                            await self.page.wait_for_timeout(1000)
                            break
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Cookie acceptance failed: {e}")
            
            # Handle country/region selection modal if present
            try:
                region_modal = self.page.locator('text=Please enter/select your country/region')
                if await region_modal.is_visible(timeout=2000):
                    logger.info("Country/region modal detected")
                    
                    # Click on the dropdown to open it
                    dropdown = self.page.locator('text=Please enter/select your country/region').locator('..').locator('input, select, [role="combobox"]')
                    if not await dropdown.is_visible(timeout=1000):
                        # Try clicking on the dropdown area
                        dropdown_area = self.page.locator('.ant-select, [class*="select"], [class*="dropdown"]').first
                        if await dropdown_area.is_visible(timeout=1000):
                            await dropdown_area.click()
                            await self.page.wait_for_timeout(500)
                    
                    # Type Brazil to filter
                    await self.page.keyboard.type("Brazil")
                    await self.page.wait_for_timeout(500)
                    
                    # Select Brazil option
                    brazil_option = self.page.locator('text=Brazil').first
                    if await brazil_option.is_visible(timeout=2000):
                        await brazil_option.click()
                        logger.info("Selected Brazil")
                        await self.page.wait_for_timeout(500)
                    
                    # Click Confirm button
                    confirm_btn = self.page.locator('button:has-text("Confirm")').first
                    if await confirm_btn.is_visible(timeout=2000):
                        await confirm_btn.click()
                        logger.info("Clicked Confirm on region modal")
                        await self.page.wait_for_timeout(1000)
            except Exception as e:
                logger.debug(f"Region modal handling: {e}")
            
            # Take screenshot for debugging
            try:
                await self.page.screenshot(path="/tmp/solarman_login_page.png")
                logger.info("Screenshot saved to /tmp/solarman_login_page.png")
            except Exception:
                pass
            
            # Wait for page to be fully loaded
            await self.page.wait_for_load_state("domcontentloaded")
            
            # Try multiple approaches to find and fill login form
            login_success = False
            
            # Approach 1: Standard input by type
            try:
                # Find email/username input
                email_inputs = await self.page.locator('input[type="email"], input[type="text"]').all()
                password_inputs = await self.page.locator('input[type="password"]').all()
                
                if email_inputs and password_inputs:
                    # Fill the first visible text/email input
                    for inp in email_inputs:
                        if await inp.is_visible():
                            await inp.fill(email)
                            logger.info("Filled email field")
                            break
                    
                    # Fill the first visible password input
                    for inp in password_inputs:
                        if await inp.is_visible():
                            await inp.fill(password)
                            logger.info("Filled password field")
                            break
                    
                    # Look for login button - specific selectors for Solarman
                    login_btn_selectors = [
                        'button:has-text("Log In")',
                        'button:has-text("Log in")',
                        'button:has-text("LOGIN")',
                        'button:has-text("Login")',
                        'button:has-text("登录")',
                        'button:has-text("Sign in")',
                        'button[type="submit"]',
                        '.login-btn',
                        '#loginBtn',
                        'input[type="submit"]',
                    ]
                    
                    for sel in login_btn_selectors:
                        try:
                            btn = self.page.locator(sel).first
                            if await btn.is_visible(timeout=2000):
                                # Wait a bit for form validation
                                await self.page.wait_for_timeout(500)
                                await btn.click(force=True)
                                login_success = True
                                logger.info(f"Clicked login button: {sel}")
                                break
                        except Exception:
                            continue
                    
                    if not login_success:
                        # Try pressing Enter on password field
                        for inp in password_inputs:
                            if await inp.is_visible():
                                await inp.press('Enter')
                                login_success = True
                                logger.info("Pressed Enter on password field")
                                break
            except Exception as e:
                logger.debug(f"Approach 1 failed: {e}")
            
            # Wait for login to process
            await self.page.wait_for_timeout(8000)
            
            # Take screenshot after login attempt
            try:
                await self.page.screenshot(path="/tmp/solarman_after_login.png")
                logger.info("Screenshot saved to /tmp/solarman_after_login.png")
            except Exception:
                pass
            
            # Check if login was successful
            current_url = self.page.url
            logger.info(f"Current URL after login: {current_url}")
            
            # Check for success indicators
            success_indicators = ['main', 'index', 'dashboard', 'plant', 'station', 'overview', 'home']
            is_success = any(ind in current_url.lower() for ind in success_indicators) and 'login' not in current_url.lower()
            
            if is_success:
                self.logged_in = True
                logger.info("Solarman login successful")
                
                # Wait for dashboard to load
                await self.page.wait_for_timeout(3000)
                
                # Extract plants from the dashboard
                plants = await self._extract_plants()
                
                return {
                    "success": True,
                    "message": "Login realizado com sucesso",
                    "url": current_url,
                    "plants": plants,
                    "total": len(plants)
                }
            else:
                logger.error(f"Solarman login failed. URL: {current_url}")
                return {
                    "success": False,
                    "error": "Login falhou. Verifique as credenciais ou tente novamente."
                }
                
        except Exception as e:
            logger.error(f"Solarman login error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _extract_plants(self) -> List[Dict]:
        """Extract plants data from the dashboard"""
        plants = []
        
        try:
            await self.page.wait_for_timeout(3000)
            
            # Try different approaches to extract plant data
            # Approach 1: Look for plant cards/tiles
            plant_cards = await self.page.locator('.plant-card, .station-card, .device-card, [class*="plant"], [class*="station"]').all()
            
            if plant_cards:
                for i, card in enumerate(plant_cards):
                    try:
                        # Extract text content from the card
                        text = await card.inner_text()
                        text_lines = [line.strip() for line in text.split('\n') if line.strip()]
                        
                        # Try to parse plant info
                        name = text_lines[0] if text_lines else f"Usina {i+1}"
                        
                        # Try to find capacity
                        capacity = 0
                        for text_line in text_lines:
                            if 'kw' in text_line.lower():
                                import re
                                match = re.search(r'([\d.]+)\s*kw', text_line.lower())
                                if match:
                                    capacity = float(match.group(1))
                                    break
                        
                        plants.append({
                            'id': f"solarman_{i}",
                            'name': name,
                            'capacity_kwp': capacity,
                            'status': 'online',
                            'source': 'solarman'
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing plant card: {e}")
            
            # Approach 2: Look for table rows
            if not plants:
                rows = await self.page.locator('table tbody tr').all()
                for i, row in enumerate(rows):
                    try:
                        cells = await row.locator('td').all()
                        if cells:
                            name = await cells[0].inner_text() if cells else f"Usina {i+1}"
                            plants.append({
                                'id': f"solarman_{i}",
                                'name': name.strip(),
                                'capacity_kwp': 0,
                                'status': 'online',
                                'source': 'solarman'
                            })
                    except Exception:
                        continue
            
            # Approach 3: Look for any list items with plant-like data
            if not plants:
                items = await self.page.locator('li[class*="plant"], li[class*="station"], .list-item').all()
                for i, item in enumerate(items):
                    try:
                        name = await item.inner_text()
                        plants.append({
                            'id': f"solarman_{i}",
                            'name': name.strip().split('\n')[0],
                            'capacity_kwp': 0,
                            'status': 'online',
                            'source': 'solarman'
                        })
                    except Exception:
                        continue
            
            self.plants_cache = plants
            self.cache_time = datetime.now(timezone.utc)
            
            logger.info(f"Extracted {len(plants)} plants from Solarman")
            
        except Exception as e:
            logger.error(f"Error extracting plants: {e}")
        
        return plants
    
    async def get_plants(self) -> List[Dict]:
        """Get list of plants (from cache or fetch new)"""
        if not self.logged_in:
            raise RuntimeError("Não está logado. Faça login primeiro.")
        
        # Check cache
        if self.plants_cache and self.cache_time:
            elapsed = (datetime.now(timezone.utc) - self.cache_time).total_seconds()
            if elapsed < self.cache_ttl_seconds:
                return self.plants_cache
        
        return await self._extract_plants()
    
    async def get_plant_generation(self, plant_id: str, date: str = None) -> Dict[str, Any]:
        """
        Get generation data for a specific plant
        
        Args:
            plant_id: Plant ID
            date: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            Generation data
        """
        if not self.logged_in:
            raise RuntimeError("Não está logado. Faça login primeiro.")
        
        # This would need to navigate to the plant detail page and extract generation data
        # Implementation depends on the actual Solarman portal structure
        
        return {
            "plant_id": plant_id,
            "date": date or datetime.now().strftime('%Y-%m-%d'),
            "generation_kwh": 0,
            "note": "Implementação pendente - necessário analisar estrutura da página"
        }


# Singleton instance
_solarman_service: Optional[SolarmanService] = None


def get_solarman_service() -> SolarmanService:
    """Get or create the singleton Solarman service instance"""
    global _solarman_service
    if _solarman_service is None:
        _solarman_service = SolarmanService()
    return _solarman_service


async def reset_solarman_service():
    """Reset the Solarman service (close browser and create new instance)"""
    global _solarman_service
    if _solarman_service:
        await _solarman_service.close()
    _solarman_service = SolarmanService()
    return _solarman_service
