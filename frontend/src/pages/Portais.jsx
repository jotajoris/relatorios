import { useState, useEffect } from 'react';
import api from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { Loader2, CheckCircle, AlertCircle, Wifi, WifiOff, Import, Sun, Zap, Factory } from 'lucide-react';

const PORTALS = [
  { id: 'growatt', name: 'Growatt (ShinePhone)', color: '#FFD600', endpoint: '/integrations/growatt/login' },
  { id: 'huawei', name: 'Huawei (FusionSolar)', color: '#E60012', endpoint: null },
  { id: 'deye', name: 'Deye / Sofar (Solarman)', color: '#0066CC', endpoint: null },
  { id: 'solis', name: 'Solis (SolisCloud)', color: '#00B050', endpoint: null },
];

const Portais = () => {
  const [activePortal, setActivePortal] = useState(null);
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [plants, setPlants] = useState([]);
  const [selectedPlants, setSelectedPlants] = useState(new Set());
  const [importing, setImporting] = useState(false);
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState('');

  useEffect(() => {
    api.get('/clients').then(r => setClients(r.data)).catch(() => {});
  }, []);

  const handleConnect = async (portal) => {
    if (!portal.endpoint) {
      toast.info(`${portal.name} sera implementado em breve`);
      return;
    }
    if (!credentials.username || !credentials.password) {
      toast.error('Preencha usuario e senha');
      return;
    }
    setLoading(true);
    setActivePortal(portal.id);
    setPlants([]);
    setSelectedPlants(new Set());
    try {
      const res = await api.post(portal.endpoint, {
        username: credentials.username,
        password: credentials.password,
      });
      if (res.data.success !== false) {
        const p = res.data.plants || [];
        setPlants(p);
        toast.success(`${p.length} usinas encontradas!`);
      } else {
        toast.error(res.data.error || 'Erro ao conectar');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao conectar com o portal');
    } finally {
      setLoading(false);
    }
  };

  const togglePlant = (idx) => {
    setSelectedPlants(prev => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedPlants.size === plants.length) {
      setSelectedPlants(new Set());
    } else {
      setSelectedPlants(new Set(plants.map((_, i) => i)));
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
      }));
      const res = await api.post('/portals/growatt/import-plants', {
        username: credentials.username,
        password: credentials.password,
        plants: selected,
        client_id: selectedClient,
      });
      if (res.data.success) {
        toast.success(`${res.data.total_imported} usinas importadas! ${res.data.total_skipped > 0 ? `(${res.data.total_skipped} ja existiam)` : ''}`);
        setSelectedPlants(new Set());
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao importar');
    } finally {
      setImporting(false);
    }
  };

  const statusIcon = (status) => {
    if (status === 'online') return <Wifi className="h-4 w-4 text-emerald-500" />;
    if (status === 'abnormal') return <AlertCircle className="h-4 w-4 text-amber-500" />;
    return <WifiOff className="h-4 w-4 text-neutral-400" />;
  };

  return (
    <div className="space-y-6" data-testid="portais-page">
      <div>
        <h1 className="text-2xl font-bold text-[#1A1A1A]">Portais de Monitoramento</h1>
        <p className="text-sm text-neutral-500 mt-1">Conecte com os portais dos inversores para importar e monitorar suas usinas</p>
      </div>

      {/* Portal Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {PORTALS.map(p => (
          <Card key={p.id} className={`cursor-pointer transition-all hover:shadow-md ${activePortal === p.id ? 'ring-2 ring-[#FFD600]' : ''}`}
            onClick={() => setActivePortal(p.id)}>
            <CardContent className="p-4 text-center">
              <div className="w-12 h-12 rounded-full mx-auto mb-2 flex items-center justify-center" style={{ backgroundColor: p.color + '20' }}>
                <Sun className="h-6 w-6" style={{ color: p.color }} />
              </div>
              <p className="font-semibold text-sm">{p.name}</p>
              <p className="text-xs text-neutral-400 mt-1">{p.endpoint ? 'Disponivel' : 'Em breve'}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Login Section */}
      {activePortal && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4 text-[#FFD600]" />
              Conectar ao {PORTALS.find(p => p.id === activePortal)?.name}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
              <div className="space-y-1">
                <Label className="text-xs">Usuario / Codigo Instalador</Label>
                <Input value={credentials.username} onChange={e => setCredentials({ ...credentials, username: e.target.value })}
                  placeholder="Ex: BTAVB001" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Senha</Label>
                <Input type="password" value={credentials.password} onChange={e => setCredentials({ ...credentials, password: e.target.value })}
                  placeholder="Senha do portal" />
              </div>
              <Button onClick={() => handleConnect(PORTALS.find(p => p.id === activePortal))}
                disabled={loading} className="bg-[#1A1A1A] hover:bg-[#333] text-white h-9">
                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Wifi className="h-4 w-4 mr-2" />}
                {loading ? 'Conectando...' : 'Buscar Usinas'}
              </Button>
            </div>

            {/* Plants List */}
            {plants.length > 0 && (
              <div className="space-y-3 mt-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">{plants.length} usinas encontradas</p>
                  <div className="flex items-center gap-3">
                    <select className="h-8 text-sm border rounded px-2" value={selectedClient}
                      onChange={e => setSelectedClient(e.target.value)}>
                      <option value="">Vincular ao cliente (opcional)</option>
                      {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                    <Button variant="outline" size="sm" onClick={toggleAll} className="text-xs h-8">
                      {selectedPlants.size === plants.length ? 'Desmarcar Todos' : 'Selecionar Todos'}
                    </Button>
                    <Button size="sm" onClick={handleImport} disabled={importing || selectedPlants.size === 0}
                      className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A] text-xs h-8">
                      {importing ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Import className="h-3 w-3 mr-1" />}
                      Importar {selectedPlants.size > 0 ? `(${selectedPlants.size})` : ''}
                    </Button>
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
                      </tr>
                    </thead>
                    <tbody>
                      {plants.map((p, i) => (
                        <tr key={i} className={`border-b last:border-0 cursor-pointer transition-colors ${selectedPlants.has(i) ? 'bg-[#FFD600]/10' : 'hover:bg-neutral-50'}`}
                          onClick={() => togglePlant(i)}>
                          <td className="py-2 px-2 text-center">
                            <input type="checkbox" checked={selectedPlants.has(i)} readOnly
                              className="rounded border-neutral-300 text-[#FFD600] focus:ring-[#FFD600]" />
                          </td>
                          <td className="py-2 px-3">
                            <p className="font-semibold text-[#1A1A1A]">{p.name}</p>
                            <p className="text-[10px] text-neutral-400">{p.username || p.alias || ''}</p>
                          </td>
                          <td className="py-2 px-3 text-neutral-500 text-xs">{p.city || '-'}</td>
                          <td className="py-2 px-2 text-center font-medium">{p.capacity_kwp}</td>
                          <td className="py-2 px-2 text-center">{statusIcon(p.status)}</td>
                          <td className="py-2 px-2 text-center text-xs">{p.today_energy_kwh || 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Portais;
