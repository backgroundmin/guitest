import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import Point
from scipy.spatial import KDTree

# CSV 파일 불러오기
file_path = './dcu_load3.csv'
df = pd.read_csv(file_path)

# GeoDataFrame으로 변환 (위도, 경도를 점으로 변환)
geometry = [Point(xy) for xy in zip(df['longitude'], df['llatitude'])]
gdf = gpd.GeoDataFrame(df, geometry=geometry)

# GeoDataFrame에 CRS(좌표 참조 시스템) 설정 (WGS84: EPSG:4326)
gdf.set_crs(epsg=4326, inplace=True)

# EPSG:3857 (Web Mercator) 좌표계로 변환 - contextily는 EPSG:3857 사용
gdf = gdf.to_crs(epsg=3857)

# 지도 시각화
fig, ax = plt.subplots(figsize=(10, 10))

# GeoDataFrame 플로팅
scatter = gdf.plot(ax=ax, marker='o', color='blue', markersize=5, alpha=0.7)

# 위성 타일 추가 (지도 위에 위성 타일 올리기)
ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery)

# 좌표 리스트 추출 (x, y 좌표)
coords = list(zip(gdf.geometry.x, gdf.geometry.y))

# KDTree를 사용하여 좌표 간 거리 계산 (빠른 최근접 탐색)
tree = KDTree(coords)

# 클릭 이벤트 핸들러 함수
def onclick(event):
    # 클릭한 좌표
    click_x, click_y = event.xdata, event.ydata

    # 클릭한 좌표에서 가장 가까운 GPS 좌표 찾기
    distance, index = tree.query([click_x, click_y])

    # 해당 좌표의 번호 출력
    print(f"Clicked on Point {index + 1}, Latitude: {df['llatitude'][index]}, Longitude: {df['longitude'][index]}")

    # # 클릭된 좌표 강조
    # ax.plot(click_x, click_y, 'ro', markersize=10)  # 클릭된 좌표를 빨간색으로 표시
    plt.draw()

# 클릭 이벤트 연결
fig.canvas.mpl_connect('button_press_event', onclick)

# 그래프 보여주기
plt.show()
