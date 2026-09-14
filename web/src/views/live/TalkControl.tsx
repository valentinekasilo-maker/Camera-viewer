import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";
import { FaMicrophone, FaMicrophoneSlash } from "react-icons/fa";
import { LuLoader, LuShieldCheck } from "react-icons/lu";

export type TalkStatus =
  | "idle"
  | "connecting"
  | "active"
  | "disconnected"
  | "unsupported";

interface TalkControlProps {
  cameraName: string;
  supports2WayTalk: boolean;
  cameraEnabled: boolean;
  isActive: boolean;
  onToggleTalk: (active: boolean) => void;
  className?: string;
  variant?: "toolbar" | "compact" | "overlay";
}

export function TalkControl({
  cameraName,
  supports2WayTalk,
  cameraEnabled,
  isActive,
  onToggleTalk,
  className,
}: TalkControlProps) {
  const [talkState, setTalkState] = useState<TalkStatus>(
    supports2WayTalk ? (isActive ? "active" : "idle") : "unsupported",
  );

  useEffect(() => {
    if (!supports2WayTalk) {
      setTalkState("unsupported");
      return;
    }
    if (isActive) {
      setTalkState("connecting");
      const timer = setTimeout(() => {
        setTalkState("active");
      }, 700);
      return () => clearTimeout(timer);
    } else {
      setTalkState("idle");
    }
  }, [isActive, supports2WayTalk]);

  const handleClick = () => {
    if (!supports2WayTalk || !cameraEnabled) return;
    onToggleTalk(!isActive);
  };

  if (!supports2WayTalk) {
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
              <FaMicrophoneSlash className="h-3.5 w-3.5 text-muted-foreground" />
              <span>Talk</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-xs">
            Camera does not support two-way audio (no backchannel detected)
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            size="sm"
            onClick={handleClick}
            disabled={!cameraEnabled}
            className={cn(
              "relative flex items-center gap-1.5 font-medium transition-all duration-300 text-xs shadow-sm",
              talkState === "active"
                ? "bg-emerald-600 hover:bg-emerald-500 text-white ring-2 ring-emerald-400/40 shadow-emerald-500/20"
                : talkState === "connecting"
                ? "bg-amber-600 hover:bg-amber-500 text-white animate-pulse"
                : "bg-secondary/80 hover:bg-secondary text-foreground border border-border/60",
              className,
            )}
          >
            {talkState === "connecting" ? (
              <>
                <LuLoader className="h-3.5 w-3.5 animate-spin" />
                <span>Connecting...</span>
              </>
            ) : talkState === "active" ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-300 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
                </span>
                <FaMicrophone className="h-3.5 w-3.5" />
                <span>Talk Active</span>
                <span className="hidden sm:inline-flex items-center text-[10px] bg-emerald-700/60 px-1 py-0.2 rounded text-emerald-100 ml-0.5">
                  <LuShieldCheck className="mr-0.5 h-2.5 w-2.5" />
                  AEC
                </span>
              </>
            ) : (
              <>
                <FaMicrophone className="h-3.5 w-3.5 text-primary" />
                <span>Talk</span>
              </>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs max-w-xs">
          {talkState === "active" ? (
            <div className="space-y-1">
              <p className="font-semibold text-emerald-400">Two-Way Telecom Active</p>
              <p className="text-muted-foreground text-[11px]">
                Transmitting microphone to camera speaker. Browser Acoustic Echo Cancellation (AEC) & AGC enabled. Click to disconnect.
              </p>
            </div>
          ) : talkState === "connecting" ? (
            <p>Negotiating low-latency P2P audio channel...</p>
          ) : (
            <div className="space-y-1">
              <p className="font-semibold">Start Two-Way Audio</p>
              <p className="text-muted-foreground text-[11px]">
                Speak to {cameraName.replace(/_/g, " ")} through PC microphone (HotKey: T).
              </p>
            </div>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
