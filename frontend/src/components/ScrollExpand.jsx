import { useCallback, useEffect, useRef } from 'react';
import './ScrollExpand.css';

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

const smoothstep = (edge0, edge1, x) => {
  const t = clamp((x - edge0) / (edge1 - edge0 || 1e-6), 0, 1);
  return t * t * (3 - 2 * t);
};

const ScrollExpand = ({
  src = '',
  mediaType = 'image',
  poster = '',
  alt = '',
  title = '',
  scrollHint = '',
  startWidth = 44,
  startHeight = 56,
  startRadius = 24,
  endRadius = 0,
  mediaZoom = 1.3,
  scrollDistance = 1.4,
  holdDistance = 0.6,
  smoothing = 0.1,
  overlayScrim = 0.65,
  useWindowScroll = false,
  enabled = true,
  children,
  className = '',
  style,
  ...rest
}) => {
  const rootRef = useRef(null);
  const trackRef = useRef(null);
  const stageRef = useRef(null);
  const frameRef = useRef(null);
  const mediaRef = useRef(null);
  const titleRef = useRef(null);
  const overlayRef = useRef(null);
  const scrimRef = useRef(null);
  const hintRef = useRef(null);

  const propsRef = useRef({});
  propsRef.current = {
    startWidth,
    startHeight,
    startRadius,
    endRadius,
    mediaZoom,
    scrollDistance,
    holdDistance,
    smoothing,
    overlayScrim,
    useWindowScroll,
    enabled
  };

  /**
   * Sequence orchestration:
   * 1. p in [0.0 -> 0.50]:
   *    Video grows from initial rounded box to 100% full screen.
   *    Title & overlay remain hidden (opacity 0) so the video has the stage completely unobstructed.
   *    Scroll hint gently fades away early (p 0.0 -> 0.15).
   *
   * 2. p in [0.50 -> 0.75]:
   *    Video is 100% full-screen.
   *    "SYNAPSE RISKOPS" title fades in and displays boldly.
   *
   * 3. p in [0.75 -> 1.0]:
   *    Overlay content fades in underneath / following the heading:
   *    "Autonomous Risk Operations Platform", tagline, and "Open Live Console" CTA button.
   */
  const applyProgress = useCallback(p => {
    const frame = frameRef.current;
    const media = mediaRef.current;
    if (!frame || !media) return;
    const c = propsRef.current;

    // Expansion phase: 0.0 -> 0.50
    const expandProgress = smoothstep(0, 0.50, p);

    const w = c.startWidth + (100 - c.startWidth) * expandProgress;
    const h = c.startHeight + (100 - c.startHeight) * expandProgress;
    const ix = Math.max(0, (100 - w) / 2);
    const iy = Math.max(0, (100 - h) / 2);
    const r = c.startRadius + (c.endRadius - c.startRadius) * expandProgress;
    frame.style.clipPath = `inset(${iy}% ${ix}% ${iy}% ${ix}% round ${r}px)`;

    media.style.transform = `scale(${c.mediaZoom + (1 - c.mediaZoom) * expandProgress})`;

    // Scrim darkens as we scroll into the text phase
    if (scrimRef.current) {
      const scrimProgress = smoothstep(0.40, 0.85, p);
      scrimRef.current.style.opacity = `${c.overlayScrim * scrimProgress}`;
    }

    // Scroll hint fades out right at the beginning
    if (hintRef.current) {
      const gone = smoothstep(0, 0.12, p);
      hintRef.current.style.opacity = `${1 - gone}`;
      hintRef.current.style.transform = `translate3d(0, ${10 * gone}px, 0)`;
    }

    // Heading "SYNAPSE RISKOPS": Fades in only AFTER full screen (from p: 0.50 to 0.75)
    if (titleRef.current) {
      const titleIn = smoothstep(0.48, 0.72, p);
      titleRef.current.style.opacity = `${titleIn}`;
      titleRef.current.style.transform = `translate3d(0, ${24 * (1 - titleIn)}px, 0)`;
      titleRef.current.style.pointerEvents = titleIn > 0.5 ? 'auto' : 'none';
    }

    // Subheadings and CTA content: Fades in when scrolling further (from p: 0.70 to 0.98)
    if (overlayRef.current) {
      const overlayIn = smoothstep(0.70, 0.98, p);
      overlayRef.current.style.opacity = `${overlayIn}`;
      overlayRef.current.style.transform = `translate3d(0, ${20 * (1 - overlayIn)}px, 0)`;
      overlayRef.current.style.pointerEvents = overlayIn > 0.5 ? 'auto' : 'none';
    }
  }, []);

  useEffect(() => {
    const root = rootRef.current;
    const track = trackRef.current;
    const stage = stageRef.current;
    if (!root || !track || !stage) return;

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let raf = 0;
    let current = 0;
    let target = 0;
    let stageH = 0;
    let running = false;

    const measure = () => {
      const c = propsRef.current;
      stageH = c.useWindowScroll ? window.innerHeight : root.clientHeight;
      if (stageH <= 0) return;
      stage.style.height = `${stageH}px`;
      track.style.height = `${stageH * (1 + Math.max(0, c.scrollDistance) + Math.max(0, c.holdDistance))}px`;

      const w = root.clientWidth || stageH;
      stage.style.setProperty('--se-title-size', `${clamp(w * 0.065, 24, 76)}px`);
    };

    const readProgress = () => {
      const c = propsRef.current;
      if (!c.enabled) return 1;
      const span = stageH * Math.max(0.01, c.scrollDistance);
      if (c.useWindowScroll) {
        const top = track.getBoundingClientRect().top;
        return clamp(-top / span, 0, 1);
      }
      return clamp(root.scrollTop / span, 0, 1);
    };

    const tick = () => {
      const c = propsRef.current;
      const k = c.smoothing <= 0 ? 1 : 1 - Math.exp(-1 / (60 * c.smoothing));
      current += (target - current) * k;
      if (Math.abs(target - current) < 0.0004) {
        current = target;
        running = false;
      }
      applyProgress(current);
      raf = running ? requestAnimationFrame(tick) : 0;
    };

    const kick = () => {
      if (running) return;
      running = true;
      if (!raf) raf = requestAnimationFrame(tick);
    };

    const onScroll = () => {
      target = readProgress();
      if (propsRef.current.smoothing <= 0 || reduceMotion) {
        current = target;
        applyProgress(current);
        return;
      }
      kick();
    };

    const onResize = () => {
      measure();
      target = readProgress();
      current = target;
      applyProgress(current);
    };

    measure();
    target = readProgress();
    current = target;
    applyProgress(current);

    const scroller = useWindowScroll ? window : root;
    scroller.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize);
    const ro = new ResizeObserver(onResize);
    ro.observe(root);

    return () => {
      if (raf) cancelAnimationFrame(raf);
      scroller.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onResize);
      ro.disconnect();
    };
  }, [applyProgress, useWindowScroll]);

  const media =
    mediaType === 'video' ? (
      <video
        ref={mediaRef}
        className="scroll-expand__media"
        src={src}
        poster={poster}
        autoPlay
        muted
        loop
        playsInline
      />
    ) : (
      <img ref={mediaRef} className="scroll-expand__media" src={src} alt={alt} draggable={false} />
    );

  return (
    <div
      ref={rootRef}
      className={`scroll-expand ${useWindowScroll ? '' : 'scroll-expand--scroller'} ${className}`.trim()}
      style={style}
      {...rest}
    >
      <div ref={trackRef} className="scroll-expand__track">
        <div ref={stageRef} className="scroll-expand__stage">
          <div ref={frameRef} className="scroll-expand__frame">
            {media}
            <div ref={scrimRef} className="scroll-expand__scrim" />
            
            {/* Overlay Container: Displays the Title first, followed by Subtitle, Tagline & CTA */}
            <div className="scroll-expand__content-wrapper">
              {title ? (
                <div ref={titleRef} className="scroll-expand__title">
                  {title}
                </div>
              ) : null}

              {children ? (
                <div ref={overlayRef} className="scroll-expand__overlay">
                  {children}
                </div>
              ) : null}
            </div>
          </div>

          {scrollHint ? (
            <div ref={hintRef} className="scroll-expand__hint">
              <span className="scroll-hint-pill">{scrollHint} ↓</span>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default ScrollExpand;
