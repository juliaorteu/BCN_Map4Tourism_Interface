#################################
### Data Preparation Pipeline ###
#################################

## Description:

## Imports
import streamlit as st
import duckdb
import pyspark
from pyspark.sql import SparkSession
from pprint import pprint
from pyspark.sql.functions import concat_ws, expr, split, when, count, collect_list, col,rand, regexp_replace, trim, min, max, avg, coalesce
import warnings
import matplotlib.pyplot as plt
from pyspark.sql.functions import udf
from pyspark.sql.types import FloatType, ArrayType, StructType, StructField
import pickle
import random
from pyspark.sql import functions as F
import pandas as pd 
import base64

## Connection to formatted database
jdbc_url = 'jdbc:duckdb:./data/barcelona_processed.db'
driver = "org.duckdb.DuckDBDriver"

# Loading the trusted datasets for explotation
##############################################
# SparkSession inicialitzation
spark = SparkSession.builder\
    .config("spark.jars", "duckdb.jar") \
    .appName("DataPreparation") \
    .getOrCreate()

# Loading airbnb data
df_airbnb = spark.read \
  .format("jdbc") \
  .option("url", jdbc_url) \
  .option("driver", driver) \
  .option("query", "SELECT * FROM df_airbnb_listings") \
  .load()

# Criminal Dataset
df_criminal = spark.read \
  .format("jdbc") \
  .option("url", jdbc_url) \
  .option("driver", driver) \
  .option("query", "SELECT * FROM df_criminal_dataset") \
  .load()

# Loading location data
df_locations = spark.read \
  .format("jdbc") \
  .option("url", jdbc_url) \
  .option("driver", driver) \
  .option("query", "SELECT * FROM df_tripadvisor_locations") \
  .load()

# Loading reviews data
df_reviews = spark.read \
  .format("jdbc") \
  .option("url", jdbc_url) \
  .option("driver", driver) \
  .option("query", "SELECT * FROM df_tripadvisor_reviews") \
  .load()

# Calculate the average rating per location_id
avg_ratings = df_reviews.groupBy('location_id').agg(avg('rating').alias('avg_rating'))
# Join the locations DataFrame with the average ratings DataFrame
df_locations = df_locations.join(avg_ratings, on='location_id', how='left')


# Dics for visualization
colors = {
    'Gràcia': 'lightblue',
    'Sant Martí': 'green',
    'Horta-Guinardó': 'red',
    'Les Corts': 'purple', 
    'Sants-Montjuïc': 'orange',
    'Nou Barris': 'pink',
    'Sarrià-Sant Gervasi': 'cadetblue',
    'Eixample': 'beige',
    'Sant Andreu': 'lightgray',
    'Ciutat Vella': 'lightgreen'
}

location_icons = {
    'restaurant': 'cutlery',
    'attraction': 'star'
}


# Important Selectings functions
def filter_apartments(data_frame):
    with st.sidebar.expander(" 🧹 Apartments Filtration"):
        
        # Minimum review score selection
        review_min = st.slider("🌟 Review Score", min_value=0, max_value=10, value=7)
        data_frame = data_frame.filter(data_frame['review_scores_value'] >= review_min)

        # Maximum price selection
        price_max = st.slider("Maximum Price per Night", min_value=0, max_value=int(data_frame.select(max("price")).first()[0]), value=80)
        data_frame = data_frame.filter(data_frame['price'] < price_max)
    
        
        # Checkbox to activate more filters
        more_filters_active = st.checkbox("More Filtration")
        if more_filters_active:
            # Checkbox to filter by room type
            room_types = data_frame.select("room_type").distinct().rdd.flatMap(lambda x: x).collect()
            selected_room_types = st.multiselect("Room Types", room_types, default=room_types)
            data_frame = data_frame.filter(data_frame['room_type'].isin(selected_room_types))
            
            # Filter by minimum number of bathrooms
            bathrooms_min = st.slider("Minimum Bathrooms", min_value=0, max_value=int(data_frame.select(max("bathrooms")).first()[0]), value=0)
            data_frame = data_frame.filter(data_frame['bathrooms'] >= bathrooms_min)
            
            # Filter by minimum number of beds
            beds_min = st.slider("Minimum Beds", min_value=0, max_value=int(data_frame.select(max("beds")).first()[0]), value=0)
            data_frame = data_frame.filter(data_frame['beds'] >= beds_min)
            
            # Filter by minimum number of nights
            min_nights = st.slider("Minimum Nights", min_value=0, max_value=int(data_frame.select(max("minimum_nights")).first()[0]), value=0)
            data_frame = data_frame.filter(data_frame['minimum_nights'] >= min_nights)
            

        
    return data_frame

## Criminal visualization in Barcelona
def criminal_implementation(dataset, selected_neighborhoods):
    selected_neighborhoods_list = [neighborhood for neighborhood, selected in selected_neighborhoods.items() if selected]
    filtered_criminal_data = dataset.filter(dataset['area_basica_policial'].isin(selected_neighborhoods_list))

    # Count crime types per neighborhood
    crime_counts = filtered_criminal_data.groupBy('area_basica_policial', 'ambit_fet').count()

    # Calculate total crimes per neighborhood
    total_crimes = crime_counts.groupBy('area_basica_policial').sum('count').withColumnRenamed("sum(count)", "total_count")
    
    # Join total crimes per neighborhood with crime details
    crime_details = crime_counts.join(total_crimes, 'area_basica_policial')
    total_crimes_all_neighborhoods = total_crimes.groupBy().sum('total_count').collect()[0][0]

    # Calculate percentage of each crime type relative to neighborhood total
    crime_percentages = crime_details.withColumn(
        "percentage",
        F.round((crime_details['count'] / crime_details['total_count']) * 100, 2)
    ).select(
        'area_basica_policial', 'ambit_fet', 'percentage', 'total_count'
    ).orderBy('area_basica_policial', 'percentage', ascending=False)

    # Convert to Pandas DataFrame for easier visualization in Streamlit
    crime_percentages_pandas = crime_percentages.toPandas()
    return crime_percentages_pandas, total_crimes_all_neighborhoods

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def popup_content_review(location_info, reviews_data, emoji):
    # Filter reviews data for the given location_id
    filtered_reviews = reviews_data.filter(reviews_data['location_id'] == location_info['location_id'])
    
    if filtered_reviews.count() == 0:
        # No reviews available for the location
        popup_content = f"""
        <h3>{location_info['name']}</h3>
        <p><strong>🌟 Rating:</strong> {location_info['avg_rating']}</p>
        <p>No Reviews yet</p>
        """
    else:
        # Randomly select a review
        random_review = filtered_reviews.orderBy(rand()).limit(1).collect()[0]
        # Construct popup content
        popup_content = f"""
        <h3> {emoji} {location_info['name']}</h3>
        <h4>🌟 Average Rating = {location_info['avg_rating']:.2f}</h4>
        <div style="display: flex; align-items: center;">
            <img src="{random_review['user_avatar_small']}" style="width: 50px; height: 50px; margin-right: 10px;">
            <h4>@{random_review['user_username']}</h4>
        </div>
        <p>(random reviewer)<p>
        <strong>Rating: </strong>{random_review['rating']}</p>
        <p><strong>{random_review['title']}</strong></p>
        <p><strong>Text: </strong>{random_review['text']}</p>
        """
    return popup_content

