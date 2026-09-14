"""Master Identity Manager coordinating models, storage, feature extraction, matching, and tracking."""

import datetime
import json
import logging
import os
import time
import uuid
from typing import Any, Optional

import cv2
import numpy as np

from frigate.identity.extractor import FeatureExtractor
from frigate.identity.matcher import IdentityMatcher, MatchResult
from frigate.identity.tracker import IdentityTracker, TrackState
from frigate.models import (
    CameraAreaMapping,
    CustomIdentity,
    IdentityReference,
    IdentitySettings,
    ObjectSightingRecord,
    ObjectTrackRecord,
)

logger = logging.getLogger(__name__)

DEFAULT_CAMERA_AREAS = {
    "front_cam": "Gate & Driveway",
    "back_cam": "Veranda & Backyard",
    "living_room": "Living Room",
    "garage": "Garage & Workshop",
    "entrance": "Front Entrance",
    "hallway": "Main Hallway",
    "patio": "Perimeter & Patio",
}


class IdentityManager:
    """Singleton service for Custom Objects & Identity Tracking in ANDRO-Vision."""

    def __init__(self, storage_root: str = "config/identities"):
        self.storage_root = os.path.abspath(storage_root)
        self.ref_storage_dir = os.path.join(self.storage_root, "references")
        self.snap_storage_dir = os.path.join(self.storage_root, "snapshots")

        os.makedirs(self.ref_storage_dir, exist_ok=True)
        os.makedirs(self.snap_storage_dir, exist_ok=True)

        self.extractor = FeatureExtractor()
        self.matcher = IdentityMatcher()
        self.tracker = IdentityTracker()

        self._cached_identities: Optional[list[dict[str, Any]]] = None
        self._cached_areas: Optional[dict[str, str]] = None

        self._ensure_defaults()

    def _ensure_defaults(self):
        """Seed default camera area mappings and identity settings if empty."""
        try:
            from peewee import SqliteDatabase
            models = [
                CustomIdentity,
                IdentityReference,
                ObjectTrackRecord,
                ObjectSightingRecord,
                CameraAreaMapping,
                IdentitySettings,
            ]
            # If models aren't bound or db is closed, bind to frigate.db
            db_path = os.path.abspath("config/frigate.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            db = SqliteDatabase(db_path, pragmas={"journal_mode": "wal", "foreign_keys": 1})
            db.bind(models)
            if db.is_closed():
                db.connect()
            db.create_tables(models, safe=True)
        except Exception as e:
            logger.debug("Database binding in IdentityManager: %s", e)

        try:
            for cam, area in DEFAULT_CAMERA_AREAS.items():
                mapping, created = CameraAreaMapping.get_or_create(
                    camera=cam,
                    defaults={"area_name": area, "notes": f"Default area for {cam}"},
                )
        except Exception as e:
            logger.debug("Area mapping table initialization: %s", e)

        try:
            IdentitySettings.get_or_create(
                id=1,
                defaults={
                    "matching_threshold_object": 0.70,
                    "matching_threshold_person": 0.75,
                    "unknown_object_threshold": 0.50,
                    "track_timeout_seconds": 60,
                    "presence_timeout_seconds": 180,
                    "away_timeout_seconds": 900,
                    "recognition_cooldown_seconds": 3,
                    "max_reference_images": 15,
                    "cross_camera_window_seconds": 90,
                    "enable_cross_camera_tracking": True,
                },
            )
        except Exception as e:
            logger.debug("Identity settings table initialization: %s", e)

    def get_camera_location(self, camera_name: str) -> str:
        """Get human-readable area name for a camera."""
        if self._cached_areas is None:
            self._cached_areas = {}
            try:
                for mapping in CameraAreaMapping.select():
                    self._cached_areas[mapping.camera] = mapping.area_name
            except Exception:
                pass
        return self._cached_areas.get(
            camera_name,
            DEFAULT_CAMERA_AREAS.get(camera_name, camera_name.capitalize().replace("_", " ")),
        )

    def invalidate_cache(self):
        self._cached_identities = None
        self._cached_areas = None

    def get_identities(
        self,
        object_class: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve all enrolled identities with parsed references and presence status."""
        query = CustomIdentity.select()
        if object_class:
            query = query.where(CustomIdentity.object_class == object_class.lower())
        if category:
            query = query.where(CustomIdentity.category == category.lower())

        identities = []
        try:
            for id_record in query:
                if search and search.lower() not in id_record.name.lower():
                    continue

                refs = []
                primary_ref_url = None
                for ref_record in id_record.references:
                    ref_url = f"/api/identities/reference-image/{ref_record.id}"
                    if not primary_ref_url:
                        primary_ref_url = ref_url
                    refs.append({
                        "id": ref_record.id,
                        "image_path": ref_record.image_path,
                        "url": ref_url,
                        "source": ref_record.source,
                        "created_at": ref_record.created_at.isoformat() if ref_record.created_at else None,
                    })

                last_seen_ts = id_record.last_seen_time.timestamp() if id_record.last_seen_time else None
                computed_status = self.tracker.calculate_presence_status(last_seen_ts)

                sightings_count = ObjectSightingRecord.select().where(ObjectSightingRecord.identity_id == id_record.id).count()

                identities.append({
                    "id": id_record.id,
                    "name": id_record.name,
                    "category": id_record.category or ("People" if id_record.is_person else "General"),
                    "object_class": id_record.object_class,
                    "color": id_record.color or "",
                    "description": id_record.description or "",
                    "notes": id_record.notes or "",
                    "is_person": id_record.is_person,
                    "status": computed_status,
                    "last_seen_camera": id_record.last_seen_camera,
                    "last_seen_location": id_record.last_seen_location,
                    "last_seen_time": id_record.last_seen_time.isoformat() if id_record.last_seen_time else None,
                    "first_seen_time": id_record.first_seen_time.isoformat() if id_record.first_seen_time else None,
                    "active_track_id": id_record.active_track_id,
                    "reference_count": len(refs),
                    "primary_reference_url": primary_ref_url,
                    "sightings_count": sightings_count,
                    "references": refs,
                    "created_at": id_record.created_at.isoformat() if id_record.created_at else None,
                    "updated_at": id_record.updated_at.isoformat() if id_record.updated_at else None,
                })
        except Exception as e:
            logger.error("Failed to query enrolled identities: %s", e)

        return identities

    def get_all_enrolled_identities(self) -> list[dict[str, Any]]:
        """Retrieve all enrolled identities with numerical reference embeddings for real-time matching."""
        if self._cached_identities is not None:
            return self._cached_identities

        identities = []
        try:
            for id_record in CustomIdentity.select():
                refs = []
                for ref_record in id_record.references:
                    vec = None
                    if ref_record.embedding_json:
                        try:
                            vec = np.array(json.loads(ref_record.embedding_json), dtype=np.float32)
                        except Exception:
                            pass
                    refs.append({
                        "id": ref_record.id,
                        "image_path": ref_record.image_path,
                        "embedding": vec,
                        "source": ref_record.source,
                        "created_at": ref_record.created_at.isoformat() if ref_record.created_at else None,
                    })

                last_seen_ts = id_record.last_seen_time.timestamp() if id_record.last_seen_time else None
                computed_status = self.tracker.calculate_presence_status(last_seen_ts)

                identities.append({
                    "id": id_record.id,
                    "name": id_record.name,
                    "category": id_record.category,
                    "object_class": id_record.object_class,
                    "color": id_record.color,
                    "description": id_record.description,
                    "notes": id_record.notes,
                    "is_person": id_record.is_person,
                    "status": computed_status,
                    "last_seen_camera": id_record.last_seen_camera,
                    "last_seen_location": id_record.last_seen_location,
                    "last_seen_time": id_record.last_seen_time.isoformat() if id_record.last_seen_time else None,
                    "first_seen_time": id_record.first_seen_time.isoformat() if id_record.first_seen_time else None,
                    "active_track_id": id_record.active_track_id,
                    "reference_count": len(refs),
                    "created_at": id_record.created_at.isoformat() if id_record.created_at else None,
                    "updated_at": id_record.updated_at.isoformat() if id_record.updated_at else None,
                    "reference_embeddings": refs,
                })
        except Exception as e:
            logger.error("Failed to load enrolled identities: %s", e)

        self._cached_identities = identities
        return identities

    def create_identity(
        self,
        name: str,
        object_class: str,
        category: Optional[str] = None,
        color: Optional[str] = None,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> dict[str, Any]:
        """Create a new custom identity."""
        identity_id = str(uuid.uuid4())
        now = datetime.datetime.now()
        is_person = object_class.strip().lower() == "person"

        CustomIdentity.create(
            id=identity_id,
            name=name.strip(),
            category=category.strip() if category else ("People" if is_person else "Vehicle" if object_class.lower() in ("car", "motorcycle", "bicycle", "bus", "truck") else "General"),
            object_class=object_class.strip().lower(),
            color=color.strip() if color else None,
            description=description.strip() if description else None,
            notes=notes.strip() if notes else None,
            is_person=is_person,
            status="not_recently_seen",
            created_at=now,
            updated_at=now,
            reference_count=0,
        )

        self.invalidate_cache()
        return self.get_identity(identity_id)

    def get_identity(self, identity_id: str) -> Optional[dict[str, Any]]:
        """Get full identity details including references, sightings timeline, and presence."""
        try:
            id_record = CustomIdentity.get(CustomIdentity.id == identity_id)
            refs = []
            for r in id_record.references:
                refs.append({
                    "id": r.id,
                    "image_path": r.image_path,
                    "url": f"/api/identities/reference-image/{r.id}",
                    "source": r.source,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                })

            sightings = []
            for s in ObjectSightingRecord.select().where(ObjectSightingRecord.identity_id == identity_id).order_by(ObjectSightingRecord.timestamp.desc()).limit(50):
                sightings.append({
                    "id": s.id,
                    "track_id": s.track_id,
                    "camera": s.camera,
                    "area": s.camera_location,
                    "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                    "confidence": s.confidence,
                    "snapshot_url": f"/api/identities/track-snapshot/{s.track_id}" if s.snapshot_path else None,
                })

            # Cameras seen on
            cameras_seen = list({s["camera"] for s in sightings if s.get("camera")})

            last_seen_ts = id_record.last_seen_time.timestamp() if id_record.last_seen_time else None
            computed_status = self.tracker.calculate_presence_status(last_seen_ts)

            return {
                "id": id_record.id,
                "name": id_record.name,
                "category": id_record.category or ("People" if id_record.is_person else "General"),
                "object_class": id_record.object_class,
                "color": id_record.color or "",
                "description": id_record.description or "",
                "notes": id_record.notes or "",
                "is_person": id_record.is_person,
                "status": computed_status,
                "last_seen_camera": id_record.last_seen_camera,
                "last_seen_location": id_record.last_seen_location,
                "last_seen_time": id_record.last_seen_time.isoformat() if id_record.last_seen_time else None,
                "first_seen_time": id_record.first_seen_time.isoformat() if id_record.first_seen_time else None,
                "active_track_id": id_record.active_track_id,
                "reference_count": len(refs),
                "primary_reference_url": refs[0]["url"] if refs else None,
                "references": refs,
                "sightings": sightings,
                "cameras_seen": cameras_seen,
                "created_at": id_record.created_at.isoformat() if id_record.created_at else None,
                "updated_at": id_record.updated_at.isoformat() if id_record.updated_at else None,
            }
        except Exception as e:
            logger.error("Error retrieving identity %s: %s", identity_id, e)
            return None

    def update_identity(self, identity_id: str, **kwargs) -> Optional[dict[str, Any]]:
        """Update identity metadata."""
        try:
            identity = CustomIdentity.get(CustomIdentity.id == identity_id)
            for k, v in kwargs.items():
                if hasattr(identity, k) and v is not None:
                    setattr(identity, k, v)
            identity.updated_at = datetime.datetime.now()
            identity.save()
            self.invalidate_cache()
            return self.get_identity(identity_id)
        except Exception as e:
            logger.error("Error updating identity %s: %s", identity_id, e)
            return None

    def delete_identity(self, identity_id: str) -> bool:
        """Delete an identity and remove all associated local reference files."""
        try:
            identity = CustomIdentity.get(CustomIdentity.id == identity_id)
            for ref in identity.references:
                file_path = os.path.join(self.ref_storage_dir, ref.image_path)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
            identity.delete_instance(recursive=True)
            self.invalidate_cache()
            return True
        except Exception as e:
            logger.error("Failed to delete identity %s: %s", identity_id, e)
            return False

    def add_reference_image(
        self, identity_id: str, image_bytes: bytes, notes: Optional[str] = None, source: str = "upload"
    ) -> Optional[dict[str, Any]]:
        """Add another reference crop/image to an existing identity."""
        try:
            identity = CustomIdentity.get(CustomIdentity.id == identity_id)
        except Exception:
            return None

        ref_id = str(uuid.uuid4())
        save_filename = f"{identity_id}_{ref_id}.jpg"
        save_path = os.path.join(self.ref_storage_dir, save_filename)

        with open(save_path, "wb") as f:
            f.write(image_bytes)

        embedding = self.extractor.extract_from_bytes(image_bytes)
        embedding_json = json.dumps(embedding.tolist()) if embedding is not None else None

        ref = IdentityReference.create(
            id=ref_id,
            identity=identity,
            image_path=save_filename,
            embedding_json=embedding_json,
            created_at=datetime.datetime.now(),
            source=source,
        )

        identity.reference_count = identity.references.count()
        identity.updated_at = datetime.datetime.now()
        identity.save()
        self.invalidate_cache()

        return {
            "id": ref.id,
            "image_path": ref.image_path,
            "url": f"/api/identities/reference-image/{ref.id}",
            "created_at": ref.created_at.isoformat(),
            "source": ref.source,
        }

    def delete_reference_image(self, reference_id: str) -> bool:
        """Delete a single reference image."""
        try:
            ref = IdentityReference.get(IdentityReference.id == reference_id)
            file_path = os.path.join(self.ref_storage_dir, ref.image_path)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            identity_id = ref.identity_id
            ref.delete_instance()

            try:
                identity = CustomIdentity.get(CustomIdentity.id == identity_id)
                identity.reference_count = identity.references.count()
                identity.save()
            except Exception:
                pass

            self.invalidate_cache()
            return True
        except Exception as e:
            logger.error("Error deleting reference %s: %s", reference_id, e)
            return False

    def get_reference_image_path(self, ref_id: str) -> Optional[str]:
        """Get absolute path to a stored reference image."""
        try:
            ref = IdentityReference.get(IdentityReference.id == ref_id)
            full_path = os.path.join(self.ref_storage_dir, ref.image_path)
            if os.path.exists(full_path):
                return full_path
        except Exception:
            pass
        return None

    def get_track_snapshot_path(self, track_id: str) -> Optional[str]:
        """Get absolute path to a stored track snapshot."""
        # First check active/recent track states
        for track in list(self.tracker.active_tracks.values()) + list(self.tracker.recently_ended_tracks):
            if (track.id == track_id or track.display_id == track_id) and track.snapshot_path:
                full_path = os.path.join(self.snap_storage_dir, track.snapshot_path)
                if os.path.exists(full_path):
                    return full_path

        # Check DB sightings
        try:
            sighting = ObjectSightingRecord.select().where(
                (ObjectSightingRecord.track_id == track_id) & (ObjectSightingRecord.snapshot_path.is_null(False))
            ).order_by(ObjectSightingRecord.timestamp.desc()).first()
            if sighting and sighting.snapshot_path:
                full_path = os.path.join(self.snap_storage_dir, sighting.snapshot_path)
                if os.path.exists(full_path):
                    return full_path
        except Exception:
            pass
        return None

    def process_detection(
        self,
        camera: str,
        object_class: str,
        bbox: Optional[list[int]] = None,
        frame_crop_bgr: Optional[np.ndarray] = None,
        crop_bytes: Optional[bytes] = None,
        base_confidence: float = 0.85,
        raw_track_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Process a camera object crop:
        Crop -> Extract 192-D feature -> Match enrolled identities -> Spatial-temporal tracker update.
        """
        camera_location = self.get_camera_location(camera)

        # 1. Feature extraction
        embedding = None
        if frame_crop_bgr is not None:
            embedding = self.extractor.extract_from_image(frame_crop_bgr)
        elif crop_bytes is not None:
            embedding = self.extractor.extract_from_bytes(crop_bytes)

        # 2. Identity Matching
        enrolled = self.get_all_enrolled_identities()
        match_result = self.matcher.match(embedding, object_class, enrolled)

        # 3. Save snapshot crop if provided
        snapshot_filename = None
        if crop_bytes or frame_crop_bgr is not None:
            snap_id = str(uuid.uuid4())
            snapshot_filename = f"{camera}_{int(time.time())}_{snap_id}.jpg"
            snap_path = os.path.join(self.snap_storage_dir, snapshot_filename)
            try:
                if crop_bytes:
                    with open(snap_path, "wb") as f:
                        f.write(crop_bytes)
                elif frame_crop_bgr is not None:
                    cv2.imwrite(snap_path, frame_crop_bgr)
            except Exception as e:
                logger.error("Error saving track snapshot: %s", e)
                snapshot_filename = None

        # 4. Update cross-camera / single-camera track
        track_state, is_new_event = self.tracker.update_track(
            camera=camera,
            camera_location=camera_location,
            object_class=object_class,
            raw_track_id=raw_track_id,
            candidate_embedding=embedding,
            match_result=match_result,
            snapshot_path=snapshot_filename,
        )

        # 5. Persist sighting to SQLite
        now_dt = datetime.datetime.now()
        try:
            ObjectSightingRecord.create(
                id=str(uuid.uuid4()),
                track_id=track_state.display_id,
                identity_id=match_result.identity_id if match_result.matched else None,
                identity_name=match_result.identity_name,
                camera=camera,
                camera_location=camera_location,
                timestamp=now_dt,
                confidence=match_result.confidence,
                snapshot_path=snapshot_filename,
            )

            if match_result.matched and match_result.identity_id:
                identity = CustomIdentity.get(CustomIdentity.id == match_result.identity_id)
                if not identity.first_seen_time:
                    identity.first_seen_time = now_dt
                identity.last_seen_time = now_dt
                identity.last_seen_camera = camera
                identity.last_seen_location = camera_location
                identity.status = "present"
                identity.active_track_id = track_state.display_id
                identity.save()
                self.invalidate_cache()
        except Exception as e:
            logger.debug("Database error persisting sighting: %s", e)

        return {
            "track_id": track_state.id,
            "track_display_id": track_state.display_id,
            "is_known": match_result.matched,
            "identity_id": match_result.identity_id,
            "identity_name": match_result.identity_name,
            "identity_confidence": match_result.confidence,
            "object_class": object_class,
            "camera": camera,
            "area": camera_location,
            "is_new_event": is_new_event,
            "status": track_state.status,
            "snapshot_url": f"/api/identities/track-snapshot/{track_state.display_id}" if snapshot_filename else None,
        }

    def get_active_tracks(self) -> list[dict[str, Any]]:
        """Get currently active and present tracks across all cameras."""
        active = []
        now = time.time()
        for track in self.tracker.active_tracks.values():
            time_since_seen = int(now - track.last_seen)
            status = "present" if time_since_seen < 60 else "not_recently_seen"
            active.append({
                "track_id": track.id,
                "track_display_id": track.display_id,
                "camera": track.camera,
                "area": track.camera_location,
                "object_class": track.object_class,
                "is_known": not track.is_unknown,
                "identity_id": track.identity_id,
                "identity_name": track.identity_name,
                "confidence": track.confidence,
                "status": status,
                "first_seen": datetime.datetime.fromtimestamp(track.first_seen).isoformat(),
                "last_seen": datetime.datetime.fromtimestamp(track.last_seen).isoformat(),
                "seconds_ago": time_since_seen,
                "sighting_count": track.sighting_count,
                "snapshot_url": f"/api/identities/track-snapshot/{track.display_id}" if track.snapshot_path else None,
            })
        return active

    def get_unknown_queue(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get unknown objects / unrecognized people queue for review."""
        unknowns = []
        for track in list(self.tracker.active_tracks.values()) + list(self.tracker.recently_ended_tracks):
            if track.is_unknown and track.status != "dismissed":
                unknowns.append({
                    "track_id": track.id,
                    "track_display_id": track.display_id,
                    "camera": track.camera,
                    "area": track.camera_location,
                    "object_class": track.object_class,
                    "first_seen": datetime.datetime.fromtimestamp(track.first_seen).isoformat(),
                    "last_seen": datetime.datetime.fromtimestamp(track.last_seen).isoformat(),
                    "sighting_count": track.sighting_count,
                    "snapshot_url": f"/api/identities/track-snapshot/{track.display_id}" if track.snapshot_path else None,
                    "status": track.status,
                })

        seen = set()
        deduped = []
        for u in unknowns:
            if u["track_display_id"] not in seen:
                seen.add(u["track_display_id"])
                deduped.append(u)
                if len(deduped) >= limit:
                    break
        return deduped

    def enroll_unknown_as_new(
        self,
        track_id: str,
        name: str,
        category: Optional[str] = None,
        color: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Enroll an unknown track as a new custom identity and save its snapshot as a reference."""
        target_track = None
        for track in list(self.tracker.active_tracks.values()) + list(self.tracker.recently_ended_tracks):
            if track.id == track_id or track.display_id == track_id:
                target_track = track
                break

        if not target_track:
            return None

        # Create new identity
        identity = self.create_identity(
            name=name,
            object_class=target_track.object_class,
            category=category,
            color=color,
            notes=notes,
        )

        # Link snapshot if available
        if target_track.snapshot_path:
            snap_path = os.path.join(self.snap_storage_dir, target_track.snapshot_path)
            if os.path.exists(snap_path):
                with open(snap_path, "rb") as f:
                    img_bytes = f.read()
                self.add_reference_image(
                    identity_id=identity["id"],
                    image_bytes=img_bytes,
                    notes=f"Enrolled from {target_track.display_id}",
                    source="confirmed_event",
                )

        # Update track state
        target_track.identity_id = identity["id"]
        target_track.identity_name = identity["name"]
        target_track.is_unknown = False
        target_track.status = "confirmed"

        # Update historical sightings
        try:
            ObjectSightingRecord.update(
                identity_id=identity["id"],
                identity_name=identity["name"],
            ).where(ObjectSightingRecord.track_id == target_track.display_id).execute()
        except Exception:
            pass

        self.invalidate_cache()
        return self.get_identity(identity["id"])

    def link_unknown_to_existing(self, track_id: str, identity_id: str) -> Optional[dict[str, Any]]:
        """Link an unknown track to an existing identity with confirmed match learning."""
        target_track = None
        for track in list(self.tracker.active_tracks.values()) + list(self.tracker.recently_ended_tracks):
            if track.id == track_id or track.display_id == track_id:
                target_track = track
                break

        if not target_track:
            return None

        try:
            identity = CustomIdentity.get(CustomIdentity.id == identity_id)
            target_track.identity_id = identity.id
            target_track.identity_name = identity.name
            target_track.is_unknown = False
            target_track.status = "confirmed"

            if target_track.snapshot_path:
                snap_path = os.path.join(self.snap_storage_dir, target_track.snapshot_path)
                if os.path.exists(snap_path):
                    with open(snap_path, "rb") as f:
                        img_bytes = f.read()
                    self.add_reference_image(
                        identity_id=identity.id,
                        image_bytes=img_bytes,
                        notes=f"Confirmed match from {target_track.display_id}",
                        source="confirmed_event",
                    )

            ObjectSightingRecord.update(
                identity_id=identity.id,
                identity_name=identity.name,
            ).where(ObjectSightingRecord.track_id == target_track.display_id).execute()

            self.invalidate_cache()
            return self.get_identity(identity_id)
        except Exception as e:
            logger.error("Error linking track %s to identity %s: %s", track_id, identity_id, e)
            return None

    def dismiss_unknown_track(self, track_id: str) -> bool:
        """Dismiss an unknown track from review."""
        for track in list(self.tracker.active_tracks.values()) + list(self.tracker.recently_ended_tracks):
            if track.id == track_id or track.display_id == track_id:
                track.status = "dismissed"
                return True
        return False

    def get_sightings_history(
        self,
        identity_id: Optional[str] = None,
        camera: Optional[str] = None,
        area: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve sightings and journey log."""
        query = ObjectSightingRecord.select().order_by(ObjectSightingRecord.timestamp.desc())
        if identity_id:
            query = query.where(ObjectSightingRecord.identity_id == identity_id)
        if camera:
            query = query.where(ObjectSightingRecord.camera == camera)
        if area:
            query = query.where(ObjectSightingRecord.camera_location == area)

        results = []
        for s in query.limit(limit):
            results.append({
                "id": s.id,
                "track_id": s.track_id,
                "identity_id": s.identity_id,
                "identity_name": s.identity_name or s.track_id,
                "camera": s.camera,
                "area": s.camera_location,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "confidence": s.confidence,
                "snapshot_url": f"/api/identities/track-snapshot/{s.track_id}" if s.snapshot_path else None,
            })
        return results

    def get_camera_area_mappings(self) -> list[dict[str, Any]]:
        """List all camera to area mappings."""
        mappings = []
        try:
            for m in CameraAreaMapping.select():
                mappings.append({
                    "camera": m.camera,
                    "area": m.area_name,
                    "notes": m.notes or "",
                })
        except Exception as e:
            logger.error("Error loading camera area mappings: %s", e)
        return mappings

    def update_camera_area(self, camera: str, area: str, notes: str = "") -> dict[str, Any]:
        """Create or update a camera to area mapping."""
        mapping, created = CameraAreaMapping.get_or_create(
            camera=camera,
            defaults={"area_name": area.strip(), "notes": notes.strip()},
        )
        if not created:
            mapping.area_name = area.strip()
            mapping.notes = notes.strip()
            mapping.save()

        self.invalidate_cache()
        return {"camera": mapping.camera, "area": mapping.area_name, "notes": mapping.notes}

    def get_settings(self) -> dict[str, Any]:
        """Retrieve identity tracking configuration."""
        try:
            s = IdentitySettings.get_or_none(IdentitySettings.id == 1)
            if s:
                return {
                    "matching_threshold_object": s.matching_threshold_object,
                    "matching_threshold_person": s.matching_threshold_person,
                    "unknown_object_threshold": s.unknown_object_threshold,
                    "track_timeout_seconds": s.track_timeout_seconds,
                    "presence_timeout_seconds": s.presence_timeout_seconds,
                    "away_timeout_seconds": s.away_timeout_seconds,
                    "recognition_cooldown_seconds": s.recognition_cooldown_seconds,
                    "max_reference_images": s.max_reference_images,
                    "cross_camera_window_seconds": s.cross_camera_window_seconds,
                    "enable_cross_camera_tracking": s.enable_cross_camera_tracking,
                }
        except Exception:
            pass

        return {
            "matching_threshold_object": 0.70,
            "matching_threshold_person": 0.75,
            "unknown_object_threshold": 0.50,
            "track_timeout_seconds": 60,
            "presence_timeout_seconds": 180,
            "away_timeout_seconds": 900,
            "recognition_cooldown_seconds": 3,
            "max_reference_images": 15,
            "cross_camera_window_seconds": 90,
            "enable_cross_camera_tracking": True,
        }

    def update_settings(self, **kwargs) -> dict[str, Any]:
        """Update identity tracking configuration."""
        try:
            s, _ = IdentitySettings.get_or_create(id=1)
            for k, v in kwargs.items():
                if hasattr(s, k) and v is not None:
                    setattr(s, k, v)
            s.save()
        except Exception as e:
            logger.error("Error saving identity settings: %s", e)

        return self.get_settings()


_default_identity_manager: Optional[IdentityManager] = None


def get_identity_manager() -> IdentityManager:
    """Retrieve global singleton IdentityManager."""
    global _default_identity_manager
    if _default_identity_manager is None:
        _default_identity_manager = IdentityManager()
    return _default_identity_manager

