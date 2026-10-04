import { useEffect, useRef } from 'react';
import { useInView } from 'framer-motion';

export default function ProblemSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });

  const stats = [
    { value: 3.2, label: 'hours', desc: 'Average MTTR' },
    { value: 60, label: '%', desc: 'False positive rate' },
    { value: 847, label: 'alerts/week', desc: 'Per engineer' },
    { value: null, label: 'Manual', desc: 'RCA takes hours‑days' },
  ];

  return (
    <section ref={ref} className="problem-section py-24 bg-neutral-900">
      <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-2 gap-12">
        <div className="stats-grid grid grid-cols-2 gap-6">
          {stats.map((s, i) => (
            <div key={i} className="stat-card bg-neutral-800 p-6 rounded-lg border border-neutral-700 hover:border-cyan-500 transition-colors">
              <div className="stat-value text-4xl font-bold text-cyan-400 mb-2">
                {isInView && s.value !== null ? (
                  <CountUp end={s.value} />
                ) : (
                  s.value !== null ? s.value : s.label
                )}{' '}{s.label}
              </div>
              <p className="stat-desc text-sm text-neutral-400">{s.desc}</p>
            </div>
          ))}
        </div>
        <div className="problem-copy">
          <h2 className="text-3xl font-bold text-white mb-4">The Problem</h2>
          <p className="text-neutral-300 leading-relaxed">
            Alert fatigue is killing your team. Manual root cause analysis delays mitigation. Your incidents are preventable — but only if you catch them early.
          </p>
        </div>
      </div>
    </section>
  );
}

function CountUp({ end }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    let current = 0;
    const duration = 1000; // 1 second
    const start = performance.now();
    const step = now => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      current = Math.floor(progress * end);
      ref.current.textContent = current;
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [end]);

  return <span ref={ref}>0</span>;
}
