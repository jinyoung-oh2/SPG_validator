# simulation_data.py
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional

class ResultTag(Enum):
    NA_NO_PATH = "NA - No Path"
    NA_COLLISION = "NA Collision"
    NA_SAFE_TARGET = "NA - Safe Target"
    COLLISION = "Collision"
    NO_COLLISION = "No Collision"

@dataclass
class SimulationResult:
    event_index: int = 0
    has_path: bool = True
    is_fail: bool = False
    fail_time_sec: Optional[int] = None
    min_distance: Optional[float] = None
    min_distance_time: int = 0
    times: List[int] = field(default_factory=list)
    own_positions: List[Tuple[float, float]] = field(default_factory=list)
    targets_positions: List[List[Tuple[float, float]]] = field(default_factory=list)
    result_tag: Optional[ResultTag] = None