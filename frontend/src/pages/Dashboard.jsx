import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import KPICard from '../components/KPICard';
import StatusBadge from '../components/StatusBadge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  Sun,
  Factory,
  DollarSign,
  Leaf,
  TrendingUp,
  ArrowRight,
  AlertTriangle,
  Zap
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import { toast } from 'sonner';

const formatCurrency = (value) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value);
};

const formatNumber = (value) => {
  return new Intl.NumberFormat('pt-BR').format(value);
};

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [statsRes, plantsRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/dashboard/plants-summary')
      ]);
      
      setStats(statsRes.data);
      setPlants(plantsRes.data);
      
      // Generate mock chart data for the last 7 days
      const mockChartData = [];
      const today = new Date();
      for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        mockChartData.push({
          day: date.toLocaleDateString('pt-BR', { weekday: 'short' }),
          generation: Math.floor(Math.random() * 1000) + 500,
          prognosis: 800
        });
      }
      setChartData(mockChartData);
    } catch (error) {
      toast.error('Erro ao carregar dados do dashboard');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 spinner"></div>
      </div>
    );
  }

  const lowPerformancePlants = plants.filter(p => p.performance < 80 && p.performance > 0);

  return (
    <div className="space-y-6 animate-fade-in" data-testid="dashboard">
      {/* Page header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-neutral-900 font-heading">Dashboard</h1>
          <p className="text-neutral-500 mt-1">
            Visão geral das suas usinas solares - {stats?.month || 'Carregando...'}
          </p>
        </div>
        <div className="flex gap-3">
          <Button asChild className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]">
            <Link to="/usinas">
              <Factory className="h-4 w-4 mr-2" />
              Ver Usinas
            </Link>
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        <KPICard
          title="Geração Total"
          value={`${formatNumber(stats?.total_generation_kwh || 0)} kWh`}
          icon={Sun}
          accent="yellow"
          subtitle="Este mês"
        />
        <KPICard
          title="Usinas Ativas"
          value={stats?.total_plants || 0}
          icon={Factory}
          accent="green"
          subtitle={`${formatNumber(stats?.total_capacity_kwp || 0)} kWp total`}
        />
        <KPICard
          title="Economia Total"
          value={formatCurrency(stats?.total_saved_brl || 0)}
          icon={DollarSign}
          accent="blue"
          subtitle="Este mês"
        />
        <KPICard
          title="CO₂ Evitado"
          value={`${formatNumber(stats?.co2_avoided_kg || 0)} kg`}
          icon={Leaf}
          accent="gray"
          subtitle={`≈ ${formatNumber(stats?.trees_equivalent || 0)} árvores`}
        />
      </div>

      {/* Charts and Tables Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Generation Chart */}
        <Card className="lg:col-span-2 border-neutral-100 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold text-neutral-900 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-[#FFD600]" />
              Geração dos Últimos 7 Dias
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" vertical={false} />
                  <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#737373', fontSize: 12 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#737373', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e5e5',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                    }}
                    formatter={(value, name) => [
                      `${formatNumber(value)} kWh`,
                      name === 'generation' ? 'Geração' : 'Prognóstico'
                    ]}
                  />
                  <Bar dataKey="generation" fill="#FFD600" radius={[4, 4, 0, 0]} name="generation" />
                  <Bar dataKey="prognosis" fill="#E5E5E5" radius={[4, 4, 0, 0]} name="prognosis" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Alerts */}
        <Card className="border-neutral-100 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold text-neutral-900 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Alertas
            </CardTitle>
          </CardHeader>
          <CardContent>
            {lowPerformancePlants.length > 0 ? (
              <ul className="space-y-3">
                {lowPerformancePlants.slice(0, 5).map((plant) => (
                  <li key={plant.id} className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg">
                    <Zap className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-neutral-900 truncate">{plant.name}</p>
                      <p className="text-xs text-amber-700">
                        Desempenho: {plant.performance}% (abaixo de 80%)
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <div className="p-3 bg-emerald-50 rounded-full mb-3">
                  <Leaf className="h-6 w-6 text-emerald-600" />
                </div>
                <p className="text-sm text-neutral-600">Nenhum alerta no momento</p>
                <p className="text-xs text-neutral-400 mt-1">Todas as usinas operando normalmente</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Plants Table */}
      <Card className="border-neutral-100 shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-semibold text-neutral-900 flex items-center gap-2">
              <Factory className="h-5 w-5 text-[#FFD600]" />
              Usinas
            </CardTitle>
            <Button variant="ghost" asChild className="text-sm text-neutral-600 hover:text-neutral-900">
              <Link to="/usinas">
                Ver todas
                <ArrowRight className="h-4 w-4 ml-1" />
              </Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {plants.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-neutral-100">
                    <th className="table-header text-left py-3 px-4">Usina</th>
                    <th className="table-header text-left py-3 px-4">Cliente</th>
                    <th className="table-header text-left py-3 px-4">Capacidade</th>
                    <th className="table-header text-left py-3 px-4">Geração</th>
                    <th className="table-header text-left py-3 px-4">Desempenho</th>
                    <th className="table-header text-left py-3 px-4">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {plants.slice(0, 5).map((plant) => (
                    <tr key={plant.id} className="table-row">
                      <td className="py-4 px-4">
                        <Link 
                          to={`/usinas/${plant.id}`}
                          className="text-sm font-medium text-neutral-900 hover:text-[#EAB308] transition-colors"
                        >
                          {plant.name}
                        </Link>
                      </td>
                      <td className="py-4 px-4 text-sm text-neutral-600">{plant.client_name}</td>
                      <td className="py-4 px-4 text-sm text-neutral-600">{plant.capacity_kwp} kWp</td>
                      <td className="py-4 px-4 text-sm text-neutral-900 font-medium tabular-nums">
                        {formatNumber(plant.generation_kwh)} kWh
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 bg-neutral-100 rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${
                                plant.performance >= 80 ? 'bg-emerald-500' : 
                                plant.performance >= 50 ? 'bg-amber-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${Math.min(plant.performance, 100)}%` }}
                            />
                          </div>
                          <span className="text-sm text-neutral-600 tabular-nums">{plant.performance}%</span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <StatusBadge status={plant.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="p-4 bg-neutral-100 rounded-full mb-4">
                <Factory className="h-8 w-8 text-neutral-400" />
              </div>
              <h3 className="text-lg font-medium text-neutral-900 mb-1">Nenhuma usina cadastrada</h3>
              <p className="text-sm text-neutral-500 mb-4">Comece adicionando sua primeira usina solar</p>
              <Button asChild className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]">
                <Link to="/usinas">
                  Cadastrar Usina
                </Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;
