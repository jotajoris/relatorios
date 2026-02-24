import { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { toast } from 'sonner';
import { 
  Users, 
  Plus, 
  Search, 
  MoreVertical, 
  Edit, 
  Trash2, 
  Building2,
  Mail,
  Phone,
  Loader2,
  Upload,
  Image,
  Crop
} from 'lucide-react';
import ImageCropper from '../components/ImageCropper';

const Clients = () => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(null);
  const logoInputRef = useRef(null);
  
  // Image cropper state
  const [cropperOpen, setCropperOpen] = useState(false);
  const [imageToCrop, setImageToCrop] = useState(null);
  const [cropClientId, setCropClientId] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    document: '',
    address: ''
  });

  // Format CPF: xxx.xxx.xxx-xx (11 digits)
  // Format CNPJ: xx.xxx.xxx/xxxx-xx (14 digits)
  const formatDocument = (value) => {
    if (!value) return '';
    // Remove all non-digits
    const digits = value.replace(/\D/g, '');
    
    if (digits.length <= 11) {
      // CPF format: xxx.xxx.xxx-xx
      return digits
        .replace(/(\d{3})(\d)/, '$1.$2')
        .replace(/(\d{3})(\d)/, '$1.$2')
        .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    } else {
      // CNPJ format: xx.xxx.xxx/xxxx-xx
      return digits
        .substring(0, 14)
        .replace(/(\d{2})(\d)/, '$1.$2')
        .replace(/(\d{3})(\d)/, '$1.$2')
        .replace(/(\d{3})(\d)/, '$1/$2')
        .replace(/(\d{4})(\d{1,2})$/, '$1-$2');
    }
  };

  // Handle document input change with formatting
  const handleDocumentChange = (e) => {
    const formatted = formatDocument(e.target.value);
    setFormData({ ...formData, document: formatted });
  };

  useEffect(() => {
    loadClients();
  }, []);

  const loadClients = async () => {
    try {
      const response = await api.get('/clients');
      setClients(response.data);
    } catch (error) {
      toast.error('Erro ao carregar clientes');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (client = null) => {
    if (client) {
      setEditingClient(client);
      setFormData({
        name: client.name || '',
        email: client.email || '',
        phone: client.phone || '',
        document: formatDocument(client.document) || '',
        address: client.address || ''
      });
    } else {
      setEditingClient(null);
      setFormData({ name: '', email: '', phone: '', document: '', address: '' });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingClient(null);
    setFormData({ name: '', email: '', phone: '', document: '', address: '' });
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast.error('Nome é obrigatório');
      return;
    }

    setSaving(true);
    try {
      if (editingClient) {
        await api.put(`/clients/${editingClient.id}`, formData);
        toast.success('Cliente atualizado com sucesso');
      } else {
        await api.post('/clients', formData);
        toast.success('Cliente cadastrado com sucesso');
      }
      handleCloseDialog();
      loadClients();
    } catch (error) {
      toast.error('Erro ao salvar cliente');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (client) => {
    if (!window.confirm(`Deseja realmente excluir o cliente "${client.name}"?`)) {
      return;
    }

    try {
      await api.delete(`/clients/${client.id}`);
      toast.success('Cliente removido com sucesso');
      loadClients();
    } catch (error) {
      toast.error('Erro ao remover cliente');
    }
  };

  const handleLogoUpload = async (clientId, file) => {
    if (!file) return;
    
    // Open cropper instead of uploading directly
    const reader = new FileReader();
    reader.onloadend = () => {
      setImageToCrop(reader.result);
      setCropClientId(clientId);
      setCropperOpen(true);
    };
    reader.readAsDataURL(file);
  };

  const handleCropComplete = async (croppedBlob) => {
    if (!croppedBlob || !cropClientId) return;
    
    setCropperOpen(false);
    setUploadingLogo(cropClientId);
    
    const formData = new FormData();
    formData.append('file', croppedBlob, 'logo.png');
    
    try {
      await api.post(`/upload/logo/client/${cropClientId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Logo atualizada com sucesso!');
      loadClients();
    } catch (error) {
      toast.error('Erro ao fazer upload da logo');
    } finally {
      setUploadingLogo(null);
      setImageToCrop(null);
      setCropClientId(null);
    }
  };

  const handleCropCancel = () => {
    setCropperOpen(false);
    setImageToCrop(null);
    setCropClientId(null);
  };

  const filteredClients = clients.filter(client =>
    client.name.toLowerCase().includes(search.toLowerCase()) ||
    client.email?.toLowerCase().includes(search.toLowerCase()) ||
    client.document?.includes(search)
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="clients-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-neutral-900 font-heading">Clientes</h1>
          <p className="text-neutral-500 mt-1">Gerencie os clientes das suas usinas solares</p>
        </div>
        <Button 
          onClick={() => handleOpenDialog()} 
          className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
          data-testid="add-client-btn"
        >
          <Plus className="h-4 w-4 mr-2" />
          Novo Cliente
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
        <Input
          placeholder="Buscar por nome, email ou documento..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
          data-testid="search-clients-input"
        />
      </div>

      {/* Clients Grid */}
      {filteredClients.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredClients.map((client) => (
            <Card key={client.id} className="border-neutral-100 shadow-sm card-hover">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {/* Logo with upload capability */}
                    <div className="relative group">
                      <input 
                        type="file" 
                        accept="image/*" 
                        className="hidden" 
                        id={`logo-${client.id}`}
                        onChange={(e) => handleLogoUpload(client.id, e.target.files[0])}
                      />
                      <label 
                        htmlFor={`logo-${client.id}`}
                        className="w-12 h-12 rounded-lg bg-[#FFD600]/10 flex items-center justify-center cursor-pointer overflow-hidden relative"
                      >
                        {uploadingLogo === client.id ? (
                          <Loader2 className="h-5 w-5 animate-spin text-[#EAB308]" />
                        ) : client.logo_url ? (
                          <img src={client.logo_url} alt={client.name} className="w-full h-full object-cover" />
                        ) : (
                          <Building2 className="h-6 w-6 text-[#EAB308]" />
                        )}
                        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                          <Upload className="h-4 w-4 text-white" />
                        </div>
                      </label>
                    </div>
                    <div>
                      <h3 className="font-semibold text-neutral-900">{client.name}</h3>
                      <p className="text-sm text-neutral-500">{formatDocument(client.document) || 'Sem documento'}</p>
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleOpenDialog(client)}>
                        <Edit className="h-4 w-4 mr-2" />
                        Editar
                      </DropdownMenuItem>
                      <DropdownMenuItem 
                        onClick={() => handleDelete(client)}
                        className="text-red-600"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Excluir
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div className="mt-4 space-y-2">
                  {client.email && (
                    <div className="flex items-center gap-2 text-sm text-neutral-600">
                      <Mail className="h-4 w-4 text-neutral-400" />
                      {client.email}
                    </div>
                  )}
                  {client.phone && (
                    <div className="flex items-center gap-2 text-sm text-neutral-600">
                      <Phone className="h-4 w-4 text-neutral-400" />
                      {client.phone}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="border-neutral-100 shadow-sm">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <div className="p-4 bg-neutral-100 rounded-full mb-4">
              <Users className="h-8 w-8 text-neutral-400" />
            </div>
            <h3 className="text-lg font-medium text-neutral-900 mb-1">Nenhum cliente encontrado</h3>
            <p className="text-sm text-neutral-500 mb-4">
              {search ? 'Tente ajustar sua busca' : 'Comece cadastrando seu primeiro cliente'}
            </p>
            {!search && (
              <Button 
                onClick={() => handleOpenDialog()} 
                className="bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A]"
              >
                <Plus className="h-4 w-4 mr-2" />
                Cadastrar Cliente
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
              {editingClient ? 'Editar Cliente' : 'Novo Cliente'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nome *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Nome do cliente ou empresa"
                data-testid="client-name-input"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="document">CPF/CNPJ</Label>
              <Input
                id="document"
                value={formData.document}
                onChange={handleDocumentChange}
                placeholder="000.000.000-00 ou 00.000.000/0000-00"
                maxLength={18}
              />
              <p className="text-xs text-neutral-500">
                {formData.document?.replace(/\D/g, '').length === 11 ? 'CPF' : 
                 formData.document?.replace(/\D/g, '').length === 14 ? 'CNPJ' : 
                 'Digite 11 dígitos para CPF ou 14 para CNPJ'}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="email@exemplo.com"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Telefone</Label>
              <Input
                id="phone"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="(00) 00000-0000"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="address">Endereço</Label>
              <Input
                id="address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Endereço completo"
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
              data-testid="save-client-btn"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Salvar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Image Cropper Dialog */}
      {cropperOpen && imageToCrop && (
        <ImageCropper
          imageSrc={imageToCrop}
          onCropComplete={handleCropComplete}
          onCancel={handleCropCancel}
          aspectRatio={1}
          circularCrop={false}
          title="Recortar Logo do Cliente"
        />
      )}
    </div>
  );
};

export default Clients;
