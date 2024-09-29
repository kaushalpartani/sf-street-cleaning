import pandas as pd
import geopandas
import pendulum
import os

def get_file_name(neighborhood_name):
    return ''.join(ch for ch in neighborhood_name if ch.isalnum())

neighborhoods = pd.read_csv("https://data.sfgov.org/api/views/gfpk-269f/rows.csv?date=20240922&accessType=DOWNLOAD")
neighborhoods["geometry"] = geopandas.GeoSeries.from_wkt(neighborhoods["the_geom"])
neighborhoods = neighborhoods[["geometry", "name"]]
neighborhoods = neighborhoods.rename(columns={"name": "NeighborhoodName"})
neighborhoods = geopandas.GeoDataFrame(neighborhoods)
neighborhoods["FileName"] = [get_file_name(x) for x in neighborhoods["NeighborhoodName"]]
neighborhoods.to_file(f"{os.environ['DATA_PATH']}/neighborhoods.geojson", driver="GeoJSON")

df = pd.read_csv("https://data.sfgov.org/api/views/yhqp-riqs/rows.csv?date=20240922&accessType=DOWNLOAD")
df = df.dropna(subset=["Line"])
df["geometry"] = geopandas.GeoSeries.from_wkt(df["Line"])
df = geopandas.GeoDataFrame(df)
df = df.sjoin(neighborhoods, predicate="intersects")
df = df[["Corridor", "Limits", "BlockSide", "WeekDay", "FromHour", "ToHour", "Week1", "Week2", "Week3", "Week4", "Week5", "Holidays", "geometry", "NeighborhoodName"]]


def get_week_of_month(date):
    day = date.day
    if day > 0 and day <= 7:
        return 1
    elif day > 7 and day <= 14:
        return 2
    elif day > 14 and day <= 21:
        return 3
    elif day > 21 and day <= 28:
        return 4
    else:
        return 5


def week_aware_get_next_time(base_time, weekday, hour, week_mapping):
    next_time = get_next_time(base_time, weekday, hour)
    while not week_mapping.get(f"Week{get_week_of_month(next_time)}"):
        next_time = get_next_time(next_time, weekday, hour)
    return next_time


def get_next_time(base_time, weekday, hour):
    mapping = {"Mon": pendulum.MONDAY,
               "Tues": pendulum.TUESDAY,
               "Wed": pendulum.WEDNESDAY,
               "Thu": pendulum.THURSDAY,
               "Fri": pendulum.FRIDAY,
               "Sat": pendulum.SATURDAY,
               "Sun": pendulum.SUNDAY}
    if weekday not in mapping:
        # probably a holiday
        return base_time.add(days=1).set(hour=hour, minute=0, second=0, microsecond=0)
    ret = base_time.next(mapping.get(weekday)).set(hour=hour, minute=0, second=0, microsecond=0)
    return ret


def get_readable_time(time):
    return f"{time.format('dddd')}, {time.format('MMMM')} {time.format('Do')} at {time.format('h:mm A')}"


def get_details_string(street_identifier, blockside, cleaning_time):
    return f"Car parked at {street_identifier} on the {blockside}. Cleaning will begin {get_readable_time(cleaning_time)}."


def generate_calendar_link(start_time, end_time, readable_details):
    embedded_details = readable_details.replace(" ", "+")
    start_time_str = start_time.strftime("%Y%m%dT%H%M00")
    end_time_str = end_time.strftime("%Y%m%dT%H%M00")
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text=Street+Cleaning+Reminder&details={embedded_details}&dates={start_time_str}/{end_time_str}"


def get_readable_street_identifier(corridor, limits):
    limits = limits.replace("-", "and")
    return f"{corridor}, between {limits}"


def enrich_data(row):
    week_mapping = {f"Week{x}": row.get(f"Week{x}") for x in range(1, 6)}
    next_cleaning = week_aware_get_next_time(week_mapping=week_mapping,
                                             base_time=pendulum.now(tz='America/Los_Angeles'),
                                             weekday=row.get("WeekDay"), hour=row.get("FromHour"))
    next_cleaning_end = next_cleaning.set(hour=row.get("ToHour"))
    next_next_cleaning = week_aware_get_next_time(week_mapping=week_mapping, base_time=next_cleaning,
                                                  weekday=row.get("WeekDay"), hour=row.get("FromHour"))
    next_next_cleaning_end = next_next_cleaning.set(hour=row.get("ToHour"))

    next_cleaning_str, next_next_cleaning_str, next_cleaning_end_str, next_next_cleaning_end_str = [
        datetime.strftime("%Y%m%dT%H%M00") for datetime in
        (next_cleaning, next_next_cleaning, next_cleaning_end, next_next_cleaning_end)]

    street_identifier = get_readable_street_identifier(row.get("Corridor"), row.get("Limits"))
    row["NextCleaning"] = next_cleaning.isoformat()
    row["NextNextCleaning"] = next_next_cleaning.isoformat()
    row["NextCleaningEnd"] = next_cleaning_end.isoformat()
    row["NextNextCleaningEnd"] = next_next_cleaning_end.isoformat()
    row["NextCleaningCalendarLink"] = generate_calendar_link(next_cleaning, next_cleaning_end,
                                                             get_details_string(street_identifier, row.get("BlockSide"),
                                                                                next_cleaning))
    row["NextNextCleaningCalendarLink"] = generate_calendar_link(next_next_cleaning, next_next_cleaning_end,
                                                                 get_details_string(street_identifier,
                                                                                    row.get("BlockSide"),
                                                                                    next_next_cleaning))
    row["StreetIdentifier"] = street_identifier
    row["FileName"] = get_file_name(row["NeighborhoodName"])
    return row

df = df.apply(enrich_data, axis=1)
df = df[["Corridor", "Limits", "BlockSide", "geometry", "NeighborhoodName", "NextCleaning", "NextNextCleaning", "NextCleaningEnd", "NextNextCleaningEnd", "NextCleaningCalendarLink", "NextNextCleaningCalendarLink", "StreetIdentifier", "FileName"]]

def sort_group_and_pick_columns(df, agg_columns, sort_columns, pick_columns):
    grouped_df = df.sort_values(sort_columns)
    pick_mapping = {x:"first" for x in pick_columns}
    grouped_df = grouped_df.groupby(agg_columns).agg(pick_mapping)
    return grouped_df

def merge_grouped_df(source_df, merged_df, on_columns, renamed_names):
    ret_df = source_df.merge(merged_df, on=on_columns)
    for renamed_name in renamed_names:
        ret_df = ret_df[ret_df[f"{renamed_name}_x"] == ret_df[f"{renamed_name}_y"]].drop(f"{renamed_name}_y", axis=1)
        ret_df = ret_df.rename(columns={f"{renamed_name}_x":renamed_name})
    return ret_df

grouped_df_next_cleaning = sort_group_and_pick_columns(df, ["geometry", "BlockSide"], ["NextCleaning"], ["NextCleaning", "NextCleaningEnd", "NextCleaningCalendarLink"])
grouped_df_next_next_cleaning = sort_group_and_pick_columns(df, ["geometry", "BlockSide"], ["NextNextCleaning"], ["NextNextCleaning", "NextNextCleaningEnd", "NextNextCleaningCalendarLink"])

step_1 = merge_grouped_df(df, grouped_df_next_cleaning, on_columns=["geometry", "BlockSide"], renamed_names=["NextCleaning", "NextCleaningEnd", "NextCleaningCalendarLink"])
step_2 = merge_grouped_df(step_1, grouped_df_next_next_cleaning, on_columns=["geometry", "BlockSide"], renamed_names=["NextNextCleaning", "NextNextCleaningEnd", "NextNextCleaningCalendarLink"])

columns = ['NextCleaning', 'NextNextCleaning', 'NextCleaningEnd', 'NextNextCleaningEnd', 'NextCleaningCalendarLink', 'NextNextCleaningCalendarLink']
step_2['metadata'] = step_2[columns].to_dict(orient='records')
step_2 = step_2.drop(columns=columns)

def apply_fn(group):
    return dict(sorted(zip(group["BlockSide"], group["metadata"])))
# new_df = step_2.merge(step_2.groupby(["geometry"]).apply(apply_fn), on=["geometry"])
group_df = step_2.groupby(["geometry"])[["BlockSide", "metadata"]].apply(apply_fn).reset_index(name='Sides')
group_df = step_2.merge(group_df, on="geometry").drop(columns=["BlockSide", "metadata"]).drop_duplicates(subset="Sides")

def split_neighborhoods_and_write_to_file(df):
    sorted_df = df.sort_values(by='FileName')
    names=sorted_df['FileName'].unique().tolist()
    for name in names:
        neighborhood_df = sorted_df.loc[sorted_df["FileName"]==name].drop(columns=["FileName", "NeighborhoodName"])
        name = name.replace(" ", "-").replace(".", "").replace("/", "")
        neighborhood_df.to_file(f"{os.environ['DATA_PATH']}/neighborhoods/{name}.geojson", driver="GeoJSON")

split_neighborhoods_and_write_to_file(group_df)