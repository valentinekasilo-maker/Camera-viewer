import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import axios from "axios";
import { useEffect, useState } from "react";
import { FaLightbulb, FaRegLightbulb } from "react-icons/fa";
import { LuLoader } from "react-icons/lu";
import { toast } from "sonner";

interface LightControlProps {
  cameraName: string;
  cameraEnabled: boolean;
  className?: string;
}

export function LightControl({
  cameraName,
  cameraEnabled,
  className,
}: LightControlProps) {
  const [lightState, setLightState] = useState<"on" | "off" | "unavailable">("off");
  const [isSupported, setIsSupported] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchStatus = async () => {
      try {
        const res = await axios.get(`cameras/${cameraName}/light`);
        if (isMounted && res.data.success) {
          setIsSupported(res.data.supported);
          setLightState(res.data.state);
        }
      } catch {
        // quiet fallback
      }
    };
    fetchStatus();
    return () => {
      isMounted = false;
    };
  }, [cameraName]);

  const handleToggle = async () => {
    if (!isSupported || !cameraEnabled || isLoading) return;
    setIsLoading(true);
    try {
      const res = await axios.post(`cameras/${cameraName}/light/toggle`);
      if (res.data.success) {
        setLightState(res.data.state);
        toast.success(
          `Camera light turned ${res.data.state.toUpperCase()}`,
        );
      } else if (res.data.state === "unavailable") {
        setIsSupported(false);
        setLightState("unavailable");
        toast.error("Light control unavailable on this camera");
      }
    } catch {
      toast.error("Failed to toggle camera light");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isSupported || lightState === "unavailable") {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              disabled
              className={cn(
                "flex items-center gap-1.5 opacity-50 cursor-not-allowed bg-secondary/30 text-muted-foreground border-border/40 text-xs",
                className,
              )}
            >
              <FaRegLightbulb className="h-3.5 w-3.5 text-muted-foreground" />
              <span>Light</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-xs">
            Light control unavailable (hardware spotlight not exposed)
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  const isLightOn = lightState === "on";

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            size="sm"
            onClick={handleToggle}
            disabled={!cameraEnabled || isLoading}
            className={cn(
              "relative flex items-center gap-1.5 font-medium transition-all duration-300 text-xs shadow-sm",
              isLightOn
                ? "bg-amber-500 hover:bg-amber-400 text-black font-semibold ring-2 ring-amber-300/60 shadow-amber-500/30"
                : "bg-secondary/80 hover:bg-secondary text-foreground border border-border/60",
              className,
            )}
          >
            {isLoading ? (
              <LuLoader className="h-3.5 w-3.5 animate-spin" />
            ) : isLightOn ? (
              <>
                <FaLightbulb className="h-3.5 w-3.5 text-black animate-bounce" />
                <span>Light On</span>
              </>
            ) : (
              <>
                <FaRegLightbulb className="h-3.5 w-3.5 text-amber-400" />
                <span>Light Off</span>
              </>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          <div className="space-y-1">
            <p className="font-semibold">
              {isLightOn ? "Camera Spotlight Active" : "Manual Light Control"}
            </p>
            <p className="text-muted-foreground text-[11px]">
              {isLightOn
                ? "Click to turn OFF camera spotlight / white LED."
                : "Click to turn ON camera spotlight / white LED."}
            </p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
