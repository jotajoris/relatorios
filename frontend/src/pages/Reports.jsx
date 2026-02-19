import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { FileText, Download, Loader2 } from 'lucide-react';

const Reports = () => {
  const [searchParams] = useSearchParams();
  const plantIdParam = searchParams.get('plant');
  const monthParam = searchParams.get('month');
  
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedPlant, setSelectedPlant] = useState(plantIdParam || '');
  const [selectedMonth, setSelectedMonth] = useState(
    monthParam || `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
  );
  const [reportType, setReportType] = useState('monthly');
  const [previewData, setPreviewData] = useState(null);

  useEffect(() => {
    loadPlants();
  }, []);

  useEffect(() => {
    if (selectedPlant && selectedMonth) {
      loadPreview();
    }
  }, [selectedPlant, selectedMonth]);

  const loadPlants = async () => {
    try {
      const response = await api.get('/plants');
      setPlants(response.data);
      if (plantIdParam && response.data.find(p => p.id === plantIdParam)) {
        setSelectedPlant(plantIdParam);
      }
    } catch (error) {
      toast.error('Erro ao carregar usinas');
    } finally {
      setLoading(false);
    }
  };

  const loadPreview = async () => {
    try {
      const response = await api.get(`/reports/plant/${selectedPlant}?month=${selectedMonth}`);
      setPreviewData(response.data);
    } catch (error) {
      console.error(error);
    }
  };

  const handleGenerateReport = async () => {
    if (!selectedPlant) {
      toast.error('Selecione uma usina');
      return;
    }

    setGenerating(true);
    try {
      const response = await api.get(`/reports/download-pdf/${selectedPlant}?month=${selectedMonth}`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `relatorio_${selectedMonth}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('PDF gerado com sucesso!');
    } catch (error) {
      if (error.response?.status === 501) {
        toast.info('Geração de PDF será implementada em breve. Veja a prévia abaixo.');
        await loadPreview();
      } else {
        toast.error('Erro ao gerar relatório');
      }
    } finally {
      setGenerating(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value || 0);
  };

  const formatNumber = (value) => {
    return new Intl.NumberFormat('pt-BR').format(value || 0);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="reports-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold text-neutral-900 font-heading">Relatórios</h1>
        <p className="text-neutral-500 mt-1">Gere relatórios profissionais para seus clientes</p>
      </div>

      {/* Report Config */}
      <Card className="border-neutral-200 shadow-sm bg-white">
        <CardHeader className="bg-white border-b border-neutral-100">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="h-5 w-5 text-[#EAB308]" />
            Configurar Relatório
          </CardTitle>
        </CardHeader>
        <CardContent className="bg-white pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>Usina *</Label>
              <Select value={selectedPlant} onValueChange={setSelectedPlant}>
                <SelectTrigger data-testid="report-plant-select">
                  <SelectValue placeholder="Selecione uma usina" />
                </SelectTrigger>
                <SelectContent>
                  {plants.map((plant) => (
                    <SelectItem key={plant.id} value={plant.id}>
                      {plant.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Período</Label>
              <Input
                type="month"
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Tipo de Relatório</Label>
              <Select value={reportType} onValueChange={setReportType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">Mensal</SelectItem>
                  <SelectItem value="annual">Anual</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <Button 
                onClick={handleGenerateReport}
                disabled={!selectedPlant || generating}
                className="w-full bg-[#1A1A1A] hover:bg-neutral-800 text-white"
                data-testid="generate-report-btn"
              >
                {generating ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                Gerar PDF
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Report Preview */}
      {previewData && (
        <Card className="border-neutral-200 shadow-sm overflow-hidden">
          <CardHeader className="bg-[#1A1A1A] text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <img 
                  src="https://customer-assets.emergentagent.com/job_powerplant-analytics/artifacts/q3i8xrcz_Logo%20ON%20sem%20fundo.png" 
                  alt="ON Soluções" 
                  className="h-10"
                />
                <div>
                  <h2 className="text-lg font-semibold">{previewData.plant?.name}</h2>
                  <p className="text-sm text-neutral-400">
                    {previewData.client?.name} • {previewData.plant?.capacity_kwp} kWp
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-[#FFD600]">
                  {selectedMonth.split('-')[1]}/{selectedMonth.split('-')[0]}
                </p>
                <p className="text-sm text-neutral-400">Relatório Mensal</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6 bg-white">
            {/* KPIs Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="p-4 bg-white rounded-lg border border-neutral-200 border-l-4 border-l-[#FFD600]">
                <p className="text-sm text-neutral-500 uppercase tracking-wide">Prognostico</p>
                <p className="text-2xl font-bold text-neutral-900">
                  {formatNumber(previewData.generation?.prognosis_kwh)} kWh
                </p>
              </div>
              <div className="p-4 bg-white rounded-lg border border-neutral-200 border-l-4 border-l-[#1A1A1A]">
                <p className="text-sm text-neutral-500 uppercase tracking-wide">Geracao do Mes</p>
                <p className="text-2xl font-bold text-neutral-900">
                  {formatNumber(previewData.generation?.total_kwh)} kWh
                </p>
              </div>
              <div className="p-4 bg-white rounded-lg border border-neutral-200 border-l-4 border-l-emerald-500">
                <p className="text-sm text-neutral-500 uppercase tracking-wide">Desempenho</p>
                <p className={`text-2xl font-bold ${
                  (previewData.generation?.performance_percent || 0) >= 100
                    ? 'text-emerald-600'
                    : (previewData.generation?.performance_percent || 0) >= 80
                      ? 'text-amber-600'
                      : 'text-red-600'
                }`}>
                  {previewData.generation?.performance_percent}%
                </p>
              </div>
              <div className="p-4 bg-white rounded-lg border border-neutral-200 border-l-4 border-l-blue-500">
                <p className="text-sm text-neutral-500 uppercase tracking-wide">Economia</p>
                <p className="text-2xl font-bold text-neutral-900">
                  {formatCurrency(previewData.financial?.saved_brl)}
                </p>
              </div>
            </div>

            {/* More Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-4">Prognóstico</h3>
                <div className="space-y-3">
                  <div className="flex justify-between p-3 bg-neutral-50 rounded-lg border border-neutral-100">
                    <span className="text-neutral-600">Geração acordada (mensal)</span>
                    <span className="font-medium">{formatNumber(previewData.plant?.monthly_prognosis_kwh)} kWh</span>
                  </div>
                  <div className="flex justify-between p-3 bg-neutral-50 rounded-lg border border-neutral-100">
                    <span className="text-neutral-600">Geração acordada (anual)</span>
                    <span className="font-medium">{formatNumber(previewData.plant?.annual_prognosis_kwh)} kWh</span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-4">Financeiro</h3>
                <div className="space-y-3">
                  <div className="flex justify-between p-3 bg-neutral-50 rounded-lg border border-neutral-100">
                    <span className="text-neutral-600">Valor faturado</span>
                    <span className="font-medium">{formatCurrency(previewData.financial?.billed_brl)}</span>
                  </div>
                  <div className="flex justify-between p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                    <span className="text-neutral-600">Economia total (acumulada)</span>
                    <span className="font-bold text-emerald-600">{formatCurrency(previewData.financial?.total_savings_all_time)}</span>
                  </div>
                  <div className="flex justify-between p-3 bg-amber-50/50 rounded-lg border border-amber-100">
                    <span className="text-neutral-600">Retorno financeiro total</span>
                    <span className="font-bold text-amber-700">{previewData.financial?.roi_total_percent}%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Consumer Units */}
            {previewData.consumer_units && previewData.consumer_units.length > 0 && (
              <div className="mt-8">
                <h3 className="text-lg font-semibold text-neutral-900 mb-4">Unidades Consumidoras</h3>
                <div className="overflow-x-auto border border-neutral-200 rounded-lg">
                  <table className="w-full text-sm">
                    <thead className="bg-neutral-50">
                      <tr className="border-b border-neutral-200">
                        <th className="text-left py-3 px-4 text-neutral-600 font-medium">Contrato</th>
                        <th className="text-left py-3 px-4 text-neutral-600 font-medium">Endereço</th>
                        <th className="text-left py-3 px-4 text-neutral-600 font-medium">Tipo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.consumer_units.map((unit) => (
                        <tr key={unit.id} className="border-b border-neutral-100 last:border-0">
                          <td className="py-3 px-4 font-medium text-neutral-900">{unit.contract_number}</td>
                          <td className="py-3 px-4 text-neutral-600">{unit.address}</td>
                          <td className="py-3 px-4">
                            <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium ${
                              unit.is_generator 
                                ? 'bg-amber-100 text-amber-700' 
                                : 'bg-blue-100 text-blue-700'
                            }`}>
                              {unit.is_generator ? 'Geradora' : 'Beneficiária'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Environmental Impact */}
            <div className="mt-8 p-6 bg-gradient-to-r from-emerald-50 to-blue-50 rounded-xl border border-emerald-100">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4">Impacto Ambiental</h3>
              <div className="grid grid-cols-2 gap-6">
                <div className="text-center">
                  <p className="text-4xl font-bold text-emerald-600">
                    {formatNumber(previewData.environmental?.co2_avoided_tons || 0)}t
                  </p>
                  <p className="text-sm text-neutral-600 mt-1">CO₂ deixados de emitir</p>
                </div>
                <div className="text-center">
                  <p className="text-4xl font-bold text-blue-600">
                    {formatNumber(previewData.environmental?.trees_saved || 0)}
                  </p>
                  <p className="text-sm text-neutral-600 mt-1">Árvores salvas (equivalente)</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!previewData && !selectedPlant && (
        <Card className="border-neutral-200 shadow-sm bg-white">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center bg-white">
            <div className="p-4 bg-neutral-100 rounded-full mb-4">
              <FileText className="h-8 w-8 text-neutral-400" />
            </div>
            <h3 className="text-lg font-medium text-neutral-900 mb-1">Selecione uma usina</h3>
            <p className="text-sm text-neutral-500">
              Escolha uma usina acima para visualizar e gerar o relatório
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Reports;
