import re
import scrapy
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scrapy.crawler import CrawlerProcess
from sklearn.preprocessing import OneHotEncoder


class PropertySpider(scrapy.Spider):
    name = 'property'
    allowed_domains = ['www.property.ie']

    def parse(self, response):
        urls = response.css('h2 a::attr(href)').extract()
        prices = response.css('h3::text').extract()
        addresses = response.css('h2 a::text').extract()
        bers = response.css('.ber-search-results img').extract()
        summaries = response.css('h4::text').extract()

        for url, price, address, ber, summary in zip(urls, prices, addresses,
                                                     bers, summaries):
            # format price and BER
            try:
                price = int(''.join([i for i in price if i.isdigit()]))
            except ValueError:
                price = 0

            if ber:
                ber = re.search(r'ber_(.*?)\.', ber).group(1)
            else:
                ber = ''

            # format address
            address = (address
                       .replace(', Ireland', '')
                       .replace(', Co. Dublin', '')
                       .replace('\\', '')
                       .replace('\n', '')
                       .strip())

            # process summary info
            summary = summary.replace('\n', '').strip()

            num_beds = re.search(r'(\d+) Bed', summary)
            num_beds = num_beds.group(1) if num_beds else ''
            num_baths = re.search(r'(\d+) Bath', summary)
            num_baths = num_baths.group(1) if num_baths else ''
            property_type = summary.split(',')[-1].strip()
            postcode = re.findall(r'Dublin (\d+)', address)

            yield {
                'URL': url,
                'Price': price,
                'Address': address,
                'Postcode': postcode[0] if postcode else '',
                'Property': property_type,
                'Bedrooms': num_beds,
                'Bathrooms': num_baths,
                'BER': ber,
            }

        pages = response.css('#pages a').extract()
        contains_next = ['Next' in p for p in pages]
        next_button = any(contains_next)

        if next_button:
            next_url_idx = contains_next.index(True)
            next_url = pages[next_url_idx].split('"')[1]
            yield response.follow(next_url, self.parse)


def crawl(link):
    process = CrawlerProcess(settings={
        "FEEDS": {"results.json":
                  {"format": "json", "overwrite": True}
                  },
        'CONCURRENT_REQUESTS': 16,
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
        },
        'LOG_LEVEL': 'INFO'
    })
    process.crawl(PropertySpider, start_urls=[link])
    process.start()  # script will block here until crawling is finished


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
    # extract data from website
    LINK = 'https://www.property.ie/property-for-sale/dublin/'
    crawl(LINK)

    df = pd.read_json('results.json')
    df['Postcode'] = 'D' + df['Postcode'].str.zfill(2)
    clean = transform(df)
    clean.to_csv('results.csv', index=False)
