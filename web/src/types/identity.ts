export type PresenceStatus = "present" | "not_recently_seen" | "away";

export interface IdentityReference {
  id: string;
  image_path: string;
  url: string;
  source: "upload" | "confirmed_event" | "manual";
  created_at: string;
}

export interface ObjectSighting {
  id: string;
  track_id: string;
  identity_id?: string;
  identity_name?: string;
  camera: string;
  area: string;
  timestamp: string;
  confidence: number;
  snapshot_url?: string;
}

export interface CustomIdentity {
  id: string;
  name: string;
  category: string;
  object_class: string;
  color?: string;
  description?: string;
  notes?: string;
  is_person: boolean;
  status: PresenceStatus;
  last_seen_camera?: string;
  last_seen_location?: string;
  last_seen_time?: string;
  first_seen_time?: string;
  active_track_id?: string;
  reference_count: number;
  primary_reference_url?: string;
  sightings_count?: number;
  references?: IdentityReference[];
  sightings?: ObjectSighting[];
  cameras_seen?: string[];
  created_at?: string;
  updated_at?: string;
}

export interface ActiveTrack {
  track_id: string;
  track_display_id: string;
  camera: string;
  area: string;
  object_class: string;
  is_known: boolean;
  identity_id?: string;
  identity_name?: string;
  confidence: number;
  status: PresenceStatus;
  first_seen: string;
  last_seen: string;
  seconds_ago: number;
  sighting_count: number;
  snapshot_url?: string;
}

export interface UnknownTrack {
  track_id: string;
  track_display_id: string;
  camera: string;
  area: string;
  object_class: string;
  first_seen: string;
  last_seen: string;
  sighting_count: number;
  snapshot_url?: string;
  status: string;
}

export interface CameraAreaMapping {
  camera: string;
  area: string;
  notes?: string;
}

export interface IdentitySettingsConfig {
  matching_threshold_object: number;
  matching_threshold_person: number;
  unknown_object_threshold: number;
  track_timeout_seconds: number;
  presence_timeout_seconds: number;
  away_timeout_seconds: number;
  recognition_cooldown_seconds: number;
  max_reference_images: number;
  cross_camera_window_seconds: number;
  enable_cross_camera_tracking: boolean;
}
