import sys
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import Point
from scipy.spatial import KDTree
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout,
    QWidget, QFileDialog, QLabel, QMessageBox, QHBoxLayout
)
# FigureCanvas를 올바르게 가져오기
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class MapCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 10))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.gdf = None
        self.tree = None
        self.df = None
        self.scatter = None
        self.annot = None
        self.selected_points = []  # 선택된 점을 저장하는 리스트
        self.click_mode_enabled = False  # 클릭 모드 상태를 저장
        self.max_click_distance = 3  # 허용되는 최대 클릭 거리 (3px)

    def load_data(self, file_path):
        try:
            # Load CSV
            self.df = pd.read_csv(file_path)
            
            # Check required columns
            if not {'longitude', 'llatitude'}.issubset(self.df.columns):
                raise ValueError("CSV must contain 'longitude' and 'llatitude' columns.")
            
            # Convert to GeoDataFrame
            geometry = [Point(xy) for xy in zip(self.df['longitude'], self.df['llatitude'])]
            self.gdf = gpd.GeoDataFrame(self.df, geometry=geometry)
            
            # Set CRS to WGS84
            self.gdf.set_crs(epsg=4326, inplace=True)
            
            # Transform to Web Mercator
            self.gdf = self.gdf.to_crs(epsg=3857)
            
            # Build KDTree
            coords = list(zip(self.gdf.geometry.x, self.gdf.geometry.y))
            self.tree = KDTree(coords)
            
            # Plot
            self.plot_map()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{e}")

    def plot_map(self):
        self.ax.clear()
        # Plot points
        self.scatter = self.gdf.plot(ax=self.ax, marker='o', color='blue', markersize=5, alpha=0.7)
        # Add basemap
        ctx.add_basemap(self.ax, source=ctx.providers.Esri.WorldImagery, zoom=18)
        self.ax.set_axis_off()
        self.fig.tight_layout()
        self.draw()

    def on_click(self, event):
        # 클릭 모드가 활성화된 경우에만 동작
        if not self.click_mode_enabled or event.inaxes != self.ax:
            return
        click_x, click_y = event.xdata, event.ydata
        if self.tree is not None:
            distance, index = self.tree.query([click_x, click_y])
            if distance < self.max_click_distance:
                self.select_point(index)

    def select_point(self, index):
        if len(self.selected_points) < 2:
            self.selected_points.append(index)
            # Update point color to red
            self.highlight_selected_points()
        else:
            QMessageBox.information(self, "Info", "You can only select two points.")

    def highlight_selected_points(self):
        # Clear existing plot
        self.plot_map()

        # Highlight selected points
        for i in self.selected_points:
            self.ax.plot(self.gdf.geometry.x[i], self.gdf.geometry.y[i], 'ro', markersize=10)  # 빨간색 점으로 표시
        self.draw()

    def delete_waypoints(self):
        if len(self.selected_points) != 2:
            QMessageBox.warning(self, "Warning", "Please select exactly two points.")
            return
        
        start_idx, end_idx = sorted(self.selected_points)
        # 두 선택된 점 사이의 웨이포인트 삭제
        self.df = self.df.drop(self.df.index[start_idx+1:end_idx])

        # 선택된 점 초기화
        self.selected_points = []

        # 데이터 업데이트 후 다시 그리기
        self.load_data(None)  # 기존 데이터를 다시 로드

    def set_click_mode(self, enabled):
        """클릭 모드 활성화/비활성화 설정"""
        self.click_mode_enabled = enabled

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPS Points Visualizer with Deletion")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout (horizontal)
        self.main_layout = QHBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        
        # Left layout for buttons and info
        self.left_layout = QVBoxLayout()

        # Load Button
        self.load_button = QPushButton("Load CSV")
        self.load_button.clicked.connect(self.load_csv)
        self.left_layout.addWidget(self.load_button)

        # Click Mode Button
        self.click_mode_button = QPushButton("Enable Point Click Mode")
        self.click_mode_button.setCheckable(True)
        self.click_mode_button.clicked.connect(self.toggle_click_mode)
        self.left_layout.addWidget(self.click_mode_button)

        # Delete Button
        self.delete_button = QPushButton("Delete Waypoints Between Selected Points")
        self.delete_button.clicked.connect(self.delete_waypoints)
        self.left_layout.addWidget(self.delete_button)
        
        # Info Label
        self.info_label = QLabel("Click on a point to select (Max: 2 points).")
        self.info_label.setStyleSheet("font-size: 16px;")
        self.left_layout.addWidget(self.info_label)

        # Add left layout to main layout
        self.main_layout.addLayout(self.left_layout)

        # Right layout for map and toolbar
        self.right_layout = QVBoxLayout()

        # Map Canvas
        self.canvas = MapCanvas(self)
        
        # Navigation Toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)  # 확대/축소 툴바 추가
        self.right_layout.addWidget(self.toolbar)

        # Add canvas to right layout
        self.right_layout.addWidget(self.canvas)

        # Add right layout to main layout
        self.main_layout.addLayout(self.right_layout)
        
        # Connect click event
        self.canvas.mpl_connect('button_press_event', self.canvas.on_click)

    def toggle_click_mode(self):
        if self.click_mode_button.isChecked():
            self.canvas.set_click_mode(True)
            self.click_mode_button.setText("Disable Point Click Mode")
        else:
            self.canvas.set_click_mode(False)
            self.click_mode_button.setText("Enable Point Click Mode")

    def delete_waypoints(self):
        self.canvas.delete_waypoints()

    def load_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_name:
            self.canvas.load_data(file_name)
            self.info_label.setText("Click on a point to select (Max: 2 points).")
    
    def update_info(self, info_text):
        self.info_label.setText(info_text)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
