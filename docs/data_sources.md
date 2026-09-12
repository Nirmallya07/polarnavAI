# Intended Data Sources

## Sea Ice

- NSIDC: National Snow and Ice Data Center
- NOAA Sea Ice Concentration and related Antarctic sea-ice products
- Planned use: sea-ice concentration, phenology, and spatial coverage inputs

## Icebergs

- U.S. National Ice Center Antarctic iceberg data
- Historical iceberg drift and position records
- Planned use: iceberg presence, drift trajectory, encounter probability, and seasonal patterns

## Weather

- Copernicus Climate Data Store
- ERA5 atmospheric reanalysis data
- Planned use: wind speed, temperature, pressure, and related atmospheric variables

## Ocean

- Copernicus Marine Service
- Ocean current and sea-surface data products
- Planned use: current direction, sea-surface temperature, wave conditions, and environmental context

## Copernicus Ocean Data

- Mounted directory: /mnt/polarnav-drive
- Environment variable override: POLARNAV_COPERNICUS_DIR
- Expected structure: one monthly NetCDF file per month for the target year
- Example file: cmems_mod_glo_phy_my_0.083deg_P1D-m_uo-vo-thetao-sithick-usi-vsi_180.00W-180.00E_75.00S-45.00S_0.49m_2023-01-01T00-00-00-2023-01-31T00-00-00.nc
- Variables used for the current MVP: uo, vo
- Mappings: uo -> ocean_u, vo -> ocean_v
- Units: m/s
- Selection strategy: resolve the file for the timestamp's year/month, then select nearest lat/lon/time using xarray lazy indexing
- Missing-data handling: NaN or invalid mask values are returned as null in the standardized environment payload rather than being silently converted to zero
- Scientific note: sithick, usi, vsi, and thetao are not treated as sea-ice concentration, wind, or air temperature in this MVP

## Dataset Policy

- No massive datasets are to be committed to the repository.
- Raw data stays under the data/raw directories only as lightweight placeholders.
- Data files should be referenced through clear documentation and local processing scripts.
