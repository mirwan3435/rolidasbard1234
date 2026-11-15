export const GlassFilter = () => (
  <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
    <filter id="glass-distortion">
      <feTurbulence
        type="fractalNoise"
        baseFrequency="0.01 0.01"
        numOctaves="1"
        seed="5"
        result="turbulence"
      />
      <feGaussianBlur in="turbulence" stdDeviation="3" result="softMap" />
      <feDisplacementMap
        in="SourceGraphic"
        in2="softMap"
        scale="70"
        xChannelSelector="R"
        yChannelSelector="G"
      />
    </filter>
  </svg>
);
