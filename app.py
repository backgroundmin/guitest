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

class MapCanvas(FigureCanvas):
    def __init__(self, main_window, parent=None):
        self.fig = Figure(figsize=(10, 10))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.gdf = None
        self.main_window = main_window  # MainWindow 참조를 저장
        self.selected_points = []  # 테이블에서 선택된 포인트 저장

    def load_data(self, file_path):
        try:
            # CSV 로드
            self.df = pd.read_csv(file_path)

            # 필요한 컬럼 확인 ('longitude'와 'llatitude'가 맞는지 확인)
            if not {'llatitude', 'longitude'}.issubset(self.df.columns):
                raise ValueError("CSV에는 'longitude'와 'llatitude' 컬럼이 포함되어 있어야 합니다.")

            # GeoDataFrame으로 변환
            geometry = [Point(xy) for xy in zip(self.df['longitude'], self.df['llatitude'])]
            self.gdf = gpd.GeoDataFrame(self.df, geometry=geometry)

            # CRS 설정 (WGS84)
            self.gdf.set_crs(epsg=4326, inplace=True)

            # Web Mercator로 변환
            self.gdf = self.gdf.to_crs(epsg=3857)

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
        # 베이스맵 추가 (Esri 위성지도)
        ctx.add_basemap(self.ax, crs=self.gdf.crs.to_string(), source=ctx.providers.Esri.WorldImagery, zoom=19)
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
        # 마우스 클릭 시 발생하는 이벤트 핸들러
        if event.inaxes != self.ax:
            return
        
        # 클릭한 위치의 Web Mercator 좌표 (x, y)
        click_x, click_y = event.xdata, event.ydata
        
        # Web Mercator 좌표를 WGS84(경도, 위도)로 변환
        point = gpd.GeoSeries([Point(click_x, click_y)], crs="EPSG:3857")
        point_wgs84 = point.to_crs(epsg=4326)

        # 경도와 위도 값 추출
        longitude, latitude = point_wgs84.geometry.x[0], point_wgs84.geometry.y[0]

        # 경도와 위도를 메인 윈도우에 출력
        self.main_window.show_coordinates(latitude, longitude)

    def remove_selected_points(self):
        if not self.selected_points:
            QMessageBox.warning(self, "경고", "제거할 포인트가 선택되지 않았습니다.")
            return
        
        # 선택된 인덱스 정렬 (삭제 시 인덱스가 꼬이지 않도록)
        for index in sorted(self.selected_points, reverse=True):
            self.df = self.df.drop(index)
            self.gdf = self.gdf.drop(index)
        
        self.df.reset_index(drop=True, inplace=True)
        self.gdf.reset_index(drop=True, inplace=True)
        self.selected_points = []
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

        # 정보 레이블
        self.info_label = QLabel("지도에서 클릭하면 해당 위치의 경도와 위도가 표시됩니다. 테이블에서 포인트를 선택하여 삭제할 수 있습니다.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 14px;")
        self.left_layout.addWidget(self.info_label)

        # 클릭한 위치의 경도, 위도 표시 레이블
        self.coordinates_label = QLabel("경도: N/A, 위도: N/A")
        self.coordinates_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.left_layout.addWidget(self.coordinates_label)

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

    def show_coordinates(self, latitude, longitude):
        # 경도와 위도를 레이블에 표시
        self.coordinates_label.setText(f"경도: {longitude:.6f}, 위도: {latitude:.6f}")

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

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
