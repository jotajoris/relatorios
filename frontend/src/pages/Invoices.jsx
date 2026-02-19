import { useState, useEffect, useCallback } from 'react';
import { Upload, FileText, Search, Trash2, CheckCircle, AlertCircle, Loader2, Filter, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
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
  const [editData, setEditData] = useState(null);
  const [savingInvoice, setSavingInvoice] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [parsedMeta, setParsedMeta] = useState(null);

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
        const pd = res.data.parsed_data || {};
        const tv = pd.tariff_values || {};
        setParsedMeta({
          uc_found: res.data.uc_found,
          consumer_unit: res.data.consumer_unit,
          uc_number: pd.uc_number || res.data.uc_number,
          message: res.data.message,
        });
        setEditData({
          consumer_unit_id: pd.consumer_unit_id || '',
          plant_id: pd.plant_id || '',
          reference_month: pd.reference_month || '',
          tariff_group: pd.tariff_group || 'B',
          is_generator: pd.is_generator || false,
          amount_total_brl: pd.amount_total_brl || 0,
          billing_cycle_start: pd.billing_cycle_start || '',
          billing_cycle_end: pd.billing_cycle_end || '',
          amount_saved_brl: pd.amount_saved_brl || 0,
          // FP
          energy_registered_fp_kwh: pd.energy_registered_fp_kwh || 0,
          tariff_total_fp: tv.tariff_total_fp || 0,
          energy_billed_fp_kwh: pd.energy_billed_fp_kwh || 0,
          energy_injected_fp_kwh: pd.energy_injected_fp_kwh || 0,
          energy_compensated_fp_kwh: pd.energy_compensated_fp_kwh || 0,
          credits_accumulated_fp_kwh: pd.credits_accumulated_fp_kwh || 0,
          tariff_te_fp: tv.te_fp_unit || tv.te_fp || 0,
          // P
          energy_registered_p_kwh: pd.energy_registered_p_kwh || 0,
          tariff_total_p: tv.tariff_total_p || 0,
          energy_billed_p_kwh: pd.energy_billed_p_kwh || 0,
          energy_injected_p_kwh: pd.energy_injected_p_kwh || 0,
          energy_compensated_p_kwh: pd.energy_compensated_p_kwh || 0,
          credits_accumulated_p_kwh: pd.credits_accumulated_p_kwh || 0,
          tariff_te_p: tv.te_p_unit || tv.te_ponta || 0,
          // Extra
          public_lighting_brl: pd.public_lighting_brl || 0,
          demand_measured_kw: pd.demand_measured_kw || 0,
          demand_injected_kw: pd.demand_injected_kw || 0,
          demand_contracted_kw: pd.demand_contracted_kw || 0,
          credits_balance_fp_kwh: pd.credits_balance_fp_kwh || 0,
          credits_balance_p_kwh: pd.credits_balance_p_kwh || 0,
          pdf_file_path: res.data.filepath || '',
          source: 'upload',
        });
        setShowEditForm(true);
        toast.success(`Fatura processada!`);
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

  const handleFieldChange = (field, value) => {
    setEditData(prev => ({ ...prev, [field]: value }));
  };

  const handleSaveInvoice = async () => {
    if (!editData?.consumer_unit_id) {
      toast.error('UC nao encontrada. Cadastre a UC antes de salvar.');
      return;
    }
    setSavingInvoice(true);
    try {
      await api.post('/invoices/save-from-upload', editData);
      toast.success('Fatura salva com sucesso!');
      setShowEditForm(false);
      setEditData(null);
      setParsedMeta(null);
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
    if (!v && v !== 0) return 'R$ 0,00';
    return `R$ ${Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatNumber = (v) => {
    if (!v && v !== 0) return '0';
    return Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
  };

  const filtered = invoices.filter(inv => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return inv.reference_month?.toLowerCase().includes(term) || inv.consumer_unit_id?.toLowerCase().includes(term);
  });

  // Editable Form View (SolarZ-style)
  if (showEditForm && editData) {
    const isGroupA = editData.tariff_group === 'A';
    return (
      <div className="space-y-4" data-testid="invoice-edit-form">
        {/* Top bar */}
        <div className="flex items-center justify-between">
          <button
            className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-800 transition-colors"
            onClick={() => { setShowEditForm(false); setEditData(null); setParsedMeta(null); }}
            data-testid="back-btn"
          >
            <ArrowLeft className="h-4 w-4" /> Voltar
          </button>
          <Button
            className="bg-[#1A1A1A] hover:bg-[#2D2D2D] text-white px-6"
            onClick={handleSaveInvoice}
            disabled={savingInvoice || !parsedMeta?.uc_found}
            data-testid="save-invoice-btn"
          >
            {savingInvoice ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Salvar
          </Button>
        </div>

        {/* UC Header */}
        <div className="flex items-center gap-3 px-1">
          <div className="w-6 h-6 rounded bg-[#1A1A1A] flex items-center justify-center">
            <FileText className="h-3.5 w-3.5 text-[#FFD600]" />
          </div>
          <span className="text-sm font-semibold text-[#1A1A1A]">
            {parsedMeta?.consumer_unit?.plant_name || 'Usina'} | {parsedMeta?.uc_number || ''} | {editData.reference_month}
          </span>
          {!parsedMeta?.uc_found && (
            <span className="ml-2 text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded">UC nao cadastrada</span>
          )}
        </div>

        {/* Main Fields */}
        <Card className="shadow-sm">
          <CardContent className="p-5 space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <Field label="Valor Faturado (R$)" value={editData.amount_total_brl}
                onChange={v => handleFieldChange('amount_total_brl', parseFloat(v) || 0)} />
              <Field label="Inicio do Ciclo" value={editData.billing_cycle_start}
                onChange={v => handleFieldChange('billing_cycle_start', v)} />
              <Field label="Fim do Ciclo" value={editData.billing_cycle_end}
                onChange={v => handleFieldChange('billing_cycle_end', v)} />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Economizado (R$)" value={editData.amount_saved_brl}
                onChange={v => handleFieldChange('amount_saved_brl', parseFloat(v) || 0)} />
              <Field label="Ilum. Publica (R$)" value={editData.public_lighting_brl}
                onChange={v => handleFieldChange('public_lighting_brl', parseFloat(v) || 0)} />
              <div />
            </div>

            {/* FORA PONTA */}
            <SectionLabel text="FORA PONTA" />
            <div className="grid grid-cols-3 gap-4">
              <Field label="Energia registrada (kWh)" value={editData.energy_registered_fp_kwh}
                onChange={v => handleFieldChange('energy_registered_fp_kwh', parseFloat(v) || 0)} />
              <Field label="Valor tarifa (R$)" value={editData.tariff_total_fp}
                onChange={v => handleFieldChange('tariff_total_fp', parseFloat(v) || 0)} step="0.000001" />
              <Field label="Energia faturada (kWh)" value={editData.energy_billed_fp_kwh}
                onChange={v => handleFieldChange('energy_billed_fp_kwh', parseFloat(v) || 0)} />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Energia injetada (kWh)" value={editData.energy_injected_fp_kwh}
                onChange={v => handleFieldChange('energy_injected_fp_kwh', parseFloat(v) || 0)} />
              <Field label="Energia compensada (kWh)" value={editData.energy_compensated_fp_kwh}
                onChange={v => handleFieldChange('energy_compensated_fp_kwh', parseFloat(v) || 0)} />
              <Field label="Credito acumulado (kWh)" value={editData.credits_accumulated_fp_kwh}
                onChange={v => handleFieldChange('credits_accumulated_fp_kwh', parseFloat(v) || 0)} />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Tarifa TE (R$)" value={editData.tariff_te_fp}
                onChange={v => handleFieldChange('tariff_te_fp', parseFloat(v) || 0)} step="0.000001" />
              <div /><div />
            </div>

            {/* PONTA (Group A only, but show for all and let user fill) */}
            {isGroupA && (
              <>
                <SectionLabel text="PONTA" />
                <div className="grid grid-cols-3 gap-4">
                  <Field label="Energia registrada (kWh)" value={editData.energy_registered_p_kwh}
                    onChange={v => handleFieldChange('energy_registered_p_kwh', parseFloat(v) || 0)} />
                  <Field label="Valor tarifa (R$)" value={editData.tariff_total_p}
                    onChange={v => handleFieldChange('tariff_total_p', parseFloat(v) || 0)} step="0.000001" />
                  <Field label="Energia faturada (kWh)" value={editData.energy_billed_p_kwh}
                    onChange={v => handleFieldChange('energy_billed_p_kwh', parseFloat(v) || 0)} />
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <Field label="Energia injetada (kWh)" value={editData.energy_injected_p_kwh}
                    onChange={v => handleFieldChange('energy_injected_p_kwh', parseFloat(v) || 0)} />
                  <Field label="Energia compensada (kWh)" value={editData.energy_compensated_p_kwh}
                    onChange={v => handleFieldChange('energy_compensated_p_kwh', parseFloat(v) || 0)} />
                  <Field label="Credito acumulado (kWh)" value={editData.credits_accumulated_p_kwh}
                    onChange={v => handleFieldChange('credits_accumulated_p_kwh', parseFloat(v) || 0)} />
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <Field label="Tarifa TE (R$)" value={editData.tariff_te_p}
                    onChange={v => handleFieldChange('tariff_te_p', parseFloat(v) || 0)} step="0.000001" />
                  <div /><div />
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  // List View
  return (
    <div className="space-y-6" data-testid="invoices-page">
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
                <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} disabled={uploading} data-testid="invoice-file-input" />
                <Button variant="default" className="bg-[#1A1A1A] hover:bg-[#2D2D2D] text-white gap-2" disabled={uploading} asChild>
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

      {/* Search */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <Input placeholder="Buscar por referencia, UC..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10" data-testid="invoice-search" />
        </div>
        <div className="flex items-center gap-1 text-sm text-neutral-500">
          <Filter className="h-4 w-4" />
          {filtered.length} fatura{filtered.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Invoices List */}
      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-neutral-400" /></div>
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
                      <p className="font-semibold text-sm text-[#1A1A1A] truncate">Ref: {inv.reference_month || 'N/A'}</p>
                      <p className="text-xs text-neutral-400">Grupo {inv.tariff_group || 'B'} | {inv.is_generator ? 'Geradora' : 'Beneficiaria'}</p>
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
                  <Button variant="ghost" size="icon" className="text-red-400 hover:text-red-600 hover:bg-red-50"
                    onClick={() => handleDeleteInvoice(inv.id)} data-testid={`delete-invoice-${inv.id}`}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

const SectionLabel = ({ text }) => (
  <div className="flex items-center gap-2 pt-2">
    <div className="w-1 h-4 bg-[#FFD600] rounded-full" />
    <span className="text-sm font-bold text-[#1A1A1A] uppercase tracking-wide">{text}</span>
  </div>
);

const Field = ({ label, value, onChange, step = 'any' }) => (
  <div className="space-y-1">
    <label className="text-xs text-neutral-500">{label}</label>
    <Input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      step={step}
      className="h-9 text-sm font-medium bg-white border-neutral-200 focus:border-[#FFD600] focus:ring-[#FFD600]/20"
      data-testid={`field-${label.replace(/[\s()\/]/g, '-').toLowerCase()}`}
    />
  </div>
);

export default InvoicesPage;
