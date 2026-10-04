import ScrollExpand from '../components/ScrollExpand';

export default function HeroSection() {
  return (
    <ScrollExpand
      src="/gemini_generated_video_a62a1b95.mp4"
      mediaType="video"
      alt="Synapse RiskOps cinematic demo"
      title="Synapse RiskOps"
      scrollHint="Scroll to explore"
      startWidth={42}
      startHeight={58}
      startRadius={24}
      endRadius={0}
      mediaZoom={1.35}
      scrollDistance={1.2}
      holdDistance={0.35}
      smoothing={0.1}
      overlayScrim={0.45}
      useWindowScroll={true}
      enabled={true}
      className="hero-section"
    >
      <div className="scroll-expand__overlay-content">
        <h2 className="overlay-subheading">Autonomous Risk Operations Platform</h2>
        <p className="overlay-tagline">
          Predict infrastructure failures. Diagnose root causes. Automate recovery.
        </p>
        <p className="overlay-credit">Built by a team of AI/ML engineers</p>
      </div>
    </ScrollExpand>
  );
}
