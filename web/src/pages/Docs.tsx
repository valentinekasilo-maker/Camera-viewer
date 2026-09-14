import { useState, useMemo, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import Logo from "@/components/Logo";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  LuCamera,
  LuCpu,
  LuEye,
  LuFileText,
  LuLayers,
  LuMic,
  LuPlay,
  LuSearch,
  LuServer,
  LuShieldAlert,
  LuSlidersHorizontal,
  LuVideo,
  LuWrench,
  LuZap,
} from "react-icons/lu";
import { cn } from "@/lib/utils";

interface DocSection {
  id: string;
  title: string;
  category: string;
  icon: React.ComponentType<{ className?: string }>;
  summary: string;
  content: React.ReactNode;
}

export default function Docs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialSection = searchParams.get("section") || "getting-started";
  const [activeSection, setActiveSection] = useState(initialSection);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    const s = searchParams.get("section");
    if (s && s !== activeSection) {
      setActiveSection(s);
    }
  }, [searchParams, activeSection]);

  const selectSection = (id: string) => {
    setActiveSection(id);
    setSearchParams({ section: id });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const docSections: DocSection[] = useMemo(
    () => [
      {
        id: "getting-started",
        title: "Getting Started",
        category: "Overview",
        icon: LuZap,
        summary: "Introduction to ANDRO-Vision local AI smart camera system.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">
              Getting Started with ANDRO-Vision
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              <strong>ANDRO-Vision</strong> is an ultra-fast, local-first AI Vision and Smart Camera surveillance platform. It provides high-performance multi-camera live viewing, sub-second camera streaming via WebRTC/go2rtc, local edge object detection (91 COCO object classes), zone triggers, motion masks, and intelligent recording.
            </p>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-border/80 bg-card p-4 shadow-sm">
                <div className="flex items-center gap-2 font-semibold text-foreground">
                  <LuVideo className="size-5 text-primary" />
                  <span>Dual-Stream Architecture</span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Substreams (`_sub`) power ultra-smooth 8-camera grid views at minimal CPU and network load, while mainstreams dynamically engage in 1080p high quality on camera selection.
                </p>
              </div>

              <div className="rounded-xl border border-border/80 bg-card p-4 shadow-sm">
                <div className="flex items-center gap-2 font-semibold text-foreground">
                  <LuCpu className="size-5 text-emerald-500" />
                  <span>Local AI Object Detection</span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  High-speed local neural network inference tracks persons, vehicles, animals, and packages in real-time with zero external cloud subscriptions required.
                </p>
              </div>
            </div>

            <h3 className="text-lg font-semibold text-foreground">Quick Access & Navigation</h3>
            <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
              <li><strong>Live Dashboard:</strong> Access all 8 cameras in real-time grid view.</li>
              <li><strong>Review & Events:</strong> Browse detected motion events, tracked object clips, and snapshots.</li>
              <li><strong>Configuration:</strong> Access Basic and Advanced camera settings under the Settings menu.</li>
            </ul>
          </div>
        ),
      },
      {
        id: "cameras",
        title: "Cameras",
        category: "Hardware",
        icon: LuCamera,
        summary: "Camera stream configurations, RTSP inputs, and stream roles.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Camera Configuration</h2>
            <p className="text-muted-foreground leading-relaxed">
              ANDRO-Vision supports standard IP cameras providing H.264 or H.265 RTSP streams. Each camera can define independent streams for detection, live playback, and recording.
            </p>

            <div className="rounded-xl border border-border/80 bg-card p-4 shadow-sm">
              <h4 className="font-semibold text-foreground">Recommended Stream Setup</h4>
              <p className="mt-1 text-xs text-muted-foreground">
                To maximize system performance and responsiveness, configure two streams per camera:
              </p>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-border/60 text-muted-foreground">
                    <tr>
                      <th className="py-2 pr-4 font-semibold">Stream</th>
                      <th className="py-2 pr-4 font-semibold">Resolution</th>
                      <th className="py-2 pr-4 font-semibold">FPS</th>
                      <th className="py-2 font-semibold">Usage</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40 text-foreground">
                    <tr>
                      <td className="py-2 pr-4 font-mono font-medium text-primary">Mainstream (`kamera_X`)</td>
                      <td className="py-2 pr-4">1920x1080 (1080p)</td>
                      <td className="py-2 pr-4">20–30 FPS</td>
                      <td className="py-2">Expanded/Fullscreen View & Recording</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 font-mono font-medium text-emerald-500">Substream (`kamera_X_sub`)</td>
                      <td className="py-2 pr-4">640x360 / 640x480</td>
                      <td className="py-2 pr-4">10–15 FPS</td>
                      <td className="py-2">8-Camera Grid & AI Object Detection</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ),
      },
      {
        id: "live-view",
        title: "Live View",
        category: "Streaming",
        icon: LuPlay,
        summary: "Dual-stream playback, Quality Selector, WebRTC, and low-latency viewing.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Live View & Dual-Stream Architecture</h2>
            <p className="text-muted-foreground leading-relaxed">
              ANDRO-Vision delivers sub-second latency video through integrated <strong>go2rtc WebRTC</strong> streaming.
            </p>

            <div className="space-y-3">
              <h3 className="text-base font-semibold text-foreground">Quality Selector Modes</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><strong className="text-foreground">AUTO:</strong> Automatically engages the crystal-clear 1080p mainstream on single-camera view and falls back to substream if bandwidth or hardware limits require.</li>
                <li><strong className="text-foreground">MAX / HIGH:</strong> Locks playback to highest resolution mainstream.</li>
                <li><strong className="text-foreground">MEDIUM / LOW:</strong> Switches to lightweight substream for ultra-low bandwidth consumption.</li>
              </ul>
            </div>

            <div className="rounded-xl border border-border/80 bg-muted/30 p-4 text-xs text-muted-foreground">
              <strong className="text-foreground">Automatic Graceful Fallback:</strong> If mainstream network buffering occurs or connection drops, ANDRO-Vision seamlessly falls back to the camera substream without interrupting playback.
            </div>
          </div>
        ),
      },
      {
        id: "object-detection",
        title: "Object Detection",
        category: "AI Engine",
        icon: LuEye,
        summary: "Local neural network detection, tracked object classes, scores, and bounding boxes.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Local AI Object Detection</h2>
            <p className="text-muted-foreground leading-relaxed">
              ANDRO-Vision features high-efficiency edge neural detectors running on CPU or accelerated hardware. Detection processes incoming substream frames and draws live bounding box overlays with confidence ratings.
            </p>

            <h3 className="text-base font-semibold text-foreground">Supported 91 COCO Object Classes</h3>
            <div className="flex flex-wrap gap-1.5 text-xs">
              {[
                "person", "car", "motorcycle", "bicycle", "bus", "truck", "dog", "cat",
                "bird", "horse", "sheep", "cow", "backpack", "handbag", "suitcase",
                "umbrella", "bottle", "chair", "laptop", "cell phone", "package"
              ].map((name) => (
                <Badge key={name} variant="secondary" className="px-2.5 py-0.5 font-mono text-[11px]">
                  {name}
                </Badge>
              ))}
              <span className="self-center text-xs text-muted-foreground">+ 70 more standard classes</span>
            </div>

            <div className="space-y-3">
              <h3 className="text-base font-semibold text-foreground">Detection Filters & Thresholds</h3>
              <ul className="list-disc space-y-1.5 pl-5 text-sm text-muted-foreground">
                <li><strong>min_score (e.g. 0.5):</strong> Minimum confidence to consider a potential candidate.</li>
                <li><strong>threshold (e.g. 0.7):</strong> Confidence required to classify and track an object as a verified detection.</li>
                <li><strong>min_area / max_area:</strong> Filter out noise (too small) or false positives (too large).</li>
              </ul>
            </div>
          </div>
        ),
      },
      {
        id: "audio-detection",
        title: "Audio Detection",
        category: "Sensors",
        icon: LuMic,
        summary: "Acoustic event classification, volume thresholds, and audio triggers.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Audio Detection & Classification</h2>
            <p className="text-muted-foreground leading-relaxed">
              For cameras equipped with microphones, ANDRO-Vision supports real-time audio detection and acoustic pattern recognition (e.g. barking, breaking glass, alarms, speech).
            </p>
            <div className="rounded-xl border border-border/80 bg-card p-4 shadow-sm text-xs text-muted-foreground space-y-2">
              <p>Configure audio sensitivity, minimum decibel triggers, and enabled audio classes under <strong>Settings &gt; Camera Configuration &gt; Audio</strong>.</p>
            </div>
          </div>
        ),
      },
      {
        id: "recording",
        title: "Recording",
        category: "Storage",
        icon: LuVideo,
        summary: "Continuous recording, motion-triggered recording, retention schedules, and storage.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Recording & Storage Retention</h2>
            <p className="text-muted-foreground leading-relaxed">
              Recording uses direct stream remuxing with zero re-encoding overhead. Segment clips are indexed into SQLite for fast seeking and playback.
            </p>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-border/80 bg-card p-3.5">
                <h4 className="font-semibold text-foreground">Continuous</h4>
                <p className="mt-1 text-xs text-muted-foreground">
                  Records 24/7 uninterrupted high-quality video footage.
                </p>
              </div>
              <div className="rounded-xl border border-border/80 bg-card p-3.5">
                <h4 className="font-semibold text-foreground">Motion Only</h4>
                <p className="mt-1 text-xs text-muted-foreground">
                  Saves segments only when scene activity or motion is detected.
                </p>
              </div>
              <div className="rounded-xl border border-border/80 bg-card p-3.5">
                <h4 className="font-semibold text-foreground">Events Only</h4>
                <p className="mt-1 text-xs text-muted-foreground">
                  Stores video only when specific tracked objects or zones are active.
                </p>
              </div>
            </div>
          </div>
        ),
      },
      {
        id: "events",
        title: "Events & Review",
        category: "Surveillance",
        icon: LuFileText,
        summary: "Event timeline, tracked item replay, snapshots, and review workflow.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Events & Review Pipeline</h2>
            <p className="text-muted-foreground leading-relaxed">
              Events combine object tracking, zone triggers, and timestamps into reviewable segments. Review items can be searched, exported, filtered by camera or object type, and replayed in the Review page.
            </p>
          </div>
        ),
      },
      {
        id: "zones",
        title: "Zones",
        category: "Geometry",
        icon: LuLayers,
        summary: "Interactive polygon zone editor, object entry/exit rules, and inertia.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Zone Configuration</h2>
            <p className="text-muted-foreground leading-relaxed">
              Zones allow you to define custom polygon areas within a camera's field of view (e.g. "Driveway", "Front Porch", "Gate").
            </p>
            <p className="text-xs text-muted-foreground">
              Define object filters per zone, requiring specific classes (e.g. alert on `person` in "Porch", but ignore in "Street"). Use the interactive Zone Editor under <strong>Settings &gt; Masks & Zones</strong>.
            </p>
          </div>
        ),
      },
      {
        id: "masks",
        title: "Masks",
        category: "Geometry",
        icon: LuSlidersHorizontal,
        summary: "Motion masks, object masks, and false-positive suppression.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Motion & Object Masks</h2>
            <p className="text-muted-foreground leading-relaxed">
              Masks eliminate repetitive false detections caused by trees swaying in wind, ceiling fans, timestamps, or reflections.
            </p>
            <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
              <li><strong>Motion Masks:</strong> Prevent motion detection in masked regions.</li>
              <li><strong>Object Filter Masks:</strong> Prevent specific objects from triggering detections when their bounding box center is inside the mask.</li>
            </ul>
          </div>
        ),
      },
      {
        id: "notifications",
        title: "Notifications",
        category: "Integrations",
        icon: LuShieldAlert,
        summary: "Real-time alerts, MQTT event broadcasting, and Webhook dispatching.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Notifications & MQTT Event Feeds</h2>
            <p className="text-muted-foreground leading-relaxed">
              ANDRO-Vision broadcasts real-time detection events over WebSockets and MQTT. You can consume snapshot payloads and metadata for custom automation flows.
            </p>
          </div>
        ),
      },
      {
        id: "ai-vision",
        title: "AI Vision Layer",
        category: "AI Engine",
        icon: LuCpu,
        summary: "Decoupled Vision AI layer, event-triggered scene understanding, and performance isolation.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Decoupled Local Vision AI Layer</h2>
            <p className="text-muted-foreground leading-relaxed">
              ANDRO-Vision enforces strict architectural separation between the real-time camera engine and high-level Vision AI inference:
            </p>

            <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 font-mono text-xs text-foreground leading-loose">
              IP Cameras &rarr; Camera Engine &rarr; Substream Object Detection &rarr; Tracked Events &rarr; Selected High-Quality Frame &rarr; Vision AI
            </div>

            <p className="text-sm text-muted-foreground">
              Vision AI never intercepts or delays raw live video frames. It analyzes only selected high-confidence event keyframes, maintaining rock-solid 60 FPS live camera playback.
            </p>
          </div>
        ),
      },
      {
        id: "performance",
        title: "Performance & Tuning",
        category: "System",
        icon: LuServer,
        summary: "Hardware acceleration (VAAPI, QuickSync, CUDA), substream optimization, and resource tuning.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Performance Optimization Guidelines</h2>
            <ul className="list-disc space-y-2.5 pl-5 text-sm text-muted-foreground">
              <li><strong>Substream Usage:</strong> Always use substreams (`_sub` at 640x360) for detection and grid view.</li>
              <li><strong>Hardware Acceleration:</strong> Enable GPU hardware decoding (Intel QuickSync, NVIDIA NVDEC, AMD VAAPI) in FFmpeg settings.</li>
              <li><strong>Direct Playback:</strong> Stream H.264 video directly through go2rtc WebRTC without server transcoding.</li>
            </ul>
          </div>
        ),
      },
      {
        id: "troubleshooting",
        title: "Troubleshooting",
        category: "Support",
        icon: LuWrench,
        summary: "Common camera streaming issues, codec compatibility, and network diagnostics.",
        content: (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">Troubleshooting & Diagnostics</h2>
            <div className="space-y-4">
              <div className="rounded-xl border border-border/80 bg-card p-4">
                <h4 className="font-semibold text-foreground">Camera stream not loading</h4>
                <p className="mt-1 text-xs text-muted-foreground">
                  Verify camera RTSP credentials and test reachability via VLC or go2rtc stream inspector. Ensure port 554 and local IP addresses are reachable.
                </p>
              </div>

              <div className="rounded-xl border border-border/80 bg-card p-4">
                <h4 className="font-semibold text-foreground">High CPU utilization</h4>
                <p className="mt-1 text-xs text-muted-foreground">
                  Ensure object detection is assigned to camera substream (`_sub`) rather than full 4K/1080p mainstream.
                </p>
              </div>
            </div>
          </div>
        ),
      },
    ],
    [],
  );

  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return docSections;
    const q = searchQuery.toLowerCase();
    return docSections.filter(
      (sec) =>
        sec.title.toLowerCase().includes(q) ||
        sec.summary.toLowerCase().includes(q) ||
        sec.category.toLowerCase().includes(q),
    );
  }, [docSections, searchQuery]);

  const currentSection = docSections.find((s) => s.id === activeSection) || docSections[0];

  return (
    <div className="flex size-full overflow-hidden bg-background">
      {/* Sidebar Navigation */}
      <aside className="scrollbar-container hidden w-64 shrink-0 flex-col border-r border-border/80 bg-background_alt p-4 md:flex overflow-y-auto">
        <div className="mb-6 flex items-center gap-2.5 px-2">
          <Logo className="size-7 text-primary" />
          <div>
            <h1 className="text-sm font-bold tracking-tight text-foreground">
              ANDRO-Vision
            </h1>
            <p className="text-[10px] font-medium text-muted-foreground">
              Documentation
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <LuSearch className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search docs..."
            className="h-9 pl-8 text-xs"
          />
        </div>

        {/* Navigation items */}
        <nav className="space-y-1">
          {filteredSections.map((sec) => {
            const Icon = sec.icon;
            const isActive = sec.id === currentSection.id;
            return (
              <button
                key={sec.id}
                onClick={() => selectSection(sec.id)}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs font-medium transition-all",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
              >
                <Icon className={cn("size-4 shrink-0", isActive ? "text-primary-foreground" : "text-primary")} />
                <span className="truncate">{sec.title}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="scrollbar-container flex-1 overflow-y-auto p-6 md:p-10">
        <div className="mx-auto max-w-3xl space-y-8">
          {/* Breadcrumb / Category */}
          <div className="flex items-center justify-between border-b border-border/60 pb-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Link to="/" className="hover:text-foreground">
                ANDRO-Vision
              </Link>
              <span>/</span>
              <span>Docs</span>
              <span>/</span>
              <span className="font-medium text-primary">{currentSection.category}</span>
            </div>
            <Link to="/">
              <Button variant="ghost" size="sm" className="text-xs">
                Back to Live View
              </Button>
            </Link>
          </div>

          {/* Render Active Section Content */}
          <article className="prose prose-neutral dark:prose-invert max-w-none">
            {currentSection.content}
          </article>
        </div>
      </main>
    </div>
  );
}
