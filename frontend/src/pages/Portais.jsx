import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { 
  Loader2, CheckCircle, AlertCircle, Wifi, WifiOff, Import, Sun, Zap, 
  RefreshCw, Settings, Trash2, Eye, EyeOff, Link, Unlink, Check, X,
  CloudDownload
} from 'lucide-react';

const PORTALS = [
  { id: 'growatt', name: 'Growatt (ShinePhone)', color: '#FFD600', available: true },
  { id: 'solarman', name: 'Deye / Sofar (Solarman)', color: '#0066CC', available: true },
  { id: 'huawei', name: 'Huawei (FusionSolar)', color: '#E60012', available: false },
  { id: 'solis', name: 'Solis (SolisCloud)', color: '#00B050', available: false },
];

const Portais = () => {
  const [activePortal, setActivePortal] = useState('growatt');
  const [portalConnections, setPortalConnections] = useState({});
  const [credentials, setCredentials] = useState({ username: '', password: '', server: 'internacional', group: '' });
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [plants, setPlants] = useState([]);
  const [importedPlantIds, setImportedPlantIds] = useState(new Set());
  const [selectedPlants, setSelectedPlants] = useState(new Set());
  const [importing, setImporting] = useState(false);
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [existingPlants, setExistingPlants] = useState([]);
  
  // Solarman session-based state
  const [solarmanStatus, setSolarmanStatus] = useState({ connected: false, loading: true });
  const [showCookieDialog, setShowCookieDialog] = useState(false);
  const [cookiesInput, setCookiesInput] = useState('');

  // Load saved connections and existing plants
  useEffect(() => {
    loadSavedConnections();
    loadClients();
    loadExistingPlants();
    checkSolarmanStatus();
  }, []);
  
  // Check Solarman session status
  const checkSolarmanStatus = async () => {
    try {
      const res = await api.get('/integrations/solarman/status');
      setSolarmanStatus({ ...res.data, loading: false });
    } catch (err) {
      setSolarmanStatus({ connected: false, loading: false });
    }
  };
  
  // Handle Solarman login via popup
  const handleSolarmanLogin = () => {
    // Open Solarman PRO login (installer portal) in new tab
    window.open('https://pro.solarmanpv.com/login', '_blank');
    
    toast.info(
      <div>
        <p className="font-medium">Faça login no Solarman</p>
        <p className="text-sm text-neutral-500 mt-1">
          Após fazer login, volte aqui e clique em "Colar Cookies" para capturar a sessão.
        </p>
      </div>,
      { duration: 8000 }
    );
  };
  
  // Disconnect Solarman
  const handleSolarmanDisconnect = async () => {
    try {
      await api.post('/integrations/solarman/disconnect');
      setSolarmanStatus({ connected: false, loading: false });
      setPlants([]);
      toast.success('Desconectado do Solarman');
    } catch (err) {
      toast.error('Erro ao desconectar');
    }
  };
  
  // Fetch Solarman plants
  const fetchSolarmanPlants = async () => {
    setRefreshing(true);
    try {
      const res = await api.get('/integrations/solarman/plants');
      if (res.data.success) {
        setPlants(res.data.plants || []);
        toast.success(`${res.data.count} usinas encontradas`);
      } else {
        toast.error(res.data.error || 'Erro ao buscar usinas');
      }
    } catch (err) {
      if (err.response?.status === 401) {
        setSolarmanStatus({ connected: false, loading: false });
        toast.error('Sessão expirada. Faça login novamente.');
      } else {
        toast.error(err.response?.data?.detail || 'Erro ao buscar usinas');
      }
    } finally {
      setRefreshing(false);
    }
  };
  
  // Save cookies manually (alternative method)
  const handleSaveCookiesManually = async () => {
    if (!cookiesInput.trim()) {
      toast.error('Cole os cookies no campo de texto');
      return;
    }
    
    try {
      // Parse cookies - support both JSON array and simple format
      let cookies;
      try {
        cookies = JSON.parse(cookiesInput);
      } catch {
        // Try parsing as simple cookie format: name=value; name2=value2
        cookies = cookiesInput.split(';').map(c => {
          const [name, ...valueParts] = c.trim().split('=');
          return { name: name.trim(), value: valueParts.join('=').trim(), domain: '.solarmanpv.com' };
        }).filter(c => c.name && c.value);
      }
      
      if (!Array.isArray(cookies) || cookies.length === 0) {
        toast.error('Formato de cookies inválido');
        return;
      }
      
      setLoading(true);
      const res = await api.post('/integrations/solarman/complete-login', { cookies });
      
      if (res.data.success) {
        toast.success('Sessão salva com sucesso!');
        setSolarmanStatus({ connected: true, loading: false });
        setShowCookieDialog(false);
        setCookiesInput('');
        // Try to fetch plants
        fetchSolarmanPlants();
      } else {
        toast.error(res.data.error || 'Erro ao salvar sessão');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao processar cookies');
    } finally {
      setLoading(false);
    }
  };

  // Update credentials when switching portals
  useEffect(() => {
    const connection = portalConnections[activePortal];
    if (connection) {
      setCredentials({
        username: connection.username || connection.email || '',
        password: connection.password || '',
        server: connection.server || 'internacional',
        group: connection.group || ''
      });
    } else {
      setCredentials({ username: '', password: '', server: 'internacional', group: '' });
    }
    setPlants([]);
    setSelectedPlants(new Set());
  }, [activePortal, portalConnections]);

  const loadSavedConnections = async () => {
    try {
      const res = await api.get('/portal-connections');
      const connections = {};
      res.data.forEach(conn => {
        connections[conn.portal_id] = conn;
      });
      setPortalConnections(connections);
    } catch (err) {
      // Silently fail if endpoint doesn't exist yet
    }
  };

  const loadClients = async () => {
    try {
      const res = await api.get('/clients');
      setClients(res.data);
    } catch (err) {}
  };

  const loadExistingPlants = async () => {
    try {
      const res = await api.get('/plants');
      setExistingPlants(res.data);
      // Create a set of growatt_name and solarman_plant_name for quick lookup
      const imported = new Set([
        ...res.data.map(p => p.growatt_name?.toLowerCase()).filter(Boolean),
        ...res.data.map(p => p.solarman_plant_name?.toLowerCase()).filter(Boolean)
      ]);
      setImportedPlantIds(imported);
    } catch (err) {}
  };

  const isPlantImported = useCallback((plantName) => {
    return existingPlants.some(p => 
      p.growatt_name?.toLowerCase() === plantName?.toLowerCase() ||
      p.solarman_plant_name?.toLowerCase() === plantName?.toLowerCase() ||
      p.name?.toLowerCase() === plantName?.toLowerCase()
    );
  }, [existingPlants]);

  const getImportedPlant = useCallback((plantName) => {
    return existingPlants.find(p => 
      p.growatt_name?.toLowerCase() === plantName?.toLowerCase() ||
      p.solarman_plant_name?.toLowerCase() === plantName?.toLowerCase() ||
      p.name?.toLowerCase() === plantName?.toLowerCase()
    );
  }, [existingPlants]);

  const handleConnect = async () => {
    const portal = PORTALS.find(p => p.id === activePortal);
    if (!portal?.available) {
      toast.info(`${portal.name} será implementado em breve`);
      return;
    }
    if (!credentials.username || !credentials.password) {
      toast.error('Preencha usuário/email e senha');
      return;
    }
    
    setLoading(true);
    setPlants([]);
    setSelectedPlants(new Set());
    
    try {
      let res;
      
      if (activePortal === 'growatt') {
        res = await api.post('/integrations/growatt/login', {
          username: credentials.username,
          password: credentials.password,
        });
      } else if (activePortal === 'solarman') {
        res = await api.post('/integrations/solarman/login', {
          email: credentials.username,
          password: credentials.password,
          server: credentials.server || 'internacional',
          group: credentials.group || '',
        });
      }
      
      if (res?.data?.success !== false) {
        const p = res.data.plants || [];
        setPlants(p);
        
        // Save connection
        await saveConnection(portal.id, credentials.username, credentials.password, true, {
          server: credentials.server,
          group: credentials.group
        });
        
        toast.success(`Conectado! ${p.length} usinas encontradas`);
      } else {
        toast.error(res?.data?.error || 'Erro ao conectar');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao conectar com o portal');
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshPlants = async () => {
    const portal = PORTALS.find(p => p.id === activePortal);
    if (!portal?.available) return;
    
    const connection = portalConnections[activePortal];
    const user = credentials.username || connection?.username || connection?.email;
    const pass = credentials.password || connection?.password;
    
    if (!user || !pass) {
      toast.error('Credenciais não encontradas. Conecte primeiro.');
      return;
    }
    
    setRefreshing(true);
    
    try {
      let res;
      
      if (activePortal === 'growatt') {
        res = await api.post('/integrations/growatt/login', {
          username: user,
          password: pass,
        });
      } else if (activePortal === 'solarman') {
        res = await api.post('/integrations/solarman/login', {
          email: user,
          password: pass,
          server: credentials.server || connection?.server || 'internacional',
          group: credentials.group || connection?.group || '',
        });
      }
      
      if (res?.data?.success !== false) {
        const p = res.data.plants || [];
        setPlants(p);
        await loadExistingPlants(); // Refresh imported plants list
        toast.success(`Lista atualizada! ${p.length} usinas`);
      } else {
        toast.error(res?.data?.error || 'Erro ao atualizar');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao atualizar lista');
    } finally {
      setRefreshing(false);
    }
  };

  const saveConnection = async (portalId, username, password, connected, extras = {}) => {
    try {
      await api.post('/portal-connections', {
        portal_id: portalId,
        username,
        email: portalId === 'solarman' ? username : undefined,
        password,
        connected,
        server: extras.server,
        group: extras.group,
        last_connected: new Date().toISOString()
      });
      
      setPortalConnections(prev => ({
        ...prev,
        [portalId]: { portal_id: portalId, username, password, connected, ...extras }
      }));
    } catch (err) {
      // Silently fail
    }
  };

  const handleDisconnect = async () => {
    try {
      await api.delete(`/portal-connections/${activePortal}`);
      setPortalConnections(prev => {
        const next = { ...prev };
        delete next[activePortal];
        return next;
      });
      setPlants([]);
      setCredentials({ username: '', password: '' });
      toast.success('Desconectado do portal');
    } catch (err) {
      toast.error('Erro ao desconectar');
    }
  };

  const togglePlant = (idx) => {
    const plant = plants[idx];
    if (isPlantImported(plant.name)) return; // Can't select already imported
    
    setSelectedPlants(prev => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  const toggleAll = () => {
    const notImported = plants
      .map((p, i) => ({ p, i }))
      .filter(({ p }) => !isPlantImported(p.name))
      .map(({ i }) => i);
    
    if (selectedPlants.size === notImported.length) {
      setSelectedPlants(new Set());
    } else {
      setSelectedPlants(new Set(notImported));
    }
  };

  const handleImport = async () => {
    if (selectedPlants.size === 0) {
      toast.error('Selecione ao menos uma usina');
      return;
    }
    
    setImporting(true);
    try {
      const selected = [...selectedPlants].map(i => ({
        name: plants[i].name,
        capacity_kwp: plants[i].capacity_kwp,
        city: plants[i].city,
        growatt_id: plants[i].id,
        installation_date: plants[i].installation_date,
        status: plants[i].status,
        total_energy_kwh: plants[i].total_energy_kwh,
        device_count: plants[i].device_count,
        id: plants[i].id,
      }));
      
      let res;
      const connection = portalConnections[activePortal];
      
      if (activePortal === 'growatt') {
        res = await api.post('/portals/growatt/import-plants', {
          username: credentials.username || connection?.username,
          password: credentials.password || connection?.password,
          plants: selected,
          client_id: selectedClient,
        });
      } else if (activePortal === 'solarman') {
        res = await api.post('/portals/solarman/import-plants', {
          email: credentials.username || connection?.username || connection?.email,
          password: credentials.password || connection?.password,
          server: credentials.server || connection?.server || 'internacional',
          group: credentials.group || connection?.group || '',
          plants: selected,
          client_id: selectedClient,
        });
      }
      
      if (res?.data?.success) {
        toast.success(`${res.data.total_imported} usinas importadas!`);
        setSelectedPlants(new Set());
        await loadExistingPlants(); // Refresh to update imported status
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao importar');
    } finally {
      setImporting(false);
    }
  };

  const handleStopTracking = async (plantName) => {
    const importedPlant = getImportedPlant(plantName);
    if (!importedPlant) return;
    
    const portalName = activePortal === 'solarman' ? 'Solarman' : 'Growatt';
    if (!window.confirm(`Deseja parar de acompanhar a usina "${plantName}"? Isso removerá o vínculo com a ${portalName}, mas manterá os dados históricos.`)) {
      return;
    }
    
    try {
      const updateFields = activePortal === 'solarman' ? {
        solarman_plant_name: null,
        solarman_plant_id: null,
        solarman_email: null,
        solarman_password: null,
        solarman_server: null,
        solarman_group: null
      } : {
        growatt_name: null,
        growatt_plant_id: null,
        last_growatt_sync: null
      };
      
      await api.patch(`/plants/${importedPlant.id}`, updateFields);
      toast.success(`Usina "${plantName}" removida do acompanhamento`);
      await loadExistingPlants();
    } catch (err) {
      toast.error('Erro ao remover acompanhamento');
    }
  };

  const statusIcon = (status) => {
    if (status === 'online') return <Wifi className="h-4 w-4 text-emerald-500" />;
    if (status === 'abnormal') return <AlertCircle className="h-4 w-4 text-amber-500" />;
    return <WifiOff className="h-4 w-4 text-neutral-400" />;
  };

  const currentConnection = portalConnections[activePortal];
  const isConnected = currentConnection?.connected;
  const notImportedCount = plants.filter(p => !isPlantImported(p.name)).length;

  return (
    <div className="space-y-6" data-testid="portais-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#1A1A1A]">Portais de Monitoramento</h1>
          <p className="text-sm text-neutral-500 mt-1">Conecte aos portais dos inversores para importar e monitorar usinas</p>
        </div>
        <Button 
          variant="outline" 
          onClick={async () => {
            toast.info('Sincronizando dados de todas as usinas...');
            try {
              const res = await api.post('/integrations/growatt/sync-all', {}, { timeout: 120000 });
              toast.success(res.data.message || 'Sincronização concluída!');
            } catch (err) { 
              toast.error(err.response?.data?.detail || 'Erro na sincronização'); 
            }
          }} 
          className="border-[#FFD600] hover:bg-[#FFD600]/10"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Sincronizar Todas
        </Button>
      </div>

      {/* Portal Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {PORTALS.map(p => {
          const conn = portalConnections[p.id];
          return (
            <Card 
              key={p.id} 
              className={`cursor-pointer transition-all hover:shadow-md ${activePortal === p.id ? 'ring-2 ring-[#FFD600]' : ''} ${!p.available ? 'opacity-60' : ''}`}
              onClick={() => p.available && setActivePortal(p.id)}
            >
              <CardContent className="p-4 text-center relative">
                {conn?.connected && (
                  <div className="absolute top-2 right-2">
                    <CheckCircle className="h-4 w-4 text-emerald-500" />
                  </div>
                )}
                <div className="w-12 h-12 rounded-full mx-auto mb-2 flex items-center justify-center" style={{ backgroundColor: p.color + '20' }}>
                  <Sun className="h-6 w-6" style={{ color: p.color }} />
                </div>
                <p className="font-semibold text-sm">{p.name}</p>
                <p className="text-xs text-neutral-400 mt-1">
                  {conn?.connected ? (
                    <span className="text-emerald-600">Conectado</span>
                  ) : p.available ? (
                    'Disponível'
                  ) : (
                    'Em breve'
                  )}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Connection Section */}
      {activePortal && PORTALS.find(p => p.id === activePortal)?.available && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Zap className="h-4 w-4 text-[#FFD600]" />
                {PORTALS.find(p => p.id === activePortal)?.name}
                {isConnected && (
                  <Badge variant="outline" className="ml-2 text-emerald-600 border-emerald-600">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Conectado
                  </Badge>
                )}
              </CardTitle>
              {isConnected && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={handleDisconnect}
                  className="text-red-500 hover:text-red-600 hover:bg-red-50"
                >
                  <Unlink className="h-4 w-4 mr-1" />
                  Desconectar
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Solarman uses session capture instead of direct login */}
            {activePortal === 'solarman' ? (
              <div className="space-y-4">
                {/* Solarman Status */}
                <div className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    {solarmanStatus.loading ? (
                      <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
                    ) : solarmanStatus.connected ? (
                      <CheckCircle className="h-5 w-5 text-emerald-500" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-amber-500" />
                    )}
                    <div>
                      <p className="font-medium text-sm">
                        {solarmanStatus.loading ? 'Verificando...' : 
                         solarmanStatus.connected ? 'Conectado ao Solarman' : 'Não conectado'}
                      </p>
                      {solarmanStatus.connected && solarmanStatus.expires_at && (
                        <p className="text-xs text-neutral-500">
                          Sessão válida até: {new Date(solarmanStatus.expires_at).toLocaleDateString('pt-BR')}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    {solarmanStatus.connected ? (
                      <>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={fetchSolarmanPlants}
                          disabled={refreshing}
                        >
                          {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                          <span className="ml-2">Buscar Usinas</span>
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={handleSolarmanDisconnect}
                          className="text-red-500 hover:text-red-600"
                        >
                          <Unlink className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <div className="flex gap-2">
                        <Button 
                          onClick={handleSolarmanLogin}
                          disabled={loading}
                          className="bg-[#0066CC] hover:bg-[#0055AA] text-white"
                        >
                          {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Link className="h-4 w-4 mr-2" />}
                          {loading ? 'Aguardando login...' : 'Fazer Login'}
                        </Button>
                        <Button 
                          variant="outline"
                          onClick={() => setShowCookieDialog(true)}
                          disabled={loading}
                        >
                          Colar Cookies
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Instructions */}
                {!solarmanStatus.connected && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                    <p className="font-medium mb-1">Como funciona:</p>
                    <ol className="list-decimal list-inside space-y-1 text-xs">
                      <li>Clique em "Fazer Login" para abrir o portal Solarman em nova aba</li>
                      <li>Faça login normalmente (incluindo CAPTCHA se necessário)</li>
                      <li>Após logar, volte aqui e clique em "Colar Cookies"</li>
                      <li>Siga as instruções para copiar os cookies do navegador</li>
                    </ol>
                    <p className="text-xs mt-2 text-amber-600">
                      A sessão expira após alguns dias. Quando isso acontecer, você precisará fazer login novamente.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              /* Growatt uses traditional username/password login */
              <>
                {/* Credentials Section */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                  <div className="space-y-1">
                    <Label className="text-xs">Usuário / Código Instalador</Label>
                    <Input 
                      value={credentials.username} 
                      onChange={e => setCredentials({ ...credentials, username: e.target.value })}
                      placeholder="Ex: BTAVB001"
                      disabled={isConnected}
                      data-testid="portal-username-input"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Senha</Label>
                    <div className="relative">
                      <Input 
                        type={showPassword ? "text" : "password"} 
                        value={credentials.password} 
                        onChange={e => setCredentials({ ...credentials, password: e.target.value })}
                        placeholder="Senha do portal" 
                        disabled={isConnected}
                        data-testid="portal-password-input"
                      />
                      <button 
                        type="button"
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  
                  {!isConnected ? (
                    <Button 
                      onClick={handleConnect}
                      disabled={loading} 
                      className="bg-[#1A1A1A] hover:bg-[#333] text-white h-9"
                      data-testid="portal-connect-btn"
                    >
                      {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Link className="h-4 w-4 mr-2" />}
                      {loading ? 'Conectando...' : 'Conectar'}
                    </Button>
                  ) : (
                    <Button 
                      onClick={handleRefreshPlants}
                      disabled={refreshing} 
                      className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A] h-9"
                      data-testid="portal-refresh-btn"
                    >
                      {refreshing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                      {refreshing ? 'Atualizando...' : 'Atualizar Lista'}
                    </Button>
                  )}
                </div>

                {isConnected && (
                  <div className="text-xs text-neutral-500">
                    Conectado como: <strong>{currentConnection?.username || currentConnection?.email}</strong>
                  </div>
                )}
              </>
            )}

            {/* Plants List */}
            {plants.length > 0 && (
              <div className="space-y-3 mt-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <p className="text-sm font-medium">{plants.length} usinas no portal</p>
                    <Badge variant="outline" className="text-emerald-600 border-emerald-600">
                      {plants.length - notImportedCount} importadas
                    </Badge>
                    {notImportedCount > 0 && (
                      <Badge variant="outline" className="text-amber-600 border-amber-600">
                        {notImportedCount} não importadas
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-3 flex-wrap">
                    <select 
                      className="h-8 text-sm border rounded px-2" 
                      value={selectedClient}
                      onChange={e => setSelectedClient(e.target.value)}
                    >
                      <option value="">Vincular ao cliente (opcional)</option>
                      {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                    {notImportedCount > 0 && (
                      <>
                        <Button variant="outline" size="sm" onClick={toggleAll} className="text-xs h-8">
                          {selectedPlants.size === notImportedCount ? 'Desmarcar' : 'Selecionar Não Importadas'}
                        </Button>
                        <Button 
                          size="sm" 
                          onClick={handleImport} 
                          disabled={importing || selectedPlants.size === 0}
                          className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A] text-xs h-8"
                        >
                          {importing ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Import className="h-3 w-3 mr-1" />}
                          Importar {selectedPlants.size > 0 ? `(${selectedPlants.size})` : ''}
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-[#1A1A1A] text-[#FFD600]">
                      <tr>
                        <th className="w-10 py-2 px-2"></th>
                        <th className="text-left py-2 px-3 font-medium text-xs">Usina</th>
                        <th className="text-left py-2 px-3 font-medium text-xs">Cidade</th>
                        <th className="text-center py-2 px-2 font-medium text-xs">kWp</th>
                        <th className="text-center py-2 px-2 font-medium text-xs">Status</th>
                        <th className="text-center py-2 px-2 font-medium text-xs">Hoje (kWh)</th>
                        <th className="text-center py-2 px-2 font-medium text-xs">Situação</th>
                        <th className="w-20 py-2 px-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {plants.map((p, i) => {
                        const imported = isPlantImported(p.name);
                        const importedPlant = getImportedPlant(p.name);
                        return (
                          <tr 
                            key={i} 
                            className={`border-b last:border-0 transition-colors ${
                              imported 
                                ? 'bg-emerald-50' 
                                : selectedPlants.has(i) 
                                  ? 'bg-[#FFD600]/10 cursor-pointer' 
                                  : 'hover:bg-neutral-50 cursor-pointer'
                            }`}
                            onClick={() => !imported && togglePlant(i)}
                          >
                            <td className="py-2 px-2 text-center">
                              {imported ? (
                                <CheckCircle className="h-4 w-4 text-emerald-500 mx-auto" />
                              ) : (
                                <input 
                                  type="checkbox" 
                                  checked={selectedPlants.has(i)} 
                                  readOnly
                                  className="rounded border-neutral-300 text-[#FFD600] focus:ring-[#FFD600]" 
                                />
                              )}
                            </td>
                            <td className="py-2 px-3">
                              <p className="font-semibold text-[#1A1A1A]">{p.name}</p>
                              <p className="text-[10px] text-neutral-400">{p.username || p.alias || ''}</p>
                            </td>
                            <td className="py-2 px-3 text-neutral-500 text-xs">{p.city || '-'}</td>
                            <td className="py-2 px-2 text-center font-medium">{p.capacity_kwp}</td>
                            <td className="py-2 px-2 text-center">{statusIcon(p.status)}</td>
                            <td className="py-2 px-2 text-center text-xs">{p.today_energy_kwh || 0}</td>
                            <td className="py-2 px-2 text-center">
                              {imported ? (
                                <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">
                                  Importada
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="text-neutral-500 text-[10px]">
                                  Não importada
                                </Badge>
                              )}
                            </td>
                            <td className="py-2 px-2 text-center">
                              {imported && (
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleStopTracking(p.name);
                                  }}
                                  className="h-7 px-2 text-red-500 hover:text-red-600 hover:bg-red-50"
                                  title="Parar de acompanhar"
                                >
                                  <EyeOff className="h-3 w-3" />
                                </Button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                
                {/* Legend */}
                <div className="flex items-center gap-4 text-xs text-neutral-500 mt-2">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-emerald-50 border border-emerald-200 rounded"></div>
                    <span>Usina importada e sendo acompanhada</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-white border border-neutral-200 rounded"></div>
                    <span>Usina não importada (selecione para importar)</span>
                  </div>
                </div>
              </div>
            )}

            {/* Empty State */}
            {isConnected && plants.length === 0 && !refreshing && (
              <div className="text-center py-8 text-neutral-500">
                <CloudDownload className="h-12 w-12 mx-auto mb-3 text-neutral-300" />
                <p className="font-medium">Nenhuma usina carregada</p>
                <p className="text-sm mt-1">Clique em "Atualizar Lista" para buscar as usinas do portal</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
      
      {/* Cookie Input Dialog for Solarman */}
      {showCookieDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4">Colar Cookies do Solarman</h3>
            
            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
              <p className="font-medium mb-2">Como obter os cookies:</p>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>Faça login no <a href="https://pro.solarmanpv.com/login" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">pro.solarmanpv.com</a> (portal de instalador)</li>
                <li>Pressione F12 para abrir as ferramentas do desenvolvedor</li>
                <li>Vá na aba "Application" (Chrome) ou "Storage" (Firefox)</li>
                <li>Clique em "Cookies" → "pro.solarmanpv.com"</li>
                <li>Copie todos os cookies no formato: nome=valor; nome2=valor2</li>
              </ol>
            </div>
            
            <textarea
              className="w-full h-32 p-3 border border-neutral-300 rounded-lg text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Cole os cookies aqui..."
              value={cookiesInput}
              onChange={(e) => setCookiesInput(e.target.value)}
            />
            
            <div className="flex justify-end gap-3 mt-4">
              <Button 
                variant="outline" 
                onClick={() => {
                  setShowCookieDialog(false);
                  setCookiesInput('');
                }}
              >
                Cancelar
              </Button>
              <Button 
                onClick={handleSaveCookiesManually}
                disabled={loading || !cookiesInput.trim()}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Salvar Sessão
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Portais;
