"""
Growatt OSS Portal Integration Service
Uses Playwright for web scraping the OSS portal to fetch plant data
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class GrowattOSSService:
    """Service class for Growatt OSS portal integration using web scraping"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.logged_in = False
        self.plants_cache: List[Dict] = []
        self.cache_time: Optional[datetime] = None
        self.cache_ttl_seconds = 300  # 5 minutes cache
    
    async def _init_browser(self):
        """Initialize browser if not already done"""
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
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
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Login to Growatt OSS portal
        
        Args:
            username: Growatt account username
            password: Growatt account password
            
        Returns:
            Login result with success status
        """
        try:
            await self._init_browser()
            
            logger.info(f"Attempting Growatt OSS login for user: {username}")
            
            # Navigate to login page
            await self.page.goto("https://oss.growatt.com/login", wait_until="networkidle", timeout=30000)
            await self.page.wait_for_timeout(2000)
            
            # Close region modal if present
            try:
                confirm_btn = self.page.locator('#fenquLayer .fenquLayerBtn:has-text("Confirm")')
                if await confirm_btn.is_visible():
                    await confirm_btn.click(force=True, timeout=3000)
                    await self.page.wait_for_timeout(500)
            except:
                pass
            
            # Accept terms if present
            try:
                agree_btn = self.page.locator('#agree')
                if await agree_btn.is_visible():
                    await agree_btn.click(force=True, timeout=3000)
                    await self.page.wait_for_timeout(500)
            except:
                pass
            
            # Fill credentials
            await self.page.locator('#userName-id').fill(username)
            await self.page.locator('#passWd-id').fill(password)
            
            # Submit login
            await self.page.locator('#passWd-id').press('Enter')
            await self.page.wait_for_timeout(8000)  # Wait longer for page to fully load
            
            # Check if login was successful
            if 'index' in self.page.url:
                self.logged_in = True
                logger.info("Growatt OSS login successful")
                
                # Immediately extract plants from the loaded page
                await self._extract_plants_from_page()
                
                return {
                    "success": True,
                    "message": "Login realizado com sucesso",
                    "url": self.page.url
                }
            else:
                logger.error(f"Growatt OSS login failed. URL: {self.page.url}")
                return {
                    "success": False,
                    "error": "Login falhou. Verifique as credenciais."
                }
                
        except Exception as e:
            logger.error(f"Growatt OSS login error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _extract_plants_from_page(self) -> None:
        """Extract plants data from the current page"""
        try:
            logger.info("Fetching plants from Growatt OSS...")
            
            # Wait for the page to fully load with tables
            await self.page.wait_for_timeout(5000)
            
            # Try to wait for table to appear
            try:
                await self.page.wait_for_selector('table tbody tr', timeout=10000)
            except:
                logger.debug("Table selector not found, proceeding anyway")
            
            frames = self.page.frames
            logger.info(f"Found {len(frames)} frames to check")
            
            for frame in frames:
                try:
                    tr_count = await frame.evaluate('() => document.querySelectorAll("table tr").length')
                    
                    if tr_count > 5:
                        raw_data = await frame.evaluate('''
                            () => {
                                const rows = document.querySelectorAll('table tbody tr');
                                const plants = [];
                                
                                rows.forEach((row) => {
                                    const cells = row.querySelectorAll('td');
                                    if (cells.length >= 10) {
                                        plants.push({
                                            number: cells[0]?.innerText?.trim() || '',
                                            group: cells[1]?.innerText?.trim() || '',
                                            status: cells[2]?.innerText?.trim() || '',
                                            plantName: cells[3]?.innerText?.trim() || '',
                                            alias: cells[4]?.innerText?.trim() || '',
                                            userName: cells[5]?.innerText?.trim() || '',
                                            city: cells[6]?.innerText?.trim() || '',
                                            revenue: cells[7]?.innerText?.trim() || '',
                                            timezone: cells[8]?.innerText?.trim() || '',
                                            installDate: cells[9]?.innerText?.trim() || '',
                                            deviceCount: cells[10]?.innerText?.trim() || '',
                                            pvPower: cells[11]?.innerText?.trim() || '',
                                            dailyGen: cells[12]?.innerText?.trim() || '',
                                            fullHours: cells[13]?.innerText?.trim() || '',
                                            totalGen: cells[14]?.innerText?.trim() || ''
                                        });
                                    }
                                });
                                
                                return plants;
                            }
                        ''')
                        
                        if raw_data:
                            plants = []
                            for p in raw_data:
                                if p.get('plantName'):
                                    pv_power = p.get('pvPower', '0')
                                    pv_power_kwp = float(pv_power.replace('kWp', '').replace(',', '.').strip() or 0)
                                    
                                    daily_gen = p.get('dailyGen', '0')
                                    daily_gen_kwh = float(daily_gen.replace('kWh', '').replace(',', '.').strip() or 0)
                                    
                                    total_gen = p.get('totalGen', '0')
                                    total_gen_kwh = float(total_gen.replace('kWh', '').replace(',', '.').strip() or 0)
                                    
                                    plants.append({
                                        "id": p.get('number', ''),
                                        "name": p.get('plantName', ''),
                                        "alias": p.get('alias', ''),
                                        "username": p.get('userName', ''),
                                        "group": p.get('group', ''),
                                        "city": p.get('city', ''),
                                        "status": "online" if p.get('status', '').lower() == 'online' else "offline",
                                        "capacity_kwp": pv_power_kwp,
                                        "today_energy_kwh": daily_gen_kwh,
                                        "total_energy_kwh": total_gen_kwh,
                                        "full_hours": float(p.get('fullHours', '0').replace(',', '.') or 0),
                                        "device_count": int(p.get('deviceCount', '0') or 0),
                                        "installation_date": p.get('installDate', ''),
                                        "timezone": p.get('timezone', ''),
                                        "revenue": p.get('revenue', ''),
                                    })
                            
                            self.plants_cache = plants
                            self.cache_time = datetime.now(timezone.utc)
                            logger.info(f"Extracted {len(plants)} plants from page")
                            return
                            
                except Exception as e:
                    logger.debug(f"Frame extraction error: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting plants from page: {e}")
    
    async def get_plants(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get list of all plants from Growatt OSS
        
        Args:
            force_refresh: Force refresh from server even if cache is valid
            
        Returns:
            List of plant information dictionaries
        """
        if not self.logged_in:
            return []
        
        # Check cache
        if not force_refresh and self.plants_cache and self.cache_time:
            cache_age = (datetime.now(timezone.utc) - self.cache_time).total_seconds()
            if cache_age < self.cache_ttl_seconds:
                logger.info(f"Returning cached plants ({len(self.plants_cache)} plants)")
                return self.plants_cache
        
        # Force refresh by re-extracting from page
        try:
            await self._extract_plants_from_page()
            return self.plants_cache
        except Exception as e:
            logger.error(f"Error refreshing plants: {e}")
            return self.plants_cache  # Return cached data if available
    
    async def get_plant_details(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific plant by name
        
        Args:
            plant_name: Name of the plant
            
        Returns:
            Plant details or None
        """
        plants = await self.get_plants()
        
        for plant in plants:
            if plant.get('name', '').lower() == plant_name.lower() or \
               plant.get('alias', '').lower() == plant_name.lower():
                return plant
        
        return None
    
    async def sync_plant_energy_data(self, plant_name: str) -> Dict[str, Any]:
        """
        Get the latest energy data for a plant
        
        Args:
            plant_name: Name of the plant to sync
            
        Returns:
            Sync result with energy data
        """
        plant = await self.get_plant_details(plant_name)
        
        if not plant:
            return {
                "success": False,
                "error": f"Usina '{plant_name}' não encontrada"
            }
        
        return {
            "success": True,
            "plant_name": plant.get('name'),
            "data": {
                "date": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                "generation_kwh": plant.get('today_energy_kwh', 0),
                "capacity_kwp": plant.get('capacity_kwp', 0),
                "status": plant.get('status'),
                "full_hours": plant.get('full_hours', 0),
            }
        }


# Singleton instance
_growatt_oss_service: Optional[GrowattOSSService] = None


def get_growatt_oss_service() -> GrowattOSSService:
    """Get or create the Growatt OSS service singleton"""
    global _growatt_oss_service
    if _growatt_oss_service is None:
        _growatt_oss_service = GrowattOSSService()
    return _growatt_oss_service


async def reset_growatt_oss_service():
    """Reset the service and close browser"""
    global _growatt_oss_service
    if _growatt_oss_service:
        await _growatt_oss_service.close()
        _growatt_oss_service = None
