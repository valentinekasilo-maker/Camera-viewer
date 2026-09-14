from peewee import (
    BlobField,
    BooleanField,
    CharField,
    CompositeKey,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
)
from playhouse.sqlite_ext import JSONField


class Event(Model):
    id = CharField(null=False, primary_key=True, max_length=30)
    label = CharField(index=True, max_length=20)
    sub_label = CharField(max_length=100, null=True)
    camera = CharField(index=True, max_length=20)
    start_time = DateTimeField()
    end_time = DateTimeField(null=True)
    top_score = (
        FloatField()
    )  # TODO remove when columns can be dropped without rebuilding table
    score = (
        FloatField()
    )  # TODO remove when columns can be dropped without rebuilding table
    false_positive = BooleanField()
    zones = JSONField()
    thumbnail = TextField()
    has_clip = BooleanField(default=True)
    has_snapshot = BooleanField(default=True)
    region = (
        JSONField()
    )  # TODO remove when columns can be dropped without rebuilding table
    box = (
        JSONField()
    )  # TODO remove when columns can be dropped without rebuilding table
    area = (
        IntegerField()
    )  # TODO remove when columns can be dropped without rebuilding table
    retain_indefinitely = BooleanField(default=False)
    ratio = FloatField(
        default=1.0
    )  # TODO remove when columns can be dropped without rebuilding table
    plus_id = CharField(max_length=30)
    model_hash = CharField(max_length=32)
    detector_type = CharField(max_length=32)
    model_type = CharField(max_length=32)
    data = JSONField()  # ex: tracked object box, region, etc.


class Timeline(Model):
    timestamp = DateTimeField()
    camera = CharField(index=True, max_length=20)
    source = CharField(index=True, max_length=20)  # ex: tracked object, audio, external
    source_id = CharField(index=True, max_length=30)
    class_type = CharField(max_length=50)  # ex: entered_zone, audio_heard
    data = JSONField()  # ex: tracked object id, region, box, etc.


class Regions(Model):
    camera = CharField(null=False, primary_key=True, max_length=20)
    grid = JSONField()  # json blob of grid
    last_update = DateTimeField()


class Recordings(Model):
    id = CharField(null=False, primary_key=True, max_length=30)
    camera = CharField(index=True, max_length=20)
    path = CharField(unique=True)
    start_time = DateTimeField()
    end_time = DateTimeField()
    duration = FloatField()
    motion = IntegerField(null=True)
    objects = IntegerField(null=True)
    dBFS = IntegerField(null=True)
    segment_size = FloatField(default=0)  # this should be stored as MB
    regions = IntegerField(null=True)
    motion_heatmap = JSONField(null=True)  # 16x16 grid, 256 values (0-255)
    keyframes = JSONField(null=True)  # ms offsets; NULL = unprobed (legacy rows)
    stream_type = CharField(default="main", max_length=8)
    has_audio = BooleanField(null=True)  # NULL = unknown (legacy rows)
    audio_rate = IntegerField(null=True)  # Hz; NULL = unknown (legacy rows)
    audio_codec = CharField(null=True, max_length=20)  # NULL = unknown (legacy rows)
    video_codec = CharField(null=True, max_length=20)  # NULL = unknown (legacy rows)


class ExportCase(Model):
    id = CharField(null=False, primary_key=True, max_length=30)
    name = CharField(index=True, max_length=100)
    description = TextField(null=True)
    created_at = DateTimeField()
    updated_at = DateTimeField()


class Export(Model):
    id = CharField(null=False, primary_key=True, max_length=30)
    camera = CharField(index=True, max_length=20)
    name = CharField(index=True, max_length=100)
    date = DateTimeField()
    video_path = CharField(unique=True)
    thumb_path = CharField(unique=True)
    in_progress = BooleanField()
    export_case = ForeignKeyField(
        ExportCase,
        null=True,
        backref="exports",
        column_name="export_case_id",
    )


class ReviewSegment(Model):
    id = CharField(null=False, primary_key=True, max_length=30)
    camera = CharField(index=True, max_length=20)
    start_time = DateTimeField()
    end_time = DateTimeField()
    severity = CharField(max_length=30)  # alert, detection
    thumb_path = CharField(unique=True)
    data = JSONField()  # additional data about detection like list of labels, zone, areas of significant motion


class UserReviewStatus(Model):
    user_id = CharField(max_length=30)
    review_segment = ForeignKeyField(ReviewSegment, backref="user_reviews")
    has_been_reviewed = BooleanField(default=False)

    class Meta:
        indexes = ((("user_id", "review_segment"), True),)


class Previews(Model):
    id = CharField(null=False, primary_key=True, max_length=30)
    camera = CharField(index=True, max_length=20)
    path = CharField(unique=True)
    start_time = DateTimeField()
    end_time = DateTimeField()
    duration = FloatField()


# Used for temporary table in record/cleanup.py
class RecordingsToDelete(Model):
    id = CharField(null=False, primary_key=False, max_length=30)

    class Meta:
        temporary = True


class User(Model):
    username = CharField(null=False, primary_key=True, max_length=30)
    role = CharField(
        max_length=20,
        default="admin",
    )
    password_hash = CharField(null=False, max_length=120)
    password_changed_at = DateTimeField(null=True)
    notification_tokens = JSONField()

    @classmethod
    def get_allowed_cameras(
        cls, role: str, roles_dict: dict[str, list[str]], all_camera_names: set[str]
    ) -> list[str]:
        if role not in roles_dict:
            return []  # Invalid role grants no access
        allowed = roles_dict[role]
        if not allowed:  # Empty list means all cameras
            return list(all_camera_names)

        return [cam for cam in allowed if cam in all_camera_names]


class Trigger(Model):
    camera = CharField(max_length=20)
    name = CharField()
    type = CharField(max_length=10)
    data = TextField()
    threshold = FloatField()
    model = CharField(max_length=30)
    embedding = BlobField()
    triggering_event_id = CharField(max_length=30)
    last_triggered = DateTimeField()

    class Meta:
        primary_key = CompositeKey("camera", "name")


class Notice(Model):
    id = CharField(null=False, primary_key=True, max_length=150)
    kind = CharField(index=True, max_length=50)
    scope = CharField(max_length=100, null=True)
    params = JSONField()
    first_seen = DateTimeField()
    last_seen = DateTimeField()
    count = IntegerField(default=1)
    dismissed_at = DateTimeField(null=True)


class NoticeStats(Model):
    kind = CharField(null=False, primary_key=True, max_length=50)
    occurrences = IntegerField(default=0)
    dismissals = IntegerField(default=0)
    first_seen = DateTimeField()
    last_seen = DateTimeField()
    # watermarks for a future analytics reporter; unused until then
    reported_occurrences = IntegerField(default=0)
    reported_dismissals = IntegerField(default=0)


class CustomIdentity(Model):
    id = CharField(null=False, primary_key=True, max_length=36)
    name = CharField(index=True, max_length=100)
    category = CharField(index=True, max_length=50)  # vehicle, person, animal, package, item, other
    object_class = CharField(index=True, max_length=50)  # car, person, motorcycle, bicycle, dog, cat, package, etc.
    color = CharField(max_length=50, null=True)
    description = TextField(null=True)
    notes = TextField(null=True)
    is_person = BooleanField(default=False)
    status = CharField(max_length=30, default="not_recently_seen")  # present, not_recently_seen, away
    last_seen_camera = CharField(max_length=50, null=True)
    last_seen_location = CharField(max_length=100, null=True)
    last_seen_time = DateTimeField(null=True)
    first_seen_time = DateTimeField(null=True)
    active_track_id = CharField(max_length=50, null=True)
    created_at = DateTimeField()
    updated_at = DateTimeField()
    reference_count = IntegerField(default=0)


class IdentityReference(Model):
    id = CharField(null=False, primary_key=True, max_length=36)
    identity = ForeignKeyField(CustomIdentity, backref="references", on_delete="CASCADE")
    image_path = CharField(max_length=255)
    embedding_json = TextField(null=True)
    created_at = DateTimeField()
    source = CharField(max_length=50, default="upload")  # upload, confirmed_event, manual_crop


class ObjectTrackRecord(Model):
    id = CharField(null=False, primary_key=True, max_length=60)
    track_id = CharField(index=True, max_length=50)  # e.g. CAR #001, PERSON #002
    camera = CharField(index=True, max_length=50)
    camera_location = CharField(max_length=100, null=True)
    object_class = CharField(index=True, max_length=50)
    identity_id = CharField(max_length=36, null=True, index=True)
    identity_name = CharField(max_length=100, null=True)
    confidence = FloatField(default=0.0)
    first_seen = DateTimeField()
    last_seen = DateTimeField()
    status = CharField(max_length=30, default="active")  # active, ended, reviewed, ignored
    snapshot_path = CharField(max_length=255, null=True)
    embedding_json = TextField(null=True)
    sighting_count = IntegerField(default=1)
    is_unknown = BooleanField(default=True)


class ObjectSightingRecord(Model):
    id = CharField(null=False, primary_key=True, max_length=60)
    track_id = CharField(index=True, max_length=50, null=True)
    identity_id = CharField(max_length=36, null=True, index=True)
    identity_name = CharField(max_length=100, null=True)
    camera = CharField(index=True, max_length=50)
    camera_location = CharField(max_length=100, null=True)
    timestamp = DateTimeField(index=True)
    confidence = FloatField(default=0.0)
    snapshot_path = CharField(max_length=255, null=True)
    details = JSONField(null=True)


class CameraAreaMapping(Model):
    camera = CharField(null=False, primary_key=True, max_length=50)
    area_name = CharField(max_length=100)
    notes = CharField(max_length=255, null=True)


class IdentitySettings(Model):
    key = CharField(null=False, primary_key=True, max_length=50)
    value = TextField()


class CameraSemanticMeta(Model):
    camera = CharField(null=False, primary_key=True, max_length=50)
    name = CharField(max_length=100)
    location = CharField(max_length=100)
    description = TextField(null=True)
    visible_areas = JSONField(null=True)
    important_objects = JSONField(null=True)
    expected_vehicles = IntegerField(default=0)
    important_zones = JSONField(null=True)
    privacy_masks = JSONField(null=True)
    special_rules = JSONField(null=True)
    environmental_motion_notes = TextField(null=True)
    updated_at = DateTimeField()


class EventRecord(Model):
    id = CharField(null=False, primary_key=True, max_length=60)
    camera = CharField(index=True, max_length=50)
    location = CharField(max_length=100, null=True)
    event_type = CharField(index=True, max_length=50)
    timestamp = DateTimeField(index=True)
    tracking_id = CharField(max_length=50, null=True)
    identity_name = CharField(max_length=100, null=True)
    confidence = FloatField(default=0.0)
    evidence_snapshot = CharField(max_length=255, null=True)
    metadata = JSONField(null=True)


