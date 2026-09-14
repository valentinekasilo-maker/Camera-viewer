import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import Logo from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { LuBookOpen, LuShieldCheck, LuCpu } from "react-icons/lu";
import { Link } from "react-router-dom";

type AboutDialogProps = {
  isOpen: boolean;
  onClose: () => void;
};

export default function AboutDialog({ isOpen, onClose }: AboutDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg overflow-hidden border border-border/80 bg-background/95 p-6 backdrop-blur-xl sm:rounded-2xl">
        <DialogHeader className="flex flex-col items-center text-center">
          <div className="mb-3 flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-inner">
            <Logo className="size-10" />
          </div>
          <DialogTitle className="text-2xl font-bold tracking-tight text-foreground">
            ANDRO-Vision
          </DialogTitle>
          <DialogDescription className="text-sm font-medium text-primary">
            Local AI Vision & Smart Camera System
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-4 text-xs text-muted-foreground">
          {/* Architecture Overview */}
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3.5 leading-relaxed">
            <div className="mb-1.5 flex items-center gap-1.5 font-semibold text-foreground">
              <LuCpu className="size-4 text-primary" />
              <span>Independent Local-First Platform</span>
            </div>
            <p>
              ANDRO-Vision is an edge-optimized NVR and real-time smart camera system designed for local AI object tracking, low-latency streaming, and high-performance continuous surveillance without mandatory cloud dependencies.
            </p>
          </div>

          {/* Open Source Attribution */}
          <div className="rounded-xl border border-border/60 bg-muted/30 p-3.5 leading-relaxed">
            <div className="mb-1.5 flex items-center gap-1.5 font-semibold text-foreground">
              <LuShieldCheck className="size-4 text-emerald-500" />
              <span>Open-Source Software Attribution & License</span>
            </div>
            <p className="mb-2">
              ANDRO-Vision incorporates modified open-source components, including Frigate NVR, go2rtc, and OpenCV.
            </p>
            <p className="text-[11px] text-muted-foreground/90">
              Copyright © Blake Blackshear and contributors. Released under the terms of the MIT License. All rights and trademarks belong to their respective holders.
            </p>
          </div>

          {/* Quick Links */}
          <div className="flex items-center justify-between pt-2">
            <Link to="/docs" onClick={onClose}>
              <Button variant="outline" size="sm" className="gap-1.5 text-xs">
                <LuBookOpen className="size-3.5 text-primary" />
                <span>Internal Documentation</span>
              </Button>
            </Link>
            <Button variant="ghost" size="sm" onClick={onClose} className="text-xs">
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
