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

        # 선택된 인덱스 정렬 (내림차순으로 정렬하여 삭제할 때 인덱스 충돌 방지)
        for index in sorted(self.selected_points, reverse=True):
            self.df = self.df.drop(index)
            self.gdf = self.gdf.drop(index)

        # 인덱스를 리셋하여 일관성 유지
        self.df.reset_index(drop=True, inplace=True)
        self.gdf.reset_index(drop=True, inplace=True)

        # KDTree 재생성
        if not self.gdf.empty:
            coords = list(zip(self.gdf.geometry.x, self.gdf.geometry.y))
            self.tree = KDTree(coords)
        else:
            self.tree = None

        # 선택된 포인트 목록 초기화
        self.selected_points = []

        # 테이블 및 지도 업데이트
        self.plot_map()
        self.main_window.update_table(self.df)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPS Points Visualizer")
        self.setGeometry(100, 100, 1200, 800)

        # 중앙 위젯 설정
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 메인 레이아웃 (수평)
        self.main_layout = QHBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # 왼쪽 레이아웃 (버튼 및 정보)
        self.left_layout = QVBoxLayout()

        # CSV 로드 버튼
        self.load_button = QPushButton("CSV 파일 로드")
        self.load_button.clicked.connect(self.load_csv)
        self.left_layout.addWidget(self.load_button)

        # 포인트 제거 버튼
        self.delete_button = QPushButton("선택된 포인트 제거")
        self.delete_button.clicked.connect(self.delete_points)
        self.left_layout.addWidget(self.delete_button)

        # 포인트 추가 버튼
        self.add_button = QPushButton("포인트 추가")
        self.add_button.clicked.connect(self.enable_add_point)
        self.left_layout.addWidget(self.add_button)

        # 포인트 간격 채우기 버튼
        self.fill_button = QPushButton("포인트 간격 채우기")
        self.fill_button.clicked.connect(self.enable_fill_points)
        self.left_layout.addWidget(self.fill_button)

        # 변경된 데이터 저장 버튼
        self.save_button = QPushButton("변경된 데이터 저장")
        self.save_button.clicked.connect(self.save_csv)
        self.left_layout.addWidget(self.save_button)

        # 정보 레이블
        self.info_label = QLabel("지도에서 클릭하면 해당 위치의 경도와 위도가 표시됩니다. 포인트를 추가하려면 '포인트 추가' 버튼을 누르세요.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 14px;")
        self.left_layout.addWidget(self.info_label)

        # 클릭한 위치의 경도, 위도 표시 레이블
        self.coordinates_label = QLabel("경도: N/A, 위도: N/A")
        self.coordinates_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.left_layout.addWidget(self.coordinates_label)

        # 포인트 인덱스 표시 레이블
        self.point_index_label = QLabel("포인트 인덱스: N/A")
        self.point_index_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.left_layout.addWidget(self.point_index_label)

        # 포인트 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Longitude', 'Latitude'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.selectionModel().selectionChanged.connect(self.on_table_selection)  # 테이블 선택 이벤트 연결
        self.left_layout.addWidget(self.table)

        # 왼쪽 레이아웃 추가
        self.main_layout.addLayout(self.left_layout, 1)

        # 오른쪽 레이아웃 (지도 및 툴바)
        self.right_layout = QVBoxLayout()

        # 지도 캔버스
        self.canvas = MapCanvas(self, self)  # self를 MapCanvas의 main_window로 전달

        # 네비게이션 툴바
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.right_layout.addWidget(self.toolbar)

        # 캔버스 추가
        self.right_layout.addWidget(self.canvas)

        # 오른쪽 레이아웃 추가
        self.main_layout.addLayout(self.right_layout, 3)

        # 캔버스 클릭 이벤트 연결
        self.canvas.mpl_connect('button_press_event', self.canvas.on_click)

    def load_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "CSV 파일 열기", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_name:
            self.canvas.load_data(file_name)

    def save_csv(self):
        # CSV 파일로 저장
        file_name, _ = QFileDialog.getSaveFileName(
            self, "CSV 파일로 저장", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_name:
            # canvas에 있는 데이터를 CSV 파일로 저장
            self.canvas.df.to_csv(file_name, index=False)
            QMessageBox.information(self, "저장 완료", "변경된 데이터를 저장했습니다.")

    def show_coordinates(self, latitude, longitude):
        # 경도와 위도를 레이블에 표시
        self.coordinates_label.setText(f"경도: {longitude:.6f}, 위도: {latitude:.6f}")

    def show_point_index(self, index):
        # 클릭한 포인트의 인덱스를 레이블에 표시
        self.point_index_label.setText(f"포인트 인덱스: {index}")

    def delete_points(self):
        # 선택된 포인트를 삭제
        selected_indices = self.canvas.selected_points.copy()
        if not selected_indices:
            QMessageBox.warning(self, "경고", "삭제할 포인트를 선택하세요.")
            return
        confirm = QMessageBox.question(
            self, "확인", f"{len(selected_indices)}개의 포인트를 제거하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.canvas.remove_selected_points()

    def update_table(self, df):
        # 테이블을 새로 고침하여 모든 포인트 표시
        self.table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.table.setItem(i, 0, QTableWidgetItem(str(row['longitude'])))
            self.table.setItem(i, 1, QTableWidgetItem(str(row['latitude'])))
        self.table.resizeColumnsToContents()

    def on_table_selection(self):
        # 테이블에서 선택된 포인트를 지도에 강조
        selected_rows = self.table.selectionModel().selectedRows()
        selected_indices = [index.row() for index in selected_rows]
        self.canvas.selected_points = selected_indices  # 선택된 포인트를 업데이트
        self.canvas.highlight_selected_points()  # 선택된 포인트를 빨간색으로 강조

    def enable_add_point(self):
        # 포인트 추가 모드를 활성화
        self.canvas.is_adding_point = True
        QMessageBox.information(self, "포인트 추가", "지도에서 포인트를 추가하려면 클릭하세요.")

    def enable_fill_points(self):
        # 포인트 간격 채우기 모드를 활성화
        self.canvas.fill_points_mode = True
        self.canvas.fill_points = []
        QMessageBox.information(self, "포인트 간격 채우기", "지도에서 두 점을 클릭하여 포인트를 채우세요.")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()