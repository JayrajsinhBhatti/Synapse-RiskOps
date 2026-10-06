/**
 * frontend/src/components/common/Card.jsx
 * 
 * Reusable SaaS Card Container with clean slot components.
 */

import React from 'react';

export function Card({ children, className = '', hover = false, onClick, ...props }) {
  return (
    <div
      onClick={onClick}
      className={`saas-card p-5 ${
        hover ? 'cursor-pointer hover:border-slate-600 hover:shadow-lg hover:shadow-black/20' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '' }) {
  return <div className={`flex items-center justify-between pb-3 mb-3 border-b dark:border-white/5 border-slate-200 ${className}`}>{children}</div>;
}

export function CardTitle({ children, className = '' }) {
  return <h3 className={`text-sm font-semibold dark:text-white text-slate-900 tracking-wide ${className}`}>{children}</h3>;
}

export function CardDescription({ children, className = '' }) {
  return <p className={`text-xs dark:text-slate-400 text-slate-600 mt-0.5 leading-relaxed ${className}`}>{children}</p>;
}

export function CardContent({ children, className = '' }) {
  return <div className={className}>{children}</div>;
}

export default Card;
