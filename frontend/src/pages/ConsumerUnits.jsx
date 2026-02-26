import { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
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
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import { 
  Zap, 
  Plus, 
  Search, 
  MoreVertical, 
  Edit, 
  Trash2,
  MapPin,
  Hash,
  Loader2,
  Upload,
  FileText,
  Percent,
  Building2,
  Receipt
} from 'lucide-react';

const ConsumerUnits = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const plantIdParam = searchParams.get('plant');
  
  const [units, setUnits] = useState([]);
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterPlant, setFilterPlant] = useState(plantIdParam || 'all');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUnit, setEditingUnit] = useState(null);
  const [saving, setSaving] = useState(false);
  
  // Upload state
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadingUnit, setUploadingUnit] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [parsedInvoice, setParsedInvoice] = useState(null);
  const fileInputRef = useRef(null);
  
  const [formData, setFormData] = useState({
    plant_id: plantIdParam || '',
    uc_number: '',
    contract_number: '',
    address: '',
    city: '',
    state: 'PR',
    holder_name: '',
    holder_document: '',
    is_generator: false,
    compensation_percentage: 100,
    tariff_group: 'B',
    tariff_modality: 'Convencional',
    contracted_demand_kw: 0,
    generator_uc_ids: []
  });

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterPlant]);

  const loadData = async () => {
    try {
      const [unitsRes, plantsRes] = await Promise.all([
        api.get('/consumer-units', { params: filterPlant !== 'all' ? { plant_id: filterPlant } : {} }),
        api.get('/plants')
      ]);
      setUnits(unitsRes.data);
      setPlants(plantsRes.data);
    } catch (error) {
      toast.error('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (unit = null) => {
    if (unit) {
      setEditingUnit(unit);
      setFormData({
        plant_id: unit.plant_id || '',
        uc_number: unit.uc_number || '',
        contract_number: unit.contract_number || '',
        address: unit.address || '',
        city: unit.city || '',
        state: unit.state || 'PR',
        holder_name: unit.holder_name || '',
        holder_document: unit.holder_document || '',
        is_generator: unit.is_generator || false,
        compensation_percentage: unit.compensation_percentage || 100,
        tariff_group: unit.tariff_group || 'B',
        tariff_modality: unit.tariff_modality || 'Convencional',
        contracted_demand_kw: unit.contracted_demand_kw || 0,
        generator_uc_ids: unit.generator_uc_ids || []
      });
    } else {
      setEditingUnit(null);
      setFormData({
        plant_id: filterPlant !== 'all' ? filterPlant : '',
        uc_number: '',
        contract_number: '',
        address: '',
        city: '',
        state: 'PR',
        holder_name: '',
        holder_document: '',
        is_generator: false,
        compensation_percentage: 100,
        tariff_group: 'B',
        tariff_modality: 'Convencional',
        contracted_demand_kw: 0,
        generator_uc_ids: []
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingUnit(null);
  };

  const handleSave = async () => {
    if (!formData.plant_id) {
      toast.error('Selecione uma usina');
      return;
    }
    if (!formData.uc_number.trim()) {
      toast.error('Número da UC é obrigatório');
      return;
    }
    if (!formData.address.trim()) {
      toast.error('Endereço é obrigatório');
      return;
    }

    setSaving(true);
    try {
      const dataToSend = {
        ...formData,
        compensation_percentage: parseFloat(formData.compensation_percentage) || 100,
        contracted_demand_kw: parseFloat(formData.contracted_demand_kw) || 0
      };
      
      if (editingUnit) {
        await api.put(`/consumer-units/${editingUnit.id}`, dataToSend);
        toast.success('Unidade consumidora atualizada com sucesso');
      } else {
        await api.post('/consumer-units', dataToSend);
        toast.success('Unidade consumidora cadastrada com sucesso');
      }
      handleCloseDialog();
      loadData();
    } catch (error) {
      toast.error('Erro ao salvar unidade consumidora');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (unit) => {
    if (!window.confirm(`Deseja realmente excluir a UC "${unit.uc_number}"?`)) {
      return;
    }

    try {
      await api.delete(`/consumer-units/${unit.id}`);
      toast.success('Unidade consumidora removida com sucesso');
      loadData();
    } catch (error) {
      toast.error('Erro ao remover unidade consumidora');
    }
  };

  // Upload PDF functions
  const handleOpenUpload = (unit) => {
    setUploadingUnit(unit);
    setParsedInvoice(null);
    setUploadDialogOpen(true);
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Apenas arquivos PDF são aceitos');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post(`/invoices/upload-pdf/${uploadingUnit.id}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.success) {
        setParsedInvoice(response.data.parsed_data);
        toast.success('PDF processado! Revise os dados antes de salvar.');
      } else {
        toast.error(response.data.error || 'Erro ao processar PDF');
      }
    } catch (error) {
      toast.error('Erro ao fazer upload do PDF');
    } finally {
      setUploading(false);
    }
  };

  const handleSaveInvoice = async () => {
    if (!parsedInvoice) return;

    setUploading(true);
    try {
      await api.post('/invoices/save-from-upload', parsedInvoice);
      toast.success('Fatura salva com sucesso!');
      setUploadDialogOpen(false);
      setParsedInvoice(null);
    } catch (error) {
      toast.error('Erro ao salvar fatura');
    } finally {
      setUploading(false);
    }
  };

  const updateParsedField = (field, value) => {
    setParsedInvoice(prev => ({ ...prev, [field]: value }));
  };

  const getPlantName = (plantId) => {
    const plant = plants.find(p => p.id === plantId);
    return plant?.name || '';
  };

  // Find plant by UC number - useful when plant_id is missing
  const findPlantByUC = (ucNumber) => {
    // First check if any plant has consumer units with this UC number
    const unit = units.find(u => u.uc_number === ucNumber);
    if (unit?.plant_id) {
      const plant = plants.find(p => p.id === unit.plant_id);
      if (plant) return plant.name;
    }
    return '';
  };

  const getGeneratorUnits = () => {
    return units.filter(u => u.is_generator && u.plant_id === formData.plant_id);
  };

  // Enhanced search - searches across UC number, address, holder name, plant name, and city
  const filteredUnits = units.filter(unit => {
    const searchLower = search.toLowerCase();
    const plantName = getPlantName(unit.plant_id);
    const plant = plants.find(p => p.id === unit.plant_id);
    
    return (
      (unit.uc_number || '').toLowerCase().includes(searchLower) ||
      (unit.address || '').toLowerCase().includes(searchLower) ||
      (unit.holder_name || '').toLowerCase().includes(searchLower) ||
      plantName.toLowerCase().includes(searchLower) ||
      (plant?.city || '').toLowerCase().includes(searchLower) ||
      (plant?.client_name || '').toLowerCase().includes(searchLower)
    );
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="consumer-units-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-neutral-900 font-heading">
            Unidades Consumidoras
          </h1>
          <p className="text-neutral-500 mt-1">Gerencie as UCs e suas faturas</p>
        </div>
        <Button 
          onClick={() => handleOpenDialog()} 
          className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
          data-testid="add-unit-btn"
        >
          <Plus className="h-4 w-4 mr-2" />
          Nova UC
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <Input
            placeholder="Buscar por UC, usina, cidade, endereço..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={filterPlant} onValueChange={setFilterPlant}>
          <SelectTrigger className="w-full md:w-64">
            <SelectValue placeholder="Filtrar por usina" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas as usinas</SelectItem>
            {plants.map((plant) => (
              <SelectItem key={plant.id} value={plant.id}>
                {plant.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Units Grid */}
      {filteredUnits.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredUnits.map((unit) => (
            <Card key={unit.id} className="border-neutral-100 shadow-sm card-hover">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                      unit.is_generator ? 'bg-amber-50' : 'bg-blue-50'
                    }`}>
                      <Zap className={`h-6 w-6 ${
                        unit.is_generator ? 'text-amber-600' : 'text-blue-600'
                      }`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-neutral-900">{unit.uc_number || unit.contract_number}</h3>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          unit.is_generator 
                            ? 'bg-amber-100 text-amber-700' 
                            : 'bg-blue-100 text-blue-700'
                        }`}>
                          {unit.is_generator ? 'Geradora' : 'Beneficiária'}
                        </span>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          unit.tariff_group === 'A' 
                            ? 'bg-purple-100 text-purple-700' 
                            : 'bg-green-100 text-green-700'
                        }`}>
                          Grupo {unit.tariff_group || 'B'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleOpenUpload(unit)}>
                        <Upload className="h-4 w-4 mr-2" />
                        Upload Fatura
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => navigate(`/faturas?uc=${unit.id}`)}>
                        <Receipt className="h-4 w-4 mr-2" />
                        Ver Faturas
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleOpenDialog(unit)}>
                        <Edit className="h-4 w-4 mr-2" />
                        Editar
                      </DropdownMenuItem>
                      <DropdownMenuItem 
                        onClick={() => handleDelete(unit)}
                        className="text-red-600"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Excluir
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div className="mt-4 space-y-2">
                  <div className="flex items-start gap-2 text-sm text-neutral-600">
                    <MapPin className="h-4 w-4 text-neutral-400 flex-shrink-0 mt-0.5" />
                    <span className="line-clamp-2">{unit.address}{unit.city && ` - ${unit.city}`}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-neutral-500">
                    <Building2 className="h-4 w-4 text-neutral-400" />
                    {getPlantName(unit.plant_id) || (
                      <span className="text-amber-600 text-xs">Vincular a uma usina</span>
                    )}
                  </div>
                  {!unit.is_generator && (
                    <div className="flex items-center gap-2 text-sm text-neutral-500">
                      <Percent className="h-4 w-4 text-neutral-400" />
                      {unit.compensation_percentage || 100}% de compensação
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="border-neutral-100 shadow-sm">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <div className="p-4 bg-neutral-100 rounded-full mb-4">
              <Zap className="h-8 w-8 text-neutral-400" />
            </div>
            <h3 className="text-lg font-medium text-neutral-900 mb-1">
              Nenhuma unidade consumidora encontrada
            </h3>
            <p className="text-sm text-neutral-500 mb-4">
              {search ? 'Tente ajustar sua busca' : 'Comece cadastrando sua primeira UC'}
            </p>
            {!search && (
              <Button 
                onClick={() => handleOpenDialog()} 
                className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
              >
                <Plus className="h-4 w-4 mr-2" />
                Cadastrar UC
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Edit/Create Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingUnit ? 'Editar Unidade Consumidora' : 'Nova Unidade Consumidora'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="plant">Usina *</Label>
                <Select
                  value={formData.plant_id}
                  onValueChange={(value) => setFormData({ ...formData, plant_id: value })}
                >
                  <SelectTrigger data-testid="unit-plant-select">
                    <SelectValue placeholder="Selecione" />
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
                <Label htmlFor="uc_number">Número da UC *</Label>
                <Input
                  id="uc_number"
                  value={formData.uc_number}
                  onChange={(e) => setFormData({ ...formData, uc_number: e.target.value })}
                  placeholder="Ex: 113577680"
                  data-testid="unit-uc-input"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="address">Endereço *</Label>
              <Input
                id="address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Rua, número, bairro"
                data-testid="unit-address-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="city">Cidade</Label>
                <Input
                  id="city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="Curitiba"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="state">Estado</Label>
                <Input
                  id="state"
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  placeholder="PR"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="holder">Titular</Label>
                <Input
                  id="holder"
                  value={formData.holder_name}
                  onChange={(e) => setFormData({ ...formData, holder_name: e.target.value })}
                  placeholder="Nome"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="document">CPF/CNPJ</Label>
                <Input
                  id="document"
                  value={formData.holder_document}
                  onChange={(e) => setFormData({ ...formData, holder_document: e.target.value })}
                  placeholder="00.000.000/0000-00"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="tariff_group">Grupo Tarifário</Label>
                <Select
                  value={formData.tariff_group}
                  onValueChange={(value) => setFormData({ ...formData, tariff_group: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="A">Grupo A (Alta Tensão)</SelectItem>
                    <SelectItem value="B">Grupo B (Baixa Tensão)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="modality">Modalidade</Label>
                <Select
                  value={formData.tariff_modality}
                  onValueChange={(value) => setFormData({ ...formData, tariff_modality: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Convencional">Convencional</SelectItem>
                    <SelectItem value="Horária Verde">Horária Verde</SelectItem>
                    <SelectItem value="Horária Azul">Horária Azul</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {formData.tariff_group === 'A' && (
              <div className="space-y-2">
                <Label htmlFor="demand">Demanda Contratada (kW)</Label>
                <Input
                  id="demand"
                  type="number"
                  value={formData.contracted_demand_kw}
                  onChange={(e) => setFormData({ ...formData, contracted_demand_kw: e.target.value })}
                  placeholder="0"
                />
              </div>
            )}

            <div className="flex items-center justify-between p-4 bg-amber-50 rounded-lg border border-amber-200">
              <div>
                <Label htmlFor="is_generator" className="text-sm font-medium text-amber-900">
                  Unidade Geradora
                </Label>
                <p className="text-xs text-amber-700 mt-0.5">
                  Marque se esta é a UC onde a usina está instalada
                </p>
              </div>
              <Switch
                id="is_generator"
                checked={formData.is_generator}
                onCheckedChange={(checked) => setFormData({ ...formData, is_generator: checked })}
              />
            </div>

            {!formData.is_generator && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="compensation">% de Compensação</Label>
                  <Input
                    id="compensation"
                    type="number"
                    min="0"
                    max="100"
                    value={formData.compensation_percentage}
                    onChange={(e) => setFormData({ ...formData, compensation_percentage: e.target.value })}
                    placeholder="100"
                  />
                  <p className="text-xs text-neutral-500">Porcentagem da energia que esta UC recebe da(s) geradora(s)</p>
                </div>

                {getGeneratorUnits().length > 0 && (
                  <div className="space-y-2">
                    <Label>UCs Geradoras</Label>
                    <div className="space-y-2">
                      {getGeneratorUnits().map(gen => (
                        <label key={gen.id} className="flex items-center gap-2 p-2 bg-neutral-50 rounded">
                          <input
                            type="checkbox"
                            checked={formData.generator_uc_ids?.includes(gen.id)}
                            onChange={(e) => {
                              const ids = formData.generator_uc_ids || [];
                              if (e.target.checked) {
                                setFormData({ ...formData, generator_uc_ids: [...ids, gen.id] });
                              } else {
                                setFormData({ ...formData, generator_uc_ids: ids.filter(id => id !== gen.id) });
                              }
                            }}
                            className="rounded"
                          />
                          <span className="text-sm">{gen.uc_number} - {gen.address}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseDialog}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSave} 
              disabled={saving}
              className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
              data-testid="save-unit-btn"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Invoice Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Upload de Fatura - UC {uploadingUnit?.uc_number}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {!parsedInvoice ? (
              <div className="border-2 border-dashed border-neutral-300 rounded-lg p-8 text-center">
                <Upload className="h-12 w-12 mx-auto text-neutral-400 mb-4" />
                <p className="text-neutral-600 mb-2">Arraste o PDF da fatura aqui ou clique para selecionar</p>
                <p className="text-sm text-neutral-500 mb-4">Apenas arquivos PDF da COPEL são aceitos</p>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  accept=".pdf"
                  className="hidden"
                />
                <Button 
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
                >
                  {uploading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Upload className="h-4 w-4 mr-2" />}
                  Selecionar PDF
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-green-800 font-medium">PDF processado com sucesso!</p>
                  <p className="text-green-600 text-sm">Revise e edite os dados antes de salvar.</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Mês de Referência</Label>
                    <Input
                      value={parsedInvoice.reference_month || ''}
                      onChange={(e) => updateParsedField('reference_month', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Vencimento</Label>
                    <Input
                      value={parsedInvoice.due_date || ''}
                      onChange={(e) => updateParsedField('due_date', e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Início do Ciclo</Label>
                    <Input
                      value={parsedInvoice.billing_cycle_start || ''}
                      onChange={(e) => updateParsedField('billing_cycle_start', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Fim do Ciclo</Label>
                    <Input
                      value={parsedInvoice.billing_cycle_end || ''}
                      onChange={(e) => updateParsedField('billing_cycle_end', e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Valor Faturado (R$)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={parsedInvoice.amount_total_brl || 0}
                      onChange={(e) => updateParsedField('amount_total_brl', parseFloat(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Economizado (R$)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={parsedInvoice.amount_saved_brl || 0}
                      onChange={(e) => updateParsedField('amount_saved_brl', parseFloat(e.target.value))}
                    />
                  </div>
                </div>

                <div className="border-t pt-4">
                  <h4 className="font-medium mb-3">Dados de Energia - Fora Ponta</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>Energia Registrada (kWh)</Label>
                      <Input
                        type="number"
                        value={parsedInvoice.energy_registered_fp_kwh || 0}
                        onChange={(e) => updateParsedField('energy_registered_fp_kwh', parseFloat(e.target.value))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Tarifa (R$/kWh)</Label>
                      <Input
                        type="number"
                        step="0.000001"
                        value={parsedInvoice.energy_tariff_fp_brl || 0}
                        onChange={(e) => updateParsedField('energy_tariff_fp_brl', parseFloat(e.target.value))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Energia Faturada (kWh)</Label>
                      <Input
                        type="number"
                        value={parsedInvoice.energy_billed_fp_kwh || 0}
                        onChange={(e) => updateParsedField('energy_billed_fp_kwh', parseFloat(e.target.value))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Energia Injetada (kWh)</Label>
                      <Input
                        type="number"
                        value={parsedInvoice.energy_injected_fp_kwh || 0}
                        onChange={(e) => updateParsedField('energy_injected_fp_kwh', parseFloat(e.target.value))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Energia Compensada (kWh)</Label>
                      <Input
                        type="number"
                        value={parsedInvoice.energy_compensated_fp_kwh || 0}
                        onChange={(e) => updateParsedField('energy_compensated_fp_kwh', parseFloat(e.target.value))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Crédito Acumulado (kWh)</Label>
                      <Input
                        type="number"
                        value={parsedInvoice.credits_accumulated_fp_kwh || 0}
                        onChange={(e) => updateParsedField('credits_accumulated_fp_kwh', parseFloat(e.target.value))}
                      />
                    </div>
                  </div>
                </div>

                {parsedInvoice.tariff_group === 'A' && (
                  <div className="border-t pt-4">
                    <h4 className="font-medium mb-3">Dados de Energia - Ponta</h4>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label>Energia Registrada (kWh)</Label>
                        <Input
                          type="number"
                          value={parsedInvoice.energy_registered_p_kwh || 0}
                          onChange={(e) => updateParsedField('energy_registered_p_kwh', parseFloat(e.target.value))}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Energia Injetada (kWh)</Label>
                        <Input
                          type="number"
                          value={parsedInvoice.energy_injected_p_kwh || 0}
                          onChange={(e) => updateParsedField('energy_injected_p_kwh', parseFloat(e.target.value))}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Crédito Acumulado (kWh)</Label>
                        <Input
                          type="number"
                          value={parsedInvoice.credits_accumulated_p_kwh || 0}
                          onChange={(e) => updateParsedField('credits_accumulated_p_kwh', parseFloat(e.target.value))}
                        />
                      </div>
                    </div>

                    <h4 className="font-medium mb-3 mt-4">Demanda</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Demanda Registrada (kW)</Label>
                        <Input
                          type="number"
                          step="0.01"
                          value={parsedInvoice.demand_registered_kw || 0}
                          onChange={(e) => updateParsedField('demand_registered_kw', parseFloat(e.target.value))}
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div className="border-t pt-4">
                  <h4 className="font-medium mb-3">Outros</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Iluminação Pública (R$)</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={parsedInvoice.public_lighting_brl || 0}
                        onChange={(e) => updateParsedField('public_lighting_brl', parseFloat(e.target.value))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>ICMS (R$)</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={parsedInvoice.icms_brl || 0}
                        onChange={(e) => updateParsedField('icms_brl', parseFloat(e.target.value))}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => { setUploadDialogOpen(false); setParsedInvoice(null); }}>
              Cancelar
            </Button>
            {parsedInvoice && (
              <Button 
                onClick={handleSaveInvoice} 
                disabled={uploading}
                className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
              >
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar Fatura'}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ConsumerUnits;
