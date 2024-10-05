import os
import pandas as pd
import utm

# UTM 좌표를 위도와 경도로 변환하는 함수
def utm_to_latlon(easting, northing, zone_number=52, northern_hemisphere=True):
    return utm.to_latlon(easting, northing, zone_number, northern=northern_hemisphere)

# 변환 작업을 수행하는 함수
def convert_utm_to_latlon_in_csv(file_path, output_dir):
    data = pd.read_csv(file_path)
    
    # UTM 좌표를 위도/경도로 변환
    data[['latitude', 'longitude']] = data.apply(
        lambda row: utm_to_latlon(row['llatitude_utm'], row['longitude_utm']), axis=1, result_type="expand"
    )
    
    # 변환된 파일을 저장
    filename = os.path.basename(file_path)
    output_file_path = os.path.join(output_dir, f'converted_{filename}')
    data.to_csv(output_file_path, index=False)
    print(f"File saved as {output_file_path}")

# 작업할 디렉토리 경로 설정
directory = './utm/dcu/waypoint/T_parking'  # 실제 경로로 변경하세요
output_directory = './utm/dcu/waypoint/T_parking/converted'  # 변환된 파일을 저장할 디렉토리 경로

# 출력 디렉토리가 없는 경우 생성
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# 디렉토리 내 모든 .csv 파일에 대해 변환 작업 수행
for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        file_path = os.path.join(directory, filename)
        convert_utm_to_latlon_in_csv(file_path, output_directory)
