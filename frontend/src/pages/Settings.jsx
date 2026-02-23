import { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
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
  RefreshCw,
  Loader2,
  CheckCircle,
  AlertCircle,
  Sun,
  Download,
  Link2,
  Upload,
  Trash2,
  Edit,
  Users,
  FileSpreadsheet
} from 'lucide-react';

const Settings = () => {
  const [plants, setPlants] = useState([]);
  const [consumerUnits, setConsumerUnits] = useState([]);
  const [inverterCredentials, setInverterCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Client logins state
  const [clientLogins, setClientLogins] = useState([]);
  const [clientLoginDialogOpen, setClientLoginDialogOpen] = useState(false);
  const [editingLogin, setEditingLogin] = useState(null);
  const [clientLoginForm, setClientLoginForm] = useState({
    inverter_app: '',
    on_unit: '',
    client_name: '',
    login: '',
    password: '',
    site_url: '',
    is_installer: false
  });
  const [savingClientLogin, setSavingClientLogin] = useState(false);
  const [uploadingExcel, setUploadingExcel] = useState(false);
  const excelInputRef = useRef(null);
  
  // Inverter credential dialog
  const [inverterDialogOpen, setInverterDialogOpen] = useState(false);
  const [inverterForm, setInverterForm] = useState({
    plant_id: '',
    brand: '',
    username: '',
    password: ''
  });
  const [savingInverter, setSavingInverter] = useState(false);

  // Growatt test dialog
  const [growattTestOpen, setGrowattTestOpen] = useState(false);
  const [growattForm, setGrowattForm] = useState({
    plant_id: '',
    username: '',
    password: ''
  });
  const [testingGrowatt, setTestingGrowatt] = useState(false);
  const [growattPlants, setGrowattPlants] = useState([]);
  const [selectedGrowattPlant, setSelectedGrowattPlant] = useState('');
  const [syncing, setSyncing] = useState(false);

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

  const handleTestGrowatt = async () => {
    if (!growattForm.username || !growattForm.password || !growattForm.plant_id) {
      toast.error('Preencha todos os campos');
      return;
    }

    setTestingGrowatt(true);
    setGrowattPlants([]);
    try {
      // Use the new login endpoint
      const response = await api.post('/integrations/growatt/login', {
        username: growattForm.username,
        password: growattForm.password
      });
      
      if (response.data.success) {
        toast.success(`Conectado! ${response.data.total} usinas encontradas`);
        setGrowattPlants(response.data.plants || []);
      }
    } catch (error) {
      const msg = error.response?.data?.detail || 'Erro ao conectar ao Growatt';
      toast.error(msg);
    } finally {
      setTestingGrowatt(false);
    }
  };

  const handleSyncGrowatt = async () => {
    if (!selectedGrowattPlant) {
      toast.error('Selecione uma usina do Growatt');
      return;
    }

    setSyncing(true);
    try {
      // First link the plant
      await api.post(`/integrations/growatt/link-plant?plant_id=${growattForm.plant_id}&growatt_plant_name=${encodeURIComponent(selectedGrowattPlant)}`);
      
      // Then sync data
      const response = await api.post('/integrations/growatt/sync', {
        username: growattForm.username,
        password: growattForm.password,
        plant_name: selectedGrowattPlant
      });
      
      if (response.data.success) {
        toast.success('Sincronização concluída!');
        setGrowattTestOpen(false);
        setGrowattForm({ plant_id: '', username: '', password: '' });
        setGrowattPlants([]);
        setSelectedGrowattPlant('');
      }
    } catch (error) {
      const msg = error.response?.data?.detail || 'Erro ao sincronizar dados';
      toast.error(msg);
    } finally {
      setSyncing(false);
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
          <TabsTrigger value="growatt">Growatt</TabsTrigger>
          <TabsTrigger value="copel">COPEL</TabsTrigger>
        </TabsList>

        {/* Inverters Tab */}
        <TabsContent value="inverters" className="space-y-6">
          <Card className="border-neutral-200 shadow-sm bg-white">
            <CardHeader className="bg-white border-b border-neutral-100">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Key className="h-5 w-5 text-[#EAB308]" />
                  Credenciais de Inversores
                </CardTitle>
                <Button 
                  onClick={() => setInverterDialogOpen(true)}
                  className="bg-[#1A1A1A] hover:bg-neutral-800 text-white"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Adicionar
                </Button>
              </div>
            </CardHeader>
            <CardContent className="bg-white pt-6">
              <p className="text-sm text-neutral-600 mb-6">
                Configure as credenciais de acesso aos portais dos inversores para sincronização automática.
              </p>
              
              {inverterCredentials.length > 0 ? (
                <div className="space-y-4">
                  {inverterCredentials.map((cred, index) => (
                    <div key={index} className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg border border-neutral-100">
                      <div className="flex items-center gap-4">
                        <div className="p-2 bg-white rounded-lg border border-neutral-200">
                          <Sun className="h-5 w-5 text-amber-600" />
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
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-neutral-500">
                  <Key className="h-12 w-12 mx-auto text-neutral-300 mb-4" />
                  <p>Nenhuma credencial cadastrada</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Growatt Tab */}
        <TabsContent value="growatt" className="space-y-6">
          <Card className="border-neutral-200 shadow-sm bg-white">
            <CardHeader className="bg-white border-b border-neutral-100">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Sun className="h-5 w-5 text-[#EAB308]" />
                    Integração Growatt
                  </CardTitle>
                  <CardDescription className="mt-1">
                    Sincronize dados de geração diretamente do portal Growatt OSS
                  </CardDescription>
                </div>
                <Button 
                  onClick={() => setGrowattTestOpen(true)}
                  className="bg-[#1A1A1A] hover:bg-neutral-800 text-white"
                >
                  <Link2 className="h-4 w-4 mr-2" />
                  Conectar
                </Button>
              </div>
            </CardHeader>
            <CardContent className="bg-white pt-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-100">
                  <h4 className="font-medium text-emerald-900 mb-2 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Funcionalidades Disponíveis
                  </h4>
                  <ul className="text-sm text-emerald-800 space-y-1">
                    <li>• Login no portal Growatt OSS</li>
                    <li>• Listagem de usinas</li>
                    <li>• Sincronização de dados de geração</li>
                    <li>• Histórico dos últimos 30 dias</li>
                  </ul>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <h4 className="font-medium text-blue-900 mb-2">Como usar</h4>
                  <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                    <li>Clique em "Conectar"</li>
                    <li>Informe suas credenciais do Growatt</li>
                    <li>Selecione a usina para sincronizar</li>
                    <li>Clique em "Sincronizar Dados"</li>
                  </ol>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* COPEL Tab */}
        <TabsContent value="copel" className="space-y-6">
          <Card className="border-neutral-200 shadow-sm bg-white">
            <CardHeader className="bg-white border-b border-neutral-100">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Zap className="h-5 w-5 text-[#EAB308]" />
                  Credenciais COPEL
                </CardTitle>
                <Button 
                  onClick={() => setCopelDialogOpen(true)}
                  className="bg-[#1A1A1A] hover:bg-neutral-800 text-white"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Adicionar
                </Button>
              </div>
            </CardHeader>
            <CardContent className="bg-white pt-6">
              <p className="text-sm text-neutral-600 mb-6">
                Configure as credenciais de acesso ao portal da COPEL para download automático das faturas.
              </p>
              
              <div className="p-4 bg-amber-50 rounded-lg border border-amber-100">
                <h4 className="font-medium text-amber-900 mb-2">Em Desenvolvimento</h4>
                <ul className="text-sm text-amber-800 space-y-1">
                  <li>• Login automático no portal da COPEL</li>
                  <li>• Download da segunda via da fatura (PDF)</li>
                  <li>• Extração automática dos dados da fatura</li>
                  <li>• Sincronização programada</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Inverter Credential Dialog */}
      <Dialog open={inverterDialogOpen} onOpenChange={setInverterDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
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
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setInverterDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveInverterCredential} 
              disabled={savingInverter}
              className="bg-[#1A1A1A] hover:bg-neutral-800 text-white"
            >
              {savingInverter ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Growatt Test Dialog */}
      <Dialog open={growattTestOpen} onOpenChange={setGrowattTestOpen}>
        <DialogContent className="sm:max-w-lg bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Sun className="h-5 w-5 text-amber-500" />
              Conectar ao Growatt
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Usina (no sistema) *</Label>
              <Select
                value={growattForm.plant_id}
                onValueChange={(value) => setGrowattForm({ ...growattForm, plant_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecione a usina para vincular" />
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
              <Label>Usuário Growatt *</Label>
              <Input
                value={growattForm.username}
                onChange={(e) => setGrowattForm({ ...growattForm, username: e.target.value })}
                placeholder="Seu login do Growatt OSS"
              />
            </div>

            <div className="space-y-2">
              <Label>Senha Growatt *</Label>
              <Input
                type="password"
                value={growattForm.password}
                onChange={(e) => setGrowattForm({ ...growattForm, password: e.target.value })}
                placeholder="••••••••"
              />
            </div>

            <Button 
              onClick={handleTestGrowatt}
              disabled={testingGrowatt}
              className="w-full bg-amber-500 hover:bg-amber-600 text-white"
            >
              {testingGrowatt ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Conectando...
                </>
              ) : (
                <>
                  <Link2 className="h-4 w-4 mr-2" />
                  Testar Conexão
                </>
              )}
            </Button>

            {/* Growatt Plants List */}
            {growattPlants.length > 0 && (
              <div className="space-y-3 pt-4 border-t border-neutral-200">
                <Label>Usinas encontradas no Growatt:</Label>
                <Select
                  value={selectedGrowattPlant}
                  onValueChange={setSelectedGrowattPlant}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione para sincronizar" />
                  </SelectTrigger>
                  <SelectContent>
                    {growattPlants.map((plant) => (
                      <SelectItem key={plant.id} value={plant.id}>
                        {plant.name} ({plant.capacity_kwp} kWp)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {selectedGrowattPlant && (
                  <Button 
                    onClick={handleSyncGrowatt}
                    disabled={syncing}
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    {syncing ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Sincronizando...
                      </>
                    ) : (
                      <>
                        <Download className="h-4 w-4 mr-2" />
                        Sincronizar Dados (30 dias)
                      </>
                    )}
                  </Button>
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setGrowattTestOpen(false);
              setGrowattPlants([]);
              setSelectedGrowattPlant('');
            }}>
              Fechar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* COPEL Credential Dialog */}
      <Dialog open={copelDialogOpen} onOpenChange={setCopelDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
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
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCopelDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveCopelCredential} 
              disabled={savingCopel}
              className="bg-[#1A1A1A] hover:bg-neutral-800 text-white"
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
