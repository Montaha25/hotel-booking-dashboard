# Hotel Booking Dashboard

An interactive Streamlit dashboard built on the Kaggle "Hotel Booking Demand" dataset (bookings July 2015 to August 2017).

## Run it

```bash
pip install -r requirements.txt
python prepare_data.py path/to/hotel_bookings.csv   # cleans the raw data
streamlit run app.py
```
## Live demo

[Open the dashboard](https://hotel-booking-insights.streamlit.app)
## What it shows

- Headline KPIs: bookings, cancellation rate, average daily rate, estimated revenue from stays
- Monthly bookings by hotel
- Cancellation rate by lead time
- Top 10 countries of origin
- Average daily rate by month and hotel
- Bookings and cancellation rate by room type, and bookings by market segment
- Sidebar filters for hotel, arrival date and zero-rate bookings

## Cleaning decisions

- Exact duplicate rows removed (about 32,000)
- Bookings with zero guests or zero nights removed
- Missing children set to 0, missing country set to "Unknown", missing agent and company set to 0 (no agent or company)
- Zero-rate bookings excluded from rate and revenue figures by default
- Revenue is estimated as daily rate times nights for bookings not canceled; it is not billing data
