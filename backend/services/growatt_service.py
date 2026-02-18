"""
Growatt API Integration Service
Handles authentication and data fetching from Growatt solar monitoring platform
"""

import growattServer
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class GrowattService:
    """Service class for Growatt API integration"""
    
    def __init__(self, server: str = "oss"):
        # Use random User-Agent to avoid 403 errors from Growatt WAF
        self.api = growattServer.GrowattApi(True, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Set server URL based on region
        # oss = Other countries (Brazil, etc)
        # openapi = Europe
        # openapi-us = North America
        # openapi-cn = China
        if server == "oss":
            self.api.server_url = 'https://server.growatt.com/'  # OSS uses same API
        elif server == "us":
            self.api.server_url = 'https://openapi-us.growatt.com/'
        elif server == "cn":
            self.api.server_url = 'https://openapi-cn.growatt.com/'
        else:
            self.api.server_url = 'https://openapi.growatt.com/'
        
        self.user_id = None
        self.logged_in = False
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Login to Growatt API
        
        Args:
            username: Growatt account username/email
            password: Growatt account password
            
        Returns:
            Login response with user info
        """
        try:
            response = self.api.login(username, password)
            if response and response.get('user'):
                self.user_id = response['user'].get('id')
                self.logged_in = True
                logger.info(f"Growatt login successful for user: {username}")
                return {
                    "success": True,
                    "user_id": self.user_id,
                    "user_name": response['user'].get('name', username)
                }
            else:
                logger.error(f"Growatt login failed for user: {username}")
                return {"success": False, "error": "Login failed - invalid credentials"}
        except Exception as e:
            logger.error(f"Growatt login error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_plant_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all plants associated with the logged in user
        
        Returns:
            List of plant information dictionaries
        """
        if not self.logged_in or not self.user_id:
            return []
        
        try:
            plants = self.api.plant_list(self.user_id)
            return [
                {
                    "id": p.get('plantId') or p.get('id'),
                    "name": p.get('plantName') or p.get('name'),
                    "capacity_kwp": float(p.get('nominal_power', 0)) / 1000 if p.get('nominal_power') else 0,
                    "location": p.get('city', ''),
                    "status": "online" if p.get('status') == '1' else "offline",
                    "today_energy_kwh": float(p.get('today_energy', 0)),
                    "total_energy_kwh": float(p.get('total_energy', 0)),
                }
                for p in plants if isinstance(p, dict)
            ]
        except Exception as e:
            logger.error(f"Error fetching plant list: {str(e)}")
            return []
    
    def get_plant_details(self, plant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific plant
        
        Args:
            plant_id: The Growatt plant ID
            
        Returns:
            Plant details dictionary or None
        """
        if not self.logged_in:
            return None
        
        try:
            details = self.api.plant_detail(plant_id)
            if not details:
                return None
            
            return {
                "id": plant_id,
                "name": details.get('plantName'),
                "capacity_kwp": float(details.get('nominal_power', 0)) / 1000,
                "today_energy_kwh": float(details.get('todayEnergy', 0)),
                "month_energy_kwh": float(details.get('monthEnergy', 0)),
                "year_energy_kwh": float(details.get('yearEnergy', 0)),
                "total_energy_kwh": float(details.get('totalEnergy', 0)),
                "current_power_kw": float(details.get('currentPower', 0)),
                "co2_reduced_kg": float(details.get('Co2Reduction', 0)),
                "efficiency_percent": float(details.get('efficiency', 0)),
            }
        except Exception as e:
            logger.error(f"Error fetching plant details for {plant_id}: {str(e)}")
            return None
    
    def get_daily_generation(self, plant_id: str, date: str) -> Optional[Dict[str, Any]]:
        """
        Get generation data for a specific date
        
        Args:
            plant_id: The Growatt plant ID
            date: Date string in YYYY-MM-DD format
            
        Returns:
            Daily generation data or None
        """
        if not self.logged_in:
            return None
        
        try:
            # Parse date
            dt = datetime.strptime(date, '%Y-%m-%d')
            
            # Get energy data for the day
            energy_data = self.api.plant_energy_data(plant_id, date)
            
            if not energy_data:
                return None
            
            return {
                "date": date,
                "generation_kwh": float(energy_data.get('energy', 0)),
                "pac_kw": float(energy_data.get('pac', 0)),
            }
        except Exception as e:
            logger.error(f"Error fetching daily generation for {plant_id} on {date}: {str(e)}")
            return None
    
    def get_month_generation(self, plant_id: str, year: int, month: int) -> List[Dict[str, Any]]:
        """
        Get daily generation data for an entire month
        
        Args:
            plant_id: The Growatt plant ID
            year: Year (e.g., 2025)
            month: Month (1-12)
            
        Returns:
            List of daily generation records
        """
        if not self.logged_in:
            return []
        
        try:
            # Format the date as required by Growatt API
            date_str = f"{year}-{month:02d}"
            
            # Try to get monthly data
            energy_data = self.api.plant_energy_overview(plant_id, date_str)
            
            daily_data = []
            if energy_data and 'data' in energy_data:
                for day_data in energy_data.get('data', []):
                    daily_data.append({
                        "date": day_data.get('date'),
                        "generation_kwh": float(day_data.get('energy', 0)),
                    })
            
            return daily_data
        except Exception as e:
            logger.error(f"Error fetching month generation for {plant_id} ({year}-{month}): {str(e)}")
            return []
    
    def get_inverter_list(self, plant_id: str) -> List[Dict[str, Any]]:
        """
        Get list of inverters for a plant
        
        Args:
            plant_id: The Growatt plant ID
            
        Returns:
            List of inverter information
        """
        if not self.logged_in:
            return []
        
        try:
            devices = self.api.device_list(plant_id)
            inverters = []
            
            for device in devices if devices else []:
                if device.get('deviceType') in ['inverter', 'max', 'mix', 'spa', 'min', 'tlx']:
                    inverters.append({
                        "serial_number": device.get('deviceSn') or device.get('sn'),
                        "alias": device.get('deviceAilas') or device.get('alias'),
                        "type": device.get('deviceType'),
                        "status": "online" if device.get('status') == '1' else "offline",
                        "last_update": device.get('lastUpdateTime'),
                    })
            
            return inverters
        except Exception as e:
            logger.error(f"Error fetching inverter list for {plant_id}: {str(e)}")
            return []
    
    def sync_plant_data(self, plant_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Sync all generation data for a plant for the last N days
        
        Args:
            plant_id: The Growatt plant ID
            days: Number of days to sync (default 30)
            
        Returns:
            Sync results with all daily data
        """
        if not self.logged_in:
            return {"success": False, "error": "Not logged in"}
        
        try:
            daily_records = []
            today = datetime.now()
            
            for i in range(days):
                date = today - timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                
                day_data = self.get_daily_generation(plant_id, date_str)
                if day_data and day_data.get('generation_kwh', 0) > 0:
                    daily_records.append(day_data)
            
            return {
                "success": True,
                "plant_id": plant_id,
                "records_fetched": len(daily_records),
                "data": daily_records
            }
        except Exception as e:
            logger.error(f"Error syncing plant data for {plant_id}: {str(e)}")
            return {"success": False, "error": str(e)}


# Singleton instance
_growatt_service: Optional[GrowattService] = None


def get_growatt_service() -> GrowattService:
    """Get or create the Growatt service singleton"""
    global _growatt_service
    if _growatt_service is None:
        _growatt_service = GrowattService()
    return _growatt_service
