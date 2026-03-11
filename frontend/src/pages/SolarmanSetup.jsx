import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { CheckCircle, Copy, ExternalLink, Loader2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import api from '../services/api';

const SolarmanSetup = () => {
  const [status, setStatus] = useState({ connected: false, loading: true });
  const [copied, setCopied] = useState(false);
  
  // Backend URL for the bookmarklet
  const backendUrl = process.env.REACT_APP_BACKEND_URL || window.location.origin;
  
  // Bookmarklet code - sends cookies to our API
  const bookmarkletCode = `javascript:(function(){
    var cookies = document.cookie;
    if (!cookies) {
      alert('Nenhum cookie encontrado. Faça login primeiro!');
      return;
    }
    
    var apiUrl = '${backendUrl}/api/integrations/solarman/capture-session';
    
    fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookies: cookies })
    })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        alert('Sucesso! ' + data.message + ' Volte para o sistema ON Usinas.');
      } else {
        alert('Erro: ' + (data.error || 'Falha ao salvar sessão'));
      }
    })
    .catch(e => {
      alert('Erro de conexão: ' + e.message);
    });
  })();`.replace(/\s+/g, ' ').trim();
  
  useEffect(() => {
    checkStatus();
    // Poll status every 5 seconds
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, []);
  
  const checkStatus = async () => {
    try {
      const res = await api.get('/integrations/solarman/status');
      setStatus({ ...res.data, loading: false });
    } catch {
      setStatus({ connected: false, loading: false });
    }
  };
  
  const copyBookmarklet = () => {
    navigator.clipboard.writeText(bookmarkletCode);
    setCopied(true);
    toast.success('Código copiado! Agora crie o favorito.');
    setTimeout(() => setCopied(false), 3000);
  };
  
  const handleDisconnect = async () => {
    try {
      await api.post('/integrations/solarman/disconnect');
      setStatus({ connected: false, loading: false });
      toast.success('Desconectado do Solarman');
    } catch {
      toast.error('Erro ao desconectar');
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50 p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-neutral-800">Configurar Solarman</h1>
          <p className="text-neutral-500 mt-1">Conecte sua conta Solarman PRO ao sistema</p>
        </div>
        
        {/* Status Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              {status.loading ? (
                <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
              ) : status.connected ? (
                <CheckCircle className="h-5 w-5 text-emerald-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-amber-500" />
              )}
              Status da Conexão
            </CardTitle>
          </CardHeader>
          <CardContent>
            {status.connected ? (
              <div className="space-y-3">
                <p className="text-emerald-600 font-medium">Conectado ao Solarman PRO</p>
                {status.captured_at && (
                  <p className="text-sm text-neutral-500">
                    Conectado em: {new Date(status.captured_at).toLocaleString('pt-BR')}
                  </p>
                )}
                <Button variant="outline" size="sm" onClick={handleDisconnect}>
                  Desconectar
                </Button>
              </div>
            ) : (
              <p className="text-amber-600">Não conectado. Siga as instruções abaixo.</p>
            )}
          </CardContent>
        </Card>
        
        {/* Instructions Card */}
        {!status.connected && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Instruções de Configuração</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Step 1 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold">
                  1
                </div>
                <div>
                  <p className="font-medium text-neutral-800">Crie um favorito com o código abaixo</p>
                  <p className="text-sm text-neutral-500 mt-1">
                    Clique com botão direito na barra de favoritos → "Adicionar página" → 
                    Cole o código no campo "URL" e dê um nome como "Capturar Solarman"
                  </p>
                  <div className="mt-3 p-3 bg-neutral-100 rounded-lg">
                    <code className="text-xs break-all text-neutral-600 block max-h-20 overflow-y-auto">
                      {bookmarkletCode}
                    </code>
                  </div>
                  <Button 
                    onClick={copyBookmarklet} 
                    size="sm" 
                    className="mt-2"
                    variant={copied ? "default" : "outline"}
                  >
                    <Copy className="h-4 w-4 mr-2" />
                    {copied ? 'Copiado!' : 'Copiar código'}
                  </Button>
                </div>
              </div>
              
              {/* Step 2 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold">
                  2
                </div>
                <div>
                  <p className="font-medium text-neutral-800">Faça login no Solarman PRO</p>
                  <p className="text-sm text-neutral-500 mt-1">
                    Abra o portal Solarman em uma nova aba e faça login normalmente
                  </p>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="mt-2"
                    onClick={() => window.open('https://pro.solarmanpv.com/login', '_blank')}
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Abrir Solarman PRO
                  </Button>
                </div>
              </div>
              
              {/* Step 3 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold">
                  3
                </div>
                <div>
                  <p className="font-medium text-neutral-800">Clique no favorito que você criou</p>
                  <p className="text-sm text-neutral-500 mt-1">
                    Após fazer login no Solarman, clique no favorito "Capturar Solarman". 
                    Um alerta vai confirmar que a sessão foi salva.
                  </p>
                </div>
              </div>
              
              {/* Step 4 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold">
                  4
                </div>
                <div>
                  <p className="font-medium text-neutral-800">Volte aqui e verifique</p>
                  <p className="text-sm text-neutral-500 mt-1">
                    Esta página atualiza automaticamente. Quando a sessão for capturada, 
                    você verá o status "Conectado" acima.
                  </p>
                </div>
              </div>
              
              {/* Alternative */}
              <div className="pt-4 border-t border-neutral-200">
                <p className="text-sm text-neutral-500">
                  <strong>Alternativa:</strong> Se não conseguir criar o favorito, você pode colar 
                  o código diretamente no Console do navegador (F12) enquanto estiver logado no Solarman.
                </p>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Back button */}
        <div className="text-center">
          <Button variant="ghost" onClick={() => window.location.href = '/portais'}>
            ← Voltar para Portais
          </Button>
        </div>
      </div>
    </div>
  );
};

export default SolarmanSetup;
