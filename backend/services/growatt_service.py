"""
Growatt API Integration Service
Handles authentication and data fetching from Growatt solar monitoring platform
Uses the new OpenAPI V1 with token-based authentication
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class GrowattService:
    """Service class for Growatt API integration using token authentication"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://openapi.growatt.com"
        self.headers = {
            "token": token,
            "Content-Type": "application/json"
        } if token else {}
        self.logged_in = token is not None
    
    def set_token(self, token: str):
        """Set the API token for authentication"""
        self.token = token
        self.headers["token"] = token
        self.logged_in = True
        logger.info("Growatt API token configured")
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request to the Growatt API"""
        if not self.token:
            return {"success": False, "error": "No API token configured"}
        
        try:
            url = f"{self.base_url}/v1{endpoint}"
            response = requests.get(url, headers=self.headers, params=params or {}, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("error_code") == 0:
                return {"success": True, "data": data.get("data", {})}
            else:
                error_msg = data.get("error_msg", "Unknown error")
                return {"success": False, "error": error_msg, "error_code": data.get("error_code")}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Growatt API request error: {str(e)}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in Growatt API: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the API connection and token validity"""
        result = self._make_request("/plant/list", {"page": 1, "perpage": 1})
        
        if result.get("success"):
            return {
                "success": True,
                "message": "Connection successful",
                "plants_count": result.get("data", {}).get("count", 0)
            }
        elif result.get("error_code") == 10011:
            return {
                "success": False,
                "error": "Token inválido ou permissão negada. Verifique se o token foi gerado pelo app ShinePhone."
            }
        else:
            return result
    
    def get_plant_list(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get list of all plants associated with the token
        
        Returns:
            List of plant information dictionaries
        """
        result = self._make_request("/plant/list", {"page": page, "perpage": per_page})
        
        if not result.get("success"):
            logger.error(f"Failed to get plant list: {result.get('error')}")
            return []
        
        plants_data = result.get("data", {})
        plants = plants_data.get("plants", [])
        
        return [
            {
                "id": p.get("plant_id") or p.get("plantId") or p.get("id"),
                "name": p.get("plant_name") or p.get("plantName") or p.get("name"),
                "capacity_kwp": float(p.get("peak_power", 0) or p.get("nominal_power", 0)) / 1000 if p.get("peak_power") or p.get("nominal_power") else 0,
                "location": p.get("city", ""),
                "country": p.get("country", ""),
                "timezone": p.get("timezone", ""),
                "status": "online" if p.get("status") == "1" else "offline",
                "today_energy_kwh": float(p.get("today_energy", 0) or 0),
                "total_energy_kwh": float(p.get("total_energy", 0) or 0),
                "current_power_kw": float(p.get("current_power", 0) or 0),
            }
            for p in plants if isinstance(p, dict)
        ]
    
    def get_plant_details(self, plant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific plant
        
        Args:
            plant_id: The Growatt plant ID
            
        Returns:
            Plant details dictionary or None
        """
        result = self._make_request("/plant/details", {"plant_id": plant_id})
        
        if not result.get("success"):
            logger.error(f"Failed to get plant details for {plant_id}: {result.get('error')}")
            return None
        
        details = result.get("data", {})
        
        return {
            "id": plant_id,
            "name": details.get("plant_name") or details.get("plantName"),
            "capacity_kwp": float(details.get("peak_power", 0) or details.get("nominal_power", 0)) / 1000,
            "today_energy_kwh": float(details.get("today_energy", 0) or 0),
            "month_energy_kwh": float(details.get("month_energy", 0) or 0),
            "year_energy_kwh": float(details.get("year_energy", 0) or 0),
            "total_energy_kwh": float(details.get("total_energy", 0) or 0),
            "current_power_kw": float(details.get("current_power", 0) or 0),
            "co2_reduced_kg": float(details.get("co2_reduction", 0) or details.get("Co2Reduction", 0) or 0),
            "efficiency_percent": float(details.get("efficiency", 0) or 0),
            "create_date": details.get("create_date"),
            "timezone": details.get("timezone"),
            "country": details.get("country"),
            "city": details.get("city"),
        }
    
    def get_plant_energy_overview(self, plant_id: str) -> Optional[Dict[str, Any]]:
        """Get energy overview for a plant"""
        result = self._make_request("/plant/energy/overview", {"plant_id": plant_id})
        
        if not result.get("success"):
            return None
            
        return result.get("data", {})
    
    def get_device_list(self, plant_id: str) -> List[Dict[str, Any]]:
        """
        Get list of devices (inverters, etc.) for a plant
        
        Args:
            plant_id: The Growatt plant ID
            
        Returns:
            List of device information
        """
        result = self._make_request("/device/list", {"plant_id": plant_id})
        
        if not result.get("success"):
            logger.error(f"Failed to get device list for {plant_id}: {result.get('error')}")
            return []
        
        devices = result.get("data", {}).get("devices", [])
        
        return [
            {
                "serial_number": d.get("device_sn") or d.get("deviceSn") or d.get("sn"),
                "alias": d.get("alias") or d.get("deviceAilas"),
                "type": d.get("device_type") or d.get("deviceType"),
                "model": d.get("device_model") or d.get("deviceModel"),
                "status": "online" if d.get("status") == "1" else "offline",
                "last_update": d.get("last_update_time") or d.get("lastUpdateTime"),
                "datalogger_sn": d.get("datalogger_sn") or d.get("dataloggerSn"),
            }
            for d in devices if isinstance(d, dict)
        ]
    
    def get_inverter_data(self, device_sn: str, device_type: str = "min") -> Optional[Dict[str, Any]]:
        """
        Get real-time data for a specific inverter
        
        Args:
            device_sn: Device serial number
            device_type: Device type (min, max, mix, tlx, spa, etc.)
            
        Returns:
            Inverter data dictionary or None
        """
        endpoint_map = {
            "min": "/device/min/data",
            "max": "/device/max/data",
            "mix": "/device/mix/data",
            "tlx": "/device/tlx/data",
            "spa": "/device/spa/data",
            "sph": "/device/sph/data",
        }
        
        endpoint = endpoint_map.get(device_type.lower(), "/device/inverter/data")
        result = self._make_request(endpoint, {"device_sn": device_sn})
        
        if not result.get("success"):
            return None
            
        return result.get("data", {})
    
    def get_plant_energy_history(self, plant_id: str, time_unit: str = "day", 
                                  start_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get historical energy data for a plant
        
        Args:
            plant_id: The Growatt plant ID
            time_unit: "day", "month", or "year"
            start_date: Start date in YYYY-MM-DD format
            
        Returns:
            List of energy data records
        """
        params = {
            "plant_id": plant_id,
            "time_unit": time_unit,
        }
        if start_date:
            params["start_date"] = start_date
            
        result = self._make_request("/plant/energy/history", params)
        
        if not result.get("success"):
            return []
            
        return result.get("data", {}).get("datas", [])
    
    def sync_plant_data(self, plant_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Sync all generation data for a plant for the last N days
        
        Args:
            plant_id: The Growatt plant ID
            days: Number of days to sync (default 30)
            
        Returns:
            Sync results with all daily data
        """
        try:
            daily_records = []
            today = datetime.now()
            start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Get historical data
            history = self.get_plant_energy_history(plant_id, "day", start_date)
            
            for record in history:
                daily_records.append({
                    "date": record.get("date") or record.get("time"),
                    "generation_kwh": float(record.get("energy", 0) or 0),
                    "power_kw": float(record.get("power", 0) or 0),
                })
            
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


def get_growatt_service(token: Optional[str] = None) -> GrowattService:
    """Get or create the Growatt service singleton"""
    global _growatt_service
    if _growatt_service is None:
        _growatt_service = GrowattService(token)
    elif token and token != _growatt_service.token:
        _growatt_service.set_token(token)
    return _growatt_service
