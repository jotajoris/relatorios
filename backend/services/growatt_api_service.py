"""
Growatt API Integration Service - Using growattServer library
Much lighter than Playwright web scraping approach
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    import growattServer
    GROWATT_AVAILABLE = True
except ImportError:
    GROWATT_AVAILABLE = False
    logger.warning("growattServer not installed. pip install growattServer")


class GrowattAPIService:
    """Lightweight Growatt integration using official API."""

    def __init__(self):
        if not GROWATT_AVAILABLE:
            raise RuntimeError("growattServer nao instalado")
        self.api = growattServer.GrowattApi()
        self.user_id = None
        self.logged_in = False

    def login(self, username: str, password: str) -> Dict[str, Any]:
        try:
            result = self.api.login(username, password)
            if result and result.get('userId'):
                self.user_id = result['userId']
                self.logged_in = True
                return {"success": True, "user_id": self.user_id, "user": result.get('userName', username)}
            return {"success": False, "error": "Login falhou - verifique usuario e senha"}
        except Exception as e:
            logger.error(f"Growatt login error: {e}")
            return {"success": False, "error": str(e)}

    def get_plants(self) -> List[Dict[str, Any]]:
        if not self.logged_in:
            return []
        try:
            result = self.api.plant_list(self.user_id)
            plants = []
            for p in result.get('data', []):
                plants.append({
                    'id': p.get('plantId', ''),
                    'name': p.get('plantName', ''),
                    'status': 'online' if p.get('status') == '1' else 'offline',
                    'capacity_kwp': float(p.get('nominalPower', 0)),
                    'today_energy_kwh': float(p.get('todayEnergy', '0').replace('kWh', '').strip() or 0),
                    'total_energy_kwh': float(p.get('totalEnergy', '0').replace('kWh', '').replace('MWh', '').strip() or 0),
                    'city': p.get('city', ''),
                    'country': p.get('country', ''),
                    'create_date': p.get('createDate', ''),
                })
            return plants
        except Exception as e:
            logger.error(f"Growatt get_plants error: {e}")
            return []

    def get_plant_detail(self, plant_id: str) -> Dict[str, Any]:
        if not self.logged_in:
            return {}
        try:
            info = self.api.plant_info(plant_id)
            return info
        except Exception as e:
            logger.error(f"Growatt plant_detail error: {e}")
            return {}

    def get_plant_energy(self, plant_id: str, date_str: str = None) -> Dict[str, Any]:
        """Get daily energy data for a plant on a specific date."""
        if not self.logged_in:
            return {}
        try:
            if not date_str:
                date_str = datetime.now().strftime('%Y-%m-%d')
            result = self.api.plant_detail(plant_id, 'day', date_str)
            return result
        except Exception as e:
            logger.error(f"Growatt plant_energy error: {e}")
            return {}

    def get_device_list(self, plant_id: str) -> List[Dict[str, Any]]:
        if not self.logged_in:
            return []
        try:
            result = self.api.device_list(plant_id)
            return result
        except Exception as e:
            logger.error(f"Growatt device_list error: {e}")
            return []

    def sync_generation_data(self, plant_id: str, year: int, month: int) -> List[Dict[str, Any]]:
        """Fetch daily generation data for an entire month."""
        if not self.logged_in:
            return []
        try:
            import calendar
            days_in_month = calendar.monthrange(year, month)[1]
            daily_data = []

            for day in range(1, days_in_month + 1):
                date_str = f"{year}-{month:02d}-{day:02d}"
                try:
                    result = self.api.plant_detail(plant_id, 'day', date_str)
                    # Extract total energy for the day
                    chart_data = result.get('chartData', {})
                    pac_data = chart_data.get('pac', [])
                    # Sum all power values for the day and convert to kWh
                    if pac_data:
                        total_kwh = sum(float(v) for v in pac_data if v) / 1000 * 24 / len(pac_data)
                    else:
                        total_kwh = float(result.get('plantData', {}).get('energy', '0').replace('kWh', '').strip() or 0)

                    if total_kwh > 0:
                        daily_data.append({
                            'date': date_str,
                            'generation_kwh': round(total_kwh, 2),
                        })
                except Exception as e:
                    logger.debug(f"No data for {date_str}: {e}")

            return daily_data
        except Exception as e:
            logger.error(f"Growatt sync error: {e}")
            return []

    def get_overview(self, plant_id: str) -> Dict[str, Any]:
        """Get comprehensive overview of a plant - today, month, year, total."""
        if not self.logged_in:
            return {}
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            # Get today's data
            day_data = self.api.plant_detail(plant_id, 'day', today)
            # Get month data
            month_str = datetime.now().strftime('%Y-%m')
            month_data = self.api.plant_detail(plant_id, 'month', month_str)
            # Get year data
            year_str = datetime.now().strftime('%Y')
            year_data = self.api.plant_detail(plant_id, 'year', year_str)

            plant_data_day = day_data.get('plantData', {})
            plant_data_month = month_data.get('plantData', {})

            return {
                'today_kwh': float(str(plant_data_day.get('energy', '0')).replace('kWh', '').replace('MWh', '').strip() or 0),
                'month_kwh': float(str(plant_data_month.get('energy', '0')).replace('kWh', '').replace('MWh', '').strip() or 0),
                'status': 'online' if plant_data_day.get('status') == '1' else 'offline',
            }
        except Exception as e:
            logger.error(f"Growatt overview error: {e}")
            return {}
