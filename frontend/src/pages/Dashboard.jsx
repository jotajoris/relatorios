import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import {
  Zap, Factory, TrendingUp, Search, ChevronRight, CheckCircle,
  AlertTriangle, AlertCircle, HelpCircle, FileText, Users, BarChart3,
  RefreshCw, Loader2, Wifi
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Dashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    try {
      const res = await api.get('/dashboard/plants-summary');
      setData(res.data);
      setLastRefresh(new Date());
    } catch (err) {
      if (!data) toast.error('Erro ao carregar dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(loadData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleSyncAll = async () => {
    setSyncing(true);
    try {
      const res = await api.post('/integrations/growatt/sync-all', {}, { timeout: 120000 });
      toast.success(res.data.message || 'Sincronizacao concluida!');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao sincronizar');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64"><div className="w-8 h-8 spinner"></div></div>
  );

  const plants = data?.plants || [];
  const totals = data?.totals || {};

  const getStatus = (p) => {
    if (p.performance >= 90) return 'normal';
    if (p.performance >= 50) return 'alert';
    if (p.performance > 0) return 'critical';
    // No prognosis but has generation data = use Growatt status
    if (p.generation_kwh > 0 && p.status === 'online') return 'normal';
    if (p.generation_kwh > 0 && p.status === 'abnormal') return 'alert';
    if (p.status === 'online') return 'normal';
    if (p.status === 'offline') return 'critical';
    return 'unknown';
  };

  const counts = { all: plants.length, normal: 0, alert: 0, critical: 0, unknown: 0 };
  plants.forEach(p => { counts[getStatus(p)]++; });

  const filtered = plants.filter(p => {
    if (filter !== 'all' && getStatus(p) !== filter) return false;
    if (search) {
      const s = search.toLowerCase();
      return p.name?.toLowerCase().includes(s) || p.client_name?.toLowerCase().includes(s) || p.city?.toLowerCase().includes(s);
    }
    return true;
  });

  const statusColors = { normal: 'bg-emerald-500', alert: 'bg-amber-500', critical: 'bg-red-500', unknown: 'bg-neutral-400' };
  const statusRing = { normal: 'ring-emerald-500', alert: 'ring-amber-500', critical: 'ring-red-500', unknown: 'ring-neutral-400' };

  return (
    <div className="space-y-5 animate-fade-in" data-testid="dashboard">
      {/* Top Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <Card className="bg-[#1A1A1A] text-white border-0">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="h-4 w-4 text-[#FFD600]" />
              <span className="text-xs text-neutral-400 font-medium">Valores Totais</span>
            </div>
            <div className="flex items-baseline gap-3">
              <div>
                <p className="text-xs text-neutral-400">Total de usinas</p>
                <p className="text-2xl font-bold">{totals.total_plants}</p>
              </div>
            </div>
            <div className="flex gap-4 mt-2 text-xs text-neutral-400">
              <span><Zap className="h-3 w-3 inline text-[#FFD600]" /> {totals.total_generation_gwh} GWh</span>
              <span><Factory className="h-3 w-3 inline" /> {totals.total_capacity_mwp} MWp</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#FFD600] border-2 bg-[#FFD600]/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="h-4 w-4 text-[#1A1A1A]" />
              <span className="text-xs font-medium">Relatorios</span>
              <ChevronRight className="h-3 w-3 ml-auto text-neutral-400" />
            </div>
            <p className="text-xs text-neutral-500">Necessitam atencao</p>
            <p className="text-xl font-bold text-[#1A1A1A]">{counts.alert + counts.critical}</p>
          </CardContent>
        </Card>

        <Card className="border-neutral-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <span className="text-xs font-medium">Alertas</span>
            </div>
            <p className="text-xs text-neutral-500">Usinas com alerta</p>
            <p className="text-xl font-bold">{counts.alert}</p>
          </CardContent>
        </Card>

        <Card className="border-neutral-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <BarChart3 className="h-4 w-4 text-emerald-500" />
              <span className="text-xs font-medium">Gestao de Desempenho</span>
            </div>
            <p className="text-xs text-neutral-500">Necessitam intervencao</p>
            <p className="text-xl font-bold">{counts.critical}</p>
          </CardContent>
        </Card>

        <Card className="border-neutral-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <Users className="h-4 w-4 text-blue-500" />
              <span className="text-xs font-medium">Clientes</span>
            </div>
            <p className="text-xs text-neutral-500">Usinas ativas</p>
            <p className="text-xl font-bold">{totals.total_plants} <span className="text-sm font-normal text-neutral-400">usinas</span></p>
          </CardContent>
        </Card>
      </div>

      {/* Filter Tabs + Search + Sync */}
      <div className="flex flex-wrap items-center gap-2">
        {[
          { key: 'all', label: 'Todos', count: counts.all, color: 'bg-[#FFD600] text-[#1A1A1A]' },
          { key: 'normal', label: 'Normal', count: counts.normal, color: 'bg-emerald-500 text-white' },
          { key: 'alert', label: 'Com alerta', count: counts.alert, color: 'bg-amber-500 text-white' },
          { key: 'critical', label: 'Critico', count: counts.critical, color: 'bg-red-500 text-white' },
          { key: 'unknown', label: 'Desconhecido', count: counts.unknown, color: 'bg-neutral-400 text-white' },
        ].map(f => (
          <button key={f.key}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${filter === f.key ? f.color : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}`}
            onClick={() => setFilter(f.key)}>
            {f.label} <span className="ml-1 opacity-80">{f.count}</span>
          </button>
        ))}

        <div className="ml-auto flex items-center gap-2">
          {lastRefresh && (
            <span className="text-[10px] text-neutral-400">
              Atualizado: {lastRefresh.toLocaleTimeString('pt-BR', {hour:'2-digit',minute:'2-digit'})}
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={loadData} className="h-7 w-7 p-0" title="Atualizar dados">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          <Button variant="outline" size="sm" onClick={handleSyncAll} disabled={syncing}
            className="h-7 text-xs border-[#FFD600] hover:bg-[#FFD600]/10" title="Sincronizar todas as usinas Growatt">
            {syncing ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Wifi className="h-3 w-3 mr-1 text-[#FFD600]" />}
            {syncing ? 'Sincronizando...' : 'Sync Growatt'}
          </Button>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
            <Input placeholder="Buscar..." value={search} onChange={e => setSearch(e.target.value)}
              className="pl-9 w-48 h-7 text-xs" data-testid="dashboard-search" />
          </div>
        </div>
      </div>

      {/* Plants Table */}
      <Card className="border-neutral-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-200">
                <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase">Usina</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase">Cliente</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase">Cidade</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase">Data</th>
                <th className="text-center py-3 px-2 text-xs font-semibold text-neutral-500 uppercase">1D</th>
                <th className="text-center py-3 px-2 text-xs font-semibold text-neutral-500 uppercase">15D</th>
                <th className="text-center py-3 px-2 text-xs font-semibold text-neutral-500 uppercase">30D</th>
                <th className="text-center py-3 px-2 text-xs font-semibold text-neutral-500 uppercase">12M</th>
                <th className="text-center py-3 px-3 text-xs font-semibold text-neutral-500 uppercase">Aviso</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => {
                const status = getStatus(p);
                return (
                  <tr key={p.id} className="border-b border-neutral-100 hover:bg-neutral-50/50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/usinas/${p.id}`)} data-testid={`plant-row-${p.id}`}>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ring-2 ${statusRing[status]} overflow-hidden bg-neutral-100`}>
                          {p.logo_url ? (
                            <img src={`${API_URL}${p.logo_url}`} alt="" className="w-full h-full object-cover" />
                          ) : (
                            <Factory className="h-5 w-5 text-neutral-400" />
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-[#1A1A1A]">{p.name}</p>
                          <p className="text-[11px] text-[#FFD600] font-medium">{p.capacity_kwp} kWp</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-neutral-600">{p.client_name}</td>
                    <td className="py-3 px-4 text-sm text-neutral-500">{p.city}{p.state ? ` - ${p.state}` : ''}</td>
                    <td className="py-3 px-4 text-sm text-neutral-500">{p.installation_date || '-'}</td>
                    <td className="py-3 px-2 text-center"><PerfBadge value={p.perf_1d} gen={p.gen_1d_kwh} /></td>
                    <td className="py-3 px-2 text-center"><PerfBadge value={p.perf_15d} gen={p.gen_15d_kwh} /></td>
                    <td className="py-3 px-2 text-center"><PerfBadge value={p.perf_30d} gen={p.gen_30d_kwh} /></td>
                    <td className="py-3 px-2 text-center"><PerfBadge value={p.perf_12m} gen={p.gen_12m_kwh} /></td>
                    <td className="py-3 px-3 text-center">
                      {status === 'critical' ? (
                        <AlertCircle className="h-5 w-5 text-red-500 mx-auto" />
                      ) : status === 'alert' ? (
                        <AlertTriangle className="h-5 w-5 text-amber-500 mx-auto" />
                      ) : status === 'normal' ? (
                        <CheckCircle className="h-5 w-5 text-emerald-500 mx-auto" />
                      ) : (
                        <HelpCircle className="h-5 w-5 text-neutral-300 mx-auto" />
                      )}
                      {p.last_sync && (
                        <p className="text-[9px] text-neutral-400 mt-0.5">
                          {new Date(p.last_sync).toLocaleDateString('pt-BR', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}
                        </p>
                      )}
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-neutral-400">
                    Nenhuma usina encontrada
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

const PerfBadge = ({ value, gen }) => {
  // Show generation kWh if no performance %
  if ((!value || value === 0) && gen > 0) {
    return <span className="inline-flex items-center justify-center px-2 h-7 rounded-full text-[10px] font-bold ring-1 text-blue-600 bg-blue-50 ring-blue-200">
      {gen >= 1000 ? `${(gen/1000).toFixed(1)}M` : `${gen.toFixed(0)}`}
    </span>;
  }
  if (!value || value === 0) return <span className="text-xs text-neutral-300">-</span>;
  const color = value >= 90 ? 'text-emerald-600 bg-emerald-50 ring-emerald-200'
    : value >= 70 ? 'text-amber-600 bg-amber-50 ring-amber-200'
    : 'text-red-600 bg-red-50 ring-red-200';
  return (
    <span className={`inline-flex items-center justify-center w-12 h-7 rounded-full text-xs font-bold ring-1 ${color}`}>
      {value}
    </span>
  );
};

export default Dashboard;
