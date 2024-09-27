import sys
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import Point
from geopy.distance import geodesic
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
        self.main_window = main_window
        self.selected_points = []
        self.is_adding_line = False
        self.is_adding_point = False
        self.line_start = None
        self.line_end = None

    def load_data(self, file_path):
        try:
            self.df = pd.read_csv(file_path)

            if not {'latitude', 'longitude'}.issubset(self.df.columns):
                raise ValueError("CSV에는 'longitude'와 'latitude' 컬럼이 포함되어 있어야 합니다.")

            geometry = [Point(xy) for xy in zip(self.df['longitude'], self.df['latitude'])]
            self.gdf = gpd.GeoDataFrame(self.df, geometry=geometry)
            self.gdf.set_crs(epsg=4326, inplace=True)
            self.gdf = self.gdf.to_crs(epsg=3857)

            self.plot_map()
            self.main_window.update_table(self.df)

        except Exception as e:
            QMessageBox.critical(self, "오류", f"데이터 로드 실패:\n{e}")

    def plot_map(self):
        self.ax.clear()
        self.gdf.plot(ax=self.ax, marker='o', color='blue', markersize=5, alpha=0.7)
        ctx.add_basemap(self.ax, source=ctx.providers.Esri.WorldImagery, zoom=18)
        self.ax.set_axis_off()
        self.fig.tight_layout()
        self.draw()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return

        click_x, click_y = event.xdata, event.ydata

        point = gpd.GeoSeries([Point(click_x, click_y)], crs="EPSG:3857")
        point_wgs84 = point.to_crs(epsg=4326)

        longitude, latitude = point_wgs84.geometry.x[0], point_wgs84.geometry.y[0]

        if self.is_adding_point:
            self.add_point(latitude, longitude)
            QMessageBox.information(self, "포인트 추가됨", f"경도: {longitude}, 위도: {latitude}의 포인트가 추가되었습니다.")
            self.is_adding_point = False
        elif self.is_adding_line:
            if self.line_start is None:
                self.line_start = (latitude, longitude)
                QMessageBox.information(self, "선 시작", f"선의 시작점 설정됨: 경도: {longitude}, 위도: {latitude}")
            else:
                self.line_end = (latitude, longitude)
                QMessageBox.information(self, "선 끝", f"선의 끝점 설정됨: 경도: {longitude}, 위도: {latitude}")
                self.generate_points_along_line()
                self.is_adding_line = False
                self.line_start = None
                self.line_end = None

    def generate_points_along_line(self):
        if self.line_start and self.line_end:
            lat1, lon1 = self.line_start
            lat2, lon2 = self.line_end

            total_distance = geodesic((lat1, lon1), (lat2, lon2)).meters
            max_points = 1000  # 포인트 개수 제한
            num_points = min(int(total_distance / 0.0876), max_points)

            # 너무 많은 포인트가 생성되지 않도록 제한
            if num_points > max_points:
                QMessageBox.warning(self, "경고", f"너무 많은 포인트가 생성됩니다. {max_points}개의 포인트로 제한됩니다.")
                num_points = max_points

            for i in range(1, num_points + 1):
                QApplication.processEvents()  # 프로그램 멈춤 방지
                fraction = i / num_points
                new_lat = lat1 + (lat2 - lat1) * fraction
                new_lon = lon1 + (lon2 - lon1) * fraction
                self.add_point(new_lat, new_lon)

            QMessageBox.information(self, "포인트 추가 완료", f"{num_points}개의 포인트가 추가되었습니다.")

    def add_point(self, latitude, longitude):
        new_row = pd.DataFrame([[latitude, longitude]], columns=['latitude', 'longitude'])
        self.df = pd.concat([self.df, new_row], ignore_index=True)

        new_geometry = Point(longitude, latitude)
        new_gdf_row = gpd.GeoDataFrame([[new_geometry]], columns=['geometry'], crs="EPSG:4326")
        new_gdf_row = new_gdf_row.to_crs(epsg=3857)
        self.gdf = pd.concat([self.gdf, new_gdf_row], ignore_index=True)

        self.plot_map()
        self.main_window.update_table(self.df)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPS Points Visualizer")
        self.setGeometry(100, 100, 1200, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        self.left_layout = QVBoxLayout()

        self.load_button = QPushButton("CSV 파일 로드")
        self.load_button.clicked.connect(self.load_csv)
        self.left_layout.addWidget(self.load_button)

        self.add_point_button = QPushButton("포인트 추가 모드")
        self.add_point_button.clicked.connect(self.enable_add_point)
        self.left_layout.addWidget(self.add_point_button)

        self.add_line_button = QPushButton("선 추가 모드")
        self.add_line_button.clicked.connect(self.enable_add_line)
        self.left_layout.addWidget(self.add_line_button)

        self.save_button = QPushButton("변경된 데이터 저장")
        self.save_button.clicked.connect(self.save_csv)
        self.left_layout.addWidget(self.save_button)

        self.info_label = QLabel("지도에서 선을 그리거나 포인트를 추가할 수 있습니다.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 14px;")
        self.left_layout.addWidget(self.info_label)

        self.coordinates_label = QLabel("경도: N/A, 위도: N/A")
        self.coordinates_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.left_layout.addWidget(self.coordinates_label)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Longitude', 'Latitude'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.left_layout.addWidget(self.table)

        self.main_layout.addLayout(self.left_layout, 1)

        self.right_layout = QVBoxLayout()

        self.canvas = MapCanvas(self, self)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.right_layout.addWidget(self.toolbar)

        self.right_layout.addWidget(self.canvas)

        self.main_layout.addLayout(self.right_layout, 3)

        self.canvas.mpl_connect('button_press_event', self.canvas.on_click)

    def load_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "CSV 파일 열기", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_name:
            self.canvas.load_data(file_name)

    def save_csv(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "CSV 파일로 저장", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_name:
            self.canvas.df.to_csv(file_name, index=False)
            QMessageBox.information(self, "저장 완료", "변경된 데이터를 저장했습니다.")

    def enable_add_point(self):
        self.canvas.is_adding_point = True
        QMessageBox.information(self, "포인트 추가 모드 활성화", "지도에서 포인트를 추가하려면 클릭하세요.")

    def enable_add_line(self):
        self.canvas.is_adding_line = True
        QMessageBox.information(self, "선 추가 모드 활성화", "선의 시작점과 끝점을 클릭하세요.")

    def update_table(self, df):
        # 테이블을 새로 고침하여 모든 포인트 표시
        self.table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.table.setItem(i, 0, QTableWidgetItem(str(row['longitude'])))
            self.table.setItem(i, 1, QTableWidgetItem(str(row['latitude'])))
        self.table.resizeColumnsToContents()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()