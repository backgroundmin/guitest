import pandas as pd
import utm

file2_path = './utm/parallel_parking_lane_transformed.csv'

# Read the second CSV into a pandas DataFrame
df2 = pd.read_csv(file2_path)

# Function to convert latitude and longitude to UTM coordinates
def latlon_to_utm(lat, lon):
    utm_coords = utm.from_latlon(lat, lon)
    return utm_coords[0], utm_coords[1], f"{utm_coords[2]}{utm_coords[3]}"

# Apply the conversion to the second CSV's latitude and longitude
df2['utm_easting'], df2['utm_northing'], df2['utm_zone_number'] = zip(*df2.apply(lambda row: latlon_to_utm(row['latitude'], row['longitude']), axis=1))

# Reorganize the columns to match the first file format
df2_transformed = df2[['latitude', 'longitude', 'utm_easting', 'utm_northing', 'utm_zone_number']]

# Save the transformed DataFrame to a new CSV file
output_path = 'd2_transformed.csv'
df2_transformed.to_csv(output_path, index=False)

print(f"Transformed CSV saved to {output_path}")
