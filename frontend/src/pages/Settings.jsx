import { useState, useEffect } from 'react';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Settings as SettingsIcon, 
  Key, 
  Zap, 
  Plus, 
  Trash2,
  RefreshCw,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

const Settings = () => {
  const [plants, setPlants] = useState([]);
  const [consumerUnits, setConsumerUnits] = useState([]);
  const [inverterCredentials, setInverterCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Inverter credential dialog
  const [inverterDialogOpen, setInverterDialogOpen] = useState(false);
  const [inverterForm, setInverterForm] = useState({
    plant_id: '',
    brand: '',
    username: '',
    password: ''
  });
  const [savingInverter, setSavingInverter] = useState(false);

  // COPEL credential dialog
  const [copelDialogOpen, setCopelDialogOpen] = useState(false);
  const [copelForm, setCopelForm] = useState({
    consumer_unit_id: '',
    cpf: '',
    password: ''
  });
  const [savingCopel, setSavingCopel] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [plantsRes, unitsRes] = await Promise.all([
        api.get('/plants'),
        api.get('/consumer-units')
      ]);
      setPlants(plantsRes.data);
      setConsumerUnits(unitsRes.data);
      
      // Load inverter credentials for each plant
      const credPromises = plantsRes.data.map(plant => 
        api.get(`/inverter-credentials/${plant.id}`).catch(() => ({ data: [] }))
      );
      const credResults = await Promise.all(credPromises);
      const allCreds = credResults.flatMap(r => r.data || []);
      setInverterCredentials(allCreds);
    } catch (error) {
      toast.error('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveInverterCredential = async () => {
    if (!inverterForm.plant_id || !inverterForm.brand || !inverterForm.username || !inverterForm.password) {
      toast.error('Preencha todos os campos');
      return;
    }

    setSavingInverter(true);
    try {
      await api.post('/inverter-credentials', inverterForm);
      toast.success('Credencial salva com sucesso');
      setInverterDialogOpen(false);
      setInverterForm({ plant_id: '', brand: '', username: '', password: '' });
      loadData();
    } catch (error) {
      toast.error('Erro ao salvar credencial');
    } finally {
      setSavingInverter(false);
    }
  };

  const handleSaveCopelCredential = async () => {
    if (!copelForm.consumer_unit_id || !copelForm.cpf || !copelForm.password) {
      toast.error('Preencha todos os campos');
      return;
    }

    setSavingCopel(true);
    try {
      await api.post('/copel-credentials', copelForm);
      toast.success('Credencial COPEL salva com sucesso');
      setCopelDialogOpen(false);
      setCopelForm({ consumer_unit_id: '', cpf: '', password: '' });
    } catch (error) {
      toast.error('Erro ao salvar credencial');
    } finally {
      setSavingCopel(false);
    }
  };

  const getPlantName = (plantId) => {
    const plant = plants.find(p => p.id === plantId);
    return plant?.name || 'Usina não encontrada';
  };

  const getUnitInfo = (unitId) => {
    const unit = consumerUnits.find(u => u.id === unitId);
    return unit ? `${unit.contract_number} - ${unit.address}` : 'UC não encontrada';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="settings-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold text-neutral-900 font-heading">Configurações</h1>
        <p className="text-neutral-500 mt-1">Gerencie credenciais e integrações</p>
      </div>

      <Tabs defaultValue="inverters" className="space-y-6">
        <TabsList className="bg-neutral-100">
          <TabsTrigger value="inverters">Inversores</TabsTrigger>
          <TabsTrigger value="copel">COPEL</TabsTrigger>
        </TabsList>

        {/* Inverters Tab */}
        <TabsContent value="inverters" className="space-y-6">
          <Card className="border-neutral-100 shadow-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Key className="h-5 w-5 text-[#FFD600]" />
                  Credenciais de Inversores
                </CardTitle>
                <Button 
                  onClick={() => setInverterDialogOpen(true)}
                  className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Adicionar Credencial
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-neutral-600 mb-6">
                Configure as credenciais de acesso aos portais dos inversores para sincronização automática dos dados de geração.
              </p>
              
              {inverterCredentials.length > 0 ? (
                <div className="space-y-4">
                  {inverterCredentials.map((cred, index) => (
                    <div key={index} className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg">
                      <div className="flex items-center gap-4">
                        <div className="p-2 bg-white rounded-lg border border-neutral-200">
                          <Zap className="h-5 w-5 text-amber-600" />
                        </div>
                        <div>
                          <p className="font-medium text-neutral-900">{getPlantName(cred.plant_id)}</p>
                          <p className="text-sm text-neutral-500">
                            {cred.brand?.toUpperCase()} • {cred.username}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {cred.last_sync ? (
                          <div className="flex items-center gap-1 text-emerald-600 text-sm">
                            <CheckCircle className="h-4 w-4" />
                            Sincronizado
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-amber-600 text-sm">
                            <AlertCircle className="h-4 w-4" />
                            Pendente
                          </div>
                        )}
                        <Button variant="ghost" size="icon">
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-neutral-500">
                  <Key className="h-12 w-12 mx-auto text-neutral-300 mb-4" />
                  <p>Nenhuma credencial cadastrada</p>
                  <p className="text-sm">Adicione credenciais para sincronizar dados automaticamente</p>
                </div>
              )}

              {/* Supported Brands */}
              <div className="mt-8 p-4 bg-blue-50 rounded-lg">
                <h4 className="font-medium text-blue-900 mb-2">Marcas Suportadas</h4>
                <div className="flex flex-wrap gap-2">
                  {['Growatt', 'FusionSolar', 'Sungrow', 'Deye', 'Solis', 'SAJ', 'SolarMan', 'Livoltek'].map((brand) => (
                    <span key={brand} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                      {brand}
                    </span>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* COPEL Tab */}
        <TabsContent value="copel" className="space-y-6">
          <Card className="border-neutral-100 shadow-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Zap className="h-5 w-5 text-[#FFD600]" />
                  Credenciais COPEL
                </CardTitle>
                <Button 
                  onClick={() => setCopelDialogOpen(true)}
                  className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Adicionar Credencial
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-neutral-600 mb-6">
                Configure as credenciais de acesso ao portal da COPEL para download automático das faturas de energia.
              </p>
              
              <div className="text-center py-8 text-neutral-500">
                <Zap className="h-12 w-12 mx-auto text-neutral-300 mb-4" />
                <p>Automação COPEL em desenvolvimento</p>
                <p className="text-sm">Em breve você poderá baixar faturas automaticamente</p>
              </div>

              <div className="mt-6 p-4 bg-amber-50 rounded-lg">
                <h4 className="font-medium text-amber-900 mb-2">Funcionalidades Planejadas</h4>
                <ul className="text-sm text-amber-800 space-y-1">
                  <li>• Login automático no portal da COPEL</li>
                  <li>• Download da segunda via da fatura (PDF)</li>
                  <li>• Extração automática dos dados da fatura</li>
                  <li>• Sincronização programada (diária)</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Inverter Credential Dialog */}
      <Dialog open={inverterDialogOpen} onOpenChange={setInverterDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Adicionar Credencial de Inversor</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Usina *</Label>
              <Select
                value={inverterForm.plant_id}
                onValueChange={(value) => setInverterForm({ ...inverterForm, plant_id: value })}
              >
                <SelectTrigger>
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
              <Label>Marca do Inversor *</Label>
              <Select
                value={inverterForm.brand}
                onValueChange={(value) => setInverterForm({ ...inverterForm, brand: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecione a marca" />
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
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Usuário / Email *</Label>
              <Input
                value={inverterForm.username}
                onChange={(e) => setInverterForm({ ...inverterForm, username: e.target.value })}
                placeholder="Seu login no portal do inversor"
              />
            </div>

            <div className="space-y-2">
              <Label>Senha *</Label>
              <Input
                type="password"
                value={inverterForm.password}
                onChange={(e) => setInverterForm({ ...inverterForm, password: e.target.value })}
                placeholder="••••••••"
              />
            </div>

            <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
              <strong>Nota:</strong> Suas credenciais são armazenadas de forma criptografada (AES-256).
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setInverterDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveInverterCredential} 
              disabled={savingInverter}
              className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
            >
              {savingInverter ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* COPEL Credential Dialog */}
      <Dialog open={copelDialogOpen} onOpenChange={setCopelDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Adicionar Credencial COPEL</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Unidade Consumidora *</Label>
              <Select
                value={copelForm.consumer_unit_id}
                onValueChange={(value) => setCopelForm({ ...copelForm, consumer_unit_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecione uma UC" />
                </SelectTrigger>
                <SelectContent>
                  {consumerUnits.map((unit) => (
                    <SelectItem key={unit.id} value={unit.id}>
                      {unit.contract_number} - {unit.address}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>CPF do Titular *</Label>
              <Input
                value={copelForm.cpf}
                onChange={(e) => setCopelForm({ ...copelForm, cpf: e.target.value })}
                placeholder="000.000.000-00"
              />
            </div>

            <div className="space-y-2">
              <Label>Senha do Portal COPEL *</Label>
              <Input
                type="password"
                value={copelForm.password}
                onChange={(e) => setCopelForm({ ...copelForm, password: e.target.value })}
                placeholder="••••••••"
              />
            </div>

            <div className="p-3 bg-amber-50 rounded-lg text-sm text-amber-700">
              <strong>Atenção:</strong> Use as mesmas credenciais do portal COPEL (agência virtual).
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCopelDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveCopelCredential} 
              disabled={savingCopel}
              className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
            >
              {savingCopel ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Settings;
