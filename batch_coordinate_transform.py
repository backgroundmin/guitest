import os
import pandas as pd

# 새롭게 주어진 첫 번째 좌표값
new_reference_lat = 37.28856264
new_reference_lon = 127.1074755
new_reference_utm_easting = 332240.8945
new_reference_utm_northing = 4128563.207
	

# 작업할 디렉토리 경로
input_directory = './utm/dcu/waypoint/parallel_parking/final/'
output_directory = './utm/mando/waypoint/parallel_parking/modified/'  # 변환된 파일을 저장할 디렉토리
# 출력 디렉토리가 없을 경우 생성
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# 디렉토리 내 모든 .csv 파일에 대해 반복 작업 수행
for filename in os.listdir(input_directory):
    if filename.endswith('.csv'):
        file_path = os.path.join(input_directory, filename)
        
        # 현재 파일 이름 출력
        print(f"Currently processing: {filename}")
        
        # 파일 로드
        df = pd.read_csv(file_path)
        
        # 기존 첫 번째 좌표값 가져오기
        original_lat = df.loc[0, 'latitude']
        original_lon = df.loc[0, 'longitude']
        original_utm_easting = df.loc[0, 'utm_easting']
        original_utm_northing = df.loc[0, 'utm_northing']
        
        # 첫 번째 좌표와의 차이 계산
        lat_diff = new_reference_lat - original_lat
        lon_diff = new_reference_lon - original_lon
        utm_easting_diff = new_reference_utm_easting - original_utm_easting
        utm_northing_diff = new_reference_utm_northing - original_utm_northing
        
        # 모든 좌표에 차이를 적용하여 변환
        df['latitude'] = df['latitude'] + lat_diff
        df['longitude'] = df['longitude'] + lon_diff
        df['utm_easting'] = df['utm_easting'] + utm_easting_diff
        df['utm_northing'] = df['utm_northing'] + utm_northing_diff
        
        # 변환된 파일을 새로운 디렉토리에 저장
        output_file_path = os.path.join(output_directory, f'modified_{filename}')
        df.to_csv(output_file_path, index=False)
        
        print(f"Processed {filename}, saved as modified_{filename}")


# # 작업할 디렉토리 경로
# 
#   # 변환된 파일을 저장할 디렉토리