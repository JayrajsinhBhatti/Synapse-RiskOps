/**
 * frontend/src/components/common/Button.jsx
 * 
 * Production-ready SaaS Button primitive with variants, loading state, and micro-interactions.
 */

import React from 'react';
import { Loader2 } from 'lucide-react';

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  icon: Icon,
  iconRight: IconRight,
  className = '',
  onClick,
  type = 'button',
  ...props
}) {
  const baseStyles =
    'relative inline-flex items-center justify-center font-medium transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]';

  const sizeStyles = {
    sm: 'text-xs px-3 py-1.5 rounded-lg gap-1.5',
    md: 'text-sm px-4 py-2 rounded-xl gap-2',
    lg: 'text-base px-6 py-2.5 rounded-xl gap-2.5 font-semibold',
  };

  const variantStyles = {
    primary:
      'bg-gradient-to-r from-indigo-500 via-indigo-600 to-indigo-700 hover:from-indigo-400 hover:to-indigo-600 text-white shadow-md shadow-indigo-500/20 hover:shadow-indigo-500/35 border border-indigo-400/30',
    cyan:
      'bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white shadow-md shadow-cyan-500/20 border border-cyan-400/30',
    secondary:
      'dark:bg-slate-900/80 bg-slate-100 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 border dark:border-slate-700/70 border-slate-300 shadow-sm',
    outline:
      'bg-transparent dark:hover:bg-white/5 hover:bg-slate-100 dark:text-slate-300 text-slate-700 dark:hover:text-white hover:text-slate-950 border dark:border-slate-700/80 border-slate-300 dark:hover:border-slate-500 hover:border-slate-400',
    ghost:
      'bg-transparent dark:hover:bg-white/5 hover:bg-slate-100 dark:text-slate-400 text-slate-600 dark:hover:text-slate-100 hover:text-slate-900',
    danger:
      'bg-rose-600/90 hover:bg-rose-500 text-white border border-rose-500/40 shadow-sm shadow-rose-600/20',
  };

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin text-current" />
      ) : Icon ? (
        <Icon className="w-4 h-4 shrink-0" />
      ) : null}

      <span>{children}</span>

      {!isLoading && IconRight && (
        <IconRight className="w-4 h-4 shrink-0 transition-transform group-hover:translate-x-0.5" />
      )}
    </button>
  );
}

export default Button;
