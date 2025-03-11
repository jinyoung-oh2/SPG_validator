# simulation_engine.py
import math
from typing import List
from simulation_data import SimulationResult, ResultTag
from geo_route_calculator import GeoRouteCalculator
from marzip_extractor import MarzipExtractor

class SimulationEngine:
    """
    시뮬레이션 로직 클래스.
    MarzipExtractor에 의존하지 않고, 외부에서 로드한 시뮬레이션 데이터를 받아 각 이벤트에 대해 SimulationResult를 반환합니다.
    충돌 거리, 시뮬레이션 시간, 시간 간격은 생성자 옵션으로 전달받습니다.
    """
    def __init__(self, marzip: dict, 
                 collision_dist: float = 0.5 + (250 / 1852),
                 sim_duration_sec: int = 5 * 60 * 60,  # 5시간
                 time_step_sec: int = 5):             # 5초 간격
        # 옵션들을 인스턴스 변수로 저장
        self.collision_dist = collision_dist
        self.sim_duration_sec = sim_duration_sec
        self.time_step_sec = time_step_sec

        extracted_marzip = MarzipExtractor.load_marzip(marzip)
        self.events = extracted_marzip.get("events", [])
        self.base_route = extracted_marzip.get("base_route", [])
        self.hinas_setup = extracted_marzip.get("hinas_setup", {})


    def simulate_event(self, event_index: int) -> SimulationResult:
        """
        safe_route가 존재하면 해당 경로를 사용하여 이벤트를 시뮬레이션합니다.
        그렇지 않으면 이전 이벤트의 safe_route를 참조하거나 경로가 없음을 반환합니다.
        """
        res = SimulationResult(event_index=event_index)
        if not self.events or event_index < 0 or event_index >= len(self.events):
            res.has_path = False
            res.result_tag = ResultTag.NA_NO_PATH
            return res

        event = self.events[event_index]
        if not event.get("own_ship_event"):
            res.has_path = False
            res.result_tag = ResultTag.NA_NO_PATH
            return res

        safe_route = event.get("safe_route")
        if not safe_route:
            if event_index == 0:
                res.has_path = False
                res.result_tag = ResultTag.NA_NO_PATH
                return res
            prev_safe = self.events[event_index - 1].get("safe_route", [])
            if not prev_safe:
                res.has_path = False
                res.result_tag = ResultTag.NA_NO_PATH
                return res
            sub_res = self._simulate_event_with_safe_route(event_index, prev_safe)
            sub_res.result_tag = ResultTag.NA_COLLISION if sub_res.is_fail else ResultTag.NA_NO_PATH
            return sub_res

        return self._simulate_event_with_safe_route(event_index, safe_route)

    def _prepare_routes(self, own_ev: dict, safe_route: List[dict]) -> dict:
        """
        safe_route와 base_route를 이용해 좌표 변환 및 누적 거리 계산을 수행합니다.
        반환값에는 기준 좌표(ref_lat, ref_lon), cos_factor, safe_route 좌표(safe_x, safe_y),
        총 safe_route 길이(total_safe_dist), base_route 좌표(base_x, base_y), base_route 총 길이(base_total_dist),
        그리고 시작점의 safe_route 상 누적 거리(proj_dist)가 포함됩니다.
        """
        start_lat = own_ev["position"]["latitude"]
        start_lon = own_ev["position"]["longitude"]
        if self.base_route:
            ref_lat = self.base_route[0]["position"]["latitude"]
            ref_lon = self.base_route[0]["position"]["longitude"]
        else:
            ref_lat, ref_lon = start_lat, start_lon
        cos_factor = math.cos(math.radians(ref_lat))
        start_x = (start_lon - ref_lon) * 60 * cos_factor
        start_y = (start_lat - ref_lat) * 60

        safe_x = [(pt["position"]["longitude"] - ref_lon) * 60 * cos_factor for pt in safe_route]
        safe_y = [(pt["position"]["latitude"] - ref_lat) * 60 for pt in safe_route]
        base_x = ([(pt["position"]["longitude"] - ref_lon) * 60 * cos_factor for pt in self.base_route]
                  if self.base_route else [])
        base_y = ([(pt["position"]["latitude"] - ref_lat) * 60 for pt in self.base_route]
                  if self.base_route else [])

        total_safe_dist = sum(math.hypot(safe_x[i + 1] - safe_x[i], safe_y[i + 1] - safe_y[i])
                              for i in range(len(safe_x) - 1))
        base_total_dist = (sum(math.hypot(base_x[i + 1] - base_x[i], base_y[i + 1] - base_y[i])
                               for i in range(len(base_x) - 1))
                           if base_x else 0.0)
        proj_dist = (GeoRouteCalculator.project_point_onto_polyline(start_x, start_y, safe_x, safe_y)
                     if len(safe_x) > 1 else 0.0)
        
        return {
            "ref_lat": ref_lat,
            "ref_lon": ref_lon,
            "cos_factor": cos_factor,
            "safe_x": safe_x,
            "safe_y": safe_y,
            "total_safe_dist": total_safe_dist,
            "base_x": base_x,
            "base_y": base_y,
            "base_total_dist": base_total_dist,
            "proj_dist": proj_dist,
        }

    def _prepare_target_info(self, event: dict, ref_lat: float, ref_lon: float, cos_factor: float) -> list:
        """
        이벤트 내 타겟 선박 정보를 변환하여, 각 선박의 초기 좌표와 속도/방향 정보를 튜플 목록으로 반환합니다.
        반환 형식: (tx0, ty0, sog, arad)
        """
        tgt_info = []
        for t in event.get("target_ships", []):
            if not t.get("position"):
                continue
            la = t["position"]["latitude"]
            lo = t["position"]["longitude"]
            try:
                sog = float(t.get("sog", 0))
                cog = float(t.get("cog", 0))
            except Exception:
                sog, cog = 0.0, 0.0
            tx0 = (lo - ref_lon) * 60 * cos_factor
            ty0 = (la - ref_lat) * 60
            tgt_info.append((tx0, ty0, sog, math.radians(cog)))
        return tgt_info

    def _simulate_dynamics(self, own_sog: float, route_data: dict, tgt_info: list) -> SimulationResult:
        """
        실제 선박의 이동(다이나믹스) 계산을 수행합니다.
        주어진 own_sog, 준비된 route_data와 타겟 정보(tgt_info)를 사용해, 
        시뮬레이션 루프를 돌며 own_ship의 경로와 타겟 선박 경로를 계산하고, 충돌 여부를 판단합니다.
        """
        res = SimulationResult()
        safe_x = route_data["safe_x"]
        safe_y = route_data["safe_y"]
        total_safe_dist = route_data["total_safe_dist"]
        base_x = route_data["base_x"]
        base_y = route_data["base_y"]
        base_total_dist = route_data["base_total_dist"]
        proj_dist = route_data["proj_dist"]

        safe_path_reached_time = None

        for sec in range(0, self.sim_duration_sec + 1, self.time_step_sec):
            res.times.append(sec)
            traveled = own_sog * (sec / 3600.0)
            desired_dist = proj_dist + traveled

            if desired_dist <= total_safe_dist:
                ox, oy = GeoRouteCalculator.interpolate_along_route(safe_x, safe_y, desired_dist)
            else:
                sx_end, sy_end = safe_x[-1], safe_y[-1]
                if safe_path_reached_time is None:
                    safe_path_reached_time = sec
                if sec - safe_path_reached_time >= self.hinas_setup.get("TCPA_GW", 60) * 60:
                    ox, oy = sx_end, sy_end
                    res.own_positions.append((ox, oy))
                    res.times.append(sec)
                    break
                remain = desired_dist - total_safe_dist
                if base_total_dist:
                    base_st = GeoRouteCalculator.project_point_onto_polyline(sx_end, sy_end, base_x, base_y)
                    base_des = base_st + remain
                    if base_des >= base_total_dist:
                        ox, oy = base_x[-1], base_y[-1]
                        res.own_positions.append((ox, oy))
                        res.times.append(sec)
                        break
                    else:
                        ox, oy = GeoRouteCalculator.interpolate_along_route(base_x, base_y, base_des)
                else:
                    ox, oy = sx_end, sy_end

            res.own_positions.append((ox, oy))
            # 타겟 선박 이동 및 충돌 검사
            for idx, (tx0, ty0, sog_t, arad) in enumerate(tgt_info):
                dt = sog_t * (sec / 3600.0)
                tx_ = tx0 + dt * math.sin(arad)
                ty_ = ty0 + dt * math.cos(arad)
                if idx >= len(res.targets_positions):
                    res.targets_positions.append([])
                res.targets_positions[idx].append((tx_, ty_))
                dd = math.hypot(ox - tx_, oy - ty_)
                current_min = res.min_distance if res.min_distance is not None else float('inf')
                if dd < current_min:
                    res.min_distance = dd
                    res.min_distance_time = sec
                    res.min_distance = dd
                    res.min_distance_time = sec
                if dd < self.collision_dist and not res.is_fail:
                    res.is_fail = True
                    res.fail_time_sec = sec
        return res

    def _simulate_event_with_safe_route(self, event_index: int, safe_route: List[dict]) -> SimulationResult:
        """
        안전 경로(safe_route)를 사용해 하나의 이벤트에 대한 시뮬레이션을 수행합니다.
        경로 관련 계산과 다이나믹스 계산을 분리하여 처리합니다.
        """
        res = SimulationResult(event_index=event_index)
        if not self.events or event_index < 0 or event_index >= len(self.events):
            res.has_path = False
            return res

        event = self.events[event_index]
        own_ev = event.get("own_ship_event")
        if not own_ev:
            res.has_path = False
            return res

        try:
            own_sog = float(own_ev.get("sog", 0))
        except Exception:
            own_sog = 0.0

        # 경로 계산 및 타겟 정보 준비 (분리된 처리)
        route_data = self._prepare_routes(own_ev, safe_route)
        tgt_info = self._prepare_target_info(event, route_data["ref_lat"], route_data["ref_lon"], route_data["cos_factor"])

        # 다이나믹스(선박 이동, 충돌 검사) 계산
        dynamics_result = self._simulate_dynamics(own_sog, route_data, tgt_info)
        dynamics_result.event_index = event_index
        dynamics_result.result_tag = ResultTag.COLLISION if dynamics_result.is_fail else ResultTag.NO_COLLISION
        return dynamics_result

    def simulate_event(self, event_index: int) -> SimulationResult:
        """
        safe_route가 존재하면 해당 경로를 사용하여 이벤트를 시뮬레이션합니다.
        그렇지 않으면 이전 이벤트의 safe_route를 참조하거나 경로가 없음을 반환합니다.
        """
        res = SimulationResult(event_index=event_index)
        if not self.events or event_index < 0 or event_index >= len(self.events):
            res.has_path = False
            res.result_tag = ResultTag.NA_NO_PATH
            return res

        event = self.events[event_index]
        if not event.get("own_ship_event"):
            res.has_path = False
            res.result_tag = ResultTag.NA_NO_PATH
            return res

        safe_route = event.get("safe_route")
        if not safe_route:
            if event_index == 0:
                res.has_path = False
                res.result_tag = ResultTag.NA_NO_PATH
                return res
            prev_safe = self.events[event_index - 1].get("safe_route", [])
            if not prev_safe:
                res.has_path = False
                res.result_tag = ResultTag.NA_NO_PATH
                return res
            sub_res = self._simulate_event_with_safe_route(event_index, prev_safe)
            sub_res.result_tag = ResultTag.NA_COLLISION if sub_res.is_fail else ResultTag.NA_NO_PATH
            return sub_res

        return self._simulate_event_with_safe_route(event_index, safe_route)
