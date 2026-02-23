"""
Growatt OSS Portal Integration Service
Uses Playwright for web scraping the OSS portal to fetch plant data

NOTE: Playwright is imported lazily to allow the app to start without it installed.
The automation features will only work when playwright is available.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any, TYPE_CHECKING

# Lazy import for playwright - will be imported when actually needed
if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

# Flag to track if playwright is available
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright not available. Growatt automation features will be disabled.")
    async_playwright = None


class GrowattOSSService:
    """Service class for Growatt OSS portal integration using web scraping"""
    
    def __init__(self):
        self.browser: Optional["Browser"] = None
        self.context: Optional["BrowserContext"] = None
        self.page: Optional["Page"] = None
        self.logged_in = False
        self.plants_cache: List[Dict] = []
        self.cache_time: Optional[datetime] = None
        self.cache_ttl_seconds = 300  # 5 minutes cache
    
    async def _init_browser(self):
        """Initialize browser if not already done"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright não está disponível. A integração Growatt está desativada neste ambiente.")
        
        if self.browser is None:
            playwright = await async_playwright().start()
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
            self.browser = await playwright.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
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
        """Extract plants data from all pages"""
        try:
            logger.info("Fetching plants from Growatt OSS...")
            
            # Wait for the page to fully load with tables
            await self.page.wait_for_timeout(5000)
            
            # Try to wait for table to appear
            try:
                await self.page.wait_for_selector('table tbody tr td', timeout=15000)
            except:
                logger.debug("Table selector not found, proceeding anyway")
            
            all_plants = []
            
            # Function to extract plants from current page view
            async def extract_current_page():
                return await self.page.evaluate('''
                    () => {
                        const rows = document.querySelectorAll('table tbody tr');
                        const plants = [];
                        
                        rows.forEach((row) => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 15) {
                                const num = cells[1]?.innerText?.trim();
                                const name = cells[4]?.innerText?.trim();
                                // Only add if it has a valid number and name
                                if (num && name && !isNaN(parseInt(num))) {
                                    // Try to get plantId from various sources
                                    let plantId = '';
                                    
                                    // Method 1: Look for link with plantId in href
                                    const links = row.querySelectorAll('a');
                                    for (const link of links) {
                                        const href = link.getAttribute('href') || link.href || '';
                                        const match = href.match(/plantId[=:](\d+)/i);
                                        if (match) {
                                            plantId = match[1];
                                            break;
                                        }
                                    }
                                    
                                    // Method 2: Check onclick attributes
                                    if (!plantId) {
                                        const elementsWithOnclick = row.querySelectorAll('[onclick]');
                                        for (const el of elementsWithOnclick) {
                                            const onclick = el.getAttribute('onclick') || '';
                                            const match = onclick.match(/plantId[=:'"\\s]*(\d+)/i);
                                            if (match) {
                                                plantId = match[1];
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // Method 3: Check data attributes
                                    if (!plantId) {
                                        plantId = row.getAttribute('data-plantid') || 
                                                  row.getAttribute('data-id') || 
                                                  cells[0]?.getAttribute('data-plantid') || '';
                                    }
                                    
                                    // Method 4: Try to extract from the plant name link
                                    if (!plantId && cells[4]) {
                                        const nameLink = cells[4].querySelector('a');
                                        if (nameLink) {
                                            const href = nameLink.getAttribute('href') || nameLink.href || '';
                                            // Try various patterns
                                            let match = href.match(/plantId[=:](\d+)/i);
                                            if (!match) match = href.match(/id[=:](\d+)/i);
                                            if (!match) match = href.match(/\/plant\/(\d+)/i);
                                            if (match) plantId = match[1];
                                        }
                                    }
                                    
                                    plants.push({
                                        number: num,
                                        plantId: plantId,  // Real Growatt plantId
                                        group: cells[2]?.innerText?.trim() || '',
                                        status: cells[3]?.innerText?.trim() || '',
                                        plantName: name,
                                        alias: cells[5]?.innerText?.trim() || '',
                                        userName: cells[6]?.innerText?.trim() || '',
                                        city: cells[7]?.innerText?.trim() || '',
                                        revenue: cells[8]?.innerText?.trim() || '',
                                        timezone: cells[9]?.innerText?.trim() || '',
                                        installDate: cells[10]?.innerText?.trim() || '',
                                        deviceCount: cells[11]?.innerText?.trim() || '',
                                        pvPower: cells[12]?.innerText?.trim() || '',
                                        dailyGen: cells[13]?.innerText?.trim() || '',
                                        fullHours: cells[14]?.innerText?.trim() || '',
                                        totalGen: cells[15]?.innerText?.trim() || ''
                                    });
                                }
                            }
                        });
                        
                        return plants;
                    }
                ''')
            
            # Extract page 1
            page1_plants = await extract_current_page()
            all_plants.extend(page1_plants)
            logger.info(f"Page 1: {len(page1_plants)} plants")
            
            # Click through pages 2, 3, 4, etc.
            existing_nums = {p['number'] for p in all_plants}
            
            for page_num in range(2, 15):  # Support up to 14 pages (200+ plants)
                try:
                    # Find and click page number link
                    page_link = self.page.locator(f'a:has-text("{page_num}")').first
                    
                    if await page_link.count() > 0:
                        # Check if this looks like a pagination link
                        link_text = await page_link.text_content()
                        if link_text and link_text.strip() == str(page_num):
                            await page_link.click()
                            await self.page.wait_for_timeout(3000)
                            
                            page_plants = await extract_current_page()
                            
                            # Filter out duplicates
                            new_plants = [p for p in page_plants if p['number'] not in existing_nums]
                            
                            if new_plants:
                                all_plants.extend(new_plants)
                                existing_nums.update(p['number'] for p in new_plants)
                                logger.info(f"Page {page_num}: +{len(new_plants)} plants")
                            else:
                                logger.info(f"Page {page_num}: No new plants, stopping pagination")
                                break
                    else:
                        break
                except Exception as e:
                    logger.debug(f"Pagination ended at page {page_num}: {e}")
                    break
            
            # Parse and normalize all plant data
            if all_plants:
                plants = []
                for idx, p in enumerate(all_plants):
                    if p.get('plantName'):
                        # Log first plant's data
                        if idx == 0:
                            logger.info(f"First plant fields: {list(p.keys())}")
                            logger.info(f"First plant plantId: {p.get('plantId')}")
                        
                        pv_power = p.get('pvPower', '0')
                        pv_power_kwp = float(pv_power.replace('kWp', '').replace(',', '.').strip() or 0)
                        
                        daily_gen = p.get('dailyGen', '0')
                        daily_gen_kwh = float(daily_gen.replace('kWh', '').replace(',', '.').strip() or 0)
                        
                        total_gen = p.get('totalGen', '0')
                        total_gen_kwh = float(total_gen.replace('kWh', '').replace(',', '.').strip() or 0)
                        
                        status = p.get('status', '').lower()
                        normalized_status = "online" if status == 'online' else ("abnormal" if status == 'abnormal' else "offline")
                        
                        # Use the plantId from the link if available, otherwise use number
                        real_plant_id = p.get('plantId') or p.get('number', '')
                        
                        plants.append({
                            "id": p.get('number', ''),
                            "plant_id": str(real_plant_id),  # Real Growatt plantId for API calls
                            "name": p.get('plantName', ''),
                            "alias": p.get('alias', ''),
                            "username": p.get('userName', ''),
                            "group": p.get('group', ''),
                            "city": p.get('city', ''),
                            "status": normalized_status,
                            "capacity_kwp": pv_power_kwp,
                            "today_energy_kwh": daily_gen_kwh,
                            "total_energy_kwh": total_gen_kwh,
                            "full_hours": float(p.get('fullHours', '0').replace(',', '.').replace('h', '').strip() or 0),
                            "device_count": int(p.get('deviceCount', '0') or 0),
                            "installation_date": p.get('installDate', ''),
                            "timezone": p.get('timezone', ''),
                            "revenue": p.get('revenue', ''),
                        })
                
                self.plants_cache = plants
                self.cache_time = datetime.now(timezone.utc)
                logger.info(f"Total: {len(plants)} plants extracted from Growatt OSS")
                
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
    
    async def get_plant_id_by_navigation(self, plant_name: str) -> Optional[str]:
        """
        Get the Growatt plantId by navigating to the plant page.
        This is a more reliable method when the plantId is not available in the table.
        
        Args:
            plant_name: Name of the plant to navigate to
            
        Returns:
            The plantId as a string, or None if not found
        """
        if not self.logged_in or not self.page:
            return None
        
        try:
            # Ensure we're on the plant list page
            current_url = self.page.url
            if '/index' not in current_url:
                await self.page.goto('https://server.growatt.com/index')
                await self.page.wait_for_selector('table', timeout=15000)
            
            # Find the plant by name in the table and click on it
            plant_link = self.page.locator(f'a:has-text("{plant_name}")').first
            
            if await plant_link.count() == 0:
                # Try partial match
                plant_rows = await self.page.locator('table tbody tr').all()
                for row in plant_rows:
                    row_text = await row.text_content()
                    if plant_name.lower() in row_text.lower():
                        links = row.locator('a')
                        if await links.count() > 0:
                            plant_link = links.first
                            break
            
            if await plant_link.count() > 0:
                # Click on the plant link
                await plant_link.click()
                await self.page.wait_for_timeout(3000)
                
                # Extract plantId from URL
                new_url = self.page.url
                
                # Try to extract plantId from URL parameters
                import re
                match = re.search(r'plantId[=:](\d+)', new_url)
                if match:
                    plant_id = match.group(1)
                    logger.info(f"Found plantId {plant_id} for '{plant_name}' from URL")
                    
                    # Navigate back to the list
                    await self.page.goto('https://server.growatt.com/index')
                    await self.page.wait_for_selector('table', timeout=10000)
                    
                    return plant_id
                
                # If not in URL, try to extract from page content
                plant_id = await self.page.evaluate('''
                    () => {
                        // Look for plantId in various places
                        const scripts = document.querySelectorAll('script');
                        for (const script of scripts) {
                            const text = script.textContent || '';
                            const match = text.match(/plantId['":\\s]*['"](\\d+)['"]/i);
                            if (match) return match[1];
                        }
                        
                        // Check in hidden inputs
                        const hiddenInputs = document.querySelectorAll('input[type="hidden"]');
                        for (const input of hiddenInputs) {
                            if (input.name?.toLowerCase().includes('plantid')) {
                                return input.value;
                            }
                        }
                        
                        // Check data attributes
                        const elementsWithData = document.querySelectorAll('[data-plantid], [data-id]');
                        for (const el of elementsWithData) {
                            const id = el.getAttribute('data-plantid') || el.getAttribute('data-id');
                            if (id && /^\\d+$/.test(id)) return id;
                        }
                        
                        return null;
                    }
                ''')
                
                if plant_id:
                    logger.info(f"Found plantId {plant_id} for '{plant_name}' from page content")
                    # Navigate back
                    await self.page.goto('https://server.growatt.com/index')
                    await self.page.wait_for_selector('table', timeout=10000)
                    return plant_id
                
                # Navigate back even if we didn't find the ID
                await self.page.goto('https://server.growatt.com/index')
                await self.page.wait_for_selector('table', timeout=10000)
            
            logger.warning(f"Could not find plantId for '{plant_name}'")
            return None
            
        except Exception as e:
            logger.error(f"Error getting plantId by navigation: {e}")
            return None

    async def sync_plant_energy_data(self, plant_name: str) -> Dict[str, Any]:
        """Get the latest energy data for a plant."""
        plant = await self.get_plant_details(plant_name)
        if not plant:
            return {"success": False, "error": f"Usina '{plant_name}' nao encontrada"}
        
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

    async def get_plant_hourly_data(self, plant_name: str, date: str) -> Dict[str, Any]:
        """Get hourly power data for a plant on a specific date by navigating the OSS portal."""
        if not self.logged_in or not self.page:
            return {"success": False, "error": "Nao logado"}
        try:
            # Find the plant and get its ID
            plants = await self.get_plants()
            plant = None
            for p in plants:
                if p.get('name','').lower() == plant_name.lower() or plant_name.lower() in p.get('name','').lower():
                    plant = p
                    break
            if not plant:
                return {"success": False, "error": f"Usina '{plant_name}' nao encontrada"}

            plant_id = plant.get('id', '')
            # Use the Growatt OSS API directly via page context
            # The OSS portal has an internal API at /panel/plant/getPlantData
            data = await self.page.evaluate(f'''
                async () => {{
                    try {{
                        const res = await fetch('/energy/compare/getPlantCompareData', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                            body: 'plantId={plant_id}&type=0&date={date}'
                        }});
                        return await res.json();
                    }} catch(e) {{
                        return {{error: e.toString()}};
                    }}
                }}
            ''')

            # Also try the plant detail API
            detail_data = await self.page.evaluate(f'''
                async () => {{
                    try {{
                        const res = await fetch('/panel/plant/getPlantData', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                            body: 'plantId={plant_id}&type=1&date={date}'
                        }});
                        return await res.json();
                    }} catch(e) {{
                        return {{error: e.toString()}};
                    }}
                }}
            ''')

            return {
                "success": True,
                "plant_name": plant.get('name'),
                "date": date,
                "compare_data": data,
                "detail_data": detail_data,
            }
        except Exception as e:
            logger.error(f"Growatt hourly data error: {e}")
            return {"success": False, "error": str(e)}

    async def get_plant_daily_data_range(self, plant_name: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get daily generation data for a date range from Growatt OSS by navigating to the plant page."""
        if not self.logged_in or not self.page:
            logger.info("Not logged in, returning error")
            return {"success": False, "error": "Nao logado"}
        try:
            logger.info(f"Starting get_plant_daily_data_range for '{plant_name}'")
            
            # Use the already loaded plants data to find the plant ID
            # This is more reliable than scraping the HTML again
            plants = await self.get_plants()
            target_plant = None
            
            for p in plants:
                if plant_name.lower() in p.get('name', '').lower():
                    target_plant = p
                    logger.info(f"Found plant in cache: {p.get('name')} - ID: {p.get('id')}")
                    break
            
            if not target_plant:
                logger.error(f"Plant '{plant_name}' not found in plant cache")
                return {"success": False, "error": f"Usina '{plant_name}' nao encontrada"}
            
            # The plant ID from get_plants() is the row number (1, 2, 3...)
            # We need to navigate to the plant page to get the real plantId
            plant_row_number = target_plant.get('id', '')
            
            # Navigate to plant list page
            await self.page.goto('https://server.growatt.com/plant.html', wait_until='networkidle')
            await self.page.wait_for_timeout(3000)
            
            # Click on the plant row using the plant name text
            logger.info(f"Looking for plant link with name containing '{plant_name}'...")
            
            # Use a more robust method - click on the anchor that contains the plant name
            clicked = await self.page.evaluate(f'''
                () => {{
                    // Get all links in the page
                    const links = document.querySelectorAll('a');
                    for (let link of links) {{
                        // Check if link text contains the plant name (case insensitive)
                        if (link.innerText && link.innerText.toLowerCase().includes('{plant_name.lower()}')) {{
                            const href = link.href;
                            if (href && href.includes('plantId=')) {{
                                // Extract plantId
                                const match = href.match(/plantId=(\d+)/);
                                if (match) {{
                                    return {{
                                        plantId: match[1],
                                        href: href,
                                        text: link.innerText
                                    }};
                                }}
                            }}
                        }}
                    }}
                    return null;
                }}
            ''')
            
            if not clicked:
                logger.error(f"Could not find link for plant '{plant_name}'")
                # Debug: List all links
                all_links = await self.page.evaluate('''
                    () => {
                        const links = document.querySelectorAll('a[href*="plantId"]');
                        return Array.from(links).slice(0, 10).map(l => ({
                            href: l.href,
                            text: l.innerText.substring(0, 50)
                        }));
                    }
                ''')
                logger.info(f"Available plant links: {all_links}")
                return {"success": False, "error": f"Usina '{plant_name}' nao encontrada no portal"}
            
            real_plant_id = clicked.get('plantId')
            logger.info(f"Found plant: {clicked}")
            
            # Navigate to the plant detail page
            await self.page.goto(clicked.get('href'), wait_until='networkidle')
            await self.page.wait_for_timeout(3000)
            
            # Parse the year-month from start_date
            month_str = start_date[:7]  # YYYY-MM
            logger.info(f"Fetching data for plantId={real_plant_id}, month={month_str}")

            # Now make the API call from the plant detail page context
            data = await self.page.evaluate(f'''
                async () => {{
                    try {{
                        const res = await fetch('/panel/plant/getPlantData', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'X-Requested-With': 'XMLHttpRequest'
                            }},
                            body: 'plantId={real_plant_id}&type=2&date={month_str}'
                        }});
                        const text = await res.text();
                        try {{
                            return JSON.parse(text);
                        }} catch(e) {{
                            return {{error: 'Parse error', raw: text.substring(0, 500)}};
                        }}
                    }} catch(e) {{
                        return {{error: e.toString()}};
                    }}
                }}
            ''')
            
            logger.info(f"Growatt API response: {str(data)[:500]}")
            
            # Go back to plant list
            await self.page.goto('https://server.growatt.com/plant.html', wait_until='networkidle')
            await self.page.wait_for_timeout(2000)

            return {
                "success": True,
                "plant_name": plant_name,
                "plant_id": real_plant_id,
                "start_date": start_date,
                "end_date": end_date,
                "data": data,
            }
        except Exception as e:
            logger.error(f"Growatt daily range error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        """Navigate to plant details and extract monthly generation history."""
        if not self.logged_in or not self.page:
            return {"success": False, "error": "Nao logado"}

        try:
            # Find the plant in the list and click on it
            rows = await self.page.query_selector_all('table tbody tr')
            plant_found = False
            for row in rows:
                text = await row.inner_text()
                if plant_name.lower() in text.lower():
                    link = await row.query_selector('a')
                    if link:
                        await link.click()
                        await self.page.wait_for_timeout(5000)
                        plant_found = True
                        break

            if not plant_found:
                return {"success": False, "error": f"Usina '{plant_name}' nao encontrada na tabela"}

            # Extract monthly data from the plant detail page
            # Try to get the energy history table
            monthly_data = await self.page.evaluate('''
                () => {
                    const data = [];
                    // Look for the energy statistics table
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const rows = table.querySelectorAll('tr');
                        for (const row of rows) {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 2) {
                                const date = cells[0]?.innerText?.trim();
                                const energy = cells[1]?.innerText?.trim();
                                if (date && energy && /\\d{4}-\\d{2}/.test(date)) {
                                    data.push({date, energy});
                                }
                            }
                        }
                    }
                    return data;
                }
            ''')

            # Go back to plant list
            await self.page.go_back()
            await self.page.wait_for_timeout(3000)

            return {
                "success": True,
                "monthly_data": monthly_data,
                "plant_name": plant_name,
            }
        except Exception as e:
            logger.error(f"Error syncing history for {plant_name}: {e}")
            return {"success": False, "error": str(e)}


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
