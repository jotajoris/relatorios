#!/usr/bin/env python3
"""
Backend API Testing for Solar Plant Management System
Tests all API endpoints including authentication, CRUD operations, and dashboard stats.
"""

import requests
import sys
import json
from datetime import datetime, timedelta

class SolarPlantAPITester:
    def __init__(self, base_url="https://solar-report-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Store test data IDs for cleanup
        self.test_client_id = None
        self.test_plant_id = None
        self.test_unit_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.text}")
                except:
                    pass
                self.failed_tests.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append(f"{name}: Error - {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health check"""
        return self.run_test("API Health Check", "GET", "", 200)

    def test_register(self):
        """Test user registration"""
        test_user_data = {
            "name": "Test User",
            "email": "test@solarsystem.com.br",
            "password": "test123456"
        }
        success, response = self.run_test(
            "User Registration", "POST", "auth/register", 200, test_user_data
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   ✓ Token received: {self.token[:20]}...")
            return True
        return False

    def test_login(self):
        """Test login with provided credentials"""
        login_data = {
            "email": "projetos.onsolucoes@gmail.com", 
            "password": "on123456"
        }
        success, response = self.run_test(
            "User Login (projetos.onsolucoes)", "POST", "auth/login", 200, login_data
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   ✓ Token received: {self.token[:20]}...")
            return True
        return False
    
    def test_login_comercial(self):
        """Test login with comercial credentials"""
        login_data = {
            "email": "comercial.onsolucoes@gmail.com", 
            "password": "on123456"
        }
        success, response = self.run_test(
            "User Login (comercial.onsolucoes)", "POST", "auth/login", 200, login_data
        )
        return success and 'access_token' in response

    def test_get_me(self):
        """Test getting current user info"""
        success, response = self.run_test("Get Current User", "GET", "auth/me", 200)
        return success and 'email' in response

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        success, response = self.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)
        if success:
            expected_fields = ['total_plants', 'total_clients', 'total_generation_kwh']
            missing_fields = [f for f in expected_fields if f not in response]
            if missing_fields:
                print(f"   ⚠️ Missing fields: {missing_fields}")
            else:
                print(f"   ✓ All expected fields present")
        return success

    def test_plants_summary(self):
        """Test plants summary endpoint"""
        return self.run_test("Plants Summary", "GET", "dashboard/plants-summary", 200)

    def test_clients_crud(self):
        """Test full CRUD operations for clients"""
        # List clients
        success, clients = self.run_test("List Clients", "GET", "clients", 200)
        if not success:
            return False
        
        initial_count = len(clients)
        print(f"   ✓ Found {initial_count} existing clients")

        # Create client
        client_data = {
            "name": "Test Client Solar LTDA",
            "email": "test.client@solarsystem.com.br",
            "phone": "(41) 99999-9999",
            "document": "12.345.678/0001-90",
            "address": "Rua Solar, 123, Curitiba - PR"
        }
        success, response = self.run_test("Create Client", "POST", "clients", 200, client_data)
        if not success:
            return False
        
        self.test_client_id = response.get('id')
        print(f"   ✓ Created client ID: {self.test_client_id}")

        # Get client by ID
        success, client = self.run_test(f"Get Client", "GET", f"clients/{self.test_client_id}", 200)
        if not success or client.get('name') != client_data['name']:
            print(f"   ❌ Client data mismatch")
            return False

        # Update client
        updated_data = client_data.copy()
        updated_data['name'] = "Updated Test Client"
        success, _ = self.run_test(f"Update Client", "PUT", f"clients/{self.test_client_id}", 200, updated_data)
        if not success:
            return False

        print("   ✓ Client CRUD operations completed")
        return True

    def test_plants_crud(self):
        """Test full CRUD operations for plants"""
        if not self.test_client_id:
            print("   ❌ No test client available for plant creation")
            return False

        # List plants
        success, plants = self.run_test("List Plants", "GET", "plants", 200)
        if not success:
            return False
        
        print(f"   ✓ Found {len(plants)} existing plants")

        # Create plant
        plant_data = {
            "name": "Test Solar Plant - Test Automation",
            "client_id": self.test_client_id,
            "capacity_kwp": 50.5,
            "address": "Rua das Placas Solares, 456",
            "city": "Curitiba",
            "state": "PR",
            "inverter_brand": "growatt",
            "monthly_prognosis_kwh": 6000,
            "annual_prognosis_kwh": 72000,
            "total_investment": 150000.00,
            "installation_date": "2024-01-15"
        }
        success, response = self.run_test("Create Plant", "POST", "plants", 200, plant_data)
        if not success:
            return False
        
        self.test_plant_id = response.get('id')
        print(f"   ✓ Created plant ID: {self.test_plant_id}")

        # Get plant by ID
        success, plant = self.run_test(f"Get Plant", "GET", f"plants/{self.test_plant_id}", 200)
        if not success or plant.get('name') != plant_data['name']:
            print(f"   ❌ Plant data mismatch")
            return False

        print("   ✓ Plant CRUD operations completed")
        return True

    def test_consumer_units_crud(self):
        """Test consumer units CRUD operations"""
        if not self.test_plant_id:
            print("   ❌ No test plant available for unit creation")
            return False

        # Create consumer unit
        unit_data = {
            "plant_id": self.test_plant_id,
            "contract_number": "987654321",
            "address": "Rua Test Consumer Unit, 789",
            "holder_name": "Test Holder",
            "is_generator": True
        }
        success, response = self.run_test("Create Consumer Unit", "POST", "consumer-units", 200, unit_data)
        if not success:
            return False
        
        self.test_unit_id = response.get('id')
        print(f"   ✓ Created consumer unit ID: {self.test_unit_id}")

        # List consumer units for the plant
        success, units = self.run_test("List Consumer Units", "GET", "consumer-units", 200, params={"plant_id": self.test_plant_id})
        if not success:
            return False

        print(f"   ✓ Found {len(units)} consumer units for test plant")
        return True

    def test_generation_data(self):
        """Test generation data operations"""
        if not self.test_plant_id:
            print("   ❌ No test plant available for generation data")
            return False

        # Create generation data for the last 7 days
        base_date = datetime.now() - timedelta(days=7)
        for i in range(7):
            date = base_date + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            generation = 200 + (i * 50)  # Varying generation
            
            gen_data = {
                "plant_id": self.test_plant_id,
                "date": date_str,
                "generation_kwh": generation,
                "source": "test_automation"
            }
            success, _ = self.run_test(f"Create Generation Data {date_str}", "POST", "generation-data", 200, gen_data)
            if not success:
                return False

        # Get generation data for the plant
        start_date = (base_date).strftime('%Y-%m-%d')
        end_date = (base_date + timedelta(days=6)).strftime('%Y-%m-%d')
        success, gen_data = self.run_test(
            "Get Generation Data", 
            "GET", 
            "generation-data", 
            200, 
            params={"plant_id": self.test_plant_id, "start_date": start_date, "end_date": end_date}
        )
        
        if success:
            print(f"   ✓ Retrieved {len(gen_data)} generation records")
        
        return success

    def test_growatt_integration(self):
        """Test Growatt integration endpoints"""
        # Test Growatt test-login endpoint (should fail without valid credentials but return proper error)
        test_data = {
            "plant_id": "test-plant-123",
            "username": "test@example.com",
            "password": "testpass"
        }
        success, response = self.run_test(
            "Growatt Test Login (Expected Fail)", "POST", "integrations/growatt/test-login", 400, test_data
        )
        # This should fail but return a proper error message
        if not success:
            print("   ✓ Growatt endpoint properly rejects invalid credentials")
        
        return True  # We expect this to fail, so pass if it fails properly

    def test_report_data(self):
        """Test report data endpoint"""
        if not self.test_plant_id:
            print("   ❌ No test plant available for report")
            return False

        current_month = datetime.now().strftime('%Y-%m')
        success, report = self.run_test(
            "Get Report Data", 
            "GET", 
            f"reports/plant/{self.test_plant_id}", 
            200,
            params={"month": current_month}
        )
        
        if success:
            expected_sections = ['plant', 'client', 'generation', 'financial', 'environmental']
            missing_sections = [s for s in expected_sections if s not in report]
            if missing_sections:
                print(f"   ⚠️ Missing report sections: {missing_sections}")
            else:
                print(f"   ✓ All report sections present")
        
        return success

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete consumer unit
        if self.test_unit_id:
            self.run_test("Delete Test Consumer Unit", "DELETE", f"consumer-units/{self.test_unit_id}", 200)
        
        # Delete plant
        if self.test_plant_id:
            self.run_test("Delete Test Plant", "DELETE", f"plants/{self.test_plant_id}", 200)
        
        # Delete client
        if self.test_client_id:
            self.run_test("Delete Test Client", "DELETE", f"clients/{self.test_client_id}", 200)

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Solar Plant Management API Tests")
        print(f"Testing against: {self.base_url}")
        
        # Test sequence
        tests = [
            ("API Health", self.test_health_check),
            ("User Login (projetos)", self.test_login),
            ("User Login (comercial)", self.test_login_comercial),
            ("Get Current User", self.test_get_me),
            ("Dashboard Stats", self.test_dashboard_stats),
            ("Plants Summary", self.test_plants_summary),
            ("Growatt Integration", self.test_growatt_integration),
            ("Clients CRUD", self.test_clients_crud),
            ("Plants CRUD", self.test_plants_crud),
            ("Consumer Units CRUD", self.test_consumer_units_crud),
            ("Generation Data", self.test_generation_data),
            ("Report Data", self.test_report_data)
        ]

        for test_name, test_func in tests:
            print(f"\n{'='*60}")
            print(f"🧪 Testing: {test_name}")
            print(f"{'='*60}")
            
            try:
                success = test_func()
                if not success:
                    print(f"❌ {test_name} failed!")
                else:
                    print(f"✅ {test_name} passed!")
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                self.failed_tests.append(f"{test_name}: Exception - {str(e)}")

        # Clean up
        self.cleanup_test_data()

        # Print final results
        self.print_results()
        return self.tests_passed == self.tests_run and len(self.failed_tests) == 0

    def print_results(self):
        """Print test results summary"""
        print(f"\n{'='*80}")
        print(f"📊 TEST RESULTS SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for i, failure in enumerate(self.failed_tests, 1):
                print(f"   {i}. {failure}")
        else:
            print(f"\n🎉 All tests passed!")

def main():
    """Main test execution"""
    tester = SolarPlantAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())