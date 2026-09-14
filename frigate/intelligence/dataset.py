"""Specialized Camera & NVR Domain Dataset for ANDRO-Vision Camera Intelligence Engine."""

from typing import Any

# Curated synthetic and structured camera event training and benchmark pairs
CAMERA_DOMAIN_DATASET: list[dict[str, Any]] = [
    {
        "id": "ds_entry_001",
        "category": "entry_exit",
        "scenario": "Person enters gate area",
        "input": {
            "camera": "front_cam",
            "area": "Gate & Driveway",
            "time": "14:22:10",
            "detections": ["person"],
            "known_identities": [],
            "unknown_objects": ["PERSON #001"],
            "recent_events": [],
        },
        "output": {
            "summary": "An unrecognized person has entered the Gate & Driveway area.",
            "objects": [{"type": "person", "identity": "Unknown Person", "confidence": 0.88}],
            "location": "Gate & Driveway",
            "activity": "entering",
            "importance": "HIGH",
            "multi_camera_journey": ["Gate & Driveway"],
        },
    },
    {
        "id": "ds_known_veh_002",
        "category": "known_vehicle",
        "scenario": "Registered vehicle arrives at gate",
        "input": {
            "camera": "front_cam",
            "area": "Gate & Driveway",
            "time": "15:42:00",
            "detections": ["car"],
            "known_identities": ["White Toyota Harrier"],
            "unknown_objects": [],
            "recent_events": [],
        },
        "output": {
            "summary": "The registered White Toyota Harrier has arrived at the Gate & Driveway.",
            "objects": [{"type": "car", "identity": "White Toyota Harrier", "confidence": 0.95}],
            "location": "Gate & Driveway",
            "activity": "arriving",
            "importance": "NORMAL",
            "multi_camera_journey": ["Gate & Driveway"],
        },
    },
    {
        "id": "ds_unknown_veh_003",
        "category": "unknown_vehicle",
        "scenario": "Unknown vehicle sighted",
        "input": {
            "camera": "front_cam",
            "area": "Gate & Driveway",
            "time": "16:15:30",
            "detections": ["car"],
            "known_identities": [],
            "unknown_objects": ["CAR #004"],
            "recent_events": [],
        },
        "output": {
            "summary": "An unknown vehicle has appeared at the Gate & Driveway.",
            "objects": [{"type": "car", "identity": "Unknown Vehicle", "confidence": 0.91}],
            "location": "Gate & Driveway",
            "activity": "stopping",
            "importance": "MEDIUM",
            "multi_camera_journey": ["Gate & Driveway"],
        },
    },
    {
        "id": "ds_known_person_004",
        "category": "known_person",
        "scenario": "Enrolled resident at front entrance",
        "input": {
            "camera": "entrance",
            "area": "Front Entrance",
            "time": "17:05:12",
            "detections": ["person"],
            "known_identities": ["John"],
            "unknown_objects": [],
            "recent_events": ["John sighted at Gate 2 minutes ago"],
        },
        "output": {
            "summary": "John is at the Front Entrance.",
            "objects": [{"type": "person", "identity": "John", "confidence": 0.96}],
            "location": "Front Entrance",
            "activity": "approaching_door",
            "importance": "NORMAL",
            "multi_camera_journey": ["Gate & Driveway", "Front Entrance"],
        },
    },
    {
        "id": "ds_multi_cam_005",
        "category": "multi_camera_transition",
        "scenario": "Vehicle progresses from Gate to Garage",
        "input": {
            "camera": "garage",
            "area": "Garage & Workshop",
            "time": "15:44:15",
            "detections": ["car"],
            "known_identities": ["White Toyota Harrier"],
            "unknown_objects": [],
            "recent_events": [
                "White Toyota Harrier detected at Gate & Driveway (15:42:00)",
                "White Toyota Harrier detected at Main Hallway (15:43:20)",
            ],
        },
        "output": {
            "summary": "The White Toyota Harrier moved from the Gate toward the Garage & Workshop.",
            "objects": [{"type": "car", "identity": "White Toyota Harrier", "confidence": 0.94}],
            "location": "Garage & Workshop",
            "activity": "parking",
            "importance": "NORMAL",
            "multi_camera_journey": ["Gate & Driveway", "Main Hallway", "Garage & Workshop"],
        },
    },
    {
        "id": "ds_package_006",
        "category": "package_delivery",
        "scenario": "Package delivered by delivery person",
        "input": {
            "camera": "entrance",
            "area": "Front Entrance",
            "time": "11:20:00",
            "detections": ["person", "package"],
            "known_identities": [],
            "unknown_objects": ["PERSON #012", "PACKAGE #001"],
            "recent_events": [],
        },
        "output": {
            "summary": "A package was delivered at the Front Entrance by an unrecognized person.",
            "objects": [
                {"type": "person", "identity": "Unknown Person", "confidence": 0.89},
                {"type": "package", "identity": "Package", "confidence": 0.93},
            ],
            "location": "Front Entrance",
            "activity": "package_delivered",
            "importance": "HIGH",
            "multi_camera_journey": ["Front Entrance"],
        },
    },
    {
        "id": "ds_night_anomaly_007",
        "category": "anomaly",
        "scenario": "Late night unknown movement in backyard",
        "input": {
            "camera": "back_cam",
            "area": "Veranda & Backyard",
            "time": "02:35:40",
            "detections": ["person"],
            "known_identities": [],
            "unknown_objects": ["PERSON #019"],
            "recent_events": [],
        },
        "output": {
            "summary": "Late night unknown person detected moving through the Veranda & Backyard.",
            "objects": [{"type": "person", "identity": "Unknown Person", "confidence": 0.87}],
            "location": "Veranda & Backyard",
            "activity": "loitering",
            "importance": "HIGH",
            "multi_camera_journey": ["Veranda & Backyard"],
        },
    },
    {
        "id": "ds_pet_008",
        "category": "animal",
        "scenario": "Enrolled pet in patio",
        "input": {
            "camera": "patio",
            "area": "Perimeter & Patio",
            "time": "08:15:00",
            "detections": ["dog"],
            "known_identities": ["Bruno"],
            "unknown_objects": [],
            "recent_events": [],
        },
        "output": {
            "summary": "Bruno the dog is active in the Perimeter & Patio.",
            "objects": [{"type": "dog", "identity": "Bruno", "confidence": 0.92}],
            "location": "Perimeter & Patio",
            "activity": "roaming",
            "importance": "LOW",
            "multi_camera_journey": ["Perimeter & Patio"],
        },
    },
]

# Curated Q&A benchmark examples verifying factual answers and hallucination prevention
CAMERA_QA_EXAMPLES: list[dict[str, Any]] = [
    {
        "question": "Where is the white Toyota?",
        "context": {
            "last_sighting": {
                "identity": "White Toyota Harrier",
                "camera": "garage",
                "area": "Garage & Workshop",
                "time": "15:44:15",
            }
        },
        "answer": "The White Toyota Harrier was last seen at the Garage & Workshop at 15:44:15.",
    },
    {
        "question": "Who is at the gate?",
        "context": {
            "active_tracks": [
                {"area": "Gate & Driveway", "identity": "John", "is_known": True}
            ]
        },
        "answer": "John is currently present at the Gate & Driveway.",
    },
    {
        "question": "Was there any unknown person detected today?",
        "context": {
            "unknown_sightings": [
                {"time": "14:22:10", "area": "Gate & Driveway", "track": "PERSON #001"}
            ]
        },
        "answer": "Yes, an unrecognized person (PERSON #001) was sighted at the Gate & Driveway at 14:22:10.",
    },
    {
        "question": "Where is the red motorcycle?",
        "context": {"sightings": []},
        "answer": "I don't have enough camera evidence to determine that. No red motorcycle has been recorded in current sightings.",
    },
]


def generate_synthetic_camera_events(count: int = 5) -> list[dict[str, Any]]:
    """Generate synthetic camera training samples from the domain pool."""
    samples = []
    for i in range(count):
        idx = i % len(CAMERA_DOMAIN_DATASET)
        sample = dict(CAMERA_DOMAIN_DATASET[idx])
        sample["generated_id"] = f"synthetic_{i+1:03d}"
        samples.append(sample)
    return samples

