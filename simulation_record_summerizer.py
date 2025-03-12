import os
import pandas as pd

class SimulationRecordSummarizer:
    def __init__(self, csv_path: str, output_dir: str = None):
        """
        :param csv_path: SPG_result.csv 파일 경로
        :param output_dir: 요약 결과를 저장할 폴더 경로. 지정하지 않으면 csv_path의 디렉토리를 사용합니다.
        """
        self.csv_path = csv_path
        if output_dir is None:
            self.output_dir = os.path.dirname(csv_path)
        else:
            self.output_dir = output_dir

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        # 출력 폴더가 없으면 생성합니다.
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.df = pd.read_csv(self.csv_path)

    def summarize_by_event(self) -> pd.DataFrame:
        """
        전체 이벤트에 대해 result_tag별 발생 횟수를 계산합니다.
        :return: result_tag와 해당 이벤트 수를 담은 DataFrame
        """
        # result_tag 열의 값별로 카운트
        event_summary = self.df['result_tag'].value_counts().reset_index()
        event_summary.columns = ['result_tag', 'count']
        return event_summary

    def summarize_by_file(self) -> pd.DataFrame:
        """
        각 파일별로 result_tag의 발생에 따라 최종 결과를 결정합니다.
        동일 파일은 하나로 취급하며, 결과 결정 규칙은 다음과 같습니다:
            - 모든 result_tag가 "No Collision"인 경우: Pass
            - 하나라도 "NA" (예: "NA - No Path")가 포함된 경우: NA
            - 하나라도 정확히 "Collision"이 있는 경우: Fail
            (단, "NA - Collision"은 NA로 취급)
        :return: 파일과 최종 결과를 담은 DataFrame
        """
        def determine_final(tags):
            tags = list(tags)
            # 먼저, 정확히 "Collision"이 있는 경우 Fail로 처리합니다.
            if any(tag == "Collision" for tag in tags):
                return "Fail"
            # 그 다음, "NA"로 시작하는 태그가 하나라도 있으면 NA 처리합니다.
            elif any(tag.startswith("NA") for tag in tags):
                return "NA"
            # 모든 태그가 "No Collision"인 경우 Pass 처리합니다.
            elif all(tag == "No Collision" for tag in tags):
                return "Pass"
            else:
                return "Unknown"
            
        # 파일별로 그룹화하여 최종 평가를 구합니다.
        file_classification = self.df.groupby("file")["result_tag"].apply(determine_final)
        # 최종 평가별 파일 수를 집계합니다.
        total_summary = file_classification.value_counts().reset_index()
        total_summary.columns = ["final_result", "count"]
        return total_summary
    
    def run(self) -> None:
        event_summary = self.summarize_by_event()
        print("=== Event-level Summary ===")
        print(event_summary)

        file_summary = self.summarize_by_file()
        print("\n=== File-level Summary ===")
        print(file_summary)

        # 저장 경로를 output_dir에 맞춰 생성
        event_csv_path = os.path.join(self.output_dir, "event_summary.csv")
        file_csv_path = os.path.join(self.output_dir, "file_summary.csv")

        event_summary.to_csv(event_csv_path, index=False, encoding="utf-8")
        file_summary.to_csv(file_csv_path, encoding="utf-8")
        print(f"\nSummary files saved to:\n  {event_csv_path}\n  {file_csv_path}")

if __name__ == "__main__":
    csv_path = "New/CA_v0.1.4_data/Random/20250226/SPG_result.csv"
    summarizer = SimulationRecordSummarizer(csv_path)
    summarizer.run()
