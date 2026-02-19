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
  Image,
  Download,
  FileSpreadsheet
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PlantDetail = () => {
  const { plantId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const excelInputRef = useRef(null);
  const invoiceInputRef = useRef(null);
  
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [data, setData] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [availableYears, setAvailableYears] = useState([]);
  const [chartMonth, setChartMonth] = useState(`${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`);
  const [ucInvoiceStatus, setUcInvoiceStatus] = useState([]);
  
  // Dialogs
  const [ucDialogOpen, setUcDialogOpen] = useState(false);
  const [editingUc, setEditingUc] = useState(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // PDF Download
  const [downloadingPdf, setDownloadingPdf] = useState(null);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState(null);
  const [reportType, setReportType] = useState('basic');
  const [monthlySummary, setMonthlySummary] = useState([]);
  
  // Excel Upload
  const [uploadingExcel, setUploadingExcel] = useState(false);
  
  // Invoice Upload
  const [uploadingInvoice, setUploadingInvoice] = useState(false);
  const [invoiceDialogOpen, setInvoiceDialogOpen] = useState(false);
  const [parsedInvoice, setParsedInvoice] = useState(null);
  const [selectedUcForInvoice, setSelectedUcForInvoice] = useState('');
  
  // Growatt integration
  const [growattDialogOpen, setGrowattDialogOpen] = useState(false);
  const [growattLoading, setGrowattLoading] = useState(false);
  const [growattPlants, setGrowattPlants] = useState([]);
  const [growattCredentials, setGrowattCredentials] = useState({
    username: '',
    password: ''
  });
  const [selectedGrowattPlant, setSelectedGrowattPlant] = useState(null);
  const [syncingGrowatt, setSyncingGrowatt] = useState(false);
  
  // Form data
  const [ucFormData, setUcFormData] = useState({
    uc_number: '',
    address: '',
    classification: 'B3-Comercial',
    compensation_percentage: 0,
    is_generator: false
  });
  
  const [plantFormData, setPlantFormData] = useState({});

  // City/State selection for irradiance
  const [statesList, setStatesList] = useState([]);
  const [filteredCities, setFilteredCities] = useState([]);
  const [citySearchText, setCitySearchText] = useState('');
  const [showCityDropdown, setShowCityDropdown] = useState(false);
  const [calculatingPrognosis, setCalculatingPrognosis] = useState(false);
  const [prognosisDetail, setPrognosisDetail] = useState(null);

  const loadStates = async () => {
    try {
      const res = await api.get('/irradiance/states');
      setStatesList(res.data);
    } catch { }
  };

  const loadCitiesByState = async (state) => {
    if (!state) { setFilteredCities([]); return; }
    try {
      const res = await api.get(`/irradiance/cities?state=${encodeURIComponent(state)}`);
      setFilteredCities(res.data.map(c => c.city).sort());
    } catch { setFilteredCities([]); }
  };

  const handleStateSelect = (e) => {
    const state = e.target.value;
    setPlantFormData(prev => ({...prev, state}));
    setCitySearchText('');
    loadCitiesByState(state);
  };

  const handleCityClick = (city) => {
    setPlantFormData(prev => ({...prev, city}));
    setCitySearchText(city);
    setShowCityDropdown(false);
  };

  const cityMatches = filteredCities.filter(c => 
    !citySearchText || c.toLowerCase().includes(citySearchText.toLowerCase())
  ).slice(0, 50);

  const calculatePrognosis = async () => {
    if (!plantFormData.city || !plantFormData.capacity_kwp) {
      toast.error('Preencha o estado, cidade e potencia');
      return;
    }
    setCalculatingPrognosis(true);
    try {
      const res = await api.post('/irradiance/calculate-prognosis', {
        city: plantFormData.city,
        capacity_kwp: plantFormData.capacity_kwp,
      });
      const d = res.data;
      setPrognosisDetail(d);
      setPlantFormData(prev => ({
        ...prev,
        monthly_prognosis_kwh: d.average_monthly_kwh,
        annual_prognosis_kwh: d.total_annual_kwh,
      }));
      toast.success(`Prognostico calculado: ${(d.total_annual_kwh/1000).toFixed(2)} MWh/ano`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao calcular prognostico');
    } finally {
      setCalculatingPrognosis(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [plantId]);

  useEffect(() => {
    if (data?.plant) {
      loadChartData();
    }
  }, [data?.plant, chartMonth]);

  useEffect(() => {
    if (plantId && selectedYear) {
      loadMonthlySummary();
      loadUcInvoiceStatus();
    }
  }, [plantId, selectedYear]);

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/plants/${plantId}/full-details`);
      setData(response.data);
      setPlantFormData(response.data.plant || {});
      loadStates();
      
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
      const response = await api.get(`/dashboard/generation-chart/${plantId}`, {
        params: { month: chartMonth }
      });
      setChartData(response.data);
    } catch (error) {
      console.error('Error loading chart data:', error);
    }
  };

  const loadMonthlySummary = async () => {
    try {
      const res = await api.get(`/plants/${plantId}/monthly-summary?year=${selectedYear}`);
      setMonthlySummary(res.data);
    } catch (error) {
      console.error('Error loading monthly summary:', error);
    }
  };

  const loadUcInvoiceStatus = async () => {
    try {
      const unitsRes = await api.get(`/consumer-units?plant_id=${plantId}`);
      const invoicesRes = await api.get(`/invoices?plant_id=${plantId}`);
      const units = unitsRes.data || [];
      const invoices = invoicesRes.data || [];
      // Build status for each UC and each month of selectedYear
      const statuses = units.map(u => {
        const months = {};
        for (let m = 1; m <= 12; m++) {
          const ref = `${String(m).padStart(2,'0')}/${selectedYear}`;
          const hasInvoice = invoices.some(inv => inv.consumer_unit_id === u.id && inv.reference_month === ref);
          months[m] = hasInvoice;
        }
        return { ...u, invoiceMonths: months };
      });
      setUcInvoiceStatus(statuses);
    } catch (error) {
      console.error('Error loading UC invoice status:', error);
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

  // Growatt Integration Functions
  const handleGrowattLogin = async () => {
    if (!growattCredentials.username || !growattCredentials.password) {
      toast.error('Preencha usuário e senha');
      return;
    }
    
    setGrowattLoading(true);
    try {
      const response = await api.post('/integrations/growatt/login', {
        username: growattCredentials.username,
        password: growattCredentials.password
      });
      
      if (response.data.success) {
        setGrowattPlants(response.data.plants || []);
        toast.success(`${response.data.total} usinas encontradas na Growatt`);
        
        // Auto-select plant if name matches
        const matchingPlant = response.data.plants?.find(
          p => p.name.toLowerCase().includes(data?.plant?.name?.toLowerCase()) ||
               data?.plant?.name?.toLowerCase().includes(p.name.toLowerCase())
        );
        if (matchingPlant) {
          setSelectedGrowattPlant(matchingPlant);
          toast.info(`Usina "${matchingPlant.name}" selecionada automaticamente`);
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao conectar com Growatt');
    } finally {
      setGrowattLoading(false);
    }
  };

  const handleSyncGrowatt = async () => {
    if (!selectedGrowattPlant) {
      toast.error('Selecione uma usina da Growatt');
      return;
    }
    
    setSyncingGrowatt(true);
    try {
      // First, link the plant
      await api.post(`/integrations/growatt/link-plant?plant_id=${plantId}&growatt_plant_name=${encodeURIComponent(selectedGrowattPlant.name)}`);
      
      // Then sync data
      const response = await api.post('/integrations/growatt/sync', {
        username: growattCredentials.username,
        password: growattCredentials.password,
        plant_name: selectedGrowattPlant.name
      });
      
      if (response.data.success) {
        toast.success('Dados sincronizados com sucesso!');
        setGrowattDialogOpen(false);
        loadData();
        loadChartData();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao sincronizar dados');
    } finally {
      setSyncingGrowatt(false);
    }
  };

  // PDF Download Functions
  const handleDownloadPdf = async (month) => {
    const monthStr = `${selectedYear}-${String(month).padStart(2, '0')}`;
    setDownloadingPdf(month);
    
    try {
      const response = await api.get(`/reports/download-pdf/${plantId}`, {
        params: { month: monthStr },
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `relatorio_${data?.plant?.name?.replace(/\s+/g, '_')}_${monthStr}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Relatório baixado com sucesso!');
    } catch (error) {
      toast.error('Erro ao gerar relatório PDF');
      console.error(error);
    } finally {
      setDownloadingPdf(null);
    }
  };

  const openReportDialog = (month) => {
    setSelectedMonth(month);
    setReportDialogOpen(true);
  };

  // Excel Upload Functions
  const handleExcelUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setUploadingExcel(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await api.post(`/generation-data/upload-growatt-excel/${plantId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (response.data.success) {
        const { parsed_data } = response.data;
        toast.success(
          `Excel importado: ${parsed_data.plant_name} - ${parsed_data.month_year}\n` +
          `${response.data.total_processed} registros processados (${parsed_data.total_generation_kwh?.toLocaleString()} kWh)`
        );
        loadData();
        loadChartData();
      } else {
        toast.error(response.data.error || 'Erro ao processar Excel');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao fazer upload do Excel');
    } finally {
      setUploadingExcel(false);
      if (excelInputRef.current) {
        excelInputRef.current.value = '';
      }
    }
  };

  // Invoice Upload Functions - Auto-detect UC
  const handleInvoiceUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setUploadingInvoice(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      // Use auto-detect endpoint - no need to select UC first
      const response = await api.post('/invoices/upload-pdf-auto', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (response.data.success) {
        if (response.data.uc_found) {
          // UC was found, show parsed data
          setParsedInvoice({
            ...response.data.parsed_data,
            uc_info: response.data.consumer_unit
          });
          toast.success(`Fatura da UC ${response.data.consumer_unit.uc_number} processada!`);
        } else {
          // UC not found
          toast.warning(response.data.message);
          setParsedInvoice({
            ...response.data.parsed_data,
            uc_not_found: true
          });
        }
        setInvoiceDialogOpen(true);
      } else {
        toast.error(response.data.error || 'Erro ao processar fatura');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao fazer upload da fatura');
    } finally {
      setUploadingInvoice(false);
      if (invoiceInputRef.current) {
        invoiceInputRef.current.value = '';
      }
    }
  };

  const handleSaveInvoice = async () => {
    if (!parsedInvoice) return;
    
    setSaving(true);
    try {
      // Create invoice from parsed data
      const invoiceData = {
        consumer_unit_id: parsedInvoice.consumer_unit_id,
        plant_id: parsedInvoice.plant_id,
        reference_month: parsedInvoice.reference_month,
        billing_cycle_start: parsedInvoice.billing_cycle_start,
        billing_cycle_end: parsedInvoice.billing_cycle_end,
        due_date: parsedInvoice.due_date,
        amount_total_brl: parsedInvoice.amount_total_brl,
        amount_saved_brl: parsedInvoice.amount_saved_brl,
        energy_registered_fp_kwh: parsedInvoice.energy_registered_fp_kwh,
        energy_registered_p_kwh: parsedInvoice.energy_registered_p_kwh,
        energy_injected_fp_kwh: parsedInvoice.energy_injected_fp_kwh,
        energy_injected_p_kwh: parsedInvoice.energy_injected_p_kwh,
        energy_compensated_fp_kwh: parsedInvoice.energy_compensated_fp_kwh,
        energy_compensated_p_kwh: parsedInvoice.energy_compensated_p_kwh,
        energy_billed_fp_kwh: parsedInvoice.energy_billed_fp_kwh,
        credits_balance_fp_kwh: parsedInvoice.credits_balance_fp_kwh,
        credits_accumulated_fp_kwh: parsedInvoice.credits_accumulated_fp_kwh,
        tariff_group: parsedInvoice.tariff_group,
        tariff_flag: parsedInvoice.tariff_flag,
        demand_contracted_kw: parsedInvoice.demand_contracted_kw,
        demand_measured_kw: parsedInvoice.demand_measured_kw,
      };
      
      await api.post('/invoices', invoiceData);
      toast.success('Fatura salva com sucesso!');
      setParsedInvoice(null);
      setInvoiceDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao salvar fatura');
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
                  {/* Month navigation */}
                  <div className="flex items-center gap-2 mt-2">
                    <Button variant="ghost" size="sm" onClick={() => {
                      const [y, m] = chartMonth.split('-').map(Number);
                      const prev = m === 1 ? `${y-1}-12` : `${y}-${String(m-1).padStart(2,'0')}`;
                      setChartMonth(prev);
                    }}><ChevronLeft className="h-4 w-4" /></Button>
                    <Input type="month" value={chartMonth} onChange={e => setChartMonth(e.target.value)} className="w-44 h-8 text-sm" />
                    <Button variant="ghost" size="sm" onClick={() => {
                      const [y, m] = chartMonth.split('-').map(Number);
                      const next = m === 12 ? `${y+1}-01` : `${y}-${String(m+1).padStart(2,'0')}`;
                      setChartMonth(next);
                    }}><ChevronRight className="h-4 w-4" /></Button>
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
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="bg-[#FFD600] text-[#1A1A1A] px-3 py-1 rounded font-medium">
                    Geração
                  </div>
                  
                  {/* Upload Excel Growatt */}
                  <input
                    ref={excelInputRef}
                    type="file"
                    accept=".xls,.xlsx"
                    onChange={handleExcelUpload}
                    className="hidden"
                  />
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => excelInputRef.current?.click()}
                    disabled={uploadingExcel}
                  >
                    {uploadingExcel ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <FileSpreadsheet className="h-4 w-4 mr-2" />
                    )}
                    Importar Excel Growatt
                  </Button>
                  
                  {/* Upload Invoice */}
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setInvoiceDialogOpen(true)}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Enviar Fatura COPEL
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
                  const summary = monthlySummary.find(s => s.month === month) || {};
                  const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                  const hasData = summary.generation_kwh > 0;
                  const perf = summary.performance_percent || 0;
                  
                  return (
                    <Card 
                      key={month} 
                      className={`transition-all hover:shadow-md ${
                        hasData ? 'border-[#FFD600]' : 'border-neutral-200'
                      }`}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-3">
                          <FileText className={`h-4 w-4 ${hasData ? 'text-[#FFD600]' : 'text-neutral-400'}`} />
                          <span className="text-sm font-semibold">{monthNames[i]}/{selectedYear}</span>
                        </div>

                        <div className="space-y-2 mb-3">
                          <div>
                            <p className="text-[10px] text-neutral-400 uppercase">Geracao</p>
                            <p className="text-sm font-bold text-[#1A1A1A]">
                              {hasData ? `${(summary.generation_kwh / 1000).toFixed(2)} MWh` : '-'}
                            </p>
                          </div>
                          <div>
                            <p className="text-[10px] text-neutral-400 uppercase">Prognostico</p>
                            <p className="text-sm text-neutral-600">
                              {summary.prognosis_kwh ? `${(summary.prognosis_kwh / 1000).toFixed(2)} MWh` : '-'}
                            </p>
                          </div>
                          <div>
                            <p className="text-[10px] text-neutral-400 uppercase">Desempenho</p>
                            <p className={`text-lg font-bold ${
                              !hasData ? 'text-neutral-300' :
                              perf >= 100 ? 'text-emerald-600' : 
                              perf >= 80 ? 'text-amber-500' : 'text-red-500'
                            }`}>
                              {hasData ? `${perf.toFixed(1)}%` : '-'}
                            </p>
                          </div>
                        </div>
                        
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full text-xs h-8"
                          onClick={() => handleDownloadPdf(month)}
                          disabled={downloadingPdf === month}
                          data-testid={`download-report-${month}`}
                        >
                          {downloadingPdf === month ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <>
                              <Download className="h-3 w-3 mr-1" />
                              Baixar PDF
                            </>
                          )}
                        </Button>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* UC Invoice Status Table */}
          {ucInvoiceStatus.length > 0 && (
            <Card className="mt-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Status de Faturas por UC - {selectedYear}</CardTitle>
                <p className="text-xs text-neutral-500">Clique no relogio para adicionar a fatura que esta faltando</p>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-[#1A1A1A] text-[#FFD600]">
                        <th className="text-left py-2 px-2 font-medium rounded-tl-md">UC</th>
                        <th className="text-left py-2 px-2 font-medium">Tipo</th>
                        {['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'].map((m,i) => (
                          <th key={i} className={`text-center py-2 px-1 font-medium ${i===11?'rounded-tr-md':''}`}>{m}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {ucInvoiceStatus.map((uc, idx) => (
                        <tr key={uc.id} className={idx % 2 === 0 ? 'bg-white' : 'bg-neutral-50'}>
                          <td className="py-1.5 px-2 font-medium text-[#1A1A1A]">{uc.uc_number}</td>
                          <td className="py-1.5 px-2">
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${uc.is_generator ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}>
                              {uc.is_generator ? 'GER' : 'BEN'}
                            </span>
                          </td>
                          {Array.from({length:12}, (_,m) => {
                            const has = uc.invoiceMonths?.[m+1];
                            return (
                              <td key={m} className="text-center py-1.5 px-1">
                                {has ? (
                                  <CheckCircle className="h-4 w-4 text-green-500 mx-auto" />
                                ) : (
                                  <button
                                    onClick={() => navigate('/faturas')}
                                    className="mx-auto block hover:scale-110 transition-transform"
                                    title={`Adicionar fatura ${['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][m]}/${selectedYear}`}
                                  >
                                    <Clock className="h-4 w-4 text-amber-400" />
                                  </button>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
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

            {/* Integração Growatt */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sun className="h-5 w-5 text-[#FFD600]" />
                  Integração com Inversores
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-neutral-500">
                  Conecte esta usina ao portal Growatt para sincronizar automaticamente os dados de geração.
                </p>
                
                {plant.growatt_plant_name ? (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center gap-2 text-green-700">
                      <CheckCircle className="h-5 w-5" />
                      <span className="font-medium">Conectado ao Growatt</span>
                    </div>
                    <p className="text-sm text-green-600 mt-1">
                      Vinculado à usina: <strong>{plant.growatt_plant_name}</strong>
                    </p>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="mt-3"
                      onClick={() => setGrowattDialogOpen(true)}
                    >
                      Sincronizar Agora
                    </Button>
                  </div>
                ) : (
                  <Button 
                    onClick={() => setGrowattDialogOpen(true)}
                    className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
                  >
                    <Zap className="h-4 w-4 mr-2" />
                    Conectar ao Growatt
                  </Button>
                )}
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
              <Label>Endereco</Label>
              <Input
                value={plantFormData.address || ''}
                onChange={(e) => setPlantFormData({...plantFormData, address: e.target.value})}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Estado</Label>
                <Select value={selectedState || plantFormData.state || ''} onValueChange={handleStateSelect}>
                  <SelectTrigger><SelectValue placeholder="Selecione o estado" /></SelectTrigger>
                  <SelectContent className="max-h-60">
                    {statesList.map(s => (
                      <SelectItem key={s} value={s}>{s.replace(/_/g, ' ')}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Cidade (Irradiancia)</Label>
                <Select value={plantFormData.city || ''} onValueChange={handleCitySelect}>
                  <SelectTrigger><SelectValue placeholder={filteredCities.length ? "Selecione a cidade" : "Escolha o estado primeiro"} /></SelectTrigger>
                  <SelectContent className="max-h-60">
                    {filteredCities.map(c => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {/* Prognosis Calculator */}
            <div className="p-3 bg-[#FFD600]/10 border border-[#FFD600]/30 rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-semibold">Prognostico por Irradiancia</Label>
                <Button size="sm" variant="outline" onClick={calculatePrognosis} disabled={calculatingPrognosis}
                  className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A] text-xs h-7">
                  {calculatingPrognosis ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Sun className="h-3 w-3 mr-1" />}
                  Calcular
                </Button>
              </div>
              {prognosisDetail && (
                <div className="text-xs space-y-1">
                  <p className="text-neutral-500">{prognosisDetail.city} - {prognosisDetail.state} | {prognosisDetail.capacity_kwp} kWp</p>
                  <div className="grid grid-cols-4 gap-1">
                    {prognosisDetail.months?.map((m, i) => (
                      <div key={i} className="bg-white px-2 py-1 rounded text-center">
                        <span className="text-neutral-400 uppercase">{m.month}</span>
                        <p className="font-bold text-[10px]">{Number(m.monthly_kwh).toLocaleString('pt-BR',{maximumFractionDigits:0})}</p>
                      </div>
                    ))}
                  </div>
                  <p className="font-semibold text-center mt-1">
                    Media: {Number(prognosisDetail.average_monthly_kwh).toLocaleString('pt-BR',{maximumFractionDigits:0})} kWh/mes | 
                    Anual: {(prognosisDetail.total_annual_kwh/1000).toFixed(2)} MWh
                  </p>
                </div>
              )}
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

      {/* Dialog Growatt Integration */}
      <Dialog open={growattDialogOpen} onOpenChange={setGrowattDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sun className="h-5 w-5 text-[#FFD600]" />
              Integração Growatt
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-6">
            {/* Login Section */}
            <div className="space-y-4">
              <h4 className="font-medium">1. Credenciais do Portal OSS Growatt</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Usuário</Label>
                  <Input
                    placeholder="Ex: BTAVB001"
                    value={growattCredentials.username}
                    onChange={(e) => setGrowattCredentials({...growattCredentials, username: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Senha</Label>
                  <Input
                    type="password"
                    value={growattCredentials.password}
                    onChange={(e) => setGrowattCredentials({...growattCredentials, password: e.target.value})}
                  />
                </div>
              </div>
              <Button 
                onClick={handleGrowattLogin}
                disabled={growattLoading}
                className="bg-[#1A1A1A] hover:bg-neutral-800 text-white"
              >
                {growattLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Conectando...
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4 mr-2" />
                    Buscar Usinas
                  </>
                )}
              </Button>
            </div>

            {/* Plant Selection */}
            {growattPlants.length > 0 && (
              <div className="space-y-4">
                <h4 className="font-medium">2. Selecione a usina na Growatt</h4>
                <p className="text-sm text-neutral-500">
                  Encontradas {growattPlants.length} usinas. Selecione qual corresponde a <strong>{data?.plant?.name}</strong>.
                </p>
                <div className="max-h-64 overflow-y-auto border rounded-lg">
                  {growattPlants.map((gp, index) => (
                    <div 
                      key={index}
                      onClick={() => setSelectedGrowattPlant(gp)}
                      className={`p-3 border-b last:border-b-0 cursor-pointer hover:bg-neutral-50 transition-colors ${
                        selectedGrowattPlant?.id === gp.id ? 'bg-[#FFD600]/10 border-l-4 border-l-[#FFD600]' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{gp.name}</p>
                          <p className="text-sm text-neutral-500">{gp.city}</p>
                        </div>
                        <div className="text-right">
                          <p className={`text-sm font-medium ${
                            gp.status === 'online' ? 'text-green-600' : 
                            gp.status === 'abnormal' ? 'text-amber-600' : 'text-red-600'
                          }`}>
                            {gp.status === 'online' ? '● Online' : gp.status === 'abnormal' ? '● Alerta' : '● Offline'}
                          </p>
                          <p className="text-sm text-neutral-500">{gp.today_energy_kwh?.toLocaleString('pt-BR')} kWh hoje</p>
                        </div>
                      </div>
                      <div className="mt-1 text-xs text-neutral-400">
                        Capacidade: {gp.capacity_kwp} kWp | Total: {gp.total_energy_kwh?.toLocaleString('pt-BR')} kWh
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sync Button */}
            {selectedGrowattPlant && (
              <div className="p-4 bg-[#FFD600]/10 rounded-lg">
                <p className="text-sm mb-3">
                  <strong>Usina selecionada:</strong> {selectedGrowattPlant.name}
                </p>
                <Button 
                  onClick={handleSyncGrowatt}
                  disabled={syncingGrowatt}
                  className="w-full bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
                >
                  {syncingGrowatt ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Sincronizando...
                    </>
                  ) : (
                    <>
                      <TrendingUp className="h-4 w-4 mr-2" />
                      Vincular e Sincronizar Dados
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Invoice Upload Dialog */}
      <Dialog open={invoiceDialogOpen} onOpenChange={setInvoiceDialogOpen}>
        <DialogContent className="sm:max-w-lg bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Upload className="h-5 w-5 text-[#FFD600]" />
              Enviar Fatura COPEL (PDF)
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Direct PDF Upload - no UC selection needed */}
            {!parsedInvoice && (
              <div className="space-y-3">
                <p className="text-sm text-neutral-500">
                  O sistema identificará automaticamente a UC pela fatura.
                </p>
                <input
                  ref={invoiceInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleInvoiceUpload}
                  className="hidden"
                />
                <Button 
                  variant="outline" 
                  className="w-full h-24 border-dashed border-2"
                  onClick={() => invoiceInputRef.current?.click()}
                  disabled={uploadingInvoice}
                >
                  {uploadingInvoice ? (
                    <div className="flex flex-col items-center gap-2">
                      <Loader2 className="h-6 w-6 animate-spin text-[#FFD600]" />
                      <span className="text-sm">Processando fatura...</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <Upload className="h-6 w-6 text-neutral-400" />
                      <span className="text-sm">Clique para selecionar o PDF</span>
                    </div>
                  )}
                </Button>
              </div>
            )}

            {/* Parsed Invoice Preview */}
            {parsedInvoice && (
              <div className="space-y-4 border rounded-lg p-4 bg-neutral-50">
                {/* UC Info */}
                {parsedInvoice.uc_info && (
                  <div className="bg-[#FFD600]/20 p-3 rounded-md">
                    <p className="text-sm font-medium">UC Identificada:</p>
                    <p className="text-lg font-bold">{parsedInvoice.uc_info.uc_number}</p>
                    <p className="text-sm text-neutral-600">{parsedInvoice.uc_info.plant_name}</p>
                  </div>
                )}
                
                {parsedInvoice.uc_not_found && (
                  <div className="bg-red-100 p-3 rounded-md">
                    <p className="text-sm font-medium text-red-600">UC não encontrada</p>
                    <p className="text-sm">{parsedInvoice.uc_number}</p>
                  </div>
                )}
                
                <h4 className="font-medium text-neutral-900">Dados Extraídos</h4>
                
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-neutral-500">Titular:</span>
                    <span className="ml-2 font-medium">{parsedInvoice.holder_name || '-'}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500">Grupo:</span>
                    <span className="ml-2 font-medium">{parsedInvoice.tariff_group} - {parsedInvoice.classification}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500">Referência:</span>
                    <span className="ml-2 font-medium">{parsedInvoice.reference_month}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500">Vencimento:</span>
                    <span className="ml-2 font-medium">{parsedInvoice.due_date}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500">Total a Pagar:</span>
                    <span className="ml-2 font-medium text-red-600">
                      R$ {parsedInvoice.amount_total_brl?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500">Economia Est.:</span>
                    <span className="ml-2 font-medium text-green-600">
                      R$ {parsedInvoice.amount_saved_brl?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
                
                <div className="border-t pt-3">
                  <h5 className="text-sm font-medium mb-2">Energia (kWh)</h5>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Registrado FP:</span>
                      <span className="font-medium">{parsedInvoice.energy_registered_fp_kwh?.toLocaleString() || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Registrado P:</span>
                      <span className="font-medium">{parsedInvoice.energy_registered_p_kwh?.toLocaleString() || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Injetado FP:</span>
                      <span className="font-medium">{parsedInvoice.energy_injected_fp_kwh?.toLocaleString() || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Injetado P:</span>
                      <span className="font-medium">{parsedInvoice.energy_injected_p_kwh?.toLocaleString() || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Compensado FP:</span>
                      <span className="font-medium text-green-600">{parsedInvoice.energy_compensated_fp_kwh?.toLocaleString() || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Compensado P:</span>
                      <span className="font-medium text-green-600">{parsedInvoice.energy_compensated_p_kwh?.toLocaleString() || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Faturado FP:</span>
                      <span className="font-medium">{parsedInvoice.energy_billed_fp_kwh?.toLocaleString() || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Créditos Acum.:</span>
                      <span className="font-medium">{parsedInvoice.credits_accumulated_fp_kwh?.toLocaleString() || 0}</span>
                    </div>
                  </div>
                </div>
                
                {/* Demand for Group A */}
                {parsedInvoice.tariff_group === 'A' && (
                  <div className="border-t pt-3">
                    <h5 className="text-sm font-medium mb-2">Demanda (kW)</h5>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-neutral-500">Contratada:</span>
                        <span className="font-medium">{parsedInvoice.demand_contracted_kw?.toLocaleString() || 0}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-500">Medida:</span>
                        <span className="font-medium">{parsedInvoice.demand_measured_kw?.toLocaleString() || 0}</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex gap-2 pt-2">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => setParsedInvoice(null)}
                  >
                    Cancelar
                  </Button>
                  <Button
                    className="flex-1 bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
                    onClick={handleSaveInvoice}
                    disabled={saving || parsedInvoice.uc_not_found}
                  >
                    {saving ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      'Salvar Fatura'
                    )}
                  </Button>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setInvoiceDialogOpen(false);
              setParsedInvoice(null);
              setSelectedUcForInvoice('');
            }}>
              Fechar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PlantDetail;
