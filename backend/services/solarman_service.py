"""
Solarman Portal Integration Service
Uses session capture approach - user logs in manually, system captures cookies

Works with Deye, Sofar, and other inverters using Solarman loggers
"""

import asyncio
import logging
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any, TYPE_CHECKING
import aiohttp

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright not available. Solarman features will be disabled.")
    async_playwright = None

# Brazil timezone
try:
    from zoneinfo import ZoneInfo
    BRT = ZoneInfo('America/Sao_Paulo')
except:
    import pytz
    BRT = pytz.timezone('America/Sao_Paulo')


class SolarmanSessionService:
    """
    Service for Solarman integration using manual login + session capture.
    User logs in via browser, system captures and reuses cookies.
    """
    
    PORTAL_URL = "https://pro.solarmanpv.com"
    LOGIN_URL = "https://pro.solarmanpv.com/login"
    API_BASE = "https://pro.solarmanpv.com"
    
    def __init__(self, db=None):
        self.db = db
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None
    
    async def _init_browser(self, headless: bool = False):
        """Initialize browser for login capture"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright não disponível")
        
        if self.browser is None:
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
            )
    
    async def close(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    async def start_login_session(self) -> Dict[str, Any]:
        """
        Start a browser session for manual login.
        Returns session_id to track this login attempt.
        """
        try:
            await self._init_browser(headless=True)
            
            # Create context with stealth settings
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
            )
            
            # Apply stealth if available
            try:
                from playwright_stealth import Stealth
                stealth = Stealth(navigator_webdriver=True, chrome_runtime=True)
                await stealth.apply_stealth_async(self.context)
            except:
                pass
            
            self.page = await self.context.new_page()
            
            # Navigate to login page
            await self.page.goto(self.LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(2000)
            
            # Accept cookies if present
            try:
                await self.page.click('button:has-text("Aceitar Tudo")', timeout=3000)
                await self.page.wait_for_timeout(500)
            except:
                pass
            
            # Handle region modal - select Brazil
            try:
                await self.page.click('.regionBtn', timeout=3000)
                await self.page.wait_for_timeout(500)
                await self.page.keyboard.type('Brazil', delay=50)
                await self.page.wait_for_timeout(500)
                await self.page.click('text=Brazil', timeout=3000)
                await self.page.wait_for_timeout(500)
                
                # Confirm region
                await self.page.evaluate('''() => {
                    const btn = document.querySelector('.ant-modal button.ant-btn-primary');
                    if(btn) { btn.disabled = false; btn.click(); }
                }''')
                await self.page.wait_for_timeout(1000)
            except:
                pass
            
            # Generate session ID
            import uuid
            session_id = str(uuid.uuid4())
            
            # Save session to DB
            if self.db is not None:
                await self.db.solarman_login_sessions.update_one(
                    {'session_id': session_id},
                    {'$set': {
                        'session_id': session_id,
                        'status': 'pending',
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
                    }},
                    upsert=True
                )
            
            return {
                'success': True,
                'session_id': session_id,
                'message': 'Sessão iniciada. Faça login no Solarman.',
                'login_url': self.LOGIN_URL
            }
            
        except Exception as e:
            logger.error(f"Error starting login session: {e}")
            return {'success': False, 'error': str(e)}
    
    async def check_login_status(self, session_id: str) -> Dict[str, Any]:
        """Check if user completed login and capture cookies"""
        try:
            if not self.page:
                return {'success': False, 'error': 'No active session', 'logged_in': False}
            
            current_url = self.page.url
            
            # Check if we're past the login page
            if 'login' not in current_url.lower() or '/main' in current_url.lower() or '/plant' in current_url.lower():
                # User logged in! Capture cookies
                cookies = await self.context.cookies()
                
                # Save cookies to DB
                if self.db is not None and cookies:
                    await self.db.solarman_sessions.update_one(
                        {'type': 'pro'},
                        {'$set': {
                            'type': 'pro',
                            'cookies': cookies,
                            'logged_in': True,
                            'captured_at': datetime.now(timezone.utc).isoformat(),
                            'expires_at': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                        }},
                        upsert=True
                    )
                    
                    # Update login session status
                    await self.db.solarman_login_sessions.update_one(
                        {'session_id': session_id},
                        {'$set': {'status': 'completed'}}
                    )
                
                await self.close()
                
                return {
                    'success': True,
                    'logged_in': True,
                    'message': 'Login capturado com sucesso!',
                    'cookies_count': len(cookies)
                }
            
            return {
                'success': True,
                'logged_in': False,
                'message': 'Aguardando login...',
                'current_url': current_url
            }
            
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return {'success': False, 'error': str(e), 'logged_in': False}
    
    async def get_saved_session(self) -> Optional[Dict]:
        """Get saved session from DB (includes cookies, localStorage, sessionStorage, and auth token)"""
        if self.db is None:
            return None
        
        session = await self.db.solarman_sessions.find_one(
            {'type': 'pro'},
            {'_id': 0}
        )
        
        if session:
            # Check if expired
            expires_at = session.get('expires_at', '')
            if expires_at:
                try:
                    exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if datetime.now(timezone.utc) > exp_date:
                        logger.info("[Solarman] Sessão expirada")
                        return None  # Expired
                except Exception as e:
                    logger.warning(f"[Solarman] Erro ao verificar expiração: {e}")
            
            # Log session info for debugging
            logger.info(f"[Solarman] Sessão encontrada - cookies: {len(session.get('cookies', []))}, "
                       f"auth_token: {'Sim' if session.get('auth_token') else 'Não'}, "
                       f"token_source: {session.get('token_source', 'N/A')}")
        
        return session
    
    async def is_session_valid(self) -> bool:
        """Check if we have a valid saved session"""
        session = await self.get_saved_session()
        return session is not None and session.get('logged_in', False)
    
    async def fetch_plants(self) -> Dict[str, Any]:
        """Fetch plants using saved session (cookies + auth token)"""
        try:
            session = await self.get_saved_session()
            if not session:
                return {'success': False, 'error': 'Sessão não encontrada. Faça login primeiro.'}
            
            cookies = session.get('cookies', [])
            auth_token = session.get('auth_token')
            local_storage = session.get('local_storage', {})
            session_storage = session.get('session_storage', {})
            
            # Build cookie header string
            cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies]) if cookies else ''
            
            # Headers with proper authentication
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Referer': f'{self.PORTAL_URL}/',
                'Origin': self.PORTAL_URL,
            }
            
            if cookie_str:
                headers['Cookie'] = cookie_str
            
            # Add Authorization header from captured token
            if auth_token:
                # Clean the token (remove Bearer prefix if present)
                token_value = auth_token.strip()
                if token_value.lower().startswith('bearer '):
                    token_value = token_value[7:]
                headers['Authorization'] = f'Bearer {token_value}'
                logger.info(f"[Solarman] Usando token de autenticação (len={len(token_value)})")
            else:
                # Try to extract token from cookies as fallback
                for cookie in cookies:
                    if cookie['name'].lower() in ['tokenkey', 'token', 'access_token']:
                        headers['Authorization'] = f'Bearer {cookie["value"]}'
                        logger.info(f"[Solarman] Usando token de cookie: {cookie['name']}")
                        break
            
            # Log session info for debugging
            logger.info(f"[Solarman] Tentando buscar usinas com {len(cookies)} cookies")
            logger.info(f"[Solarman] Headers: {list(headers.keys())}")
            logger.info(f"[Solarman] Has Authorization: {'Authorization' in headers}")
            
            async with aiohttp.ClientSession() as http_session:
                # Try different API endpoints for Solarman PRO
                # These endpoints are based on common Solarman API patterns
                endpoints = [
                    # Station/Plant list endpoints
                    ('/maintain-s/maintain/station/page', 'POST', {'page': 1, 'size': 100}),
                    ('/maintain-s/maintain/station/list', 'GET', None),
                    ('/business/station/list', 'GET', None),
                    ('/api/v1/plant/list', 'GET', None),
                    ('/api/station/list', 'GET', None),
                    ('/maintain/plant/list', 'GET', None),
                    ('/business/maintain/plant/list', 'GET', None),
                    # Alternative patterns
                    ('/station/v1.0/list', 'GET', None),
                    ('/plant/v1.0/list', 'GET', None),
                ]
                
                for endpoint, method, body in endpoints:
                    try:
                        url = f"{self.API_BASE}{endpoint}"
                        logger.debug(f"[Solarman] Tentando {method} {url}")
                        
                        if method == 'POST':
                            async with http_session.post(url, headers=headers, json=body, timeout=30, ssl=False) as resp:
                                response_status = resp.status
                                response_text = await resp.text()
                        else:
                            async with http_session.get(url, headers=headers, timeout=30, ssl=False) as resp:
                                response_status = resp.status
                                response_text = await resp.text()
                        
                        logger.debug(f"[Solarman] {endpoint} -> status {response_status}")
                        
                        if response_status == 200:
                            try:
                                data = json.loads(response_text)
                                
                                # Check various response formats
                                plants = None
                                if isinstance(data, dict):
                                    # Handle different API response structures
                                    if data.get('success') == True or data.get('code') == 0 or data.get('code') == '0':
                                        plants = data.get('data', data.get('list', data.get('plants', data.get('stationList', data.get('records', [])))))
                                        # If data is a dict with list inside
                                        if isinstance(plants, dict):
                                            plants = plants.get('records', plants.get('list', plants.get('data', [])))
                                    elif data.get('success') == False or data.get('code') not in [0, '0', None]:
                                        logger.debug(f"[Solarman] API error response: {data.get('msg', data.get('message', 'Unknown'))}")
                                        continue
                                    else:
                                        plants = data.get('data', data.get('list', data.get('plants', data.get('stationList', []))))
                                elif isinstance(data, list):
                                    plants = data
                                
                                if plants and len(plants) > 0:
                                    logger.info(f"[Solarman] Encontradas {len(plants)} usinas via {endpoint}")
                                    return {
                                        'success': True,
                                        'plants': plants,
                                        'count': len(plants),
                                        'endpoint': endpoint
                                    }
                            except json.JSONDecodeError:
                                logger.debug(f"[Solarman] {endpoint} não retornou JSON válido: {response_text[:200]}")
                                continue
                        elif response_status == 401:
                            logger.warning(f"[Solarman] 401 Unauthorized em {endpoint}")
                            continue  # Try next endpoint instead of failing immediately
                        elif response_status == 403:
                            logger.warning(f"[Solarman] 403 Forbidden em {endpoint}")
                            continue
                                
                    except asyncio.TimeoutError:
                        logger.debug(f"[Solarman] Timeout em {endpoint}")
                        continue
                    except Exception as e:
                        logger.debug(f"[Solarman] Erro em {endpoint}: {e}")
                        continue
                
                # If none of the endpoints worked, check if we got any 401s
                logger.warning("[Solarman] Nenhum endpoint retornou dados")
                
                # Invalidate session since nothing worked
                if self.db is not None:
                    await self.db.solarman_sessions.update_one(
                        {'type': 'pro'},
                        {'$set': {'logged_in': False}}
                    )
                
                return {
                    'success': False, 
                    'error': 'Não foi possível buscar as usinas. Verifique se o login está ativo no portal.',
                    'hint': 'Tente fazer login novamente no Solarman e use o bookmarklet para capturar a sessão.'
                }
                
        except Exception as e:
            logger.error(f"[Solarman] Erro geral: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _fetch_plants_via_scraping(self, cookies: List[Dict]) -> Dict[str, Any]:
        """Fetch plants by scraping the web page with saved cookies"""
        try:
            await self._init_browser(headless=True)
            
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            # Add cookies
            await context.add_cookies(cookies)
            
            page = await context.new_page()
            
            # Navigate to plant list
            await page.goto(f"{self.PORTAL_URL}/main", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
            
            # Check if logged in
            if 'login' in page.url.lower():
                await context.close()
                await self.close()
                
                # Invalidate session
                if self.db is not None:
                    await self.db.solarman_sessions.update_one(
                        {'type': 'pro'},
                        {'$set': {'logged_in': False}}
                    )
                
                return {'success': False, 'error': 'Sessão expirada. Faça login novamente.'}
            
            # Extract plant data from page
            plants_data = await page.evaluate('''
                () => {
                    const plants = [];
                    
                    // Try different selectors for plant cards
                    const selectors = [
                        '.plant-card', '.station-card', '[class*="plant"]', 
                        '[class*="station"]', '.ant-card', '.list-item'
                    ];
                    
                    for (const selector of selectors) {
                        const cards = document.querySelectorAll(selector);
                        if (cards.length > 0) {
                            cards.forEach((card, idx) => {
                                const text = card.innerText || '';
                                const nameEl = card.querySelector('[class*="name"], [class*="title"], h3, h4');
                                const powerEl = card.querySelector('[class*="power"], [class*="kw"]');
                                const energyEl = card.querySelector('[class*="energy"], [class*="kwh"]');
                                
                                plants.push({
                                    index: idx,
                                    name: nameEl?.innerText?.trim() || `Usina ${idx + 1}`,
                                    power_kw: powerEl?.innerText?.trim() || '',
                                    energy_kwh: energyEl?.innerText?.trim() || '',
                                    raw_text: text.substring(0, 300)
                                });
                            });
                            break;
                        }
                    }
                    
                    // Also try extracting from table
                    const tables = document.querySelectorAll('table');
                    tables.forEach(table => {
                        const rows = table.querySelectorAll('tbody tr');
                        rows.forEach((row, idx) => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 3) {
                                plants.push({
                                    index: idx,
                                    name: cells[0]?.innerText?.trim() || '',
                                    status: cells[1]?.innerText?.trim() || '',
                                    power_kw: cells[2]?.innerText?.trim() || '',
                                    energy_kwh: cells[3]?.innerText?.trim() || ''
                                });
                            }
                        });
                    });
                    
                    return {
                        plants: plants,
                        pageTitle: document.title,
                        url: window.location.href,
                        bodyPreview: document.body?.innerText?.substring(0, 1000)
                    };
                }
            ''')
            
            await context.close()
            await self.close()
            
            return {
                'success': True,
                'plants': plants_data.get('plants', []),
                'count': len(plants_data.get('plants', [])),
                'page_title': plants_data.get('pageTitle', ''),
                'source': 'scraping'
            }
            
        except Exception as e:
            logger.error(f"Error scraping plants: {e}")
            await self.close()
            return {'success': False, 'error': str(e)}
    
    async def get_plant_generation(self, plant_id: str, date: str = None) -> Dict[str, Any]:
        """Get generation data for a specific plant"""
        # Implementation similar to fetch_plants but for specific plant data
        pass
    
    async def disconnect(self) -> Dict[str, Any]:
        """Remove saved session"""
        try:
            if self.db is not None:
                await self.db.solarman_sessions.delete_many({'type': 'pro'})
            return {'success': True, 'message': 'Sessão removida'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Global instance
_solarman_service: Optional[SolarmanSessionService] = None

def get_solarman_service(db=None) -> SolarmanSessionService:
    global _solarman_service
    if _solarman_service is None:
        _solarman_service = SolarmanSessionService(db)
    elif db is not None and _solarman_service.db is None:
        _solarman_service.db = db
    return _solarman_service

async def reset_solarman_service():
    global _solarman_service
    if _solarman_service is not None:
        await _solarman_service.close()
        _solarman_service = None
