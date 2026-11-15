import { useEffect, useRef, useState, type ReactNode } from "react";
import { Emblem } from "./ui/Emblem";

const KEY = "jarvis-splash";

function seen() {
  try {
    return sessionStorage.getItem(KEY) === "1";
  } catch {
    return true;
  }
}

function finishSplash() {
  try {
    sessionStorage.setItem(KEY, "1");
  } catch {
    /* abaikan */
  }
  window.dispatchEvent(new Event("jarvis-splash-done"));
}

export function Splash({ children }: { children: ReactNode }) {
  const reduced = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [phase, setPhase] = useState<"draw" | "fly" | "reveal" | "off">(() => (seen() ? "off" : "draw"));
  const flyer = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (phase === "off") return;
    if (reduced) {
      const timer = window.setTimeout(() => {
        finishSplash();
        setPhase("off");
      }, 280);
      return () => window.clearTimeout(timer);
    }
    if (phase !== "draw") return;
    const fly = window.setTimeout(() => setPhase("fly"), 1400);
    return () => window.clearTimeout(fly);
  }, [phase, reduced]);

  useEffect(() => {
    if (phase !== "fly") return;
    const node = flyer.current;
    let frame = 0;
    let stopped = false;
    const started = performance.now();
    const look = () => {
      if (stopped) return;
      const target = document.querySelector("[data-splash-target]");
      if (node && target) {
        const to = target.getBoundingClientRect();
        const from = node.getBoundingClientRect();
        const dx = to.left + to.width / 2 - (from.left + from.width / 2);
        const dy = to.top + to.height / 2 - (from.top + from.height / 2);
        node.style.willChange = "transform";
        const motion = node.animate(
          [
            { transform: "translate(0px, 0px) scale(1)" },
            { transform: `translate(${dx * 0.5}px, ${dy * 0.5}px) scale(0.62)`, offset: 0.45 },
            { transform: `translate(${dx}px, ${dy}px) scale(0.34)` },
          ],
          { duration: 780, easing: "cubic-bezier(.22, 1.25, .36, 1)", fill: "forwards" },
        );
        node.querySelector(".mark")?.animate(
          [{ opacity: 1 }, { opacity: 0, offset: 0.62 }, { opacity: 0 }],
          { duration: 780, fill: "forwards" },
        );
        node.querySelector(".splash-dot")?.animate(
          [
            { transform: "scale(0)", opacity: 0 },
            { transform: "scale(0)", opacity: 0, offset: 0.4 },
            { transform: "scale(1)", opacity: 1 },
          ],
          { duration: 780, easing: "cubic-bezier(.22, 1.25, .36, 1)", fill: "forwards" },
        );
        const go = () => {
          node.style.willChange = "";
          document.documentElement.style.setProperty("--reveal-x", `${to.left + to.width / 2}px`);
          document.documentElement.style.setProperty("--reveal-y", `${to.top + to.height / 2}px`);
          setPhase("reveal");
        };
        motion.onfinish = go;
        return;
      }
      if (performance.now() - started > 1200) {
        finishSplash();
        setPhase("off");
        return;
      }
      frame = requestAnimationFrame(look);
    };
    frame = requestAnimationFrame(look);
    return () => {
      stopped = true;
      cancelAnimationFrame(frame);
    };
  }, [phase]);

  useEffect(() => {
    if (phase !== "reveal") return;
    const timer = window.setTimeout(() => {
      finishSplash();
      setPhase("off");
    }, 820);
    return () => window.clearTimeout(timer);
  }, [phase]);

  const covered = !reduced && (phase === "draw" || phase === "fly");
  const shell = covered ? "app-hold" : phase === "reveal" && !reduced ? "app-reveal" : "app-shown";

  return (
    <>
      <div className={shell}>{children}</div>
      {phase !== "off" && (
        <div className={`splash${reduced ? " splash-fade" : ""}`}>
          <div className="splash-glow" />
          <div className="splash-center">
            <div ref={flyer} className={`splash-mark${phase === "draw" ? " splash-in" : ""}`}>
              <Emblem size={72} state="idle" />
              <span className="splash-dot" />
            </div>
            <span className="splash-caption">JARVIS</span>
          </div>
        </div>
      )}
    </>
  );
}
