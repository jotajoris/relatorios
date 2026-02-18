import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../services/api';
import KPICard from '../components/KPICard';
import StatusBadge from '../components/StatusBadge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import {
  Sun,
  TrendingUp,
  DollarSign,
  Leaf,
  ArrowLeft,
  Upload,
  Calendar,
  Zap,
  FileText,
  Loader2
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
  ReferenceLine
} from 'recharts';

const formatCurrency = (value) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value);
};

const formatNumber = (value) => {
  return new Intl.NumberFormat('pt-BR').format(value);
};

const PlantDetail = () => {
  const { plantId } = useParams();
  const [plant, setPlant] = useState(null);
  const [client, setClient] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);

  const loadPlantData = useCallback(async () => {
    try {
      const [plantRes, reportRes] = await Promise.all([
        api.get(`/plants/${plantId}`),
        api.get(`/reports/plant/${plantId}?month=${selectedMonth}`)
      ]);
      
      setPlant(plantRes.data);
      setReportData(reportRes.data);
      
      if (reportRes.data.client) {
        setClient(reportRes.data.client);
      }
      
      // Format chart data
      const dailyData = reportRes.data.generation.daily_data || [];
      setChartData(dailyData.map((d, i) => ({
        day: i + 1,
        generation: d.generation_kwh,
        prognosis: reportRes.data.plant.monthly_prognosis_kwh / 30
      })));
      
    } catch (error) {
      toast.error('Erro ao carregar dados da usina');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [plantId, selectedMonth]);

  useEffect(() => {
    loadPlantData();
  }, [loadPlantData]);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    try {
      const response = await api.post(`/generation-data/upload/${plantId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success(`Upload concluído: ${response.data.total_processed} registros processados`);
      setUploadDialogOpen(false);
      loadPlantData();
    } catch (error) {
      toast.error('Erro ao fazer upload do arquivo');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 spinner"></div>
      </div>
    );
  }

  if (!plant) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <p className="text-neutral-500">Usina não encontrada</p>
        <Button asChild className="mt-4">
          <Link to="/usinas">Voltar para Usinas</Link>
        </Button>
      </div>
    );
  }

  const generation = reportData?.generation || {};
  const financial = reportData?.financial || {};
  const environmental = reportData?.environmental || {};

  return (
    <div className="space-y-6 animate-fade-in" data-testid="plant-detail-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/usinas">
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl lg:text-3xl font-bold text-neutral-900 font-heading">
                {plant.name}
              </h1>
              <StatusBadge status={plant.status} />
            </div>
            <p className="text-neutral-500 mt-1">
              {client?.name || 'Cliente'} • {plant.capacity_kwp} kWp
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-neutral-400" />
            <Input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="w-40"
            />
          </div>
          <Button 
            onClick={() => setUploadDialogOpen(true)}
            variant="outline"
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload Dados
          </Button>
          <Button asChild className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]">
            <Link to={`/relatorios?plant=${plantId}&month=${selectedMonth}`}>
              <FileText className="h-4 w-4 mr-2" />
              Gerar Relatório
            </Link>
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        <KPICard
          title="Geração"
          value={`${formatNumber(generation.total_kwh || 0)} kWh`}
          icon={Sun}
          accent="yellow"
          subtitle={`Meta: ${formatNumber(generation.prognosis_kwh || 0)} kWh`}
        />
        <KPICard
          title="Desempenho"
          value={`${generation.performance_percent || 0}%`}
          icon={TrendingUp}
          accent={generation.performance_percent >= 80 ? 'green' : 'red'}
          subtitle="vs prognóstico"
        />
        <KPICard
          title="Economia"
          value={formatCurrency(financial.saved_brl || 0)}
          icon={DollarSign}
          accent="blue"
          subtitle={`Faturado: ${formatCurrency(financial.billed_brl || 0)}`}
        />
        <KPICard
          title="CO₂ Evitado"
          value={`${formatNumber(environmental.co2_avoided_kg || 0)} kg`}
          icon={Leaf}
          accent="gray"
          subtitle={`≈ ${environmental.trees_saved || 0} árvores`}
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="generation" className="space-y-6">
        <TabsList className="bg-neutral-100">
          <TabsTrigger value="generation">Geração</TabsTrigger>
          <TabsTrigger value="financial">Financeiro</TabsTrigger>
          <TabsTrigger value="units">Unidades Consumidoras</TabsTrigger>
        </TabsList>

        <TabsContent value="generation" className="space-y-6">
          {/* Daily Generation Chart */}
          <Card className="border-neutral-100 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Zap className="h-5 w-5 text-[#FFD600]" />
                Geração Diária
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" vertical={false} />
                    <XAxis 
                      dataKey="day" 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#737373', fontSize: 11 }}
                    />
                    <YAxis 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#737373', fontSize: 11 }}
                      tickFormatter={(value) => `${value} kWh`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #e5e5e5',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                      }}
                      formatter={(value) => [`${formatNumber(value)} kWh`]}
                      labelFormatter={(label) => `Dia ${label}`}
                    />
                    <ReferenceLine 
                      y={plant.monthly_prognosis_kwh / 30} 
                      stroke="#A1A1AA" 
                      strokeDasharray="5 5"
                      label={{ value: 'Meta', position: 'right', fill: '#737373', fontSize: 11 }}
                    />
                    <Bar dataKey="generation" fill="#FFD600" radius={[4, 4, 0, 0]} name="Geração" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Historical Chart */}
          {reportData?.historical && reportData.historical.length > 0 && (
            <Card className="border-neutral-100 shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-emerald-600" />
                  Histórico de Geração (12 meses)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={reportData.historical} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
                      <XAxis 
                        dataKey="month" 
                        axisLine={false} 
                        tickLine={false}
                        tick={{ fill: '#737373', fontSize: 11 }}
                        tickFormatter={(value) => {
                          const [year, month] = value.split('-');
                          return `${month}/${year.slice(2)}`;
                        }}
                      />
                      <YAxis 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fill: '#737373', fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#fff',
                          border: '1px solid #e5e5e5',
                          borderRadius: '8px'
                        }}
                        formatter={(value, name) => [
                          `${formatNumber(value)} kWh`,
                          name === 'generation_kwh' ? 'Geração' : 'Prognóstico'
                        ]}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="generation_kwh" 
                        name="Geração" 
                        stroke="#FFD600" 
                        strokeWidth={2}
                        dot={{ fill: '#FFD600', strokeWidth: 2 }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="prognosis_kwh" 
                        name="Prognóstico" 
                        stroke="#A1A1AA" 
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="financial" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="border-neutral-100 shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Resumo Financeiro</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center py-3 border-b border-neutral-100">
                  <span className="text-neutral-600">Economia no mês</span>
                  <span className="text-xl font-bold text-emerald-600">
                    {formatCurrency(financial.saved_brl || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center py-3 border-b border-neutral-100">
                  <span className="text-neutral-600">Valor faturado</span>
                  <span className="text-xl font-bold text-neutral-900">
                    {formatCurrency(financial.billed_brl || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center py-3 border-b border-neutral-100">
                  <span className="text-neutral-600">Retorno financeiro (mês)</span>
                  <span className="text-xl font-bold text-[#EAB308]">
                    {financial.roi_monthly_percent || 0}%
                  </span>
                </div>
                <div className="flex justify-between items-center py-3">
                  <span className="text-neutral-600">Retorno total acumulado</span>
                  <span className="text-xl font-bold text-blue-600">
                    {financial.roi_total_percent || 0}%
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card className="border-neutral-100 shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Economia Total</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <p className="text-4xl font-bold text-emerald-600">
                    {formatCurrency(financial.total_savings_all_time || 0)}
                  </p>
                  <p className="text-neutral-500 mt-2">desde a instalação</p>
                </div>
                {plant.total_investment > 0 && (
                  <div className="mt-6 p-4 bg-amber-50 rounded-lg">
                    <p className="text-sm text-amber-800">
                      <strong>Investimento inicial:</strong> {formatCurrency(plant.total_investment)}
                    </p>
                    <div className="mt-2 w-full h-2 bg-amber-200 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-amber-500 rounded-full"
                        style={{ width: `${Math.min(financial.roi_total_percent || 0, 100)}%` }}
                      />
                    </div>
                    <p className="text-xs text-amber-700 mt-1">
                      {financial.roi_total_percent || 0}% do investimento recuperado
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="units" className="space-y-6">
          <Card className="border-neutral-100 shadow-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Unidades Consumidoras</CardTitle>
                <Button variant="outline" size="sm" asChild>
                  <Link to={`/unidades-consumidoras?plant=${plantId}`}>
                    Gerenciar UCs
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {reportData?.consumer_units && reportData.consumer_units.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-neutral-100">
                        <th className="table-header text-left py-3 px-4">Contrato</th>
                        <th className="table-header text-left py-3 px-4">Endereço</th>
                        <th className="table-header text-left py-3 px-4">Tipo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.consumer_units.map((unit) => (
                        <tr key={unit.id} className="table-row">
                          <td className="py-4 px-4 text-sm font-medium text-neutral-900">
                            {unit.contract_number}
                          </td>
                          <td className="py-4 px-4 text-sm text-neutral-600">
                            {unit.address}
                          </td>
                          <td className="py-4 px-4">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
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
              ) : (
                <div className="text-center py-8 text-neutral-500">
                  Nenhuma unidade consumidora cadastrada
                </div>
              )}
            </CardContent>
          </Card>

          {/* Invoices table */}
          {reportData?.invoices && reportData.invoices.length > 0 && (
            <Card className="border-neutral-100 shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Faturas do Mês</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-neutral-100">
                        <th className="table-header text-left py-3 px-3">UC</th>
                        <th className="table-header text-right py-3 px-3">Consumo</th>
                        <th className="table-header text-right py-3 px-3">Compensado</th>
                        <th className="table-header text-right py-3 px-3">Faturado</th>
                        <th className="table-header text-right py-3 px-3">Economia</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.invoices.map((invoice) => (
                        <tr key={invoice.id} className="table-row">
                          <td className="py-3 px-3 text-neutral-900">
                            {reportData.consumer_units.find(u => u.id === invoice.consumer_unit_id)?.contract_number || '-'}
                          </td>
                          <td className="py-3 px-3 text-right text-neutral-600">
                            {formatNumber(invoice.consumption_fora_ponta_kwh + invoice.consumption_ponta_kwh)} kWh
                          </td>
                          <td className="py-3 px-3 text-right text-neutral-600">
                            {formatNumber(invoice.energy_compensated_kwh)} kWh
                          </td>
                          <td className="py-3 px-3 text-right font-medium text-neutral-900">
                            {formatCurrency(invoice.amount_billed_brl)}
                          </td>
                          <td className="py-3 px-3 text-right font-medium text-emerald-600">
                            {formatCurrency(invoice.amount_saved_brl)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Upload de Dados de Geração</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <p className="text-sm text-neutral-600">
              Faça upload de um arquivo Excel (.xlsx) ou CSV com os dados de geração diária.
            </p>
            <div className="p-4 bg-neutral-50 rounded-lg">
              <p className="text-sm font-medium text-neutral-700 mb-2">Formato esperado:</p>
              <ul className="text-xs text-neutral-500 space-y-1">
                <li>• Coluna com data (ex: "data", "date", "dia")</li>
                <li>• Coluna com geração em kWh (ex: "geracao", "kwh", "energia")</li>
              </ul>
            </div>
            <div className="border-2 border-dashed border-neutral-200 rounded-lg p-6 text-center">
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={handleFileUpload}
                className="hidden"
                id="file-upload"
                disabled={uploading}
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                {uploading ? (
                  <div className="flex flex-col items-center">
                    <Loader2 className="h-8 w-8 text-[#FFD600] animate-spin mb-2" />
                    <span className="text-sm text-neutral-600">Processando arquivo...</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <Upload className="h-8 w-8 text-neutral-400 mb-2" />
                    <span className="text-sm text-neutral-600">
                      Clique para selecionar ou arraste o arquivo
                    </span>
                    <span className="text-xs text-neutral-400 mt-1">.xlsx, .xls ou .csv</span>
                  </div>
                )}
              </label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setUploadDialogOpen(false)}>
              Cancelar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PlantDetail;
