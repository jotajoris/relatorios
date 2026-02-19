"""
Test suite for new implementations:
1. Reports page KPIs (prognosis, generation, performance, economia)
2. PDF upload with tariff_values fields
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "projetos.onsolucoes@gmail.com",
        "password": "on123456"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("access_token")

@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestReportsKPIs:
    """Test Reports page KPI data (prognosis, generation, performance, economia)"""
    
    def test_plants_list_for_reports(self, auth_headers):
        """GET /api/plants returns plants for report dropdown"""
        response = requests.get(f"{BASE_URL}/api/plants", headers=auth_headers)
        assert response.status_code == 200
        plants = response.json()
        assert isinstance(plants, list)
        print(f"Found {len(plants)} plants")
    
    def test_report_data_contains_kpis(self, auth_headers):
        """GET /api/reports/plant/{id} returns KPI fields: prognosis, generation, performance, economia"""
        # First get a plant
        plants_response = requests.get(f"{BASE_URL}/api/plants", headers=auth_headers)
        assert plants_response.status_code == 200
        plants = plants_response.json()
        
        if not plants:
            pytest.skip("No plants available for testing")
        
        plant_id = plants[0]['id']
        month = "2025-01"
        
        # Get report data
        response = requests.get(f"{BASE_URL}/api/reports/plant/{plant_id}?month={month}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify KPI fields exist
        assert 'generation' in data, "Missing 'generation' in report data"
        assert 'financial' in data, "Missing 'financial' in report data"
        
        gen = data['generation']
        assert 'prognosis_kwh' in gen, "Missing prognosis_kwh in generation"
        assert 'total_kwh' in gen, "Missing total_kwh in generation"
        assert 'performance_percent' in gen, "Missing performance_percent in generation"
        
        fin = data['financial']
        assert 'saved_brl' in fin, "Missing saved_brl (Economia) in financial"
        
        print(f"KPIs found - Prognosis: {gen['prognosis_kwh']}, Generation: {gen['total_kwh']}, Performance: {gen['performance_percent']}%, Economia: {fin['saved_brl']}")


class TestPDFUploadTariffValues:
    """Test PDF upload returns tariff_values with new fields"""
    
    def test_upload_group_a_pdf_tariff_values(self, auth_headers):
        """POST /api/invoices/upload-pdf-auto returns tariff_values for Group A PDF"""
        pdf_path = "/tmp/113577680_geradora.pdf"
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found at {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('113577680_geradora.pdf', f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/api/invoices/upload-pdf-auto",
                headers=auth_headers,
                files=files
            )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        
        assert data.get('success') == True, f"Upload not successful: {data}"
        
        parsed = data.get('parsed_data', {})
        tariff_values = parsed.get('tariff_values', {})
        
        # Verify tariff_total_p and tariff_total_fp
        assert 'tariff_total_p' in tariff_values, "Missing tariff_total_p"
        assert 'tariff_total_fp' in tariff_values, "Missing tariff_total_fp"
        assert 'te_p_unit' in tariff_values, "Missing te_p_unit"
        assert 'te_fp_unit' in tariff_values, "Missing te_fp_unit"
        
        # Verify expected values
        assert abs(tariff_values['tariff_total_p'] - 2.21079) < 0.001, f"tariff_total_p incorrect: {tariff_values['tariff_total_p']}"
        assert abs(tariff_values['tariff_total_fp'] - 0.51475) < 0.001, f"tariff_total_fp incorrect: {tariff_values['tariff_total_fp']}"
        assert abs(tariff_values['te_p_unit'] - 0.562895) < 0.001, f"te_p_unit incorrect: {tariff_values['te_p_unit']}"
        assert abs(tariff_values['te_fp_unit'] - 0.3503) < 0.001, f"te_fp_unit incorrect: {tariff_values['te_fp_unit']}"
        
        print(f"Tariff values correct: tariff_total_p={tariff_values['tariff_total_p']}, tariff_total_fp={tariff_values['tariff_total_fp']}")
    
    def test_upload_group_a_pdf_amount_saved(self, auth_headers):
        """Parser extracts amount_saved_brl=159.07 for UC 113577680"""
        pdf_path = "/tmp/113577680_geradora.pdf"
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found at {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('113577680_geradora.pdf', f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/api/invoices/upload-pdf-auto",
                headers=auth_headers,
                files=files
            )
        
        assert response.status_code == 200
        data = response.json()
        parsed = data.get('parsed_data', {})
        
        amount_saved = parsed.get('amount_saved_brl', 0)
        assert abs(amount_saved - 159.07) < 0.01, f"amount_saved_brl incorrect: {amount_saved}, expected 159.07"
        print(f"amount_saved_brl correct: {amount_saved}")
    
    def test_upload_group_a_pdf_energy_compensated(self, auth_headers):
        """Parser extracts energy_compensated_p_kwh=303 and energy_billed_p_kwh=-265 for UC 113577680"""
        pdf_path = "/tmp/113577680_geradora.pdf"
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found at {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('113577680_geradora.pdf', f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/api/invoices/upload-pdf-auto",
                headers=auth_headers,
                files=files
            )
        
        assert response.status_code == 200
        data = response.json()
        parsed = data.get('parsed_data', {})
        
        energy_compensated_p = parsed.get('energy_compensated_p_kwh', 0)
        energy_billed_p = parsed.get('energy_billed_p_kwh', 0)
        
        assert abs(energy_compensated_p - 303) < 0.1, f"energy_compensated_p_kwh incorrect: {energy_compensated_p}, expected 303"
        assert abs(energy_billed_p - (-265)) < 0.1, f"energy_billed_p_kwh incorrect: {energy_billed_p}, expected -265"
        
        print(f"Energy values correct: compensated_p={energy_compensated_p}, billed_p={energy_billed_p}")
    
    def test_upload_group_b_pdf(self, auth_headers):
        """POST /api/invoices/upload-pdf-auto works for Group B PDF"""
        pdf_path = "/tmp/102480958.pdf"
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found at {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('102480958.pdf', f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/api/invoices/upload-pdf-auto",
                headers=auth_headers,
                files=files
            )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        
        assert data.get('success') == True, f"Upload not successful: {data}"
        
        parsed = data.get('parsed_data', {})
        assert parsed.get('tariff_group') == 'B', f"Expected Group B, got {parsed.get('tariff_group')}"
        print(f"Group B PDF parsed successfully, UC: {parsed.get('uc_number')}")


class TestInvoiceAPIEndpoints:
    """Test invoice CRUD endpoints"""
    
    def test_list_invoices(self, auth_headers):
        """GET /api/invoices returns list"""
        response = requests.get(f"{BASE_URL}/api/invoices", headers=auth_headers)
        assert response.status_code == 200
        invoices = response.json()
        assert isinstance(invoices, list)
        print(f"Found {len(invoices)} invoices")
    
    def test_unauthorized_access(self):
        """GET /api/invoices without auth returns 401/403"""
        response = requests.get(f"{BASE_URL}/api/invoices")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
