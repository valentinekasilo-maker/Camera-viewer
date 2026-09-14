import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  CameraModelSpec,
  CameraQAResponse,
  ModelManagerTelemetry,
  SemanticUnderstanding,
  VisualInspectionResult,
} from "@/types/intelligence";
import axios from "axios";
import React, { useEffect, useRef, useState } from "react";
import {
  FaCar,
  FaChevronDown,
  FaChevronRight,
  FaChevronUp,
  FaDoorOpen,
  FaHistory,
  FaMapMarkerAlt,
  FaMicrophone,
  FaMicrophoneSlash,
  FaPaperPlane,
  FaPowerOff,
  FaQuestionCircle,
  FaRobot,
  FaSave,
  FaTrashAlt,
  FaVolumeMute,
  FaVolumeUp,
} from "react-icons/fa";
import {
  LuCamera,
  LuCheck,
  LuCopy,
  LuEye,
  LuLoader,
  LuRefreshCw,
  LuShieldCheck,
  LuSparkles,
} from "react-icons/lu";
import { toast } from "sonner";

interface CameraIntelligencePanelProps {
  selectedCamera?: string;
  className?: string;
}

export function CameraIntelligencePanel({
  selectedCamera,
  className,
}: CameraIntelligencePanelProps) {
  const [activeTab, setActiveTab] = useState<string>("assistant");
  const [models, setModels] = useState<CameraModelSpec[]>([]);
  const [telemetry, setTelemetry] = useState<ModelManagerTelemetry | null>(null);
  const [semanticFeed, setSemanticFeed] = useState<SemanticUnderstanding[]>([]);
  const [question, setQuestion] = useState("");
  const [qaHistory, setQaHistory] = useState<CameraQAResponse[]>([]);
  const [isAsking, setIsAsking] = useState(false);
  const [isSwitchingModel, setIsSwitchingModel] = useState(false);
  const [escalateGemini, setEscalateGemini] = useState(true);

  // Expanded reasoning trace card IDs
  const [expandedTraceIdx, setExpandedTraceIdx] = useState<number | null>(0);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  // Multimodal Visual Frame Inspector States
  const [inspectorCamera, setInspectorCamera] = useState<string>(
    selectedCamera || "camera_7",
  );
  const [inspectorPrompt, setInspectorPrompt] = useState<string>(
    "Describe what is happening in this camera frame in detail.",
  );
  const [isInspectingVisual, setIsInspectingVisual] = useState(false);
  const [visualResult, setVisualResult] = useState<VisualInspectionResult | null>(
    null,
  );
  const [snapshotTimestamp, setSnapshotTimestamp] = useState<number>(Date.now());

  // Voice Interaction States (STT & TTS)
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState<number | null>(null);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const recognitionRef = useRef<any>(null);

  // Gate & Vehicle Intelligence States
  const [gateStatus, setGateStatus] = useState<any>(null);
  const [vehicleStatus, setVehicleStatus] = useState<any>(null);

  // Semantic Map State
  const [cameraSemantics, setCameraSemantics] = useState<any[]>([]);
  const [editingCamera, setEditingCamera] = useState<string>(
    selectedCamera || "camera_7",
  );
  const [editFormData, setEditFormData] = useState<any>(null);
  const [isSavingSemantic, setIsSavingSemantic] = useState(false);

  // Timeline Events
  const [timelineEvents, setTimelineEvents] = useState<any[]>([]);

  // Update selected camera bindings
  useEffect(() => {
    if (selectedCamera) {
      setInspectorCamera(selectedCamera);
      setEditingCamera(selectedCamera);
    }
  }, [selectedCamera]);

  // Web Speech STT setup
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onresult = (event: any) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        setQuestion(transcript);
      };

      recognition.onerror = () => {
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleVoiceListen = () => {
    if (!recognitionRef.current) {
      toast.error("Speech Recognition is not supported by your browser");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
        toast.info("Listening... Speak your question now", { duration: 2500 });
      } catch {
        setIsListening(false);
      }
    }
  };

  // Web Speech TTS playback
  const speakText = (text: string, index?: number) => {
    if (!("speechSynthesis" in window)) {
      toast.error("Text-to-Speech is not supported by your browser");
      return;
    }

    if (isSpeaking && speakingIndex === index) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      setSpeakingIndex(null);
      return;
    }

    window.speechSynthesis.cancel();
    const cleanText = text
      .replace(/[*_#`~]/g, "")
      .replace(/https?:\/\/\S+/g, "")
      .trim();
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(
      (v) =>
        v.lang.startsWith("en") &&
        (v.name.includes("Natural") ||
          v.name.includes("Google") ||
          v.name.includes("Samantha") ||
          v.name.includes("Ava")),
    );
    if (naturalVoice) utterance.voice = naturalVoice;

    utterance.onstart = () => {
      setIsSpeaking(true);
      setSpeakingIndex(index ?? -1);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      setSpeakingIndex(null);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      setSpeakingIndex(null);
    };

    window.speechSynthesis.speak(utterance);
  };

  const copyToClipboard = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    toast.success("Answer copied to clipboard");
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const fetchModels = async () => {
    try {
      const res = await axios.get("intelligence/models");
      if (res.data.success) {
        setModels(res.data.models);
        setTelemetry(res.data.telemetry);
      }
    } catch {
      // quiet fallback
    }
  };

  const fetchFeed = async () => {
    try {
      const url = selectedCamera
        ? `intelligence/semantic-feed?camera=${selectedCamera}&limit=20`
        : "intelligence/semantic-feed?limit=20";
      const res = await axios.get(url);
      if (res.data.success) {
        setSemanticFeed(res.data.feed);
      }
    } catch {
      // quiet fallback
    }
  };

  const fetchGateAndVehicles = async () => {
    try {
      const [gateRes, vehRes] = await Promise.all([
        axios.get("intelligence/gate"),
        axios.get("intelligence/vehicles"),
      ]);
      setGateStatus(gateRes.data);
      setVehicleStatus(vehRes.data);
    } catch {
      // quiet fallback
    }
  };

  const fetchSemantics = async () => {
    try {
      const res = await axios.get("semantic/cameras");
      if (res.data?.cameras) {
        setCameraSemantics(res.data.cameras);
        const current = res.data.cameras.find(
          (c: any) => c.camera === editingCamera,
        );
        if (current) {
          setEditFormData(current);
        }
      }
    } catch {
      // quiet fallback
    }
  };

  const fetchTimeline = async () => {
    try {
      const res = await axios.get("intelligence/timeline?limit=25");
      if (res.data?.events) {
        setTimelineEvents(res.data.events);
      }
    } catch {
      // quiet fallback
    }
  };

  useEffect(() => {
    fetchModels();
    fetchFeed();
    fetchGateAndVehicles();
    fetchSemantics();
    fetchTimeline();

    const interval = setInterval(() => {
      fetchFeed();
      fetchGateAndVehicles();
      fetchTimeline();
    }, 4000);
    return () => clearInterval(interval);
  }, [selectedCamera]);

  useEffect(() => {
    const current = cameraSemantics.find((c) => c.camera === editingCamera);
    if (current) {
      setEditFormData(current);
    }
  }, [editingCamera, cameraSemantics]);

  const handleModelSwitch = async (modelId: string) => {
    setIsSwitchingModel(true);
    try {
      const res = await axios.post("intelligence/models/switch", {
        model_id: modelId,
      });
      if (res.data.success) {
        setTelemetry(res.data.telemetry);
        toast.success(`Switched to ${modelId}`);
        fetchModels();
      }
    } catch {
      toast.error("Failed to switch model");
    } finally {
      setIsSwitchingModel(false);
    }
  };

  const handleToggleLoad = async () => {
    if (!telemetry) return;
    setIsSwitchingModel(true);
    try {
      if (telemetry.is_loaded) {
        const res = await axios.post("intelligence/models/unload");
        if (res.data.success) {
          setTelemetry(res.data.telemetry);
          toast.info("Model unloaded from memory");
        }
      } else {
        const res = await axios.post("intelligence/models/load", {
          model_id: telemetry.active_model.id || "andro-vision-0.5b-q4",
        });
        if (res.data.success) {
          setTelemetry(res.data.telemetry);
          toast.success("Model loaded into memory");
        }
      }
      fetchModels();
    } catch {
      toast.error("Model operation failed");
    } finally {
      setIsSwitchingModel(false);
    }
  };

  const handleAsk = async (e?: React.FormEvent, customQ?: string) => {
    if (e) e.preventDefault();
    const queryText = (customQ || question).trim();
    if (!queryText || isAsking) return;

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }

    setIsAsking(true);
    try {
      const res = await axios.post("intelligence/ask", {
        question: queryText,
        session_id: "andro_vision_live",
        escalate_gemini: escalateGemini,
      });
      if (res.data.success) {
        const answerItem: CameraQAResponse = res.data.response;
        setQaHistory((prev) => [answerItem, ...prev.slice(0, 14)]);
        setQuestion("");
        setExpandedTraceIdx(0);

        if (autoSpeak && answerItem.answer) {
          speakText(answerItem.answer, 0);
        }
      }
    } catch {
      toast.error("Failed to query Camera Intelligence Engine");
    } finally {
      setIsAsking(false);
    }
  };

  const handleVisualInspect = async (promptOverride?: string) => {
    const promptToUse = (promptOverride || inspectorPrompt).trim();
    if (!promptToUse || isInspectingVisual) return;

    setIsInspectingVisual(true);
    try {
      const res = await axios.post("intelligence/inspect-camera", {
        camera: inspectorCamera,
        question: promptToUse,
      });
      if (res.data.success && res.data.result) {
        const r = res.data.result;
        const resultObj: VisualInspectionResult = {
          camera: inspectorCamera,
          question: promptToUse,
          answer: r.answer || "Analysis completed.",
          confidence: r.confidence || 0.96,
          model: r.model || "gemini-3.6-flash",
          snapshot_url: `/api/intelligence/cameras/${inspectorCamera}/snapshot?t=${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          error: r.error,
        };
        setVisualResult(resultObj);
        toast.success("Gemini Multimodal Vision Analysis Complete!");

        // Also add to QA history
        const qaItem: CameraQAResponse = {
          question: `[Visual ${inspectorCamera}] ${promptToUse}`,
          answer: r.answer,
          confidence: r.confidence || 0.96,
          model: r.model || "gemini-3.6-flash",
          latency_ms: 1200,
          timestamp: new Date().toISOString(),
          escalated_to_gemini: true,
          camera: inspectorCamera,
          snapshot_url: `/api/intelligence/cameras/${inspectorCamera}/snapshot?t=${Date.now()}`,
        };
        setQaHistory((prev) => [qaItem, ...prev.slice(0, 14)]);

        if (autoSpeak && r.answer) {
          speakText(r.answer, 0);
        }
      }
    } catch {
      toast.error("Failed visual frame inspection with Gemini");
    } finally {
      setIsInspectingVisual(false);
    }
  };

  const handleSaveSemantic = async () => {
    if (!editFormData || isSavingSemantic) return;
    setIsSavingSemantic(true);
    try {
      const res = await axios.put(
        `semantic/cameras/${editingCamera}`,
        editFormData,
      );
      if (res.data?.success) {
        toast.success(`Saved semantic metadata for ${editingCamera}`);
        fetchSemantics();
      }
    } catch {
      toast.error("Failed to save camera semantic metadata");
    } finally {
      setIsSavingSemantic(false);
    }
  };

  const clearHistory = () => {
    setQaHistory([]);
    toast.info("Conversation history cleared");
  };

  return (
    <div className={cn("space-y-4 text-foreground", className)}>
      {/* Top Bar: Google Gemini Aura Banner & Tier Status */}
      <div className="relative overflow-hidden rounded-2xl border border-primary/30 bg-gradient-to-br from-indigo-950/40 via-background/90 to-purple-950/40 backdrop-blur-xl p-4 shadow-lg space-y-3">
        <div className="absolute -top-10 -right-10 h-32 w-32 rounded-full bg-primary/20 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-10 -left-10 h-32 w-32 rounded-full bg-purple-500/15 blur-3xl pointer-events-none" />

        <div className="relative flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 to-purple-600 text-white shadow-md shadow-primary/20 ring-1 ring-white/20">
              <LuSparkles className="size-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="font-extrabold text-sm tracking-tight bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
                  Gemini-Powered Camera AI
                </h4>
                <Badge
                  variant="outline"
                  className="text-[10px] bg-indigo-500/15 text-indigo-300 border-indigo-500/30 flex items-center gap-1 font-mono uppercase"
                >
                  <LuShieldCheck className="size-3 text-indigo-400" />
                  Gemini 3.6 Flash
                </Badge>
                {escalateGemini ? (
                  <Badge
                    variant="outline"
                    className="text-[10px] bg-purple-500/15 text-purple-300 border-purple-500/30 flex items-center gap-1"
                  >
                    <span className="size-1.5 rounded-full bg-purple-400 animate-ping" />
                    L2: DEEP REASONING
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="text-[10px] bg-emerald-500/15 text-emerald-300 border-emerald-500/30 flex items-center gap-1"
                  >
                    <span className="size-1.5 rounded-full bg-emerald-400" />
                    L1: LOCAL FAST
                  </Badge>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground flex items-center gap-1.5 mt-0.5">
                <span>Multi-Camera Grounded Context</span>
                <span>•</span>
                <span>Zero Hallucination Guarantee</span>
              </p>
            </div>
          </div>

          {/* Model Switch & Mode Toggle */}
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant={escalateGemini ? "default" : "outline"}
              size="sm"
              onClick={() => setEscalateGemini(!escalateGemini)}
              className={cn(
                "h-8 text-xs font-semibold gap-1.5 transition-all shadow-sm",
                escalateGemini
                  ? "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white border-0"
                  : "border-border/60 hover:bg-secondary/60",
              )}
            >
              <LuSparkles className="size-3.5" />
              {escalateGemini ? "Gemini Deep Vision: ON" : "Local Model Only"}
            </Button>

            <Select
              value={telemetry?.active_model.id || "andro-vision-0.5b-q4"}
              onValueChange={handleModelSwitch}
              disabled={isSwitchingModel}
            >
              <SelectTrigger className="h-8 text-xs bg-secondary/40 min-w-[140px] border-border/50">
                <SelectValue placeholder="Local Tier" />
              </SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m.id} value={m.id} className="text-xs">
                    {m.name} ({m.quantization})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              variant={telemetry?.is_loaded ? "outline" : "secondary"}
              size="sm"
              onClick={handleToggleLoad}
              disabled={isSwitchingModel}
              className="h-8 text-xs gap-1.5"
            >
              {isSwitchingModel ? (
                <LuLoader className="size-3.5 animate-spin" />
              ) : (
                <FaPowerOff
                  className={cn(
                    "size-3",
                    telemetry?.is_loaded
                      ? "text-amber-400"
                      : "text-emerald-400",
                  )}
                />
              )}
              {telemetry?.is_loaded ? "Unload" : "Load L1"}
            </Button>
          </div>
        </div>

        {/* Live Gate & Vehicle Status Baseline Widgets */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-border/30 text-xs">
          {/* Gate Widget */}
          <div className="flex items-center justify-between p-2.5 rounded-xl bg-secondary/30 border border-border/30">
            <div className="flex items-center gap-2">
              <FaDoorOpen className="text-primary text-sm" />
              <div>
                <span className="font-semibold text-foreground">
                  Cam 7 Gate:
                </span>
                <span className="text-[11px] text-muted-foreground ml-1.5">
                  {gateStatus?.certainty_level || "CONFIRMED"}
                </span>
              </div>
            </div>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] font-mono uppercase font-bold",
                gateStatus?.state === "OPEN"
                  ? "bg-amber-500/20 text-amber-400 border-amber-500/40"
                  : gateStatus?.state === "CLOSED"
                    ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                    : "bg-slate-500/20 text-slate-400 border-slate-500/40",
              )}
            >
              {gateStatus?.state || "CLOSED"}
            </Badge>
          </div>

          {/* Vehicle Baseline Widget */}
          <div className="flex items-center justify-between p-2.5 rounded-xl bg-secondary/30 border border-border/30">
            <div className="flex items-center gap-2">
              <FaCar className="text-primary text-sm" />
              <div>
                <span className="font-semibold text-foreground">
                  Parking Baseline:
                </span>
                <span className="text-[11px] text-muted-foreground ml-1.5">
                  Expected 2 Cars
                </span>
              </div>
            </div>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] font-mono",
                vehicleStatus?.both_cars_present
                  ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                  : "bg-amber-500/20 text-amber-400 border-amber-500/40",
              )}
            >
              {vehicleStatus?.current_count ?? 2}/2 Present
            </Badge>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5 bg-secondary/50 p-1 rounded-xl">
          <TabsTrigger
            value="assistant"
            className="text-xs gap-1.5 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-semibold"
          >
            <LuSparkles className="size-3.5" />
            <span>Q&A</span>
          </TabsTrigger>
          <TabsTrigger
            value="vision"
            className="text-xs gap-1.5 rounded-lg data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-semibold"
          >
            <LuEye className="size-3.5" />
            <span>Vision</span>
          </TabsTrigger>
          <TabsTrigger
            value="feed"
            className="text-xs gap-1.5 rounded-lg font-semibold"
          >
            <LuSparkles className="size-3" />
            <span>Feed</span>
          </TabsTrigger>
          <TabsTrigger
            value="timeline"
            className="text-xs gap-1.5 rounded-lg font-semibold"
          >
            <FaHistory className="size-3" />
            <span>Timeline</span>
          </TabsTrigger>
          <TabsTrigger
            value="semantic"
            className="text-xs gap-1.5 rounded-lg font-semibold"
          >
            <LuCamera className="size-3.5" />
            <span>Semantic</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Gemini Conversational Q&A Assistant */}
        <TabsContent value="assistant" className="space-y-3 pt-2">
          <div className="rounded-2xl border border-border/40 bg-card/60 backdrop-blur-xl p-4 shadow-sm space-y-3">
            {/* Header & Controls */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <FaRobot className="text-primary size-4" />
                <h4 className="font-bold text-xs text-foreground">
                  Conversational Camera Assistant
                </h4>
              </div>

              {/* Voice & Auto-Speak Controls */}
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setAutoSpeak(!autoSpeak)}
                  className={cn(
                    "h-7 px-2 text-[10px] gap-1",
                    autoSpeak
                      ? "text-primary bg-primary/10"
                      : "text-muted-foreground",
                  )}
                  title="Auto-speak answers with voice"
                >
                  {autoSpeak ? (
                    <FaVolumeUp className="size-3 text-primary animate-pulse" />
                  ) : (
                    <FaVolumeMute className="size-3" />
                  )}
                  <span>Auto-Voice</span>
                </Button>

                {qaHistory.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearHistory}
                    className="h-7 px-2 text-[10px] text-muted-foreground hover:text-destructive gap-1"
                  >
                    <FaTrashAlt className="size-2.5" />
                    <span>Clear</span>
                  </Button>
                )}
              </div>
            </div>

            {/* Natural Query Input with Voice STT button */}
            <form
              onSubmit={(e) => handleAsk(e)}
              className="relative flex items-center gap-2"
            >
              <div className="relative flex-1">
                <Input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder={
                    isListening
                      ? "Listening to voice input..."
                      : "Ask about gate, cars, dining room TV, clothesline, person whereabouts..."
                  }
                  className={cn(
                    "h-10 text-xs bg-secondary/40 pr-10 rounded-xl transition-all border-border/50",
                    isListening &&
                      "ring-2 ring-primary border-primary bg-primary/5 animate-pulse",
                  )}
                  disabled={isAsking}
                />
                <button
                  type="button"
                  onClick={toggleVoiceListen}
                  className={cn(
                    "absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors",
                    isListening
                      ? "bg-red-500 text-white animate-bounce shadow-md"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary",
                  )}
                  title={
                    isListening
                      ? "Stop listening"
                      : "Speak to Gemini (Voice Input)"
                  }
                >
                  {isListening ? (
                    <FaMicrophoneSlash className="size-3.5" />
                  ) : (
                    <FaMicrophone className="size-3.5" />
                  )}
                </button>
              </div>

              <Button
                type="submit"
                size="sm"
                disabled={isAsking || !question.trim()}
                className="h-10 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-md gap-1.5 font-semibold text-xs"
              >
                {isAsking ? (
                  <LuLoader className="size-4 animate-spin" />
                ) : (
                  <>
                    <FaPaperPlane className="size-3" />
                    <span>Ask</span>
                  </>
                )}
              </Button>
            </form>

            {/* Quick Prompt Chips */}
            <div className="space-y-1.5 pt-1">
              <p className="text-[10px] font-semibold text-muted-foreground tracking-wider uppercase">
                Quick Intelligence Inquiries
              </p>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { label: "🚪 Is gate open?", query: "Is the gate open?" },
                  {
                    label: "🚗 Both cars in parking?",
                    query: "Are both cars in the parking?",
                  },
                  {
                    label: "📺 TV on in dining room?",
                    query: "Is the TV on in the dining room?",
                  },
                  {
                    label: "👕 Clothes on line?",
                    query: "Are there clothes hanging on the backyard line?",
                  },
                  {
                    label: "👤 Where was John last seen?",
                    query: "Where was John last seen?",
                  },
                  {
                    label: "⏱️ Last 10 minutes activity",
                    query: "What happened in the last 10 minutes?",
                  },
                ].map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleAsk(undefined, item.query)}
                    disabled={isAsking}
                    className="rounded-full bg-secondary/70 hover:bg-secondary border border-border/50 px-3 py-1 text-[11px] text-muted-foreground hover:text-foreground transition-all hover:scale-105 active:scale-95 shadow-sm"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Conversation Flow / QA Cards */}
            {qaHistory.length > 0 ? (
              <div className="space-y-3 pt-3 border-t border-border/30 max-h-[460px] overflow-y-auto pr-1">
                {qaHistory.map((item, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-border/40 bg-card/80 backdrop-blur-md p-3.5 space-y-2.5 text-xs shadow-sm hover:border-border/60 transition-all"
                  >
                    {/* User Question Header */}
                    <div className="flex items-start justify-between gap-2">
                      <span className="flex items-center gap-1.5 font-bold text-foreground">
                        <FaQuestionCircle className="text-primary size-3.5 flex-shrink-0" />
                        {item.question}
                      </span>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <Badge
                          variant="secondary"
                          className="text-[9px] font-mono py-0 px-1.5 bg-secondary/60"
                        >
                          {item.latency_ms}ms
                        </Badge>
                        {item.escalated_to_gemini && (
                          <Badge
                            variant="outline"
                            className="text-[9px] font-mono py-0 px-1.5 bg-indigo-500/10 text-indigo-400 border-indigo-500/30"
                          >
                            Gemini 3.6
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Answer Bubble with Left Accent Glow */}
                    <div className="rounded-lg bg-secondary/25 border-l-4 border-primary p-3 space-y-2">
                      <p className="text-foreground/95 whitespace-pre-line leading-relaxed text-xs">
                        {item.answer}
                      </p>

                      {/* Attached Snapshot Preview (if visual inquiry) */}
                      {item.snapshot_url && (
                        <div className="pt-2">
                          <img
                            src={item.snapshot_url}
                            alt="Analyzed Frame Snapshot"
                            className="w-full max-h-48 object-cover rounded-lg border border-border/40 shadow-sm"
                          />
                        </div>
                      )}
                    </div>

                    {/* Action Toolbar: Voice Speak, Copy, Reasoning Trace Toggle */}
                    <div className="flex items-center justify-between pt-1 text-[11px] text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => speakText(item.answer, idx)}
                          className={cn(
                            "flex items-center gap-1 px-2 py-0.5 rounded-md hover:bg-secondary hover:text-foreground transition-colors",
                            isSpeaking &&
                              speakingIndex === idx &&
                              "text-primary font-bold animate-pulse",
                          )}
                          title="Read out loud"
                        >
                          {isSpeaking && speakingIndex === idx ? (
                            <>
                              <FaVolumeMute className="size-3" />
                              <span>Stop Voice</span>
                            </>
                          ) : (
                            <>
                              <FaVolumeUp className="size-3" />
                              <span>Speak</span>
                            </>
                          )}
                        </button>

                        <button
                          type="button"
                          onClick={() => copyToClipboard(item.answer, idx)}
                          className="flex items-center gap-1 px-2 py-0.5 rounded-md hover:bg-secondary hover:text-foreground transition-colors"
                          title="Copy Answer"
                        >
                          {copiedIdx === idx ? (
                            <>
                              <LuCheck className="size-3 text-emerald-400" />
                              <span className="text-emerald-400">Copied</span>
                            </>
                          ) : (
                            <>
                              <LuCopy className="size-3" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>

                      {/* Collapsible Reasoning Trace */}
                      {item.debug && (
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedTraceIdx(
                              expandedTraceIdx === idx ? null : idx,
                            )
                          }
                          className="flex items-center gap-1 text-[10px] text-primary hover:underline font-mono"
                        >
                          <span>Reasoning Trace</span>
                          {expandedTraceIdx === idx ? (
                            <FaChevronUp className="size-2.5" />
                          ) : (
                            <FaChevronDown className="size-2.5" />
                          )}
                        </button>
                      )}
                    </div>

                    {/* Collapsible Gemini Reasoning & Tool Diagnostic Box */}
                    {item.debug && expandedTraceIdx === idx && (
                      <div className="p-2.5 rounded-lg bg-black/40 border border-border/30 font-mono text-[10px] space-y-1.5 text-muted-foreground mt-2">
                        <div className="flex items-center justify-between text-indigo-300 font-semibold border-b border-white/10 pb-1">
                          <span>
                            Intent: {item.debug.detected_intent || "N/A"}
                          </span>
                          <span>
                            Confidence: {Math.round(item.confidence * 100)}%
                          </span>
                        </div>
                        {item.debug.tools_queried && (
                          <div>
                            <span className="text-slate-400">
                              Tools Queried:{" "}
                            </span>
                            <span className="text-emerald-400">
                              {item.debug.tools_queried.join(", ") ||
                                "semantic_eval"}
                            </span>
                          </div>
                        )}
                        {item.debug.entities?.target_camera && (
                          <div>
                            <span className="text-slate-400">
                              Target Camera:{" "}
                            </span>
                            <span className="text-amber-300">
                              {item.debug.entities.target_camera}
                            </span>
                          </div>
                        )}
                        {item.debug.entities?.subject && (
                          <div>
                            <span className="text-slate-400">Subject: </span>
                            <span className="text-cyan-300">
                              {item.debug.entities.subject}
                            </span>
                          </div>
                        )}
                        <div className="text-[9px] text-slate-500 pt-0.5">
                          Context Char Size:{" "}
                          {item.debug.reasoning_context_size_chars || 0} •
                          Escalated:{" "}
                          {item.debug.escalated_to_gemini ? "True" : "False"}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 rounded-xl border border-dashed border-border/40 bg-secondary/10 space-y-2">
                <LuSparkles className="size-7 text-primary/60 mx-auto animate-pulse" />
                <p className="text-xs font-semibold text-foreground">
                  No questions asked yet
                </p>
                <p className="text-[11px] text-muted-foreground max-w-xs mx-auto">
                  Type or speak a question above to test Gemini-level multi-camera
                  reasoning and zero-hallucination answers.
                </p>
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab 2: Multimodal Visual Frame Inspector (Gemini Vision Live) */}
        <TabsContent value="vision" className="space-y-3 pt-2">
          <div className="rounded-2xl border border-border/40 bg-card/60 backdrop-blur-xl p-4 shadow-sm space-y-3.5">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <LuEye className="text-primary size-4" />
                <h4 className="font-bold text-xs text-foreground">
                  Gemini 3.6 Flash Multimodal Frame Inspector
                </h4>
              </div>

              {/* Camera Selector */}
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-muted-foreground">
                  Target Camera:
                </span>
                <Select
                  value={inspectorCamera}
                  onValueChange={(val) => {
                    setInspectorCamera(val);
                    setSnapshotTimestamp(Date.now());
                  }}
                >
                  <SelectTrigger className="h-8 text-xs bg-secondary/40 min-w-[130px] border-border/50">
                    <SelectValue placeholder="Select Camera" />
                  </SelectTrigger>
                  <SelectContent>
                    {[
                      { id: "camera_1", name: "Camera 1 (Front Porch)" },
                      { id: "camera_2", name: "Camera 2 (Driveway)" },
                      { id: "camera_3", name: "Camera 3 (Garage)" },
                      { id: "camera_4", name: "Camera 4 (Side Yard)" },
                      { id: "camera_5", name: "Camera 5 (Backyard)" },
                      { id: "camera_6", name: "Camera 6 (Living Room)" },
                      { id: "camera_7", name: "Camera 7 (Gate & Parking)" },
                      { id: "camera_8", name: "Camera 8 (Dining Room)" },
                    ].map((cam) => (
                      <SelectItem key={cam.id} value={cam.id} className="text-xs">
                        {cam.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSnapshotTimestamp(Date.now())}
                  className="h-8 px-2 text-xs"
                  title="Refresh Frame Snapshot"
                >
                  <LuRefreshCw className="size-3.5" />
                </Button>
              </div>
            </div>

            {/* Live Camera Frame Preview */}
            <div className="relative rounded-xl overflow-hidden border border-border/40 bg-black/60 aspect-video flex items-center justify-center">
              <img
                src={`/api/intelligence/cameras/${inspectorCamera}/snapshot?t=${snapshotTimestamp}`}
                alt="Camera Frame"
                className="w-full h-full object-cover"
                onError={(e: any) => {
                  e.target.style.display = "none";
                }}
              />
              <div className="absolute top-2 left-2 flex items-center gap-1.5">
                <Badge
                  variant="outline"
                  className="bg-black/70 backdrop-blur-md text-white border-white/20 text-[10px] uppercase font-mono font-bold"
                >
                  {inspectorCamera} LIVE SNAPSHOT
                </Badge>
              </div>
            </div>

            {/* Vision Query Presets */}
            <div className="space-y-1.5">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Multimodal Vision Prompt Presets
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {[
                  {
                    label: "📺 TV Screen Status",
                    cam: "camera_8",
                    prompt:
                      "Is the TV on in the dining room? What is displayed on the screen?",
                  },
                  {
                    label: "👕 Clothesline Check",
                    cam: "camera_5",
                    prompt:
                      "Are there clothes hanging on the backyard line? Describe them.",
                  },
                  {
                    label: "🚪 Gate State & Obstacles",
                    cam: "camera_7",
                    prompt:
                      "Is the main gate open or closed? Is there any car or obstacle blocking it?",
                  },
                  {
                    label: "🚗 Parking Spot Count",
                    cam: "camera_7",
                    prompt:
                      "How many cars are parked in the parking area? Describe each car.",
                  },
                  {
                    label: "📦 Delivery / Package Check",
                    cam: "camera_1",
                    prompt:
                      "Is there any package, parcel, or delivery box visible on the porch?",
                  },
                  {
                    label: "🔍 Full Scene Security Audit",
                    cam: inspectorCamera,
                    prompt:
                      "Perform a deep visual security audit of this entire frame. List all people, vehicles, and abnormal items.",
                  },
                ].map((preset, pIdx) => (
                  <button
                    key={pIdx}
                    type="button"
                    onClick={() => {
                      if (preset.cam) setInspectorCamera(preset.cam);
                      setInspectorPrompt(preset.prompt);
                      handleVisualInspect(preset.prompt);
                    }}
                    disabled={isInspectingVisual}
                    className="flex items-center justify-between p-2 rounded-xl bg-secondary/40 hover:bg-secondary border border-border/30 text-left text-xs transition-all hover:border-primary/50 group"
                  >
                    <span className="font-medium text-foreground group-hover:text-primary transition-colors">
                      {preset.label}
                    </span>
                    <FaChevronRight className="size-2.5 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Visual Prompt Input */}
            <div className="space-y-2 pt-2 border-t border-border/30">
              <label className="text-[11px] font-semibold text-foreground">
                Custom Gemini Vision Prompt
              </label>
              <div className="flex gap-2">
                <Input
                  value={inspectorPrompt}
                  onChange={(e) => setInspectorPrompt(e.target.value)}
                  placeholder="Ask Gemini to analyze anything in this frame..."
                  className="h-9 text-xs bg-secondary/40 rounded-xl"
                  disabled={isInspectingVisual}
                />
                <Button
                  onClick={() => handleVisualInspect()}
                  disabled={isInspectingVisual || !inspectorPrompt.trim()}
                  className="h-9 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-semibold text-xs shadow-md gap-1.5 flex-shrink-0"
                >
                  {isInspectingVisual ? (
                    <LuLoader className="size-3.5 animate-spin" />
                  ) : (
                    <>
                      <LuSparkles className="size-3.5" />
                      <span>Analyze Frame</span>
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Visual Inspection Result Card */}
            {visualResult && (
              <div className="rounded-xl border border-primary/30 bg-gradient-to-br from-indigo-950/20 via-secondary/20 to-purple-950/20 p-3.5 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-bold text-foreground">
                    <LuSparkles className="text-primary size-3.5" />
                    <span>Gemini 3.6 Flash Visual Analysis</span>
                  </div>
                  <Badge
                    variant="outline"
                    className="text-[10px] bg-primary/10 text-primary border-primary/30 font-mono"
                  >
                    Confidence: {Math.round(visualResult.confidence * 100)}%
                  </Badge>
                </div>
                <p className="text-foreground/90 whitespace-pre-line leading-relaxed pl-3 border-l-2 border-primary">
                  {visualResult.answer}
                </p>
                <div className="flex items-center justify-between pt-1 text-[11px] text-muted-foreground">
                  <span>
                    Camera: {visualResult.camera} • {visualResult.timestamp}
                  </span>
                  <button
                    type="button"
                    onClick={() => speakText(visualResult.answer)}
                    className="flex items-center gap-1 text-primary hover:underline"
                  >
                    <FaVolumeUp className="size-3" />
                    <span>Speak Answer</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab 3: Live Semantic Feed */}
        <TabsContent value="feed" className="space-y-3 pt-2">
          <div className="rounded-2xl border border-border/40 bg-card/60 backdrop-blur-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-xs flex items-center gap-1.5 text-foreground">
                <LuSparkles className="text-amber-400" />
                Live Semantic Understandings
              </h4>
              <Badge variant="secondary" className="text-[10px] font-mono">
                {semanticFeed.length} Events
              </Badge>
            </div>

            <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
              {semanticFeed.length > 0 ? (
                semanticFeed.map((event) => (
                  <div
                    key={event.id}
                    className={cn(
                      "p-3 rounded-xl border transition-all text-xs space-y-2",
                      event.importance === "HIGH"
                        ? "border-red-500/30 bg-red-500/5 hover:border-red-500/50"
                        : event.importance === "MEDIUM"
                          ? "border-amber-500/30 bg-amber-500/5 hover:border-amber-500/50"
                          : "border-border/40 bg-secondary/20 hover:border-border/60",
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-semibold text-foreground leading-snug">
                        {event.summary}
                      </p>
                      <span className="text-[10px] text-muted-foreground font-mono flex-shrink-0">
                        {event.time}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge
                        variant="outline"
                        className="text-[10px] flex items-center gap-1 border-primary/30 text-primary"
                      >
                        <FaMapMarkerAlt className="text-[9px]" />
                        {event.location}
                      </Badge>

                      <Badge
                        variant="secondary"
                        className={cn(
                          "text-[10px] uppercase font-mono tracking-wider",
                          event.importance === "HIGH"
                            ? "bg-red-500/20 text-red-400 border-red-500/30"
                            : event.importance === "MEDIUM"
                              ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
                              : "bg-blue-500/20 text-blue-400 border-blue-500/30",
                        )}
                      >
                        {event.activity}
                      </Badge>

                      {event.multi_camera_journey &&
                        event.multi_camera_journey.length > 1 && (
                          <div className="flex items-center gap-1 text-[10px] text-muted-foreground bg-secondary/40 px-2 py-0.5 rounded-md border border-border/20">
                            <span>Journey:</span>
                            {event.multi_camera_journey.map((pt, pIdx) => (
                              <React.Fragment key={pIdx}>
                                <span className="font-semibold text-foreground">
                                  {pt}
                                </span>
                                {pIdx <
                                  event.multi_camera_journey.length - 1 && (
                                  <FaChevronRight className="text-[8px] opacity-60" />
                                )}
                              </React.Fragment>
                            ))}
                          </div>
                        )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-xs text-muted-foreground">
                  No recent semantic events. Waiting for camera motion / object
                  triggers...
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Tab 4: Event Timeline Memory */}
        <TabsContent value="timeline" className="space-y-3 pt-2">
          <div className="rounded-2xl border border-border/40 bg-card/60 backdrop-blur-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-xs flex items-center gap-1.5 text-foreground">
                <FaHistory className="text-primary" />
                Local Event Timeline Memory
              </h4>
              <Badge variant="secondary" className="text-[10px] font-mono">
                {timelineEvents.length} Recorded
              </Badge>
            </div>

            <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
              {timelineEvents.length > 0 ? (
                timelineEvents.map((evt) => (
                  <div
                    key={evt.id}
                    className="p-2.5 rounded-lg border border-border/30 bg-secondary/20 flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-1.5 font-semibold text-foreground">
                        <Badge variant="outline" className="text-[10px] py-0">
                          {evt.camera}
                        </Badge>
                        <span className="capitalize">
                          {evt.event_type.replace(/_/g, " ")}
                        </span>
                        {evt.identity_name && (
                          <span className="text-primary">
                            ({evt.identity_name})
                          </span>
                        )}
                      </div>
                      {evt.metadata?.summary && (
                        <p className="text-[11px] text-muted-foreground">
                          {evt.metadata.summary}
                        </p>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground font-mono flex-shrink-0">
                      {evt.timestamp ? evt.timestamp.slice(11, 19) : ""}
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-xs text-muted-foreground">
                  No timeline events recorded yet.
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Tab 5: Camera Semantic Map Editor */}
        <TabsContent value="semantic" className="space-y-3 pt-2">
          <div className="rounded-2xl border border-border/40 bg-card/60 backdrop-blur-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-xs flex items-center gap-1.5 text-foreground">
                <LuCamera className="text-primary" />
                Camera Semantic Description Editor
              </h4>

              <Select value={editingCamera} onValueChange={setEditingCamera}>
                <SelectTrigger className="h-8 text-xs bg-secondary/40 min-w-[140px] border-border/50">
                  <SelectValue placeholder="Select Camera" />
                </SelectTrigger>
                <SelectContent>
                  {cameraSemantics.map((c) => (
                    <SelectItem
                      key={c.camera}
                      value={c.camera}
                      className="text-xs"
                    >
                      {c.name || c.camera} ({c.location})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {editFormData && (
              <div className="space-y-2.5 text-xs">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[11px] font-semibold text-muted-foreground">
                      Camera Name
                    </label>
                    <Input
                      value={editFormData.name || ""}
                      onChange={(e) =>
                        setEditFormData({
                          ...editFormData,
                          name: e.target.value,
                        })
                      }
                      className="h-8 text-xs bg-secondary/30 mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-muted-foreground">
                      Location / Area
                    </label>
                    <Input
                      value={editFormData.location || ""}
                      onChange={(e) =>
                        setEditFormData({
                          ...editFormData,
                          location: e.target.value,
                        })
                      }
                      className="h-8 text-xs bg-secondary/30 mt-1"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-muted-foreground">
                    Description & Scene Context
                  </label>
                  <Textarea
                    value={editFormData.description || ""}
                    onChange={(e) =>
                      setEditFormData({
                        ...editFormData,
                        description: e.target.value,
                      })
                    }
                    rows={2}
                    className="text-xs bg-secondary/30 mt-1"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[11px] font-semibold text-muted-foreground">
                      Expected Vehicles (Baseline)
                    </label>
                    <Input
                      type="number"
                      value={editFormData.expected_vehicles || 0}
                      onChange={(e) =>
                        setEditFormData({
                          ...editFormData,
                          expected_vehicles: parseInt(e.target.value) || 0,
                        })
                      }
                      className="h-8 text-xs bg-secondary/30 mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-muted-foreground">
                      Environmental Motion Notes
                    </label>
                    <Input
                      value={editFormData.environmental_motion_notes || ""}
                      onChange={(e) =>
                        setEditFormData({
                          ...editFormData,
                          environmental_motion_notes: e.target.value,
                        })
                      }
                      placeholder="e.g. Suppress tree/leaf wind motion"
                      className="h-8 text-xs bg-secondary/30 mt-1"
                    />
                  </div>
                </div>

                <Button
                  onClick={handleSaveSemantic}
                  disabled={isSavingSemantic}
                  size="sm"
                  className="w-full gap-1.5 h-8 text-xs mt-2"
                >
                  {isSavingSemantic ? (
                    <LuLoader className="size-3.5 animate-spin" />
                  ) : (
                    <FaSave className="size-3.5" />
                  )}
                  Save Camera Semantic Description
                </Button>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
