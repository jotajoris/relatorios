"""
Backend API tests for Solar Plant Management System
Testing: Auth, Consumer Units, Invoices, Upload
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndAuth:
    """Authentication and health check tests"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ API Root: {data}")
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "projetos.onsolucoes@gmail.com",
            "password": "on123456"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == "projetos.onsolucoes@gmail.com"
        print(f"✓ Login success: {data['user']['email']}")
        return data["access_token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        print("✓ Invalid login rejected")


class TestConsumerUnits:
    """Consumer Units CRUD tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "projetos.onsolucoes@gmail.com",
            "password": "on123456"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get authenticated headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_list_consumer_units(self, auth_headers):
        """Test listing consumer units"""
        response = requests.get(f"{BASE_URL}/api/consumer-units", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} consumer units")
        
        # Check that units have required new fields
        if len(data) > 0:
            unit = data[0]
            assert "id" in unit
            assert "plant_id" in unit
            assert "address" in unit
            # New fields should be present
            assert "uc_number" in unit or "contract_number" in unit  # Migration support
            print(f"  First UC: {unit.get('uc_number', unit.get('contract_number', 'N/A'))}")
    
    def test_list_plants(self, auth_headers):
        """Test listing plants to get plant_id for UC creation"""
        response = requests.get(f"{BASE_URL}/api/plants", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} plants")
        return data
    
    def test_create_consumer_unit_with_new_fields(self, auth_headers):
        """Test creating UC with new fields (uc_number, tariff_group, compensation_percentage)"""
        # First get a valid plant_id
        plants_response = requests.get(f"{BASE_URL}/api/plants", headers=auth_headers)
        plants = plants_response.json()
        
        if len(plants) == 0:
            pytest.skip("No plants available for UC creation test")
        
        plant_id = plants[0]["id"]
        
        # Create UC with new fields
        uc_data = {
            "plant_id": plant_id,
            "uc_number": "TEST_12345678",
            "contract_number": "TEST_CONTRACT",
            "address": "Rua de Teste, 100 - Centro",
            "city": "Curitiba",
            "state": "PR",
            "holder_name": "Teste Holder",
            "holder_document": "00.000.000/0001-00",
            "is_generator": False,
            "compensation_percentage": 50.0,
            "tariff_group": "B",
            "tariff_modality": "Convencional",
            "contracted_demand_kw": 0,
            "generator_uc_ids": []
        }
        
        response = requests.post(f"{BASE_URL}/api/consumer-units", headers=auth_headers, json=uc_data)
        assert response.status_code == 200
        
        created = response.json()
        assert created["uc_number"] == "TEST_12345678"
        assert created["compensation_percentage"] == 50.0
        assert created["tariff_group"] == "B"
        assert created["is_generator"] == False
        print(f"✓ Created UC: {created['uc_number']} with {created['compensation_percentage']}% compensation")
        
        # Cleanup - delete the test UC
        delete_response = requests.delete(f"{BASE_URL}/api/consumer-units/{created['id']}", headers=auth_headers)
        assert delete_response.status_code == 200
        print(f"✓ Deleted test UC: {created['id']}")


class TestInvoices:
    """Invoice endpoints tests"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get authenticated headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "projetos.onsolucoes@gmail.com",
            "password": "on123456"
        })
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_list_invoices(self, auth_headers):
        """Test listing invoices"""
        response = requests.get(f"{BASE_URL}/api/invoices", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} invoices")


class TestPDFUpload:
    """PDF upload and parsing tests"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get authenticated headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "projetos.onsolucoes@gmail.com",
            "password": "on123456"
        })
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    @pytest.fixture
    def test_uc(self, auth_headers):
        """Create or get a test UC for PDF upload"""
        # First get existing UCs
        response = requests.get(f"{BASE_URL}/api/consumer-units", headers=auth_headers)
        units = response.json()
        
        if len(units) > 0:
            return units[0]
        
        # Create one if none exists
        plants_response = requests.get(f"{BASE_URL}/api/plants", headers=auth_headers)
        plants = plants_response.json()
        
        if len(plants) == 0:
            pytest.skip("No plants available for PDF upload test")
        
        uc_data = {
            "plant_id": plants[0]["id"],
            "uc_number": "TEST_UPLOAD_UC",
            "address": "Test Address for Upload",
            "is_generator": False,
            "tariff_group": "B"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/consumer-units", headers=auth_headers, json=uc_data)
        return create_response.json()
    
    def test_upload_pdf_grupo_a(self, auth_headers, test_uc):
        """Test PDF upload for Grupo A invoice"""
        pdf_path = "/tmp/fatura_grupo_a.pdf"
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('fatura_grupo_a.pdf', f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/api/invoices/upload-pdf/{test_uc['id']}", 
                headers=auth_headers,
                files=files
            )
        
        assert response.status_code == 200
        data = response.json()
        print(f"✓ PDF upload response: success={data.get('success')}")
        
        if data.get('success'):
            parsed = data.get('parsed_data', {})
            print(f"  - Tariff Group: {parsed.get('tariff_group')}")
            print(f"  - Reference Month: {parsed.get('reference_month')}")
            print(f"  - Total Amount: R$ {parsed.get('amount_total_brl')}")
        else:
            print(f"  - Error: {data.get('error')}")
    
    def test_upload_pdf_grupo_b(self, auth_headers, test_uc):
        """Test PDF upload for Grupo B invoice"""
        pdf_path = "/tmp/fatura_grupo_b.pdf"
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('fatura_grupo_b.pdf', f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/api/invoices/upload-pdf/{test_uc['id']}", 
                headers=auth_headers,
                files=files
            )
        
        assert response.status_code == 200
        data = response.json()
        print(f"✓ PDF upload response: success={data.get('success')}")
        
        if data.get('success'):
            parsed = data.get('parsed_data', {})
            print(f"  - Tariff Group: {parsed.get('tariff_group')}")
            print(f"  - Reference Month: {parsed.get('reference_month')}")
            print(f"  - Total Amount: R$ {parsed.get('amount_total_brl')}")
        else:
            print(f"  - Error: {data.get('error')}")


class TestDashboard:
    """Dashboard endpoint tests"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get authenticated headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "projetos.onsolucoes@gmail.com",
            "password": "on123456"
        })
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_dashboard_stats(self, auth_headers):
        """Test dashboard stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_plants" in data
        assert "total_clients" in data
        print(f"✓ Dashboard stats: {data['total_plants']} plants, {data['total_clients']} clients")
    
    def test_dashboard_plants_summary(self, auth_headers):
        """Test plants summary endpoint"""
        response = requests.get(f"{BASE_URL}/api/dashboard/plants-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Plants summary: {len(data)} plants")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
