# geo_route_calculator.py
import math
from typing import List, Tuple

class GeoRouteCalculator:
    @staticmethod
    def interpolate_along_route(xs: List[float], ys: List[float], desired_dist: float) -> Tuple[float, float]:
        """누적 거리를 계산하여 desired_dist에 해당하는 좌표를 보간합니다."""
        if len(xs) < 2:
            return xs[0], ys[0]
        cumdist = [0.0]
        for i in range(1, len(xs)):
            seg_len = math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1])
            cumdist.append(cumdist[-1] + seg_len)
        if desired_dist >= cumdist[-1]:
            return xs[-1], ys[-1]
        for i in range(1, len(cumdist)):
            if cumdist[i] >= desired_dist:
                ratio = (desired_dist - cumdist[i - 1]) / (cumdist[i] - cumdist[i - 1])
                return xs[i - 1] + ratio * (xs[i] - xs[i - 1]), ys[i - 1] + ratio * (ys[i] - ys[i - 1])
        return xs[-1], ys[-1]

    @staticmethod
    def project_point_onto_polyline(px: float, py: float, xs: List[float], ys: List[float]) -> float:
        """주어진 점(px,py)가 폴리라인 상에서 가장 가까운 누적 거리 위치를 반환합니다."""
        best_dist_along = 0.0
        best_distance = float('inf')
        cumdist = [0.0]
        for i in range(1, len(xs)):
            dx, dy = xs[i] - xs[i - 1], ys[i] - ys[i - 1]
            seg_len = math.hypot(dx, dy)
            cumdist.append(cumdist[-1] + seg_len)
            if seg_len == 0:
                continue
            t = max(0, min(1, ((px - xs[i - 1]) * dx + (py - ys[i - 1]) * dy) / (seg_len ** 2)))
            proj_x = xs[i - 1] + t * dx
            proj_y = ys[i - 1] + t * dy
            dist = math.hypot(px - proj_x, py - proj_y)
            if dist < best_distance:
                best_distance = dist
                best_dist_along = cumdist[i - 1] + t * seg_len
        return best_dist_along
