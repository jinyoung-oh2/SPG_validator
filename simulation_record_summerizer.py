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
        각 파일별로 result_tag의 발생 횟수를 계산합니다.
        :return: 파일을 인덱스로 하고, 각 result_tag별 발생 횟수를 컬럼으로 하는 피벗 테이블 형태의 DataFrame
        """
        file_summary = self.df.groupby(['file', 'result_tag']).size().unstack(fill_value=0)
        return file_summary

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
