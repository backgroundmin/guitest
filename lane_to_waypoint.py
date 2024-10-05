import pandas as pd

# 첫 번째와 두 번째 파일의 경로를 지정합니다.
file_1_path = '/mnt/data/modified_pp_0_final (2).csv'
output_path = '/mnt/data/modified_file.csv'

# 파일을 읽어옵니다.
df1 = pd.read_csv(file_1_path)

# 첫 번째 파일에 'seq' 열을 추가합니다 (1부터 순차적으로 증가하는 값으로 설정).
df1['seq'] = range(1, len(df1) + 1)

# 'option' 열을 추가하고 모든 값을 0으로 설정합니다.
df1['option'] = 0

# 첫 번째 파일의 열 이름을 두 번째 파일과 일치하도록 변경합니다.
df1_renamed = df1.rename(columns={
    'latitude': 'latitude',
    'longitude': 'longitude',
    'utm_easting': 'latitude_utm',
    'utm_northing': 'longitude_utm'
})

# 필요한 열만 선택하여 최종적으로 형식을 맞춥니다.
df1_final = df1_renamed[['seq', 'latitude', 'longitude', 'latitude_utm', 'longitude_utm', 'option']]

df1_final.to_csv(output_path, index=False)

# 수정된 파일 경로를 출력합니다.
output_path
