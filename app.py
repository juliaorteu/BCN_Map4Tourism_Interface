
##################################
### Map4Tourism - Tourism Tool ###
##################################

# Imports
import folium
from streamlit_folium import folium_static
import numpy as np
from DataPreparationPipeline import *

st.write("""
    <div style="display:flex;align-items:center;">
        <img src="data:image/png;base64,{}" width="110">
        <h1 style="margin-left:10px;">BCN Map4Tourism</h1>       
    </div>
""".format(get_base64_of_bin_file("images/logo.png")), unsafe_allow_html=True)
st.write("Welcome! Choose your neighborhood 🏘️ and explore local restaurants alongside crime rate \n statistics for a more informed experience. 😊🍽️📊")


# Selection of neighbourhoods to visualize
selected_neighborhoods = {}
with st.sidebar.expander("Neighborhoods"):
    col1, col2 = st.columns([2, 1])
    for neighborhood, color in colors.items():
        is_selected = col1.checkbox(f"{neighborhood}", key=f"chk_{neighborhood}")
        selected_neighborhoods[neighborhood] = is_selected
        col2.markdown(f"<span style='display: inline-block; width: 12px; height: 12px; background: {color}; margin-left: 10px;'></span>", unsafe_allow_html=True)


# !!!!!!Attention!!!!!_____________________________________________________________________________________
# Limited computational resources may restrict rendering capabilities locally 
# Additional resources would enable processing of larger datasets.
# --> Constarint less apartments for visualization in local:  num_samples/1000 -- only 10% of the total data
# --> If you have resources descoment the indicated line
num_samples = st.sidebar.slider("Percentage of Locations Displayed", min_value=1, max_value=100, value=20)
#sampled_data = df_airbnb.sample(withReplacement=False, fraction=num_samples/100, seed=42) # MORE RESOURCES
sampled_data = df_airbnb.sample(withReplacement=False, fraction=num_samples/1000, seed=42) # LESS RESOURCES
sampled_locations = df_locations.sample(withReplacement=False, fraction=num_samples/100, seed=42) 
#__________________________________________________________________________________________________________


# Sampled data filtered based on user selection
sampled_data = filter_apartments(sampled_data)

filtered_data = sampled_data[sampled_data['neighbourhood'].isin([neighborhood for neighborhood, selected in selected_neighborhoods.items() if selected])]
filtered_locations = sampled_locations[sampled_locations['neighbourhood'].isin([neighborhood for neighborhood, selected in selected_neighborhoods.items() if selected])]

# Display the number of apartments & Locations
st.markdown(f'''
<div style="
    border-radius: 10px;
    border: 2px solid #ff9832;
    padding: 15px;
    margin-top: 5px;
    margin-bottom: 5px;
    font-size: 16px;
    color: #ff9832;
    background-color: #ffffff;
    box-shadow: 2px 2px 12px rgba(0,0,0,0.1);">
    <b> Displayed Apartments </b> {filtered_data.count()}
</div>
''', unsafe_allow_html=True)

# users choose if see  restaurants_attractions
show_restaurants_attractions = st.checkbox("Show Restaurants & Attractions")
# Creation of a map visualization of Barcelona
m = folium.Map(location=[41.3879, 2.1699], zoom_start=12)

if show_restaurants_attractions:
    min_rating = st.slider("🧹 Filter by Minimum Rating", min_value=0, max_value=10, value=5)
    filtered_locations = filtered_locations.filter(filtered_locations['avg_rating'] >= min_rating)

    for row in filtered_locations.collect():
        emoji = "🍽️" if row['type'] == "restaurant" else "📌"
        popup_content = popup_content_review(row, df_reviews, emoji)
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_content, max_width=600),  # Popup con nombre y tipo
            tooltip=f"{emoji} {row['type']} ",
            icon=folium.Icon(color=colors.get(row['neighbourhood'], 'gray'), icon=location_icons.get(row['type']))
        ).add_to(m)



    st.markdown(f'''
    <div style="
        border-radius: 10px;
        border: 2px solid #a26464;
        padding: 15px;
        margin-top: 5px;
        margin-bottom: 5px;
        font-size: 16px;
        color: #a26464;
        background-color: #ffffff;
        box-shadow: 2px 2px 12px rgba(0,0,0,0.1);">
        <b>Displayed Restaurants </b> {filtered_locations.filter(filtered_locations['type'] == 'restaurant').count()}<br>
        <b>Displayed Attractions </b> {filtered_locations.filter(filtered_locations['type'] == 'attraction').count()}
    </div>
    ''', unsafe_allow_html=True)

for row in filtered_data.collect():
    neighbourhood = row['neighbourhood']
    marker_color = colors.get(neighbourhood, 'gray')  
    description = '🏠 ' + row['property_type'] + '\n\n' + 'Price ' + str(row['price']) + " €"

    popup_content = """
                    <p>{summary}</p>
                    <b>🌟 Review Score: {review_scores_rating}<b>
                    <p>💲 Price: {price} €</p>
                    <p>🔒 Security Deposit: {security_deposit} €</p>
                    <p>🧹 Cleaning Fee: {cleaning_fee} €</p>
                    <p>🚽 Bathrooms: {bathrooms}</p>
                    <p>🛌 Beds: {beds}</p>
                    <p>    ➡️ Type: {bed_type}</p>
                    """.format(
                        summary='🏠 ' + row['Name'],
                        review_scores_rating=int(row['review_scores_value']),
                        price=row['price'],
                        security_deposit=row['security_deposit'],
                        cleaning_fee=row['cleaning_fee'],
                        bathrooms=row['bathrooms'],
                        beds=row['beds'],
                        bed_type=row['bed_type']
                    )
    # Crear el marcador con el color especificado
    folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup = folium.Popup(popup_content, max_width=300),
        tooltip=f"{description}",
        icon=folium.Icon(color=marker_color, icon='home', prefix='fa')
    ).add_to(m)

# Show the map
folium_static(m)


# Criminal Analysis 

top_crimes_by_neighborhood, total_crimes_all_neighborhoods = criminal_implementation(df_criminal, selected_neighborhoods)

st.subheader("Top 5 Crime Types by Neighborhood")
if not top_crimes_by_neighborhood.empty:
    grouped = top_crimes_by_neighborhood.groupby('area_basica_policial')
    neighborhoods = list(grouped.groups.keys())
    highest_risk_neighborhood = None
    highest_crime_ratio = 0
    for i in range(0, len(neighborhoods), 2):  
        cols = st.columns(2)  
        for j in range(2):
            if i + j < len(neighborhoods):  
                name = neighborhoods[i + j]
                group = grouped.get_group(name)
                with cols[j]:  
                    st.markdown(f"###### 📍 {name}")
                    display_group = group[['ambit_fet', 'percentage']].copy()
                    display_group = display_group.rename(columns={'ambit_fet': 'Crimes', 'percentage': 'Percentage'})
                    st.dataframe(display_group.sort_values(by='Percentage', ascending=False).head(5).set_index('Crimes'))
                    total_crimes_neighborhood = group['total_count'].iloc[0]
                    crime_ratio = total_crimes_neighborhood / total_crimes_all_neighborhoods
                    st.markdown(f"**Crime Ratio**  {crime_ratio:.2f}")

                    if crime_ratio > highest_crime_ratio:
                        highest_crime_ratio = crime_ratio
                        highest_risk_neighborhood = name

    if highest_risk_neighborhood:
        st.markdown(f'<div style="background-color: #FFCCCC; color: maroon; padding: 10px; border-radius: 10px; border: 2px solid maroon; font-size: 20px;"><span style="font-size: 24px;">⚠️</span> <strong>Highest Risk Neighborhood:</strong> {highest_risk_neighborhood}</div>', unsafe_allow_html=True)
else:
    st.write("No criminality data available.")






