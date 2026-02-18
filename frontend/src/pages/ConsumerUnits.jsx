import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../services/api';
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
  Loader2
} from 'lucide-react';

const ConsumerUnits = () => {
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
  const [formData, setFormData] = useState({
    plant_id: plantIdParam || '',
    contract_number: '',
    address: '',
    holder_name: '',
    is_generator: false
  });

  useEffect(() => {
    loadData();
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
        contract_number: unit.contract_number || '',
        address: unit.address || '',
        holder_name: unit.holder_name || '',
        is_generator: unit.is_generator || false
      });
    } else {
      setEditingUnit(null);
      setFormData({
        plant_id: filterPlant !== 'all' ? filterPlant : '',
        contract_number: '',
        address: '',
        holder_name: '',
        is_generator: false
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
    if (!formData.contract_number.trim()) {
      toast.error('Número do contrato é obrigatório');
      return;
    }
    if (!formData.address.trim()) {
      toast.error('Endereço é obrigatório');
      return;
    }

    setSaving(true);
    try {
      if (editingUnit) {
        await api.put(`/consumer-units/${editingUnit.id}`, formData);
        toast.success('Unidade consumidora atualizada com sucesso');
      } else {
        await api.post('/consumer-units', formData);
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
    if (!window.confirm(`Deseja realmente excluir a UC "${unit.contract_number}"?`)) {
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

  const getPlantName = (plantId) => {
    const plant = plants.find(p => p.id === plantId);
    return plant?.name || 'Usina não encontrada';
  };

  const filteredUnits = units.filter(unit =>
    unit.contract_number.toLowerCase().includes(search.toLowerCase()) ||
    unit.address.toLowerCase().includes(search.toLowerCase()) ||
    unit.holder_name?.toLowerCase().includes(search.toLowerCase())
  );

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
          <p className="text-neutral-500 mt-1">Gerencie as UCs vinculadas às suas usinas</p>
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
            placeholder="Buscar por contrato, endereço..."
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
                      <h3 className="font-semibold text-neutral-900">{unit.contract_number}</h3>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        unit.is_generator 
                          ? 'bg-amber-100 text-amber-700' 
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {unit.is_generator ? 'Geradora' : 'Beneficiária'}
                      </span>
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
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
                    <span className="line-clamp-2">{unit.address}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-neutral-500">
                    <Hash className="h-4 w-4 text-neutral-400" />
                    {getPlantName(unit.plant_id)}
                  </div>
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

      {/* Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingUnit ? 'Editar Unidade Consumidora' : 'Nova Unidade Consumidora'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="plant">Usina *</Label>
              <Select
                value={formData.plant_id}
                onValueChange={(value) => setFormData({ ...formData, plant_id: value })}
              >
                <SelectTrigger data-testid="unit-plant-select">
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
              <Label htmlFor="contract">Número do Contrato (UC) *</Label>
              <Input
                id="contract"
                value={formData.contract_number}
                onChange={(e) => setFormData({ ...formData, contract_number: e.target.value })}
                placeholder="Ex: 123456789"
                data-testid="unit-contract-input"
              />
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

            <div className="space-y-2">
              <Label htmlFor="holder">Titular</Label>
              <Input
                id="holder"
                value={formData.holder_name}
                onChange={(e) => setFormData({ ...formData, holder_name: e.target.value })}
                placeholder="Nome do titular"
              />
            </div>

            <div className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg">
              <div>
                <Label htmlFor="is_generator" className="text-sm font-medium">
                  Unidade Geradora
                </Label>
                <p className="text-xs text-neutral-500 mt-0.5">
                  Marque se esta é a UC onde a usina está instalada
                </p>
              </div>
              <Switch
                id="is_generator"
                checked={formData.is_generator}
                onCheckedChange={(checked) => setFormData({ ...formData, is_generator: checked })}
              />
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
              data-testid="save-unit-btn"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ConsumerUnits;
