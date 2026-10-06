/**
 * frontend/src/components/common/Modal.jsx
 * 
 * Accessible dialog modal with ESC key dismiss and smooth backdrop.
 */

import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export function Modal({ isOpen, onClose, title, description, children, maxWidth = 'max-w-xl' }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-150">
      <div
        className={`relative w-full ${maxWidth} rounded-2xl dark:bg-slate-900 bg-white border dark:border-slate-700/80 border-slate-200 shadow-2xl p-6 dark:text-slate-100 text-slate-900 animate-in zoom-in-95 duration-150`}
        role="dialog"
        aria-modal="true"
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          aria-label="Close dialog"
        >
          <X className="w-5 h-5" />
        </button>

        {(title || description) && (
          <div className="mb-5 pr-8">
            {title && <h3 className="text-lg font-bold dark:text-white text-slate-900 tracking-tight">{title}</h3>}
            {description && <p className="text-xs dark:text-slate-400 text-slate-600 mt-1 leading-relaxed">{description}</p>}
          </div>
        )}

        <div>{children}</div>
      </div>
    </div>
  );
}

export default Modal;
