import { useState, useEffect, useCallback } from 'react';
import { Upload, FileText, Search, Trash2, Eye, CheckCircle, AlertCircle, Loader2, Filter } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import api from '../services/api';

const CONCESSIONARIAS = [
  { value: 'copel', label: 'COPEL' },
  { value: 'energisa_ms', label: 'Energisa MS' },
];

const InvoicesPage = () => {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [concessionaria, setConcessionaria] = useState('copel');
  const [searchTerm, setSearchTerm] = useState('');
  const [parsedResult, setParsedResult] = useState(null);
  const [showResultDialog, setShowResultDialog] = useState(false);
  const [savingInvoice, setSavingInvoice] = useState(false);

  const loadInvoices = useCallback(async () => {
    try {
      const res = await api.get('/invoices');
      setInvoices(res.data);
    } catch {
      toast.error('Erro ao carregar faturas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadInvoices(); }, [loadInvoices]);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Apenas arquivos PDF sao aceitos');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/invoices/upload-pdf-auto', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (res.data.success) {
        setParsedResult(res.data);
        setShowResultDialog(true);
        if (res.data.uc_found) {
          toast.success(`Fatura da UC ${res.data.parsed_data?.uc_number || ''} processada!`);
        } else {
          toast.warning(`UC ${res.data.uc_number} nao encontrada no sistema`);
        }
      } else {
        toast.error(res.data.error || 'Erro ao processar PDF');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao enviar arquivo');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleSaveInvoice = async () => {
    if (!parsedResult?.parsed_data?.consumer_unit_id) {
      toast.error('UC nao encontrada. Cadastre a UC antes de salvar.');
      return;
    }
    setSavingInvoice(true);
    try {
      await api.post('/invoices/save-from-upload', parsedResult.parsed_data);
      toast.success('Fatura salva com sucesso!');
      setShowResultDialog(false);
      setParsedResult(null);
      loadInvoices();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao salvar fatura');
    } finally {
      setSavingInvoice(false);
    }
  };

  const handleDeleteInvoice = async (id) => {
    if (!window.confirm('Deseja realmente excluir esta fatura?')) return;
    try {
      await api.delete(`/invoices/${id}`);
      toast.success('Fatura removida');
      loadInvoices();
    } catch {
      toast.error('Erro ao remover fatura');
    }
  };

  const formatCurrency = (v) => {
    if (!v) return 'R$ 0,00';
    return `R$ ${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatNumber = (v) => {
    if (!v) return '0';
    return Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
  };

  const filtered = invoices.filter(inv => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      inv.reference_month?.toLowerCase().includes(term) ||
      inv.consumer_unit_id?.toLowerCase().includes(term) ||
      inv.plant_id?.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6" data-testid="invoices-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#1A1A1A]">Faturas</h1>
          <p className="text-sm text-neutral-500 mt-1">Upload e gerenciamento de faturas de energia</p>
        </div>
      </div>

      {/* Upload Card */}
      <Card className="border-2 border-dashed border-[#FFD600]/40 bg-[#FFD600]/5">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row items-start md:items-center gap-4">
            <div className="flex-1">
              <h3 className="font-semibold text-[#1A1A1A] mb-1">Upload de Fatura</h3>
              <p className="text-sm text-neutral-500">
                Selecione a concessionaria e faca o upload do PDF. A UC sera detectada automaticamente.
              </p>
            </div>
            <div className="flex items-center gap-3 w-full md:w-auto">
              <Select value={concessionaria} onValueChange={setConcessionaria}>
                <SelectTrigger className="w-[160px]" data-testid="select-concessionaria">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONCESSIONARIAS.map(c => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <label className="cursor-pointer">
                <input
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  data-testid="invoice-file-input"
                />
                <Button
                  variant="default"
                  className="bg-[#1A1A1A] hover:bg-[#2D2D2D] text-white gap-2"
                  disabled={uploading}
                  asChild
                >
                  <span>
                    {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                    {uploading ? 'Processando...' : 'Enviar PDF'}
                  </span>
                </Button>
              </label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search & Filter */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <Input
            placeholder="Buscar por referencia, UC..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
            data-testid="invoice-search"
          />
        </div>
        <div className="flex items-center gap-1 text-sm text-neutral-500">
          <Filter className="h-4 w-4" />
          {filtered.length} fatura{filtered.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Invoices List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <FileText className="h-12 w-12 text-neutral-300 mb-3" />
            <p className="text-neutral-500 font-medium">Nenhuma fatura encontrada</p>
            <p className="text-sm text-neutral-400 mt-1">Faca o upload de uma fatura PDF acima</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {filtered.map((inv) => (
            <Card key={inv.id} className="hover:shadow-md transition-shadow" data-testid={`invoice-card-${inv.id}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-[#1A1A1A] flex items-center justify-center flex-shrink-0">
                      <FileText className="h-5 w-5 text-[#FFD600]" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-sm text-[#1A1A1A] truncate">
                        Ref: {inv.reference_month || 'N/A'}
                      </p>
                      <p className="text-xs text-neutral-400">
                        Grupo {inv.tariff_group || 'B'} | {inv.is_generator ? 'Geradora' : 'Beneficiaria'}
                      </p>
                    </div>
                  </div>

                  <div className="hidden sm:flex items-center gap-6 text-sm">
                    <div className="text-right">
                      <p className="text-xs text-neutral-400">Consumo</p>
                      <p className="font-medium">{formatNumber((inv.energy_registered_fp_kwh || 0) + (inv.energy_registered_p_kwh || 0))} kWh</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-neutral-400">Compensado</p>
                      <p className="font-medium text-emerald-600">{formatNumber((inv.energy_compensated_fp_kwh || 0) + (inv.energy_compensated_p_kwh || 0))} kWh</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-neutral-400">Total</p>
                      <p className="font-semibold">{formatCurrency(inv.amount_total_brl)}</p>
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-red-400 hover:text-red-600 hover:bg-red-50"
                    onClick={() => handleDeleteInvoice(inv.id)}
                    data-testid={`delete-invoice-${inv.id}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Parsed Result Dialog */}
      <Dialog open={showResultDialog} onOpenChange={setShowResultDialog}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {parsedResult?.uc_found ? (
                <CheckCircle className="h-5 w-5 text-emerald-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-amber-500" />
              )}
              Resultado da Leitura
            </DialogTitle>
          </DialogHeader>

          {parsedResult && (
            <div className="space-y-4">
              {/* UC Info */}
              <div className="p-3 rounded-lg bg-neutral-50 border">
                <p className="text-sm font-medium">
                  UC: <span className="text-[#1A1A1A] font-bold">{parsedResult.parsed_data?.uc_number || parsedResult.uc_number || 'N/A'}</span>
                </p>
                {parsedResult.consumer_unit && (
                  <p className="text-xs text-neutral-500 mt-1">
                    {parsedResult.consumer_unit.holder_name} | Usina: {parsedResult.consumer_unit.plant_name}
                  </p>
                )}
                {!parsedResult.uc_found && (
                  <p className="text-xs text-amber-600 mt-1">{parsedResult.message}</p>
                )}
              </div>

              {/* Parsed Data Grid */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <DataRow label="Referencia" value={parsedResult.parsed_data?.reference_month} />
                <DataRow label="Vencimento" value={parsedResult.parsed_data?.due_date} />
                <DataRow label="Grupo" value={parsedResult.parsed_data?.tariff_group} />
                <DataRow label="Bandeira" value={parsedResult.parsed_data?.tariff_flag} />
                <DataRow label="Total" value={formatCurrency(parsedResult.parsed_data?.amount_total_brl)} highlight />
                <DataRow label="Ilum. Publica" value={formatCurrency(parsedResult.parsed_data?.public_lighting_brl)} />
              </div>

              {/* Energy Data */}
              <div>
                <h4 className="font-semibold text-sm mb-2 text-[#1A1A1A]">Dados de Energia</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {parsedResult.parsed_data?.tariff_group === 'A' ? (
                    <>
                      <DataRow label="Energia Reg. Ponta" value={`${formatNumber(parsedResult.parsed_data?.energy_registered_p_kwh)} kWh`} />
                      <DataRow label="Energia Reg. F.Ponta" value={`${formatNumber(parsedResult.parsed_data?.energy_registered_fp_kwh)} kWh`} />
                      <DataRow label="Injetada Ponta" value={`${formatNumber(parsedResult.parsed_data?.energy_injected_p_kwh)} kWh`} />
                      <DataRow label="Injetada F.Ponta" value={`${formatNumber(parsedResult.parsed_data?.energy_injected_fp_kwh)} kWh`} />
                      <DataRow label="Compensada Ponta" value={`${formatNumber(parsedResult.parsed_data?.energy_compensated_p_kwh)} kWh`} />
                      <DataRow label="Compensada F.Ponta" value={`${formatNumber(parsedResult.parsed_data?.energy_compensated_fp_kwh)} kWh`} />
                      <DataRow label="Demanda Medida" value={`${parsedResult.parsed_data?.demand_measured_kw || 0} kW`} />
                      <DataRow label="Demanda Injetada" value={`${parsedResult.parsed_data?.demand_injected_kw || 0} kW`} />
                    </>
                  ) : (
                    <>
                      <DataRow label="Consumo" value={`${formatNumber(parsedResult.parsed_data?.energy_registered_fp_kwh)} kWh`} />
                      <DataRow label="Compensado" value={`${formatNumber(parsedResult.parsed_data?.energy_compensated_fp_kwh)} kWh`} />
                      <DataRow label="Faturado" value={`${formatNumber(parsedResult.parsed_data?.energy_billed_fp_kwh)} kWh`} />
                      <DataRow label="Cred. Acumulado FP" value={`${formatNumber(parsedResult.parsed_data?.credits_accumulated_fp_kwh)} kWh`} />
                    </>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                {parsedResult.uc_found && (
                  <Button
                    className="flex-1 bg-[#1A1A1A] hover:bg-[#2D2D2D] text-white"
                    onClick={handleSaveInvoice}
                    disabled={savingInvoice}
                    data-testid="save-invoice-btn"
                  >
                    {savingInvoice ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CheckCircle className="h-4 w-4 mr-2" />}
                    Salvar Fatura
                  </Button>
                )}
                <Button variant="outline" onClick={() => setShowResultDialog(false)}>
                  Fechar
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

const DataRow = ({ label, value, highlight }) => (
  <div className="flex justify-between items-center py-1.5 px-2 rounded bg-neutral-50">
    <span className="text-neutral-500">{label}</span>
    <span className={`font-medium ${highlight ? 'text-[#1A1A1A] font-bold' : ''}`}>{value || '-'}</span>
  </div>
);

export default InvoicesPage;
