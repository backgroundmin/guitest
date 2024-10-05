import pandas as pd

file_2_path = '/mnt/data/merge_waypoint_no_parking_v1.csv'
output_path = '/mnt/data/converted_file.csv'
df2 = pd.read_csv(file_2_path)  # 두 번째 파일 (변환 대상)

# 두 번째 파일에서 불필요한 열을 제거 ('seq', 'option', 기타 불필요한 열)
df2_modified = df2.drop(columns=['seq', 'option', 'Unnamed: 6', 'Unnamed: 7'])

# 열 이름 변경: 'latitude_utm' -> 'utm_easting', 'longitude_utm' -> 'utm_northing'
df2_modified = df2_modified.rename(columns={
    'latitude_utm': 'utm_easting',
    'longitude_utm': 'utm_northing'
})

# 'utm_zone_number' 열 추가 (첫 번째 파일의 값 사용, 여기서는 '52S'로 가정)
df2_modified['utm_zone_number'] = '52S'  # 필요한 값을 넣어주면 됩니다.

# 첫 번째 파일의 열 순서에 맞게 정렬
df2_final = df2_modified[['latitude', 'longitude', 'utm_easting', 'utm_northing', 'utm_zone_number']]

# 결과를 CSV 파일로 저장
df2_final.to_csv(output_path, index=False)

# 출력 파일 경로
output_path
