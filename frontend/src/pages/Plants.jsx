import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { toast } from 'sonner';
import { 
  Factory, 
  Plus, 
  Search, 
  MoreVertical, 
  Edit, 
  Trash2,
  Sun,
  MapPin,
  Zap,
  Eye,
  Loader2
} from 'lucide-react';

const formatNumber = (value) => {
  return new Intl.NumberFormat('pt-BR').format(value);
};

const Plants = () => {
  const [plants, setPlants] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPlant, setEditingPlant] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    client_id: '',
    capacity_kwp: '',
    address: '',
    city: '',
    state: 'PR',
    inverter_brand: '',
    monthly_prognosis_kwh: '',
    annual_prognosis_kwh: '',
    total_investment: '',
    installation_date: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const [statesList, setStatesList] = useState([]);
  const [filteredCities, setFilteredCities] = useState([]);
  const [citySearch, setCitySearch] = useState('');
  const [showCityDrop, setShowCityDrop] = useState(false);
  const [calcingProg, setCalcingProg] = useState(false);
  const [progDetail, setProgDetail] = useState(null);

  useEffect(() => {
    api.get('/irradiance/states').then(r => setStatesList(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (formData.state) {
      api.get(`/irradiance/cities?state=${encodeURIComponent(formData.state)}`).then(r => {
        setFilteredCities(r.data.map(c => c.city).sort());
      }).catch(() => {});
    }
  }, [formData.state]);

  const cityMatches = filteredCities.filter(c => !citySearch || c.toLowerCase().includes(citySearch.toLowerCase())).slice(0, 50);

  const calcPrognosis = async () => {
    if (!formData.city || !formData.capacity_kwp) { toast.error('Preencha cidade e potencia'); return; }
    setCalcingProg(true);
    try {
      const res = await api.post('/irradiance/calculate-prognosis', { city: formData.city, capacity_kwp: parseFloat(formData.capacity_kwp) });
      setProgDetail(res.data);
      setFormData(prev => ({
        ...prev,
        monthly_prognosis_kwh: res.data.average_monthly_kwh.toString(),
        annual_prognosis_kwh: res.data.total_annual_kwh.toString(),
      }));
      toast.success(`Prognostico: ${(res.data.total_annual_kwh/1000).toFixed(2)} MWh/ano`);
    } catch (err) { toast.error(err.response?.data?.detail || 'Erro'); }
    finally { setCalcingProg(false); }
  };

  const loadData = async () => {
    try {
      const [plantsRes, clientsRes] = await Promise.all([
        api.get('/dashboard/plants-summary'),
        api.get('/clients')
      ]);
      setPlants(plantsRes.data?.plants || plantsRes.data || []);
      setClients(clientsRes.data);
    } catch (error) {
      toast.error('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = async (plant = null) => {
    if (plant) {
      try {
        const response = await api.get(`/plants/${plant.id}`);
        const plantData = response.data;
        setEditingPlant(plantData);
        setFormData({
          name: plantData.name || '',
          client_id: plantData.client_id || '',
          capacity_kwp: plantData.capacity_kwp?.toString() || '',
          address: plantData.address || '',
          city: plantData.city || '',
          state: plantData.state || 'PR',
          inverter_brand: plantData.inverter_brand || '',
          monthly_prognosis_kwh: plantData.monthly_prognosis_kwh?.toString() || '',
          annual_prognosis_kwh: plantData.annual_prognosis_kwh?.toString() || '',
          total_investment: plantData.total_investment?.toString() || '',
          installation_date: plantData.installation_date || ''
        });
      } catch (error) {
        toast.error('Erro ao carregar dados da usina');
        return;
      }
    } else {
      setEditingPlant(null);
      setFormData({
        name: '',
        client_id: '',
        capacity_kwp: '',
        address: '',
        city: '',
        state: 'PR',
        inverter_brand: '',
        monthly_prognosis_kwh: '',
        annual_prognosis_kwh: '',
        total_investment: '',
        installation_date: ''
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingPlant(null);
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast.error('Nome é obrigatório');
      return;
    }
    if (!formData.client_id) {
      toast.error('Selecione um cliente');
      return;
    }
    if (!formData.capacity_kwp) {
      toast.error('Capacidade é obrigatória');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        ...formData,
        capacity_kwp: parseFloat(formData.capacity_kwp) || 0,
        monthly_prognosis_kwh: parseFloat(formData.monthly_prognosis_kwh) || 0,
        annual_prognosis_kwh: parseFloat(formData.annual_prognosis_kwh) || 0,
        total_investment: parseFloat(formData.total_investment) || 0
      };

      if (editingPlant) {
        await api.put(`/plants/${editingPlant.id}`, payload);
        toast.success('Usina atualizada com sucesso');
      } else {
        await api.post('/plants', payload);
        toast.success('Usina cadastrada com sucesso');
      }
      handleCloseDialog();
      loadData();
    } catch (error) {
      toast.error('Erro ao salvar usina');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (plant) => {
    if (!window.confirm(`Deseja realmente excluir a usina "${plant.name}"?`)) {
      return;
    }

    try {
      await api.delete(`/plants/${plant.id}`);
      toast.success('Usina removida com sucesso');
      loadData();
    } catch (error) {
      toast.error('Erro ao remover usina');
    }
  };

  const filteredPlants = plants.filter(plant =>
    plant.name.toLowerCase().includes(search.toLowerCase()) ||
    plant.client_name?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="plants-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-neutral-900 font-heading">Usinas</h1>
          <p className="text-neutral-500 mt-1">Gerencie suas usinas solares fotovoltaicas</p>
        </div>
        <Button 
          onClick={() => handleOpenDialog()} 
          className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
          data-testid="add-plant-btn"
        >
          <Plus className="h-4 w-4 mr-2" />
          Nova Usina
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
        <Input
          placeholder="Buscar por nome ou cliente..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
          data-testid="search-plants-input"
        />
      </div>

      {/* Plants Grid */}
      {filteredPlants.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPlants.map((plant) => (
            <Card key={plant.id} className="border-neutral-100 shadow-sm card-hover overflow-hidden">
              <div className="h-2 bg-gradient-to-r from-[#FFD600] to-[#EAB308]" />
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-amber-50 flex items-center justify-center">
                      <Sun className="h-6 w-6 text-[#EAB308]" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-neutral-900">{plant.name}</h3>
                      <p className="text-sm text-neutral-500">{plant.client_name}</p>
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem asChild>
                        <Link to={`/usinas/${plant.id}`}>
                          <Eye className="h-4 w-4 mr-2" />
                          Ver detalhes
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleOpenDialog(plant)}>
                        <Edit className="h-4 w-4 mr-2" />
                        Editar
                      </DropdownMenuItem>
                      <DropdownMenuItem 
                        onClick={() => handleDelete(plant)}
                        className="text-red-600"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Excluir
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-neutral-500 uppercase tracking-wide">Capacidade</p>
                    <p className="text-lg font-bold text-neutral-900">{plant.capacity_kwp} kWp</p>
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 uppercase tracking-wide">Geração</p>
                    <p className="text-lg font-bold text-neutral-900">{formatNumber(plant.generation_kwh)} kWh</p>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-neutral-500">Desempenho</span>
                    <span className="text-sm font-medium text-neutral-700">{plant.performance}%</span>
                  </div>
                  <div className="w-full h-2 bg-neutral-100 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all ${
                        plant.performance >= 80 ? 'bg-emerald-500' : 
                        plant.performance >= 50 ? 'bg-amber-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(plant.performance, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <StatusBadge status={plant.status} />
                  <Button variant="ghost" size="sm" asChild className="text-neutral-600">
                    <Link to={`/usinas/${plant.id}`}>
                      Ver detalhes
                      <Zap className="h-4 w-4 ml-1" />
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="border-neutral-100 shadow-sm">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <div className="p-4 bg-neutral-100 rounded-full mb-4">
              <Factory className="h-8 w-8 text-neutral-400" />
            </div>
            <h3 className="text-lg font-medium text-neutral-900 mb-1">Nenhuma usina encontrada</h3>
            <p className="text-sm text-neutral-500 mb-4">
              {search ? 'Tente ajustar sua busca' : 'Comece cadastrando sua primeira usina'}
            </p>
            {!search && (
              <Button 
                onClick={() => handleOpenDialog()} 
                className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
              >
                <Plus className="h-4 w-4 mr-2" />
                Cadastrar Usina
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingPlant ? 'Editar Usina' : 'Nova Usina'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2 space-y-2">
                <Label htmlFor="name">Nome da Usina *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Ex: Usina Solar Residencial"
                  data-testid="plant-name-input"
                />
              </div>

              <div className="col-span-2 space-y-2">
                <Label htmlFor="client">Cliente *</Label>
                <Select
                  value={formData.client_id}
                  onValueChange={(value) => setFormData({ ...formData, client_id: value })}
                >
                  <SelectTrigger data-testid="plant-client-select">
                    <SelectValue placeholder="Selecione um cliente" />
                  </SelectTrigger>
                  <SelectContent>
                    {clients.map((client) => (
                      <SelectItem key={client.id} value={client.id}>
                        {client.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="capacity">Capacidade (kWp) *</Label>
                <Input
                  id="capacity"
                  type="number"
                  step="0.01"
                  value={formData.capacity_kwp}
                  onChange={(e) => setFormData({ ...formData, capacity_kwp: e.target.value })}
                  placeholder="Ex: 10.5"
                  data-testid="plant-capacity-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="inverter">Marca do Inversor</Label>
                <Select
                  value={formData.inverter_brand}
                  onValueChange={(value) => setFormData({ ...formData, inverter_brand: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="growatt">Growatt</SelectItem>
                    <SelectItem value="fusionsolar">FusionSolar</SelectItem>
                    <SelectItem value="sungrow">Sungrow</SelectItem>
                    <SelectItem value="deye">Deye</SelectItem>
                    <SelectItem value="solis">Solis</SelectItem>
                    <SelectItem value="saj">SAJ</SelectItem>
                    <SelectItem value="solarman">SolarMan</SelectItem>
                    <SelectItem value="livoltek">Livoltek</SelectItem>
                    <SelectItem value="outro">Outro</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="col-span-2 space-y-2">
                <Label htmlFor="address">Endereço</Label>
                <Input
                  id="address"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="Rua, número"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Estado</Label>
                  <select className="w-full h-9 rounded-md border border-neutral-200 bg-white px-3 py-1 text-sm"
                    value={formData.state} onChange={(e) => { setFormData({...formData, state: e.target.value, city: ''}); setCitySearch(''); }}>
                    <option value="">Selecione o estado</option>
                    {statesList.map(s => <option key={s} value={s}>{s.replace(/_/g,' ')}</option>)}
                  </select>
                </div>
                <div className="space-y-2 relative">
                  <Label>Cidade (Irradiancia)</Label>
                  <Input value={citySearch || formData.city} onChange={(e) => { setCitySearch(e.target.value); setShowCityDrop(true);
                    if (!formData.state && e.target.value.length >= 2) api.get(`/irradiance/cities?q=${encodeURIComponent(e.target.value)}`).then(r => setFilteredCities(r.data.map(c=>c.city).sort())).catch(()=>{});
                  }} onFocus={() => setShowCityDrop(true)} onBlur={() => setTimeout(()=>setShowCityDrop(false),200)} placeholder="Digite para buscar..." />
                  {showCityDrop && cityMatches.length > 0 && (
                    <div className="absolute z-[100] top-full left-0 right-0 mt-1 bg-white border rounded-lg shadow-xl max-h-48 overflow-y-auto">
                      {cityMatches.map(c => (
                        <button key={c} type="button" className={`w-full text-left px-3 py-2 text-sm hover:bg-[#FFD600]/20 border-b last:border-0 ${formData.city===c?'bg-[#FFD600]/10 font-semibold':''}`}
                          onClick={() => { setFormData(prev=>({...prev,city:c})); setCitySearch(c); setShowCityDrop(false);
                            api.get(`/irradiance/cities?q=${encodeURIComponent(c)}`).then(r=>{const m=r.data.find(x=>x.city===c);if(m)setFormData(prev=>({...prev,state:m.state}))}).catch(()=>{});
                          }}>{c}</button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Prognosis by Irradiance - same layout as PlantDetail */}
              <div className="p-3 bg-[#FFD600]/10 border border-[#FFD600]/30 rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-semibold">Prognostico por Irradiancia</Label>
                  <Button size="sm" variant="outline" onClick={calcPrognosis} disabled={calcingProg} type="button"
                    className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A] text-xs h-7">
                    {calcingProg ? 'Calculando...' : 'Calcular'}
                  </Button>
                </div>
                {progDetail && (
                  <div className="text-xs space-y-2">
                    <p className="text-neutral-500">{progDetail.city} - {progDetail.state} | {progDetail.capacity_kwp} kWp</p>
                    <div className="grid grid-cols-4 gap-2">
                      {progDetail.months?.map((m, i) => (
                        <div key={i} className="bg-white px-2 py-2 rounded-lg text-center border">
                          <span className="text-neutral-400 uppercase text-[9px] block">{m.month}</span>
                          <p className="font-bold text-sm">{Math.round(m.monthly_kwh).toLocaleString('pt-BR')}</p>
                          <p className="text-[8px] text-neutral-400">irr: {m.irradiance}</p>
                        </div>
                      ))}
                    </div>
                    <p className="font-semibold text-center">
                      Media: {Number(progDetail.average_monthly_kwh).toLocaleString('pt-BR',{maximumFractionDigits:0})} kWh/mes |
                      Anual: {(progDetail.total_annual_kwh/1000).toFixed(2)} MWh
                    </p>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Prognostico Mensal (kWh)</Label>
                  <Input type="number" value={formData.monthly_prognosis_kwh} onChange={(e) => setFormData({...formData, monthly_prognosis_kwh: e.target.value})} placeholder="Auto-calculado" />
                </div>
                <div className="space-y-2">
                  <Label>Prognostico Anual (kWh)</Label>
                  <Input type="number" value={formData.annual_prognosis_kwh} onChange={(e) => setFormData({...formData, annual_prognosis_kwh: e.target.value})} placeholder="Auto-calculado" />
                </div>
                <div className="space-y-2">
                  <Label>Investimento Total (R$)</Label>
                  <Input type="number" value={formData.total_investment} onChange={(e) => setFormData({...formData, total_investment: e.target.value})} placeholder="Ex: 50000" />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="investment">Investimento Total (R$)</Label>
                <Input
                  id="investment"
                  type="number"
                  value={formData.total_investment}
                  onChange={(e) => setFormData({ ...formData, total_investment: e.target.value })}
                  placeholder="Ex: 50000"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="installation_date">Data de Instalação</Label>
                <Input
                  id="installation_date"
                  type="date"
                  value={formData.installation_date}
                  onChange={(e) => setFormData({ ...formData, installation_date: e.target.value })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseDialog}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSave} 
              disabled={saving}
              className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
              data-testid="save-plant-btn"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Plants;
