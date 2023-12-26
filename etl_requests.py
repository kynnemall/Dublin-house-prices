import re
import json
import requests
import concurrent
import requests_random_user_agent
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from scipy.sparse import csr_matrix
from sklearn.preprocessing import OneHotEncoder

START_URL = 'https://www.property.ie/property-for-sale/dublin/'
BASE_URL = 'https://www.property.ie/property-for-sale/dublin/price_international_rental-onceoff_standard/p_XXX/'


def scrape_page(url, return_soup=False):
    response = requests.get(url, headers={'referer': 'https://www.google.com/'})
    good_response = '200' in str(response)
    if good_response:
        soup = BeautifulSoup(response.content, 'lxml')

        # get addresses and format
        items = soup.find_all('div', {'class': 'sresult_address'})
        addresses = [e.a.text for e in items]
        postcodes = [re.findall('(Dublin \d+)', a) for a in addresses]
        links = [e.a['href'] for e in items]

        # get bedrooms, bathrooms, and property type
        summaries = [tag.text for tag in soup.find_all('h4')]
        summaries = [s.replace('\n', '').strip() for s in summaries]

        # get BER
        imgs = [e.img for e in soup.find_all(
            'div', class_='ber-search-results')]
        bers = []
        for i in imgs:
            if hasattr(i, 'src'):
                ber = re.findall(r'ber_(.*?).png', i['src'])
                if not ber:
                    ber = ''
                else:
                    ber = ber[0]
                bers.append(ber)
            else:
                bers.append('')

        # get prices and format
        prices = [e.text for e in soup.find_all('h3')]
        prices = [re.findall(r'€(\d+,\d+,\d+|\d+,\d+)', p) for p in prices]
        prices = [int(p[0].replace(',', '')) if p else p for p in prices]

        data = []
        for address, code, price, link in zip(addresses, postcodes, prices, links, bers, summaries):

            data.append([code[0], price, link])
    else:
        print('Bad response:\t' + str(response))

    if return_soup and good_response:
        return data, soup
    else:
        return data


def scrape_properties():
    data, soup = scrape_page(START_URL, return_soup=True)

    # get number of pages
    links = [a.text for a in soup.find_all('a')]
    next_idx = [links.index(i) for i in links if i.strip().startswith('Next')]
    N = int(links[next_idx[0] - 1])
    nums = [str(n) for n in range(2, N+1)]
    urls = [BASE_URL.replace('XXX', n) for n in nums]

    # multithreading approach to make multiple requests
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(scrape_page, url) for url in urls]
    results = [future.result() for future in futures]
    for r in results:
        data.extend(r)

    # save scraped data
    print(f'Saving data on {len(data)} properties')
    with open('data/results1.json', 'w') as f:
        json.dump(data, f)


def onehot_encode_series(series):
    encoder = OneHotEncoder()
    var = series.values.reshape(-1, 1)
    encoder.fit(var)
    onehot = encoder.transform(var)
    if isinstance(onehot, csr_matrix):
        onehot = onehot.toarray()

    # roughly 8x memory savings by using Boolean dtype for dense matrix
    onehot = pd.DataFrame(
        onehot, columns=encoder.categories_[0], index=series.index
    ).astype(bool)
    return onehot


def transform(df):
    # format numeric columns
    clean = df[df['Price'] > 0]
    clean.replace('', np.nan, inplace=True)
    for c in ('Bedrooms', 'Price', 'Bathrooms'):
        clean[c] = clean[c].astype(float)

    # adjust postcodes to allow other regions
    codes = clean[clean['Postcode'] != 'D00']
    nocodes = clean[clean['Postcode'] == 'D00']
    nocodes['Postcode'] = nocodes['Address'].str.split(', ').str[-1]
    counts = nocodes['Postcode'].value_counts()
    keep = counts[counts >= 10].index
    nocodes = nocodes[nocodes['Postcode'].isin(keep)]
    clean = pd.concat([codes, nocodes])

    # subset data to remove outlier properties
    clean = (clean[
        (clean['Price'] < 7e5) &
        ~(clean['Property'].str.contains('Group'))
    ])
    clean['Property'] = clean['Property'].str.replace(' For Sale', '')

    # one-hot encodings
    clean['BER'].fillna('Unrated', inplace=True)
    ber_onehot = onehot_encode_series(clean['BER'])
    post_onehot = onehot_encode_series(clean['Postcode'])
    prop_onehot = onehot_encode_series(clean['Property'])

    clean = pd.concat(
        [clean.drop(columns='Address'), post_onehot, ber_onehot, prop_onehot],
        axis=1)
    clean.dropna(inplace=True)

    # filter out too many bathrooms and bedrooms
    clean = clean[(clean['Bedrooms'] < 7) & (clean['Bathrooms'] < 5)]

    # remove property types present in less than 100 samples
    counts = clean['Property'].value_counts()
    keep = counts[counts >= 100].index
    clean = clean[clean['Property'].isin(keep)]

    return clean


if __name__ == '__main__':
    scrape_properties()
    df = pd.read_json('data/results1.json')
    clean = transform(df)
    # clean.to_csv('data/clean.csv', index=False)
