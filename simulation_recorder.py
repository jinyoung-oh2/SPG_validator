import os
import csv
from simulation_data import SimulationResult

class SimulationRecorder:
    """
    SimulationResult 객체들을 CSV 파일에 기록하는 클래스입니다.
    """
    def __init__(self, output_path: str):
        # 출력 경로가 없으면 생성합니다.
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        self.output_csv = os.path.join(output_path, "SPG_result.csv")
        # CSV 파일이 없을 때만 헤더를 기록합니다.
        if not os.path.exists(self.output_csv):
            self.init_csv()

    def init_csv(self) -> None:
        """CSV 파일이 없으면 헤더를 기록합니다."""
        with open(self.output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "file",
                "event_index",
                "result_tag",
                "min_distance",
                "fail_time_sec"
            ])

    def record(self, file: str, sim_result: SimulationResult) -> None:
        """하나의 SimulationResult를 CSV 파일에 기록합니다."""
        with open(self.output_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                file,
                sim_result.event_index,
                sim_result.result_tag.value if sim_result.result_tag else "",
                sim_result.min_distance,
                sim_result.fail_time_sec
            ])
