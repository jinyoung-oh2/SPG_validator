import math
import matplotlib.pyplot as plt
from simulation_data import SimulationResult, ResultTag

class SimulationVisualizer:
    """
    시뮬레이션 결과를 플로팅하는 클래스.
    SimulationEngine에서 생성된 결과와 이벤트 데이터를 기반으로 시각화를 수행합니다.
    """
    PLOT_SKIP = 10

    def __init__(self, engine):
        """
        engine: SimulationEngine 인스턴스
        """
        self.engine = engine

    def set_axis_limits(self, ax):
        ax.set_xlim(-20, 20)
        ax.set_ylim(-20, 40)
        ax.set_aspect("equal")

    def plot_collision_event(self, sim_res: SimulationResult, out_file: str) -> None:
        idx = sim_res.event_index
        fig, ax = plt.subplots(figsize=(8, 6))

        # 기준 좌표 설정
        ref = (self.engine.base_route[0] if self.engine.base_route 
               else self.engine.events[0]["own_ship_event"])
        ref_lat, ref_lon = ref["position"]["latitude"], ref["position"]["longitude"]
        cos_factor = math.cos(math.radians(ref_lat))
        bx = [(pt["position"]["longitude"] - ref_lon) * 60 * cos_factor for pt in self.engine.base_route]
        by = [(pt["position"]["latitude"] - ref_lat) * 60 for pt in self.engine.base_route]
        if bx and by:
            ax.plot(bx, by, "ko-", label="Base Route")

        # safe_route 선택: 결과 태그에 따라 현재 이벤트 또는 이전 이벤트 사용
        if sim_res.result_tag not in (ResultTag.NA_NO_PATH, ResultTag.NA_COLLISION) or idx == 0:
            event = self.engine.events[idx]
        else:
            event = self.engine.events[idx - 1]
        sr = event.get("safe_route", [])
        if sr:
            sx = [(pt["position"]["longitude"] - ref_lon) * 60 * cos_factor for pt in sr]
            sy = [(pt["position"]["latitude"] - ref_lat) * 60 for pt in sr]
            ax.plot(sx, sy, "o--", color="darkorange", label="Safe Route")

        # Own Ship 경로 플로팅
        for i in range(0, len(sim_res.own_positions) - 1, self.PLOT_SKIP):
            x0, y0 = sim_res.own_positions[i]
            x1, y1 = sim_res.own_positions[min(i + self.PLOT_SKIP, len(sim_res.own_positions) - 1)]
            alpha = 0.2 + 0.8 * (i / (len(sim_res.own_positions) - 1))
            ax.plot([x0, x1], [y0, y1], color="red", alpha=alpha, lw=2)
        if sim_res.own_positions:
            ax.scatter(sim_res.own_positions[-1][0], sim_res.own_positions[-1][1],
                       marker="*", color="crimson", s=20, label="Own Ship")

        # Target Ship 경로 플로팅
        for t_idx, tpos in enumerate(sim_res.targets_positions):
            for i in range(0, len(tpos) - 1, self.PLOT_SKIP):
                x0, y0 = tpos[i]
                x1, y1 = tpos[min(i + self.PLOT_SKIP, len(tpos) - 1)]
                alpha = 0.2 + 0.8 * (i / (len(tpos) - 1))
                ax.plot([x0, x1], [y0, y1], color="blue", alpha=alpha, lw=1.5)
            if tpos:
                lbl = "Target Ship" if t_idx == 0 else None
                ax.scatter(tpos[-1][0], tpos[-1][1], marker="x", color="blue", s=15, label=lbl)

        # 충돌 지점 표시
        if sim_res.is_fail and sim_res.fail_time_sec in sim_res.times:
            fail_idx = sim_res.times.index(sim_res.fail_time_sec)
            cx, cy = sim_res.own_positions[fail_idx]
            ax.scatter(cx, cy, edgecolor="yellow", facecolor="red", s=20, marker="o", lw=2,
                       label="Collision Point", zorder=5)

        info = [
            f"Event {idx} - {sim_res.result_tag.value}",
            f"Fail={sim_res.is_fail}, fail_time={sim_res.fail_time_sec}",
            f"MinDist={sim_res.min_distance:.3f}NM @t={sim_res.min_distance_time}",
        ]
        ax.set_title(f"Event {idx} - {sim_res.result_tag.value}")
        ax.set_xlabel("Longitude Offset (NM)")
        ax.set_ylabel("Latitude Offset (NM)")
        self.set_axis_limits(ax)
        ax.grid(True)
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        fig.tight_layout()
        ax.text(0.02, 0.98, "\n".join(info), transform=ax.transAxes,
                va="top", ha="left", fontsize=9, bbox=dict(facecolor="white", alpha=0.7))
        fig.savefig(out_file)
        plt.close(fig)