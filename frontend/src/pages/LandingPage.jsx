/**
 * frontend/src/pages/LandingPage.jsx
 * 
 * Complete SaaS Landing Page for Synapse RiskOps.
 * Incorporates:
 * - Local Background Video Hero (/gemini_generated_video_a62a1b95.mp4)
 * - Bento-grid Capabilities with Chakra Petch typography
 * - 3-Step Interactive Architecture Journey (Scanning line, radar ripples, mini charts)
 * - Auto-scrolling horizontal integrations marquee
 * - Tabbed interactive FAQ with smooth framer-motion accordions
 * - Immersive newsletter footer with glassmorphic cluster status
 */

import React from 'react';
import HeroVideoSection from '../components/landing/HeroVideoSection';
import FeaturesBentoSection from '../components/landing/FeaturesBentoSection';
import HowItWorksStepsSection from '../components/landing/HowItWorksStepsSection';
import StackIntegrationsSection from '../components/landing/StackIntegrationsSection';
import FAQInteractiveSection from '../components/landing/FAQInteractiveSection';
import LandingFooterV2 from '../components/landing/LandingFooterV2';

export default function LandingPage({ onLaunchApp, onSignIn, onGetStarted }) {
  const handleSignIn = () => {
    if (onSignIn) onSignIn();
    else if (onLaunchApp) onLaunchApp();
  };

  const handleGetStarted = () => {
    if (onGetStarted) onGetStarted();
    else if (onLaunchApp) onLaunchApp();
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 transition-colors duration-300">
      {/* 1. HERO WITH LOCAL VIDEO BACKGROUND & FLOATING NAVBAR */}
      <HeroVideoSection
        onSignIn={handleSignIn}
        onGetStarted={handleGetStarted}
        onLaunchApp={onLaunchApp}
      />

      {/* 2. BENTO-GRID CORE CAPABILITIES */}
      <FeaturesBentoSection />

      {/* 3. 3-STEP AUTONOMOUS PIPELINE JOURNEY */}
      <HowItWorksStepsSection onGetStarted={handleGetStarted} />

      {/* 4. AUTO-SCROLLING PRODUCTION STACK INTEGRATIONS */}
      <StackIntegrationsSection />

      {/* 5. TABBED INTERACTIVE ACCORDION FAQ */}
      <FAQInteractiveSection onGetStarted={handleGetStarted} />

      {/* 6. IMMERSIVE NEWSLETTER & GLASSMORPHIC FOOTER */}
      <LandingFooterV2 onLaunchApp={handleGetStarted} />
    </div>
  );
}
