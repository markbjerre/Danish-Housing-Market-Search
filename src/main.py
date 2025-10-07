import streamlit as st
import folium
from streamlit_folium import st_folium
from .data_loader import DataLoader
from .scoring import PropertyScorer

def main():
    st.title("Danish Housing Market Analysis")
    
    # Initialize components
    data_loader = DataLoader()
    scorer = PropertyScorer()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    min_price = st.sidebar.number_input("Minimum Price (DKK)", value=0)
    max_price = st.sidebar.number_input("Maximum Price (DKK)", value=10000000)
    min_size = st.sidebar.number_input("Minimum Size (m²)", value=0)
    property_type = st.sidebar.selectbox(
        "Property Type",
        ["All", "House", "Apartment", "Villa"]
    )
    
    try:
        # Load properties
        properties = data_loader.load_properties("properties.csv")
        
        # Filter properties
        filtered_properties = [
            p for p in properties
            if p.price >= min_price
            and p.price <= max_price
            and p.square_meters >= min_size
            and (property_type == "All" or p.property_type == property_type)
        ]
        
        # Score properties
        for property in filtered_properties:
            property.score = scorer.score_property(property, properties)
        
        # Create map
        m = folium.Map(location=[56.2639, 9.5018], zoom_start=7)  # Center on Denmark
        
        # Add properties to map
        for property in filtered_properties:
            folium.Marker(
                [property.latitude, property.longitude],
                popup=f"{property.address}<br>Price: {property.price:,.0f} DKK<br>Size: {property.square_meters} m²<br>Score: {property.score:.1f}",
            ).add_to(m)
        
        # Display map
        st_folium(m, width=800, height=600)
        
        # Display property list
        st.header("Property List")
        for property in sorted(filtered_properties, key=lambda p: p.score, reverse=True):
            st.write(f"---")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{property.address}**")
                st.write(f"Type: {property.property_type}")
            with col2:
                st.write(f"Price: {property.price:,.0f} DKK")
                st.write(f"Score: {property.score:.1f}/100")
    
    except FileNotFoundError:
        st.error("No property data found. Please add a properties.csv file to the data directory.")

if __name__ == "__main__":
    main()