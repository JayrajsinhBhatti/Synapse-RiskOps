/**
 * frontend/src/components/landing/LandingNavbar.jsx
 * 
 * Production SaaS Landing Navbar with sticky blur and navigation anchors.
 */

import React, { useState, useEffect } from 'react';
import { Activity, ShieldCheck, ArrowRight, Zap, Menu, X } from 'lucide-react';
import Button from '../common/Button';

export function LandingNavbar({ onSignIn, onGetStarted }) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { label: 'Product', href: '#how-it-works' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Capabilities', href: '#capabilities' },
    { label: 'Architecture', href: '#architecture' },
    { label: 'About', href: '#about' },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 ${
        scrolled
          ? 'bg-slate-950/80 backdrop-blur-xl border-b border-white/10 shadow-lg shadow-black/20 py-3.5'
          : 'bg-transparent py-5'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
        {/* Brand Logo */}
        <a href="#" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 via-indigo-600 to-cyan-400 flex items-center justify-center text-white shadow-glow-sm group-hover:shadow-glow-md transition-all">
            <Zap className="w-5 h-5" />
          </div>
          <div className="flex flex-col">
            <span className="font-extrabold text-base tracking-tight text-white flex items-center gap-1.5">
              Synapse <span className="text-cyan-400 font-semibold">RiskOps</span>
            </span>
            <span className="text-[9px] uppercase tracking-wider text-slate-400 font-mono -mt-0.5">
              AIOps Incident Platform
            </span>
          </div>
        </a>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-7 text-xs font-medium text-slate-300">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="hover:text-white transition-colors"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Right CTA Actions */}
        <div className="hidden md:flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={onSignIn}
            className="text-xs font-semibold text-slate-300 hover:text-white"
          >
            Sign In
          </Button>
          <Button
            variant="cyan"
            size="sm"
            onClick={onGetStarted}
            iconRight={ArrowRight}
            className="text-xs font-semibold"
          >
            Get Started
          </Button>
        </div>

        {/* Mobile Hamburger */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 text-slate-400 hover:text-white"
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-slate-950/95 border-b border-slate-800 px-6 py-4 space-y-3">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="block text-sm text-slate-300 hover:text-white py-1"
            >
              {link.label}
            </a>
          ))}
          <div className="pt-3 border-t border-slate-800 flex flex-col gap-2">
            <Button variant="secondary" size="sm" onClick={onSignIn} className="w-full">
              Sign In
            </Button>
            <Button variant="cyan" size="sm" onClick={onGetStarted} className="w-full">
              Get Started
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}

export default LandingNavbar;
