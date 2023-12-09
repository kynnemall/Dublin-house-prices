import numpy as np
import pandas as pd
import streamlit as st


# TODO
# page for plotting regression coefficients and showing results

@st.cache_data
def load_data():
    df = pd.read_json('results.json')
    df['Postcode'] = df['Postcode'].replace('', 'NA')
    df.replace('', np.nan, inplace=True)
    for c in ('Bedrooms', 'Price', 'Bathrooms'):
        df[c] = df[c].astype(float)
    st.session_state['df'] = df


@st.cache_data
def load_clean_data():
    clean = pd.read_csv('clean.csv')
    st.session_state['clean'] = clean


@st.cache_resource
def load_model():
    pass


st.header('Dublin Property Prices App')
st.markdown(
    """
    Searching for a property in Dublin but unsure what to make of the price?
    Then this app is for you!
    
    The **Search** page allows you to filter properties and view the shortlisted
    properties in table format. You can expand this table view by hovering over
    it and clicking the 'View Fullscreen' button when it appears.
    
    The **Stats** page allows you to see how machine learning may predict house
    prices based on BER rating, Dublin postcode, the number
    of bedrooms, and the number of bathrooms.
    """
)

with st.expander('Notes'):
    st.subheader('General')
    st.markdown(
        """
        All data were extracted from www.property.ie in accordance with
        web scraping rules for the domain in question. The data presented
        herein are accurate to within 3 days of posting.
        """
    )

    st.subheader('Disclaimer')
    st.markdown(
        """
        House price predictions were generated using an artificial intelligence 
        model based on factors such as Building Energy Rating (BER), postcode, 
        number of bedrooms, and number of bathrooms. The primary purpose of 
        this app is to aid users in understanding whether property prices may 
        be over or under an expected value based on the provided information.

        It is important to note that the predicted values are model 
        approximations and should not be regarded as definitive or guaranteed 
        prices. This app is also part of a small project aimed at 
        investigating how available property specifications may influence 
        market prices.

        Real estate markets are intricate and influenced by various dynamic 
        factors such as supply and demand. The AI model may not account for all 
        these variables, and users are advised to use the predicted values as 
        general estimates rather than precise indicators.
        """
    )

# load data
load_data()
load_clean_data()
