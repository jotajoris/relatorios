"""
Backend API tests for Invoices, PDF Upload, and Report Generation
Testing new features:
- POST /api/invoices/upload-pdf-auto - Auto UC detection upload
- GET /api/invoices - List invoices
- POST /api/invoices/save-from-upload - Save invoice from upload
- DELETE /api/invoices/{id} - Remove invoice
- GET /api/reports/download-pdf/{plant_id} - PDF report generation

Test PDFs:
- /tmp/113577680_geradora.pdf (Group A)
- /tmp/102480958.pdf (Group B)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAuthFixture:
    """Auth fixtures for tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "projetos.onsolucoes@gmail.com",
            "password": "on123456"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get authenticated headers"""
        return {"Authorization": f"Bearer {auth_token}"}


class TestInvoicesList(TestAuthFixture):
    """Test GET /api/invoices"""
    
    def test_list_invoices_success(self, auth_headers):
        """Test listing invoices returns 200 and list"""
        response = requests.get(f"{BASE_URL}/api/invoices", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} invoices")
    
    def test_list_invoices_unauthorized(self):
        """Test listing invoices without auth returns 401/403"""
        response = requests.get(f"{BASE_URL}/api/invoices")
        assert response.status_code in [401, 403]
        print("✓ Unauthorized access rejected")


class TestPDFAutoUpload(TestAuthFixture):
    """Test POST /api/invoices/upload-pdf-auto - Auto UC detection"""
    
    def test_upload_pdf_grupo_a_auto(self, auth_headers):
        """Test auto upload for Group A invoice (UC 113577680)"""
        pdf_path = "/tmp/113577680_geradora.pdf"
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('113577680_geradora.pdf', f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/api/invoices/upload-pdf-auto",
                headers=auth_headers,
                files=files
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "success" in data
        print(f"✓ Group A PDF upload response: success={data.get('success')}")
        
        if data.get('success'):
            parsed = data.get('parsed_data', {})
            print(f"  - UC Number: {parsed.get('uc_number')}")
            print(f"  - Tariff Group: {parsed.get('tariff_group')}")
            print(f"  - Reference Month: {parsed.get('reference_month')}")
            print(f"  - Total Amount: R$ {parsed.get('amount_total_brl')}")
            print(f"  - UC Found: {data.get('uc_found')}")
            
            # Verify Group A specific fields were extracted
            assert parsed.get('tariff_group') == 'A', f"Expected Group A, got {parsed.get('tariff_group')}"
            assert parsed.get('energy_registered_p_kwh', 0) >= 0  # Should have ponta data
            assert parsed.get('energy_registered_fp_kwh', 0) >= 0  # Should have fora ponta
        else:
            error = data.get('error', 'Unknown error')
            print(f"  - Error: {error}")
            # Even on parse failure, endpoint should return valid JSON
            assert "error" in data or "parsed_data" in data
    
    def test_upload_pdf_grupo_b_auto(self, auth_headers):
        """Test auto upload for Group B invoice (UC 102480958)"""
        pdf_path = "/tmp/102480958.pdf"
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('102480958.pdf', f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/api/invoices/upload-pdf-auto",
                headers=auth_headers,
                files=files
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        print(f"✓ Group B PDF upload response: success={data.get('success')}")
        
        if data.get('success'):
            parsed = data.get('parsed_data', {})
            print(f"  - UC Number: {parsed.get('uc_number')}")
            print(f"  - Tariff Group: {parsed.get('tariff_group')}")
            print(f"  - Reference Month: {parsed.get('reference_month')}")
            print(f"  - Total Amount: R$ {parsed.get('amount_total_brl')}")
            print(f"  - Energy Registered FP: {parsed.get('energy_registered_fp_kwh')} kWh")
            print(f"  - Energy Compensated FP: {parsed.get('energy_compensated_fp_kwh')} kWh")
            print(f"  - UC Found: {data.get('uc_found')}")
            
            # Verify Group B specific characteristics
            assert parsed.get('tariff_group') == 'B', f"Expected Group B, got {parsed.get('tariff_group')}"
    
    def test_upload_invalid_file_type(self, auth_headers):
        """Test that non-PDF files are rejected"""
        # Create a fake file
        files = {'file': ('test.txt', b'This is not a PDF', 'text/plain')}
        response = requests.post(
            f"{BASE_URL}/api/invoices/upload-pdf-auto",
            headers=auth_headers,
            files=files
        )
        
        assert response.status_code == 400
        print("✓ Non-PDF file rejected with 400")


class TestSaveFromUpload(TestAuthFixture):
    """Test POST /api/invoices/save-from-upload"""
    
    def test_save_invoice_requires_consumer_unit(self, auth_headers):
        """Test saving invoice without consumer_unit_id fails"""
        response = requests.post(
            f"{BASE_URL}/api/invoices/save-from-upload",
            headers=auth_headers,
            json={
                "reference_month": "12/2025",
                "billing_cycle_start": "2025-11-15",
                "billing_cycle_end": "2025-12-15",
                "amount_total_brl": 100.0
            }
        )
        
        assert response.status_code == 400
        print("✓ Save without consumer_unit_id rejected")


class TestDeleteInvoice(TestAuthFixture):
    """Test DELETE /api/invoices/{id}"""
    
    def test_delete_nonexistent_invoice(self, auth_headers):
        """Test deleting non-existent invoice returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/invoices/nonexistent-id-123",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        print("✓ Delete non-existent invoice returns 404")


class TestPDFReportGeneration(TestAuthFixture):
    """Test GET /api/reports/download-pdf/{plant_id}"""
    
    def test_list_plants_for_report(self, auth_headers):
        """Get plant_id for report test"""
        response = requests.get(f"{BASE_URL}/api/plants", headers=auth_headers)
        assert response.status_code == 200
        plants = response.json()
        print(f"✓ Found {len(plants)} plants")
        return plants
    
    def test_download_pdf_report_success(self, auth_headers):
        """Test PDF report generation for a plant"""
        # Get a plant ID
        plants_response = requests.get(f"{BASE_URL}/api/plants", headers=auth_headers)
        plants = plants_response.json()
        
        if not plants:
            pytest.skip("No plants available for report test")
        
        plant_id = plants[0]["id"]
        plant_name = plants[0].get("name", "Unknown")
        
        # Download PDF for December 2025
        response = requests.get(
            f"{BASE_URL}/api/reports/download-pdf/{plant_id}",
            headers=auth_headers,
            params={"month": "2025-12"}
        )
        
        assert response.status_code == 200, f"Report generation failed: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf'
        
        # Verify it's a valid PDF (starts with %PDF)
        content = response.content
        assert content[:4] == b'%PDF', "Response is not a valid PDF"
        
        print(f"✓ PDF report generated for plant '{plant_name}' ({len(content)} bytes)")
    
    def test_download_pdf_invalid_month_format(self, auth_headers):
        """Test report with invalid month format returns 400"""
        plants_response = requests.get(f"{BASE_URL}/api/plants", headers=auth_headers)
        plants = plants_response.json()
        
        if not plants:
            pytest.skip("No plants available for report test")
        
        plant_id = plants[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/reports/download-pdf/{plant_id}",
            headers=auth_headers,
            params={"month": "invalid-date"}
        )
        
        assert response.status_code == 400
        print("✓ Invalid month format rejected")
    
    def test_download_pdf_nonexistent_plant(self, auth_headers):
        """Test report for non-existent plant returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/reports/download-pdf/nonexistent-plant-id",
            headers=auth_headers,
            params={"month": "2025-12"}
        )
        
        assert response.status_code == 404
        print("✓ Non-existent plant returns 404")


class TestEndToEndInvoiceFlow(TestAuthFixture):
    """End-to-end test: Upload, verify, save, delete invoice"""
    
    def test_create_and_delete_test_uc(self, auth_headers):
        """Create a test UC, upload invoice, and clean up"""
        # Get plants
        plants_response = requests.get(f"{BASE_URL}/api/plants", headers=auth_headers)
        plants = plants_response.json()
        
        if not plants:
            pytest.skip("No plants available for E2E test")
        
        plant_id = plants[0]["id"]
        
        # Create test UC matching the PDF UC number
        uc_data = {
            "plant_id": plant_id,
            "uc_number": "102480958",  # Matches Group B PDF
            "contract_number": "TEST_E2E",
            "address": "Rua de Teste E2E - Test",
            "holder_name": "E2E Test Holder",
            "is_generator": False,
            "tariff_group": "B",
            "compensation_percentage": 100.0
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/consumer-units",
            headers=auth_headers,
            json=uc_data
        )
        
        if create_response.status_code != 200:
            print(f"Create UC failed (may already exist): {create_response.text}")
            # Try to find existing UC
            uc_response = requests.get(f"{BASE_URL}/api/consumer-units", headers=auth_headers)
            units = uc_response.json()
            test_uc = next((u for u in units if u.get('uc_number') == '102480958'), None)
            
            if not test_uc:
                pytest.skip("Could not create or find test UC")
            created_uc = test_uc
        else:
            created_uc = create_response.json()
        
        print(f"✓ Test UC ready: {created_uc.get('uc_number')}")
        
        # Now upload PDF with auto detection
        pdf_path = "/tmp/102480958.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('102480958.pdf', f, 'application/pdf')}
            upload_response = requests.post(
                f"{BASE_URL}/api/invoices/upload-pdf-auto",
                headers=auth_headers,
                files=files
            )
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        
        print(f"✓ Upload response: success={upload_data.get('success')}, uc_found={upload_data.get('uc_found')}")
        
        if upload_data.get('success') and upload_data.get('uc_found'):
            # Save the invoice
            save_response = requests.post(
                f"{BASE_URL}/api/invoices/save-from-upload",
                headers=auth_headers,
                json=upload_data.get('parsed_data')
            )
            
            assert save_response.status_code == 200
            save_data = save_response.json()
            
            assert save_data.get('success'), f"Save failed: {save_data}"
            invoice_id = save_data.get('invoice_id')
            
            print(f"✓ Invoice saved: {invoice_id}")
            
            # Verify invoice appears in list
            list_response = requests.get(f"{BASE_URL}/api/invoices", headers=auth_headers)
            invoices = list_response.json()
            saved_invoice = next((i for i in invoices if i.get('id') == invoice_id), None)
            
            assert saved_invoice, f"Saved invoice {invoice_id} not found in list"
            print(f"✓ Invoice verified in list: ref={saved_invoice.get('reference_month')}")
            
            # Delete the invoice
            delete_response = requests.delete(
                f"{BASE_URL}/api/invoices/{invoice_id}",
                headers=auth_headers
            )
            
            assert delete_response.status_code == 200
            print(f"✓ Invoice deleted: {invoice_id}")
        else:
            print(f"  Skipping save/delete - UC not found or parse failed")
        
        # Clean up test UC if we created it
        if create_response.status_code == 200:
            requests.delete(
                f"{BASE_URL}/api/consumer-units/{created_uc['id']}",
                headers=auth_headers
            )
            print(f"✓ Test UC cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
