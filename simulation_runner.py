import os
import csv
from simulation_engine import SimulationEngine
from simulation_recorder import SimulationRecorder
from simulation_record_summerizer import SimulationRecordSummarizer

class SimulationRunner:
    """
    주어진 폴더 내의 모든 .marzip 파일을 읽어 시뮬레이션을 실행하고,
    각 이벤트의 결과를 Recorder를 통해 CSV에 기록하며,
    CSV 파일에 이미 기록된 파일은 건너뜁니다.
    """
    def __init__(self, base_data_dir: str, output_path: str = None):
        self.base_data_dir = base_data_dir
        if output_path is None:
            self.output_path = base_data_dir
        else:
            self.output_path = output_path
        self.recorder = SimulationRecorder(self.output_path)

    def get_all_marzip_files(self) -> list:
        """기본 데이터 디렉토리 내의 모든 .marzip 파일 경로를 재귀적으로 수집합니다."""
        marzip_files = []
        for root, _, files in os.walk(self.base_data_dir):
            for file in files:
                if file.endswith('.marzip'):
                    marzip_files.append(os.path.join(root, file))
        return marzip_files

    def load_processed_files(self) -> set:
        """
        이미 CSV 파일에 기록된 파일 목록을 읽어, 처리한 파일의 집합을 반환합니다.
        CSV 파일의 첫 번째 열에 파일 경로가 기록되어 있다고 가정합니다.
        """
        processed = set()
        if os.path.exists(self.recorder.output_csv):
            with open(self.recorder.output_csv, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)  # 헤더 스킵
                for row in reader:
                    if row:
                        processed.add(row[0])
        return processed

    def run(self) -> None:
        marzip_files = self.get_all_marzip_files()
        total_files = len(marzip_files)
        print(f"Found {total_files} marzip file(s) in {self.base_data_dir}")
        
        processed_files = self.load_processed_files()
        processed = 0
        
        for marzip_file in marzip_files:
            if marzip_file in processed_files:
                print(f"Skipping already processed file: {marzip_file}")
                continue
            engine = SimulationEngine(marzip_file)
            # engine.events에 있는 각 이벤트에 대해 시뮬레이션 실행
            for i in range(len(engine.events)):
                sim_result = engine.simulate_event(i)
                self.recorder.record(marzip_file, sim_result)
            processed += 1
            print(f"Processed {processed} of {total_files} files.")
        print("Simulation completed. Results saved.")

        summarizer = SimulationRecordSummarizer(self.recorder.recorder.output_csv) 
        summarizer.run()

def main():
    base_data_dir = "/media/avikus/One Touch/HinasControlSilsCA/CA_v0.1.4_data/Random/20250226"
    output_path = "New/CA_v0.1.4_data/Random/20250226/"
    runner = SimulationRunner(base_data_dir, output_path)
    runner.run()
    

if __name__ == "__main__":
    main()
