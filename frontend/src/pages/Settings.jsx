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
  FileSpreadsheet,
  Clock,
  Timer,
  Wifi,
  Search
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

  // Sync interval state
  const [syncInterval, setSyncInterval] = useState(30);
  const [syncStatus, setSyncStatus] = useState(null);
  const [savingSyncInterval, setSavingSyncInterval] = useState(false);
  const [loadingSyncStatus, setLoadingSyncStatus] = useState(true);

  useEffect(() => {
    loadData();
    loadSyncSettings();
  }, []);

  const loadData = async () => {
    try {
      const [plantsRes, unitsRes, loginsRes] = await Promise.all([
        api.get('/plants'),
        api.get('/consumer-units'),
        api.get('/client-logins').catch(() => ({ data: [] }))
      ]);
      setPlants(plantsRes.data);
      setConsumerUnits(unitsRes.data);
      setClientLogins(loginsRes.data || []);
      
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

  const loadSyncSettings = async () => {
    try {
      const [intervalRes, statusRes] = await Promise.all([
        api.get('/settings/sync-interval').catch(() => ({ data: { interval_minutes: 30 } })),
        api.get('/settings/sync-status').catch(() => ({ data: null }))
      ]);
      setSyncInterval(intervalRes.data?.interval_minutes || 30);
      setSyncStatus(statusRes.data);
    } catch (error) {
      console.error('Error loading sync settings:', error);
    } finally {
      setLoadingSyncStatus(false);
    }
  };

  const handleSaveSyncInterval = async () => {
    setSavingSyncInterval(true);
    try {
      await api.put('/settings/sync-interval', { interval_minutes: syncInterval });
      toast.success(`Intervalo de sincronização atualizado para ${syncInterval} minutos`);
      loadSyncSettings();
    } catch (error) {
      toast.error('Erro ao atualizar intervalo');
    } finally {
      setSavingSyncInterval(false);
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

  // Client Login functions
  const handleOpenClientLoginDialog = (login = null) => {
    if (login) {
      setEditingLogin(login);
      setClientLoginForm({
        inverter_app: login.inverter_app || '',
        on_unit: login.on_unit || '',
        client_name: login.client_name || '',
        login: login.login || '',
        password: login.password || '',
        site_url: login.site_url || '',
        is_installer: login.is_installer || false
      });
    } else {
      setEditingLogin(null);
      setClientLoginForm({
        inverter_app: '',
        on_unit: '',
        client_name: '',
        login: '',
        password: '',
        site_url: '',
        is_installer: false
      });
    }
    setClientLoginDialogOpen(true);
  };

  const handleSaveClientLogin = async () => {
    if (!clientLoginForm.inverter_app || !clientLoginForm.login || !clientLoginForm.password) {
      toast.error('Preencha os campos obrigatórios: App, Login e Senha');
      return;
    }

    setSavingClientLogin(true);
    try {
      if (editingLogin) {
        await api.put(`/client-logins/${editingLogin.id}`, clientLoginForm);
        toast.success('Login atualizado com sucesso');
      } else {
        await api.post('/client-logins', clientLoginForm);
        toast.success('Login adicionado com sucesso');
      }
      setClientLoginDialogOpen(false);
      setClientLoginForm({ inverter_app: '', on_unit: '', client_name: '', login: '', password: '', site_url: '', is_installer: false });
      setEditingLogin(null);
      loadData();
    } catch (error) {
      toast.error('Erro ao salvar login');
    } finally {
      setSavingClientLogin(false);
    }
  };

  const handleDeleteClientLogin = async (login) => {
    if (!window.confirm(`Deseja excluir o login "${login.client_name || login.login}"?`)) return;
    
    try {
      await api.delete(`/client-logins/${login.id}`);
      toast.success('Login removido');
      loadData();
    } catch (error) {
      toast.error('Erro ao remover login');
    }
  };

  const handleExcelUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadingExcel(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/client-logins/upload-excel', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success(`${response.data.imported} logins importados com sucesso!`);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao importar Excel');
    } finally {
      setUploadingExcel(false);
      if (excelInputRef.current) excelInputRef.current.value = '';
    }
  };

  const downloadExcelTemplate = () => {
    // Create CSV template
    const headers = ['inverter_app', 'on_unit', 'client_name', 'login', 'password', 'site_url', 'is_installer'];
    const example = ['Growatt', 'ON CWB', 'João Silva', 'joao@email.com', 'senha123', 'https://server.growatt.com', 'false'];
    const example2 = ['Growatt', 'ON CG', 'INSTALADOR', 'BTAVB001', 'Comercial2023', 'https://server.growatt.com', 'true'];
    
    const csvContent = [
      headers.join(','),
      example.join(','),
      example2.join(',')
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'modelo_logins_clientes.csv';
    link.click();
  };

  const getPlantName = (plantId) => {
    const plant = plants.find(p => p.id === plantId);
    return plant?.name || 'Usina não encontrada';
  };

  // Sort logins: installer first, then by client name
  const sortedClientLogins = [...clientLogins].sort((a, b) => {
    if (a.is_installer && !b.is_installer) return -1;
    if (!a.is_installer && b.is_installer) return 1;
    return (a.client_name || '').localeCompare(b.client_name || '');
  });

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

      <Tabs defaultValue="sync" className="space-y-6">
        <TabsList className="bg-neutral-100">
          <TabsTrigger value="sync">Sincronização</TabsTrigger>
          <TabsTrigger value="client-logins">Logins de Clientes</TabsTrigger>
          <TabsTrigger value="inverters">Inversores</TabsTrigger>
          <TabsTrigger value="growatt">Growatt</TabsTrigger>
          <TabsTrigger value="copel">COPEL</TabsTrigger>
        </TabsList>

        {/* Sync Settings Tab */}
        <TabsContent value="sync" className="space-y-6">
          <Card className="border-neutral-200 shadow-sm bg-white">
            <CardHeader className="bg-white border-b border-neutral-100">
              <CardTitle className="text-lg flex items-center gap-2">
                <Timer className="h-5 w-5 text-[#EAB308]" />
                Sincronização Automática Growatt
              </CardTitle>
              <CardDescription>
                Configure a frequência de sincronização automática dos dados de geração do portal Growatt.
              </CardDescription>
            </CardHeader>
            <CardContent className="bg-white pt-6 space-y-6">
              {loadingSyncStatus ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
                </div>
              ) : (
                <>
                  {/* Current Status */}
                  {syncStatus && (
                    <div className="grid md:grid-cols-3 gap-4 p-4 bg-neutral-50 rounded-lg border border-neutral-100">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-white rounded-lg border border-neutral-200">
                          <Wifi className="h-5 w-5 text-emerald-500" />
                        </div>
                        <div>
                          <p className="text-xs text-neutral-500">Usinas Configuradas</p>
                          <p className="text-lg font-bold text-neutral-900">{syncStatus.plants_with_credentials || 0}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-white rounded-lg border border-neutral-200">
                          <Clock className="h-5 w-5 text-blue-500" />
                        </div>
                        <div>
                          <p className="text-xs text-neutral-500">Última Sincronização</p>
                          <p className="text-sm font-medium text-neutral-900">
                            {syncStatus.last_sync 
                              ? new Date(syncStatus.last_sync).toLocaleString('pt-BR', { 
                                  day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' 
                                })
                              : 'Nunca'
                            }
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-white rounded-lg border border-neutral-200">
                          <RefreshCw className="h-5 w-5 text-amber-500" />
                        </div>
                        <div>
                          <p className="text-xs text-neutral-500">Próxima Execução</p>
                          <p className="text-sm font-medium text-neutral-900">
                            {syncStatus.next_run 
                              ? new Date(syncStatus.next_run).toLocaleString('pt-BR', { 
                                  day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' 
                                })
                              : '-'
                            }
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Interval Configuration */}
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">Intervalo de Sincronização (minutos)</Label>
                      <div className="flex gap-3 items-center max-w-md">
                        <Select
                          value={String(syncInterval)}
                          onValueChange={(value) => setSyncInterval(Number(value))}
                        >
                          <SelectTrigger data-testid="sync-interval-select">
                            <SelectValue placeholder="Selecione o intervalo" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="15">15 minutos</SelectItem>
                            <SelectItem value="30">30 minutos</SelectItem>
                            <SelectItem value="60">1 hora</SelectItem>
                            <SelectItem value="120">2 horas</SelectItem>
                            <SelectItem value="360">6 horas</SelectItem>
                            <SelectItem value="720">12 horas</SelectItem>
                            <SelectItem value="1440">24 horas</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button 
                          onClick={handleSaveSyncInterval}
                          disabled={savingSyncInterval}
                          className="bg-[#1A1A1A] hover:bg-neutral-800 text-white"
                          data-testid="save-sync-interval-btn"
                        >
                          {savingSyncInterval ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            'Salvar'
                          )}
                        </Button>
                      </div>
                      <p className="text-xs text-neutral-500">
                        O sistema sincroniza automaticamente os dados de geração de todas as usinas 
                        com credenciais Growatt configuradas.
                      </p>
                    </div>
                  </div>

                  {/* Info Box */}
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                    <h4 className="font-medium text-blue-900 mb-2 flex items-center gap-2">
                      <Sun className="h-4 w-4" />
                      Como Funciona
                    </h4>
                    <ul className="text-sm text-blue-800 space-y-1">
                      <li>• O sistema busca automaticamente os dados de geração do dia atual</li>
                      <li>• Usinas sem geração no dia são marcadas como "offline" ou "0 kWh"</li>
                      <li>• Você pode forçar uma sincronização manual no Dashboard (botão "Sync Growatt")</li>
                      <li>• Apenas usinas com credenciais Growatt configuradas são sincronizadas</li>
                    </ul>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Client Logins Tab */}
        <TabsContent value="client-logins" className="space-y-6">
          <Card className="border-neutral-200 shadow-sm bg-white">
            <CardHeader className="bg-white border-b border-neutral-100">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Users className="h-5 w-5 text-[#EAB308]" />
                  Logins e Senhas de Clientes
                </CardTitle>
                <div className="flex gap-2">
                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    ref={excelInputRef}
                    onChange={handleExcelUpload}
                    className="hidden"
                  />
                  <Button
                    variant="outline"
                    onClick={downloadExcelTemplate}
                    className="text-neutral-600"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Modelo CSV
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => excelInputRef.current?.click()}
                    disabled={uploadingExcel}
                    className="text-neutral-600"
                  >
                    {uploadingExcel ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <FileSpreadsheet className="h-4 w-4 mr-2" />
                    )}
                    Importar CSV
                  </Button>
                  <Button 
                    onClick={() => handleOpenClientLoginDialog()}
                    className="bg-[#1A1A1A] hover:bg-neutral-800 text-white"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Adicionar
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="bg-white pt-6">
              <p className="text-sm text-neutral-600 mb-4">
                Gerencie os logins de acesso aos portais de monitoramento dos seus clientes. 
                O primeiro login marcado como "Instalador" será usado como login padrão.
              </p>
              
              {sortedClientLogins.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-neutral-50 border-b border-neutral-200">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium text-neutral-600">App/Portal</th>
                        <th className="px-4 py-3 text-left font-medium text-neutral-600">Unidade ON</th>
                        <th className="px-4 py-3 text-left font-medium text-neutral-600">Cliente</th>
                        <th className="px-4 py-3 text-left font-medium text-neutral-600">Login</th>
                        <th className="px-4 py-3 text-left font-medium text-neutral-600">Senha</th>
                        <th className="px-4 py-3 text-left font-medium text-neutral-600">Site</th>
                        <th className="px-4 py-3 text-right font-medium text-neutral-600">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {sortedClientLogins.map((login) => (
                        <tr key={login.id} className={login.is_installer ? 'bg-[#FFD600]/10' : 'hover:bg-neutral-50'}>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {login.is_installer && (
                                <span className="px-2 py-0.5 bg-[#FFD600] text-[#1A1A1A] text-xs font-semibold rounded">
                                  INSTALADOR
                                </span>
                              )}
                              <span className="font-medium">{login.inverter_app}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-neutral-600">{login.on_unit || '-'}</td>
                          <td className="px-4 py-3 text-neutral-900 font-medium">{login.client_name || '-'}</td>
                          <td className="px-4 py-3 font-mono text-neutral-700">{login.login}</td>
                          <td className="px-4 py-3 font-mono text-neutral-700">{login.password}</td>
                          <td className="px-4 py-3">
                            {login.site_url ? (
                              <a href={login.site_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs">
                                {login.site_url.replace(/^https?:\/\//, '').substring(0, 25)}...
                              </a>
                            ) : '-'}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex justify-end gap-2">
                              <Button 
                                variant="ghost" 
                                size="icon" 
                                className="h-8 w-8"
                                onClick={() => handleOpenClientLoginDialog(login)}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button 
                                variant="ghost" 
                                size="icon" 
                                className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50"
                                onClick={() => handleDeleteClientLogin(login)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-neutral-500">
                  <Users className="h-12 w-12 mx-auto mb-4 text-neutral-300" />
                  <p>Nenhum login cadastrado</p>
                  <p className="text-sm mt-1">Adicione logins manualmente ou importe via CSV</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

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

      {/* Client Login Dialog */}
      <Dialog open={clientLoginDialogOpen} onOpenChange={setClientLoginDialogOpen}>
        <DialogContent className="sm:max-w-lg bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Users className="h-5 w-5 text-[#EAB308]" />
              {editingLogin ? 'Editar Login' : 'Novo Login de Cliente'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="flex items-center gap-3 p-3 bg-neutral-50 rounded-lg">
              <input
                type="checkbox"
                id="is_installer"
                checked={clientLoginForm.is_installer}
                onChange={(e) => setClientLoginForm({ ...clientLoginForm, is_installer: e.target.checked })}
                className="h-4 w-4 accent-[#EAB308]"
              />
              <label htmlFor="is_installer" className="text-sm font-medium text-neutral-700">
                Login de Instalador (aparece no topo da lista)
              </label>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>App / Portal *</Label>
                <Select
                  value={clientLoginForm.inverter_app}
                  onValueChange={(value) => setClientLoginForm({ ...clientLoginForm, inverter_app: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Growatt">Growatt</SelectItem>
                    <SelectItem value="FusionSolar">FusionSolar (Huawei)</SelectItem>
                    <SelectItem value="Sungrow">Sungrow</SelectItem>
                    <SelectItem value="Deye">Deye</SelectItem>
                    <SelectItem value="Solis">Solis Cloud</SelectItem>
                    <SelectItem value="SolarMan">SolarMan</SelectItem>
                    <SelectItem value="iSolarCloud">iSolarCloud</SelectItem>
                    <SelectItem value="SAJ">SAJ</SelectItem>
                    <SelectItem value="Outro">Outro</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Unidade ON</Label>
                <Select
                  value={clientLoginForm.on_unit}
                  onValueChange={(value) => setClientLoginForm({ ...clientLoginForm, on_unit: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ON CWB">ON CWB</SelectItem>
                    <SelectItem value="ON CG">ON CG</SelectItem>
                    <SelectItem value="Outro">Outro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Nome do Cliente</Label>
              <Input
                value={clientLoginForm.client_name}
                onChange={(e) => setClientLoginForm({ ...clientLoginForm, client_name: e.target.value })}
                placeholder="Nome do cliente ou empresa"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Login *</Label>
                <Input
                  value={clientLoginForm.login}
                  onChange={(e) => setClientLoginForm({ ...clientLoginForm, login: e.target.value })}
                  placeholder="Email ou usuário"
                />
              </div>

              <div className="space-y-2">
                <Label>Senha *</Label>
                <Input
                  value={clientLoginForm.password}
                  onChange={(e) => setClientLoginForm({ ...clientLoginForm, password: e.target.value })}
                  placeholder="Senha"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Site/URL do Portal</Label>
              <Input
                value={clientLoginForm.site_url}
                onChange={(e) => setClientLoginForm({ ...clientLoginForm, site_url: e.target.value })}
                placeholder="https://server.growatt.com"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setClientLoginDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveClientLogin} 
              disabled={savingClientLogin}
              className="bg-[#1A1A1A] hover:bg-neutral-800 text-white"
            >
              {savingClientLogin ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Settings;
