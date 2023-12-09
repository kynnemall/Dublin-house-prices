import streamlit as st


tab_titles = ['Properties Table', 'Graphs']
table, graphs = st.tabs(tab_titles)

with table:
    df = st.session_state['df']
    ber_options = [''] + sorted(df['BER'].unique())
    zip_options = [''] + sorted(df['Postcode'].unique())

    col1, col2 = st.columns(2)
    ber = col1.selectbox('Select BER', ber_options)
    code = col2.selectbox('Select Postcode', ber_options)

    # ranges for bedrooms, bathrooms, and prices
    bed_low, bed_hi = 1, int(df['Bedrooms'].max())
    low_bed, hi_bed = col1.slider(
        'Select range for # bedrooms', bed_low, bed_hi, (bed_low, bed_hi), step=1
    )

    bath_low, bath_hi = 1, int(df['Bathrooms'].max())
    low_bath, hi_bath = col2.slider(
        'Select range for # bathrooms', bath_low, bath_hi, (bath_low, bath_hi),
        step=1
    )

    low_price, high_price = 1, int(df['Price'].max())
    low, high = st.slider(
        'Select Price range', low_price, high_price, (low_price, high_price),
        step=5000
    )

    # filter dataframe
    fdf = df[(df['Price'] >= low) & (df['Price'] <= high)
             & (df['Bedrooms'] >= low_bed) & (df['Bedrooms'] <= hi_bed)
             & (df['Bathrooms'] >= low_bath) & (df['Bathrooms'] <= hi_bath)]
    if code:
        fdf = fdf[fdf['Postcode'] == code]
    if ber:
        fdf = fdf[df['BER'] == ber]

    st.session_state['fdf'] = fdf
    st.dataframe(fdf)

with graphs:
    pass
