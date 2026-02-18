import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { Eye, EyeOff, Sun, Loader2 } from 'lucide-react';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_powerplant-analytics/artifacts/q3i8xrcz_Logo%20ON%20sem%20fundo.png";
const BG_IMAGE = "https://images.unsplash.com/photo-1508514177221-188b1cf16e9d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzd8MHwxfHNlYXJjaHwzfHxzb2xhciUyMHBhbmVsc3xlbnwwfHx8fDE3NzE0MTcwNTB8MA&ixlib=rb-4.1.0&q=85";

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
        toast.success('Bem-vindo de volta!');
      } else {
        if (!name.trim()) {
          toast.error('Por favor, informe seu nome');
          setLoading(false);
          return;
        }
        await register(name, email, password);
        toast.success('Conta criada com sucesso!');
      }
      navigate('/');
    } catch (error) {
      const message = error.response?.data?.detail || 'Erro ao fazer login. Tente novamente.';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Form */}
      <div className="w-full lg:w-[45%] flex flex-col justify-center px-8 lg:px-16 py-12 bg-white">
        <div className="max-w-md mx-auto w-full">
          {/* Logo */}
          <div className="mb-8">
            <img src={LOGO_URL} alt="ON Soluções Energéticas" className="h-14" />
          </div>

          {/* Welcome text */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-neutral-900 font-heading">
              {isLogin ? 'Bem-vindo de volta' : 'Criar conta'}
            </h1>
            <p className="text-neutral-500 mt-2">
              {isLogin 
                ? 'Acesse sua conta para gerenciar suas usinas solares'
                : 'Preencha os dados abaixo para criar sua conta'}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {!isLogin && (
              <div className="space-y-2">
                <Label htmlFor="name" className="text-neutral-700">Nome completo</Label>
                <Input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Seu nome"
                  className="h-12 border-neutral-200 focus:ring-2 focus:ring-[#FFD600] focus:border-transparent"
                  data-testid="register-name-input"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-neutral-700">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                className="h-12 border-neutral-200 focus:ring-2 focus:ring-[#FFD600] focus:border-transparent"
                required
                data-testid="login-email-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-neutral-700">Senha</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="h-12 border-neutral-200 focus:ring-2 focus:ring-[#FFD600] focus:border-transparent pr-10"
                  required
                  data-testid="login-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {isLogin && (
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm text-neutral-600">
                  <input type="checkbox" className="rounded border-neutral-300" />
                  Lembrar de mim
                </label>
                <button type="button" className="text-sm text-[#EAB308] hover:underline">
                  Esqueceu a senha?
                </button>
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-[#FFD600] hover:bg-[#EAB308] text-[#1A1A1A] font-semibold text-base transition-all active:scale-[0.98]"
              data-testid="login-submit-btn"
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                isLogin ? 'Entrar' : 'Criar conta'
              )}
            </Button>
          </form>

          {/* Toggle login/register */}
          <p className="mt-6 text-center text-neutral-600">
            {isLogin ? 'Não tem uma conta?' : 'Já tem uma conta?'}
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="ml-1 text-[#EAB308] font-medium hover:underline"
              data-testid="toggle-auth-mode"
            >
              {isLogin ? 'Criar conta' : 'Fazer login'}
            </button>
          </p>
        </div>
      </div>

      {/* Right side - Image */}
      <div className="hidden lg:block lg:w-[55%] relative">
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${BG_IMAGE})` }}
        />
        <div className="absolute inset-0 bg-gradient-to-br from-[#1A1A1A]/80 to-[#1A1A1A]/40" />
        
        {/* Overlay content */}
        <div className="relative z-10 h-full flex flex-col justify-end p-12">
          <div className="max-w-lg">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-[#FFD600] rounded-lg">
                <Sun className="h-6 w-6 text-[#1A1A1A]" />
              </div>
              <span className="text-[#FFD600] font-semibold">Energia Solar</span>
            </div>
            <h2 className="text-4xl font-bold text-white font-heading mb-4">
              Gerencie suas usinas solares com eficiência
            </h2>
            <p className="text-neutral-300 text-lg">
              Acompanhe a geração, monitore o desempenho e gere relatórios profissionais para seus clientes.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
