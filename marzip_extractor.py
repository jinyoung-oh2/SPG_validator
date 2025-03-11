#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
marzip_extractor.py
"""

import zipfile
import pyarrow as pa
import pyarrow.ipc as ipc
import json
from colorama import Fore, Style

class MarzipExtractor:
    def __init__(self):
        pass

    @classmethod
    def load_marzip(cls, file_path: str) -> dict:
        """단일 marzip 파일을 로드하여 데이터를 반환합니다."""
        try:
            return cls._extract(file_path)
        except Exception as e:
            print(f"Error loading marzip file {file_path}: {e}")
            return None

    @classmethod
    def _extract(cls, file_path: str) -> dict:
        """
        .marzip 파일에서 데이터를 읽어 필수 정보를 추출한 후,
        결과를 딕셔너리로 반환합니다.
        """
        data = cls._extract_and_read_marzip(file_path)
        static_dataset = data.get("static_dataset", [])
        own_ship_time_series = data.get("own_ship_time_series", [])
        target_ship_time_series = data.get("target_ship_time_series", {})
        simulation_result = data.get("simulation_result", {})

        if not simulation_result:
            print("simulation_result가 비어있습니다. 기본 경로 및 이벤트 추출을 건너뜁니다.")

        if simulation_result:
            base_route, hinas_setup, own_ship_static, events = cls._extract_simulation_data(simulation_result)
        else:
            base_route, hinas_setup, own_ship_static, events = ([], {}, {}, [])

        return {
            "static_dataset": static_dataset,
            "own_ship_time_series": own_ship_time_series,
            "target_ship_time_series": target_ship_time_series,
            "simulation_result": simulation_result,
            "base_route": base_route,
            "events": events,
            "hinas_setup": hinas_setup,
            "own_ship_static": own_ship_static,
        }

    @classmethod
    def safe_get(cls, data, keys, default=None):
        """
        중첩 딕셔너리에서 keys 순서대로 값을 안전하게 가져옵니다.
        """
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, default)
                if data == default:
                    return default
            else:
                return default
        return data

    @classmethod
    def _extract_simulation_data(cls, data: dict):
        """
        simulation_result 내부에서 필요한 정보들을 추출합니다.
        """
        try:
            base_route = cls.safe_get(data, ["trafficSituation", "ownShip", "waypoints"], default=[])
            hinas_setup = cls.safe_get(data, ["cagaData", "caga_configuration", "hinas_setup"], default={})
        except Exception as e:
            print(f"base_route 또는 hinas_setup 추출 실패: {e}")
            base_route, hinas_setup = [], {}

        try:
            own_ship_static = cls.safe_get(data, ["trafficSituation", "ownShip", "static"], default={})
        except Exception as e:
            print(f"own_ship_static 추출 실패: {e}")
            own_ship_static = {}

        try:
            events = cls._extract_events_info(data)
        except Exception as e:
            print(f"events 추출 실패: {e}")
            events = []

        return base_route, hinas_setup, own_ship_static, events

    @classmethod
    def _extract_events_info(cls, data: dict):
        """
        cagaData → eventData에서 이벤트들을 추출합니다.
        target_ships는 원본 그대로 유지합니다.
        """
        events = []
        event_data = cls.safe_get(data, ["cagaData", "eventData"], default=[])
        if isinstance(event_data, list):
            for event in event_data:
                events.append({
                    "safe_route": cls.safe_get(event, ["safe_path_info", "route"], default=[]),
                    "target_ships": cls.safe_get(event, ["timeSeriesData", "targetShips"], default=[]),
                    "own_ship_event": cls.safe_get(event, ["timeSeriesData", "ownShip"], default={}),
                    "caPathGenFail": cls.safe_get(event, ["caPathGenFail"]),
                    "isNearTarget": cls.safe_get(event, ["isNearTarget"])
                })
        return events

    @classmethod
    def _read_arrow_from_data(cls, data, file_name=""):
        """
        바이너리 데이터로부터 Arrow 파일을 읽어 Arrow Table을 반환합니다.
        """
        try:
            buffer_reader = pa.BufferReader(data)
            try:
                reader = ipc.RecordBatchFileReader(buffer_reader)
            except pa.lib.ArrowInvalid:
                buffer_reader.seek(0)
                reader = ipc.RecordBatchStreamReader(buffer_reader)
            return reader.read_all()
        except Exception as e:
            print(f"[ERROR] Arrow 파일 읽기 실패 (버퍼 방식): {file_name}, {e}")
            return None

    @classmethod
    def _extract_and_read_marzip(cls, file_path: str) -> dict:
        """
        .marzip 파일 내 압축된 Arrow 및 JSON 파일들을 ZIP 내부에서 직접 읽어 데이터를 반환합니다.
        시계열 데이터는 own_ship_time_series와 target_ship_time_series(키: id)로 구분합니다.
        """
        own_ship_time_series = []
        target_ship_time_series = {}  # id별로 row들을 저장할 dict
        static_dataset = []
        simulation_result = {}

        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                names = zip_ref.namelist()
                timeseries_files = [n for n in names if n.endswith('timeseries.arrow')]
                static_files = [n for n in names if n.endswith('static.arrow')]
                json_files = [n for n in names if n.endswith('.json')]

                # timeseries 파일 처리
                for name in timeseries_files:
                    try:
                        with zip_ref.open(name) as f:
                            data = f.read()
                        table = cls._read_arrow_from_data(data, name)
                        if not table:
                            print(Fore.RED + f"Arrow 파일 읽기 실패: {name}" + Style.RESET_ALL)
                            continue
                        for row in table.to_pylist():
                            if row.get("ownShip", False):
                                own_ship_time_series.append(row)
                            else:
                                target_id = row.get("id")
                                if target_id is None:
                                    continue
                                target_ship_time_series.setdefault(target_id, []).append(row)
                    except Exception as e:
                        print(Fore.RED + f"파일 읽기 오류: {name} / {e}" + Style.RESET_ALL)

                # static 파일 처리
                for name in static_files:
                    try:
                        with zip_ref.open(name) as f:
                            data = f.read()
                        table = cls._read_arrow_from_data(data, name)
                        if not table:
                            print(Fore.RED + f"Arrow 파일 읽기 실패: {name}" + Style.RESET_ALL)
                            continue
                        static_dataset.extend(table.to_pylist())
                    except Exception as e:
                        print(Fore.RED + f"파일 읽기 오류: {name} / {e}" + Style.RESET_ALL)

                # JSON 파일 처리 (첫 번째 성공한 파일 사용)
                for name in json_files:
                    try:
                        with zip_ref.open(name) as json_file:
                            simulation_result = json.load(json_file)
                        if simulation_result:
                            break
                    except Exception as e:
                        print(Fore.RED + f"JSON 파일 읽기 오류: {name} / {e}" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"압축 파일 처리 중 오류 발생: {file_path} / {e}" + Style.RESET_ALL)
            return {}

        return {
            "static_dataset": static_dataset,
            "own_ship_time_series": own_ship_time_series,
            "target_ship_time_series": target_ship_time_series,
            "simulation_result": simulation_result
        }
