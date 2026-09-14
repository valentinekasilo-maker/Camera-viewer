/** TypeScript interfaces for ANDRO-Vision Camera Intelligence Engine */

export interface CameraModelSpec {
  id: string;
  name: string;
  tier: "0.5B" | "1.2B" | "3.0B";
  parameters: string;
  quantization: string;
  ram_required_mb: number;
  context_window: number;
  description: string;
  recommended_hardware: string;
  is_active: boolean;
  is_loaded: boolean;
}

export interface ModelManagerTelemetry {
  is_loaded: boolean;
  active_model: {
    id: string;
    name: string;
    tier: string;
    quantization: string;
    ram_usage_mb: number;
    runtime_backend: string;
  };
  total_inferences: number;
  avg_latency_ms: number;
  loaded_seconds_ago: number;
}

export interface SemanticUnderstandingObject {
  type: string;
  identity: string;
  confidence: number;
}

export interface SemanticUnderstanding {
  id: string;
  time: string;
  camera: string;
  location: string;
  summary: string;
  activity: string;
  importance: "HIGH" | "NORMAL" | "LOW" | "MEDIUM";
  objects: SemanticUnderstandingObject[];
  multi_camera_journey: string[];
  created_at: string;
}

export interface CameraQAResponse {
  question: string;
  answer: string;
  confidence: number;
  model: string;
  evidence?: any[];
  latency_ms: number;
  timestamp: string;
  escalated_to_gemini?: boolean;
  hallucination_guarantee_passed?: boolean;
  snapshot_url?: string;
  camera?: string;
  debug?: {
    question?: string;
    detected_intent?: string;
    entities?: {
      subject?: string;
      subject_type?: string;
      resolved_pronoun?: string;
      target_camera?: string;
      target_location?: string;
    };
    time_range?: {
      seconds?: number;
      description?: string;
    };
    tools_queried?: string[];
    evidence_count?: number;
    reasoning_context_size_chars?: number;
    selected_model?: string;
    escalated_to_gemini?: boolean;
    latency_ms?: number;
  };
}

export interface VisualInspectionResult {
  camera: string;
  question: string;
  answer: string;
  confidence: number;
  model: string;
  snapshot_url?: string;
  timestamp: string;
  error?: string;
}

