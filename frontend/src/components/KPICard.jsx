import { TrendingUp, TrendingDown } from 'lucide-react';

const accentColors = {
  yellow: 'bg-[#FFD600]',
  green: 'bg-emerald-500',
  blue: 'bg-blue-500',
  gray: 'bg-neutral-400',
  red: 'bg-red-500'
};

const iconBgColors = {
  yellow: 'bg-amber-50 text-[#FFD600]',
  green: 'bg-emerald-50 text-emerald-600',
  blue: 'bg-blue-50 text-blue-600',
  gray: 'bg-neutral-100 text-neutral-600',
  red: 'bg-red-50 text-red-600'
};

const KPICard = ({ 
  title, 
  value, 
  subtitle,
  icon: Icon, 
  trend, 
  trendValue,
  accent = 'yellow',
  className = ''
}) => {
  return (
    <div className={`relative bg-white rounded-xl p-5 border border-neutral-100 shadow-sm overflow-hidden card-hover ${className}`}>
      {/* Accent bar */}
      <div className={`absolute top-0 left-0 w-1 h-full rounded-l-xl ${accentColors[accent]}`} />
      
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-neutral-500 font-medium uppercase tracking-wide mb-1">
            {title}
          </p>
          <p className="text-2xl lg:text-3xl font-bold text-neutral-900 tracking-tight tabular-nums">
            {value}
          </p>
          {subtitle && (
            <p className="text-sm text-neutral-500 mt-1">{subtitle}</p>
          )}
          {trend !== undefined && (
            <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${
              trend >= 0 ? 'text-emerald-600' : 'text-red-600'
            }`}>
              {trend >= 0 ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              <span>{Math.abs(trend)}% {trendValue || 'vs mês anterior'}</span>
            </div>
          )}
        </div>
        
        {Icon && (
          <div className={`p-3 rounded-lg ${iconBgColors[accent]}`}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </div>
  );
};

export default KPICard;
