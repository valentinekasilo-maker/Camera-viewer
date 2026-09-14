import { cn } from "@/lib/utils";

type LogoProps = {
  className?: string;
};
export default function Logo({ className }: LogoProps) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={cn("size-8 transition-transform hover:scale-105", className)}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Outer Glow Ring / Cyber Aperture */}
      <circle
        cx="50"
        cy="50"
        r="44"
        className="stroke-primary"
        strokeWidth="3.5"
        strokeDasharray="4 2"
        opacity="0.85"
      />
      {/* Precision Lens Hexagon / Iris Petals */}
      <polygon
        points="50,14 81.18,32 81.18,68 50,86 18.82,68 18.82,32"
        className="stroke-primary"
        strokeWidth="3"
        strokeLinejoin="round"
        fill="currentColor"
        fillOpacity="0.08"
      />
      {/* Inner Optical Pupil */}
      <circle
        cx="50"
        cy="50"
        r="18"
        className="fill-primary stroke-primary"
        strokeWidth="2"
      />
      {/* Core AI Vision Spark */}
      <circle
        cx="45"
        cy="45"
        r="5"
        fill="#ffffff"
        opacity="0.9"
      />
      {/* Optical Reticle Crosshairs */}
      <line x1="50" y1="6" x2="50" y2="16" className="stroke-primary" strokeWidth="2.5" strokeLinecap="round" />
      <line x1="50" y1="84" x2="50" y2="94" className="stroke-primary" strokeWidth="2.5" strokeLinecap="round" />
      <line x1="6" y1="50" x2="16" y2="50" className="stroke-primary" strokeWidth="2.5" strokeLinecap="round" />
      <line x1="84" y1="50" x2="94" y2="50" className="stroke-primary" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
