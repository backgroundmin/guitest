import pandas as pd
import utm

# Load your CSV file
file_path = './utm/dcu/waypoint/mando_T_parking_test_7.csv'  # Update this to your actual file path
data = pd.read_csv(file_path)

# Function to convert UTM coordinates to latitude and longitude
def utm_to_latlon(easting, northing, zone_number=52, northern_hemisphere=True):
    return utm.to_latlon(easting, northing, zone_number, northern=northern_hemisphere)

# Apply the conversion to the UTM columns
data[['latitude', 'longitude']] = data.apply(
    lambda row: utm_to_latlon(row['llatitude_utm'], row['longitude_utm']), axis=1, result_type="expand"
)

# Save the updated file
output_file_path = './utm/dcu/waypoint/mando_T_parking_test_7_filled.csv'  # Update this to your desired output file path
data.to_csv(output_file_path, index=False)

print(f"File saved as {output_file_path}")
