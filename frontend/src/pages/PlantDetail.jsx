import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend
} from 'recharts';
import { 
  Sun,
  Zap,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  Upload,
  Plus,
  Edit,
  Trash2,
  FileText,
  Settings,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Building2,
  MapPin,
  Percent,
  Clock,
  Loader2,
  ExternalLink,
  Copy,
  Image
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PlantDetail = () => {
  const { plantId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [data, setData] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [availableYears, setAvailableYears] = useState([]);
  
  // Dialogs
  const [ucDialogOpen, setUcDialogOpen] = useState(false);
  const [editingUc, setEditingUc] = useState(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Form data
  const [ucFormData, setUcFormData] = useState({
    uc_number: '',
    address: '',
    classification: 'B3-Comercial',
    compensation_percentage: 0,
    is_generator: false
  });
  
  const [plantFormData, setPlantFormData] = useState({});

  useEffect(() => {
    loadData();
  }, [plantId]);

  useEffect(() => {
    if (data?.plant) {
      loadChartData();
    }
  }, [data?.plant]);

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/plants/${plantId}/full-details`);
      setData(response.data);
      setPlantFormData(response.data.plant || {});
      
      // Load available years for reports
      try {
        const yearsRes = await api.get(`/reports/${plantId}/years`);
        setAvailableYears(yearsRes.data);
      } catch (e) {
        setAvailableYears([new Date().getFullYear()]);
      }
    } catch (error) {
      toast.error('Erro ao carregar dados da usina');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadChartData = async () => {
    try {
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      const response = await api.get(`/dashboard/generation-chart/${plantId}`, {
        params: { start_date: startDate, end_date: endDate }
      });
      setChartData(response.data);
    } catch (error) {
      console.error('Error loading chart data:', error);
    }
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await api.post(`/upload/logo/plant/${plantId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (response.data.success) {
        toast.success('Logo atualizado com sucesso');
        loadData();
      }
    } catch (error) {
      toast.error('Erro ao fazer upload da logo');
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await api.put(`/plants/${plantId}`, plantFormData);
      toast.success('Configurações salvas');
      setConfigDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error('Erro ao salvar configurações');
    } finally {
      setSaving(false);
    }
  };

  const handleAddUc = () => {
    setEditingUc(null);
    setUcFormData({
      uc_number: '',
      address: '',
      classification: 'B3-Comercial',
      compensation_percentage: 0,
      is_generator: false
    });
    setUcDialogOpen(true);
  };

  const handleEditUc = (uc) => {
    setEditingUc(uc);
    setUcFormData({
      uc_number: uc.uc_number || '',
      address: uc.address || '',
      classification: `${uc.tariff_group || 'B'}${uc.tariff_modality ? '-' + uc.tariff_modality : '3'}-Comercial`,
      compensation_percentage: uc.compensation_percentage || 0,
      is_generator: uc.is_generator || false
    });
    setUcDialogOpen(true);
  };

  const handleSaveUc = async () => {
    if (!ucFormData.uc_number.trim()) {
      toast.error('Número da UC é obrigatório');
      return;
    }

    setSaving(true);
    try {
      const ucData = {
        plant_id: plantId,
        uc_number: ucFormData.uc_number,
        address: ucFormData.address,
        tariff_group: ucFormData.classification.charAt(0),
        compensation_percentage: parseFloat(ucFormData.compensation_percentage) || 0,
        is_generator: ucFormData.is_generator
      };

      if (editingUc) {
        await api.put(`/consumer-units/${editingUc.id}`, ucData);
        toast.success('UC atualizada');
      } else {
        await api.post('/consumer-units', ucData);
        toast.success('UC cadastrada');
      }
      setUcDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error('Erro ao salvar UC');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteUc = async (uc) => {
    if (!window.confirm(`Deseja remover a UC ${uc.uc_number}?`)) return;
    
    try {
      await api.delete(`/consumer-units/${uc.id}`);
      toast.success('UC removida');
      loadData();
    } catch (error) {
      toast.error('Erro ao remover UC');
    }
  };

  const copyShareLink = () => {
    const link = `${window.location.origin}/public/plant/${data.plant.public_share_token || plantId}`;
    navigator.clipboard.writeText(link);
    toast.success('Link copiado!');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 spinner"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-neutral-500">Usina não encontrada</p>
      </div>
    );
  }

  const { plant, client, generators, beneficiaries, reports, stats, activities } = data;

  return (
    <div className="space-y-6 animate-fade-in" data-testid="plant-detail-page">
      {/* Header */}
      <div className="bg-[#1A1A1A] rounded-xl p-6 text-white">
        <div className="flex items-start gap-6">
          {/* Logo */}
          <div 
            className="w-20 h-20 bg-[#FFD600] rounded-lg flex items-center justify-center cursor-pointer overflow-hidden"
            onClick={() => fileInputRef.current?.click()}
          >
            {plant.logo_url || client?.logo_url ? (
              <img 
                src={`${API_URL}${plant.logo_url || client?.logo_url}`} 
                alt="Logo" 
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="text-center">
                <Image className="h-8 w-8 text-[#1A1A1A] mx-auto" />
                <span className="text-xs text-[#1A1A1A]">Logo</span>
              </div>
            )}
          </div>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleLogoUpload}
            accept="image/*"
            className="hidden"
          />
          
          {/* Info */}
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{plant.name}</h1>
            <div className="flex items-center gap-4 mt-2 text-neutral-300 text-sm">
              <span className="flex items-center gap-1">
                <Building2 className="h-4 w-4" />
                {client?.contact_person || client?.name || 'Responsável'}
              </span>
              {plant.installation_date && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  {plant.installation_date}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Zap className="h-4 w-4" />
                {plant.annual_prognosis_kwh ? `${(plant.annual_prognosis_kwh / 1000).toFixed(2)} MWh/ano` : '-'}
              </span>
            </div>
          </div>
          
          {/* KPIs */}
          <div className="flex gap-4">
            <div className="bg-white/10 rounded-lg px-6 py-3 text-center min-w-[140px]">
              <p className="text-xs text-neutral-400">Status</p>
              <div className="flex items-center justify-center gap-2 mt-1">
                <span className="text-2xl font-bold">Ok</span>
                <CheckCircle className="h-6 w-6 text-green-400" />
              </div>
            </div>
            <div className="bg-white/10 rounded-lg px-6 py-3 text-center min-w-[140px]">
              <p className="text-xs text-neutral-400">Potência Instalada</p>
              <p className="text-2xl font-bold">{plant.capacity_kwp}<span className="text-sm font-normal">kWp</span></p>
            </div>
            <div className="bg-[#FFD600] text-[#1A1A1A] rounded-lg px-6 py-3 text-center min-w-[140px]">
              <p className="text-xs">Geração 12 Meses</p>
              <p className="text-2xl font-bold">{(stats.total_generation_12m_kwh / 1000).toFixed(2)}<span className="text-sm font-normal">MWh</span></p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4 bg-neutral-100">
          <TabsTrigger value="overview" className="data-[state=active]:bg-[#FFD600] data-[state=active]:text-[#1A1A1A]">
            Visão Geral
          </TabsTrigger>
          <TabsTrigger value="reports" className="data-[state=active]:bg-[#FFD600] data-[state=active]:text-[#1A1A1A]">
            Relatórios
          </TabsTrigger>
          <TabsTrigger value="credits" className="data-[state=active]:bg-[#FFD600] data-[state=active]:text-[#1A1A1A]">
            Sistema de Crédito
          </TabsTrigger>
          <TabsTrigger value="config" className="data-[state=active]:bg-[#FFD600] data-[state=active]:text-[#1A1A1A]">
            Configurações
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Visão Geral */}
        <TabsContent value="overview" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chart */}
            <div className="lg:col-span-2">
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Geração Diária</CardTitle>
                    <div className="flex items-center gap-2 text-sm">
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 bg-[#FFD600] rounded"></div>
                        <span>Geração</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-0.5 bg-red-500"></div>
                        <span>Prognóstico</span>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis 
                          dataKey="date" 
                          tickFormatter={(value) => value.split('-')[2]}
                          fontSize={12}
                        />
                        <YAxis 
                          tickFormatter={(value) => `${value} kWh`}
                          fontSize={12}
                        />
                        <Tooltip 
                          formatter={(value, name) => [
                            `${value.toFixed(2)} kWh`,
                            name === 'generation' ? 'Geração' : 'Prognóstico'
                          ]}
                        />
                        <Bar dataKey="generation" fill="#FFD600" radius={[4, 4, 0, 0]} />
                        <ReferenceLine y={chartData[0]?.prognosis || 0} stroke="#ef4444" strokeDasharray="5 5" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  
                  {/* Stats below chart */}
                  <div className="flex justify-center gap-12 mt-4 pt-4 border-t">
                    <div className="text-center">
                      <p className="text-sm text-neutral-500">Gerado</p>
                      <p className="text-xl font-bold">{(chartData.reduce((sum, d) => sum + d.generation, 0) / 1000).toFixed(2)} MWh</p>
                    </div>
                    <div className="text-center">
                      <p className="text-sm text-neutral-500">Desempenho</p>
                      <p className="text-xl font-bold text-green-600">
                        {chartData.length > 0 
                          ? `${((chartData.reduce((sum, d) => sum + d.generation, 0) / chartData.reduce((sum, d) => sum + d.prognosis, 0)) * 100).toFixed(2)}%`
                          : '-'}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Activity Timeline */}
            <div className="lg:col-span-1">
              <Card className="h-full">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Timeline</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4 max-h-[350px] overflow-y-auto">
                    {activities && activities.length > 0 ? (
                      activities.slice(0, 10).map((activity, idx) => (
                        <div key={idx} className="flex gap-3 text-sm">
                          <div className="w-8 h-8 bg-[#FFD600] rounded-full flex items-center justify-center flex-shrink-0">
                            <Clock className="h-4 w-4 text-[#1A1A1A]" />
                          </div>
                          <div>
                            <p className="text-neutral-500 text-xs">
                              {new Date(activity.created_at).toLocaleString('pt-BR')}
                            </p>
                            <p className="text-neutral-900">{activity.description}</p>
                            {activity.user_name && (
                              <p className="text-xs text-[#FFD600]">{activity.user_name}</p>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-neutral-500 text-center py-4">Nenhuma atividade recente</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Tab 2: Relatórios */}
        <TabsContent value="reports" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="bg-[#FFD600] text-[#1A1A1A] px-3 py-1 rounded font-medium">
                    Geração
                  </div>
                  <Button variant="outline" size="sm">
                    Gerar Relatório Personalizado
                  </Button>
                </div>
                
                {/* Year Navigation */}
                <div className="flex items-center gap-2">
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setSelectedYear(y => y - 1)}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Ano anterior
                  </Button>
                  <span className="font-bold text-lg px-4">{selectedYear}</span>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setSelectedYear(y => y + 1)}
                  >
                    Próximo ano
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {Array.from({ length: 12 }, (_, i) => {
                  const month = i + 1;
                  const report = reports?.find(r => r.month === month && r.year === selectedYear);
                  const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                  
                  return (
                    <Card 
                      key={month} 
                      className={`cursor-pointer transition-all hover:shadow-md ${
                        report ? 'border-[#FFD600]' : 'border-neutral-200 opacity-60'
                      }`}
                    >
                      <CardContent className="p-4 text-center">
                        <div className="flex items-center justify-center gap-2 mb-2">
                          <FileText className={`h-4 w-4 ${report ? 'text-[#FFD600]' : 'text-neutral-400'}`} />
                          <span className="text-sm font-medium">{monthNames[i]}/{selectedYear}</span>
                        </div>
                        <p className="text-xs text-neutral-500">Desempenho</p>
                        <p className={`text-lg font-bold ${
                          report?.performance_percentage >= 100 ? 'text-green-600' : 
                          report?.performance_percentage >= 80 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {report ? `${report.performance_percentage.toFixed(2)}%` : '-'}
                        </p>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Sistema de Crédito */}
        <TabsContent value="credits" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Listas de Distribuição de Créditos</CardTitle>
                  <p className="text-sm text-neutral-500 mt-1">
                    Configure as UCs geradoras e beneficiárias com suas porcentagens
                  </p>
                </div>
                <Button 
                  onClick={handleAddUc}
                  className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Adicionar UC
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {/* Active Distribution List Header */}
              <div className="bg-[#FFD600] text-[#1A1A1A] px-4 py-2 rounded-t-lg font-medium flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                Vigência 12/2025 - Baseada em Lista de Porcentagem
              </div>
              
              {/* Table */}
              <div className="border border-t-0 rounded-b-lg overflow-hidden">
                <table className="w-full">
                  <thead className="bg-neutral-50">
                    <tr>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-600">Denominação</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-600">Contrato</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-neutral-600">Classificação</th>
                      <th className="text-right px-4 py-3 text-sm font-medium text-neutral-600">Porcentagem</th>
                      <th className="text-right px-4 py-3 text-sm font-medium text-neutral-600">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Generators first */}
                    {generators?.map((uc, idx) => (
                      <tr key={uc.id} className="border-t hover:bg-neutral-50">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <Sun className="h-4 w-4 text-amber-500" />
                            <span className="font-medium">{uc.address || plant.name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-neutral-600">{uc.uc_number}</td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-sm">
                            {uc.tariff_modality || `${uc.tariff_group || 'A'}4-Comercial`}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right font-medium">0%</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-1">
                            <Button variant="ghost" size="sm" onClick={() => handleEditUc(uc)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteUc(uc)}>
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    
                    {/* Beneficiaries */}
                    {beneficiaries?.map((uc, idx) => (
                      <tr key={uc.id} className="border-t hover:bg-neutral-50">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <Zap className="h-4 w-4 text-blue-500" />
                            <span>{uc.address}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-neutral-600">{uc.uc_number}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded text-sm ${
                            uc.tariff_modality?.includes('B1') 
                              ? 'bg-blue-100 text-blue-700' 
                              : 'bg-green-100 text-green-700'
                          }`}>
                            {uc.tariff_modality || `${uc.tariff_group || 'B'}3-Comercial`}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right font-medium">{uc.compensation_percentage || 0}%</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-1">
                            <Button variant="ghost" size="sm" onClick={() => handleEditUc(uc)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteUc(uc)}>
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    
                    {(!generators?.length && !beneficiaries?.length) && (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-neutral-500">
                          Nenhuma UC cadastrada. Clique em "Adicionar UC" para começar.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              
              {/* Total percentage indicator */}
              {beneficiaries?.length > 0 && (
                <div className="mt-4 p-4 bg-neutral-50 rounded-lg">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-neutral-600">Total de porcentagem distribuída:</span>
                    <span className={`font-bold ${
                      beneficiaries.reduce((sum, uc) => sum + (uc.compensation_percentage || 0), 0) === 100
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}>
                      {beneficiaries.reduce((sum, uc) => sum + (uc.compensation_percentage || 0), 0).toFixed(2)}%
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 4: Configurações */}
        <TabsContent value="config" className="mt-6">
          <div className="space-y-6">
            {/* Cadastro */}
            <Card>
              <CardHeader>
                <CardTitle>Cadastro</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-6">
                  {/* Logo */}
                  <div 
                    className="w-24 h-24 bg-neutral-100 rounded-lg flex items-center justify-center cursor-pointer border-2 border-dashed border-neutral-300 hover:border-[#FFD600] transition-colors"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {plant.logo_url ? (
                      <img src={`${API_URL}${plant.logo_url}`} alt="Logo" className="w-full h-full object-cover rounded-lg" />
                    ) : (
                      <div className="text-center">
                        <Upload className="h-6 w-6 text-neutral-400 mx-auto" />
                        <span className="text-xs text-neutral-500">Logo</span>
                      </div>
                    )}
                  </div>
                  
                  {/* Info */}
                  <div className="flex-1 space-y-1 text-sm">
                    <p><strong>{plant.name}</strong></p>
                    <p>Potência: {plant.capacity_kwp} kWp</p>
                    <p>Total Investido: R$ {(plant.total_investment || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
                    <p>Data de Importação: {plant.installation_date || '-'}</p>
                    <p>Geração Anual Acordada: {plant.annual_prognosis_kwh?.toLocaleString('pt-BR')} kWh</p>
                    <p>Endereço: {plant.city} - {plant.state}, {plant.address}</p>
                  </div>
                </div>
                <Button variant="link" className="mt-4 text-[#FFD600] p-0" onClick={() => setConfigDialogOpen(true)}>
                  Editar Cadastro
                </Button>
              </CardContent>
            </Card>

            {/* Preferências */}
            <Card>
              <CardHeader>
                <CardTitle>Preferências</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>Exibir alerta de relatórios ausentes</Label>
                  <Switch 
                    checked={plantFormData.show_missing_reports_alert}
                    onCheckedChange={(v) => setPlantFormData({...plantFormData, show_missing_reports_alert: v})}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label>Usina Ativa (monitorada)</Label>
                  <Switch 
                    checked={plantFormData.is_monitored}
                    onCheckedChange={(v) => setPlantFormData({...plantFormData, is_monitored: v})}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label>Usar configurações globais de notificação</Label>
                  <Switch 
                    checked={plantFormData.use_global_notifications}
                    onCheckedChange={(v) => setPlantFormData({...plantFormData, use_global_notifications: v})}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label>Notificar usuário quando a usina entrar em estado crítico</Label>
                  <Switch 
                    checked={plantFormData.notify_critical_state}
                    onCheckedChange={(v) => setPlantFormData({...plantFormData, notify_critical_state: v})}
                  />
                </div>
                <Button onClick={handleSaveConfig} className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]">
                  Salvar Preferências
                </Button>
              </CardContent>
            </Card>

            {/* Link de Compartilhamento */}
            <Card>
              <CardHeader>
                <CardTitle>Link de compartilhamento</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-neutral-500">
                  Use esse link para compartilhar as informações de geração dessa usina.
                </p>
                <div className="flex items-center gap-2">
                  <Switch 
                    checked={plantFormData.public_share_enabled}
                    onCheckedChange={(v) => setPlantFormData({...plantFormData, public_share_enabled: v})}
                  />
                  <Label>Permitir que as informações de geração dessa usina sejam vistas por qualquer um com o link.</Label>
                </div>
                {plantFormData.public_share_enabled && (
                  <div className="flex gap-2">
                    <Input 
                      readOnly 
                      value={`${window.location.origin}/public/plant/${plant.public_share_token || plantId}`}
                      className="flex-1"
                    />
                    <Button variant="outline" onClick={copyShareLink}>
                      <Copy className="h-4 w-4" />
                    </Button>
                    <Button variant="outline" onClick={() => window.open(`/public/plant/${plant.public_share_token || plantId}`, '_blank')}>
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Perda de Eficiência */}
            <Card>
              <CardHeader>
                <CardTitle>Perda de Eficiência</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-neutral-500 mb-4">
                  Defina a porcentagem de perda de eficiência da usina por ano.
                </p>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>1º ano:</span>
                    <span className="font-medium">{plantFormData.efficiency_loss_year1 || 2.5}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>2º ano:</span>
                    <span className="font-medium">{plantFormData.efficiency_loss_year2 || 1.5}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Demais anos:</span>
                    <span className="font-medium">{plantFormData.efficiency_loss_other || 0.5}%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* UC Dialog */}
      <Dialog open={ucDialogOpen} onOpenChange={setUcDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingUc ? 'Editar UC' : 'Nova UC'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Número da UC *</Label>
              <Input
                value={ucFormData.uc_number}
                onChange={(e) => setUcFormData({...ucFormData, uc_number: e.target.value})}
                placeholder="Ex: 113577680"
              />
            </div>
            <div className="space-y-2">
              <Label>Endereço</Label>
              <Input
                value={ucFormData.address}
                onChange={(e) => setUcFormData({...ucFormData, address: e.target.value})}
                placeholder="Rua, número, bairro"
              />
            </div>
            <div className="space-y-2">
              <Label>Classificação</Label>
              <Select
                value={ucFormData.classification}
                onValueChange={(v) => setUcFormData({...ucFormData, classification: v})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="A4-Comercial">A4 - Comercial</SelectItem>
                  <SelectItem value="A4-Industrial">A4 - Industrial</SelectItem>
                  <SelectItem value="B1-Residencial">B1 - Residencial</SelectItem>
                  <SelectItem value="B2-Rural">B2 - Rural</SelectItem>
                  <SelectItem value="B3-Comercial">B3 - Comercial</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between p-4 bg-amber-50 rounded-lg">
              <div>
                <Label className="text-amber-900">Unidade Geradora</Label>
                <p className="text-xs text-amber-700">Marque se é uma UC onde há geração</p>
              </div>
              <Switch
                checked={ucFormData.is_generator}
                onCheckedChange={(v) => setUcFormData({...ucFormData, is_generator: v, compensation_percentage: v ? 0 : ucFormData.compensation_percentage})}
              />
            </div>
            {!ucFormData.is_generator && (
              <div className="space-y-2">
                <Label>Porcentagem de Compensação (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={ucFormData.compensation_percentage}
                  onChange={(e) => setUcFormData({...ucFormData, compensation_percentage: e.target.value})}
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUcDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleSaveUc} disabled={saving} className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Config Dialog */}
      <Dialog open={configDialogOpen} onOpenChange={setConfigDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Editar Cadastro da Usina</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4 max-h-[60vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Nome da Usina</Label>
                <Input
                  value={plantFormData.name || ''}
                  onChange={(e) => setPlantFormData({...plantFormData, name: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Potência (kWp)</Label>
                <Input
                  type="number"
                  value={plantFormData.capacity_kwp || ''}
                  onChange={(e) => setPlantFormData({...plantFormData, capacity_kwp: parseFloat(e.target.value)})}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Total Investido (R$)</Label>
                <Input
                  type="number"
                  value={plantFormData.total_investment || ''}
                  onChange={(e) => setPlantFormData({...plantFormData, total_investment: parseFloat(e.target.value)})}
                />
              </div>
              <div className="space-y-2">
                <Label>Data de Instalação</Label>
                <Input
                  type="date"
                  value={plantFormData.installation_date || ''}
                  onChange={(e) => setPlantFormData({...plantFormData, installation_date: e.target.value})}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Geração Mensal Acordada (kWh)</Label>
                <Input
                  type="number"
                  value={plantFormData.monthly_prognosis_kwh || ''}
                  onChange={(e) => setPlantFormData({...plantFormData, monthly_prognosis_kwh: parseFloat(e.target.value)})}
                />
              </div>
              <div className="space-y-2">
                <Label>Geração Anual Acordada (kWh)</Label>
                <Input
                  type="number"
                  value={plantFormData.annual_prognosis_kwh || ''}
                  onChange={(e) => setPlantFormData({...plantFormData, annual_prognosis_kwh: parseFloat(e.target.value)})}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Endereço</Label>
              <Input
                value={plantFormData.address || ''}
                onChange={(e) => setPlantFormData({...plantFormData, address: e.target.value})}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Cidade</Label>
                <Input
                  value={plantFormData.city || ''}
                  onChange={(e) => setPlantFormData({...plantFormData, city: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Estado</Label>
                <Input
                  value={plantFormData.state || ''}
                  onChange={(e) => setPlantFormData({...plantFormData, state: e.target.value})}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Marca do Inversor</Label>
              <Select
                value={plantFormData.inverter_brand || ''}
                onValueChange={(v) => setPlantFormData({...plantFormData, inverter_brand: v})}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecione" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="growatt">Growatt</SelectItem>
                  <SelectItem value="solis">Solis</SelectItem>
                  <SelectItem value="fronius">Fronius</SelectItem>
                  <SelectItem value="sma">SMA</SelectItem>
                  <SelectItem value="huawei">Huawei</SelectItem>
                  <SelectItem value="outro">Outro</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfigDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleSaveConfig} disabled={saving} className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PlantDetail;
