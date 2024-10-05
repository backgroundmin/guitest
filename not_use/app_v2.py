import sys
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import Point
from scipy.spatial import KDTree
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout,
    QWidget, QFileDialog, QLabel, QMessageBox, QHBoxLayout, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# geopy 임포트
from geopy.distance import geodesic

class MapCanvas(FigureCanvas):
    def __init__(self, main_window, parent=None):
        self.fig = Figure(figsize=(10, 10))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.gdf = None
        self.main_window = main_window  # MainWindow 참조를 저장
        self.selected_points = []  # 테이블에서 선택된 포인트 저장
        self.is_adding_point = False  # 포인트 추가 모드 상태
        self.fill_points_mode = False  # 포인트 간격 채우기 모드 상태
        self.fill_points = []  # 채울 포인트의 두 점 저장

    def load_data(self, file_path):
        try:
            # CSV 로드
            self.df = pd.read_csv(file_path)

            # 필요한 컬럼 확인 ('longitude'와 'latitude'가 맞는지 확인)
            if not {'latitude', 'longitude'}.issubset(self.df.columns):
                raise ValueError("CSV에는 'longitude'와 'latitude' 컬럼이 포함되어 있어야 합니다.")

            # GeoDataFrame으로 변환
            geometry = [Point(xy) for xy in zip(self.df['longitude'], self.df['latitude'])]
            self.gdf = gpd.GeoDataFrame(self.df, geometry=geometry)

            # CRS 설정 (WGS84)
            self.gdf.set_crs(epsg=4326, inplace=True)

            # Web Mercator로 변환
            self.gdf = self.gdf.to_crs(epsg=3857)

            # KDTree 구축
            coords = list(zip(self.gdf.geometry.x, self.gdf.geometry.y))
            self.tree = KDTree(coords)

            # 지도 그리기
            self.plot_map()

            # 테이블 업데이트
            self.main_window.update_table(self.df)

        except Exception as e:
            QMessageBox.critical(self, "오류", f"데이터 로드 실패:\n{e}")

    def plot_map(self):
        self.ax.clear()
        # 포인트 플롯
        self.gdf.plot(ax=self.ax, marker='o', color='blue', markersize=5, alpha=0.7)
        # 베이스맵 추가
        ctx.add_basemap(self.ax, source=ctx.providers.Esri.WorldImagery, zoom=18)
        self.ax.set_axis_off()
        self.fig.tight_layout()
        self.draw()

    def highlight_selected_points(self):
        # 기존 포인트 그리기
        self.plot_map()
        
        # 선택된 포인트 강조
        for i in self.selected_points:
            self.ax.plot(self.gdf.geometry.x[i], self.gdf.geometry.y[i], 'ro', markersize=10)  # 빨간색 강조
        self.draw()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return

        click_x, click_y = event.xdata, event.ydata

        # Web Mercator 좌표를 WGS84(경도, 위도)로 변환
        point = gpd.GeoSeries([Point(click_x, click_y)], crs="EPSG:3857")
        point_wgs84 = point.to_crs(epsg=4326)

        # 경도와 위도를 메인 윈도우에 출력
        longitude, latitude = point_wgs84.geometry.x[0], point_wgs84.geometry.y[0]

        if self.is_adding_point:
            self.add_point(latitude, longitude)
            QMessageBox.information(self, "포인트 추가됨", f"경도: {longitude}, 위도: {latitude}의 포인트가 추가되었습니다.")
        elif self.fill_points_mode:
            self.fill_points.append((latitude, longitude))
            if len(self.fill_points) == 2:
                self.fill_between_points(self.fill_points[0], self.fill_points[1])
                self.fill_points = []
                self.fill_points_mode = False
                QMessageBox.information(self, "포인트 채우기 완료", "두 점 사이에 포인트를 채웠습니다.")
            else:
                QMessageBox.information(self, "포인트 선택", "두 번째 포인트를 선택하세요.")
        else:
            # 기존 클릭 처리
            self.main_window.show_coordinates(latitude, longitude)
            # 가까운 포인트의 인덱스 찾기
            if self.gdf is not None:
                distance, index = self.tree.query([click_x, click_y])
                self.main_window.show_point_index(index)

    def add_point(self, latitude, longitude):
        # 새로운 포인트를 DataFrame에 추가
        new_row = pd.DataFrame([[latitude, longitude]], columns=['latitude', 'longitude'])
        self.df = pd.concat([self.df, new_row], ignore_index=True)

        # 새로운 포인트를 GeoDataFrame에 추가 (WGS84 좌표계에서 추가)
        new_geometry = Point(longitude, latitude)
        new_gdf_row = gpd.GeoDataFrame([[new_geometry]], columns=['geometry'], crs="EPSG:4326")
        new_gdf_row = new_gdf_row.to_crs(epsg=3857)  # 좌표계를 Web Mercator로 변환
        self.gdf = pd.concat([self.gdf, new_gdf_row], ignore_index=True)

        # KDTree 재생성 (새로운 포인트 포함)
        coords = list(zip(self.gdf.geometry.x, self.gdf.geometry.y))
        self.tree = KDTree(coords)

        # 테이블 및 지도 업데이트
        self.plot_map()  # 지도 업데이트
        self.main_window.update_table(self.df)  # 테이블 업데이트
        self.is_adding_point = False  # 포인트 추가 모드 종료

    def fill_between_points(self, point1, point2, interval_km=0.1):
        """
        두 지점 사이를 일정 간격으로 포인트를 채웁니다.
        interval_km: 간격 (킬로미터 단위)
        """
        # 두 점의 위도와 경도
        lat1, lon1 = point1
        lat2, lon2 = point2

        # 두 지점 사이의 전체 거리 계산
        total_distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers

        if total_distance == 0:
            QMessageBox.warning(self, "경고", "두 점이 동일한 위치에 있습니다.")
            return

        # 포인트 생성 간격 계산
        num_points = int(total_distance / interval_km)

        if num_points == 0:
            QMessageBox.warning(self, "경고", "두 점 사이의 거리가 간격보다 짧습니다.")
            return

        # 위도와 경도의 선형 보간
        lats = [lat1 + (lat2 - lat1) * i / (num_points + 1) for i in range(1, num_points + 1)]
        lons = [lon1 + (lon2 - lon1) * i / (num_points + 1) for i in range(1, num_points + 1)]

        for lat, lon in zip(lats, lons):
            self.add_point(lat, lon)

    def remove_selected_points(self):
        if not self.selected_points:
            QMessageBox.warning(self, "경고", "삭제할 포인트가 선택되지 않았습니다.")
            return

        # 선택된 인덱스 정렬 (내림차순으로 정렬하여 삭제할
