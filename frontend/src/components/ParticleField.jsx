import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "../lib/hooks";

const COLORS = ["46, 196, 182", "157, 78, 221", "255, 209, 102", "230, 57, 70"];
const LINK_DISTANCE = 130;

// Canvas "network" of drifting nodes; static when the user prefers reduced motion.
export default function ParticleField({ className = "", density = 0.00008 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return undefined;
    const reduce = prefersReducedMotion();
    let width = 0;
    let height = 0;
    let particles = [];
    let frame = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.max(28, Math.min(120, Math.round(width * height * density)));
      particles = Array.from({ length: count }, (_, i) => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.28,
        vy: (Math.random() - 0.5) * 0.28,
        r: Math.random() * 1.7 + 0.6,
        c: COLORS[i % 11 === 0 ? 3 : i % 5 === 0 ? 2 : i % 2],
      }));
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < -10) p.x = width + 10;
        if (p.x > width + 10) p.x = -10;
        if (p.y < -10) p.y = height + 10;
        if (p.y > height + 10) p.y = -10;
      }
      for (let i = 0; i < particles.length; i += 1) {
        for (let j = i + 1; j < particles.length; j += 1) {
          const a = particles[i];
          const b = particles[j];
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < LINK_DISTANCE) {
            ctx.strokeStyle = `rgba(${a.c}, ${(1 - d / LINK_DISTANCE) * 0.22})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
      for (const p of particles) {
        ctx.fillStyle = `rgba(${p.c}, 0.85)`;
        ctx.shadowColor = `rgba(${p.c}, 0.9)`;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.shadowBlur = 0;
      if (!reduce) frame = window.requestAnimationFrame(draw);
    };

    resize();
    draw();
    const observer = new ResizeObserver(() => {
      resize();
      if (reduce) draw();
    });
    observer.observe(canvas);
    const onVisibility = () => {
      window.cancelAnimationFrame(frame);
      if (!document.hidden && !reduce) frame = window.requestAnimationFrame(draw);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [density]);

  return <canvas ref={canvasRef} className={`particle-field ${className}`} aria-hidden="true" />;
}
