import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Hotel Booking Insights", layout="wide")

HOTEL_COLORS = {"City Hotel": "#4C78A8", "Resort Hotel": "#F58518"}
TEMPLATE = "plotly_dark"


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["arrival_date", "reservation_status_date"])
    df["arrival_month"] = df["arrival_date"].dt.to_period("M").dt.to_timestamp()
    bins = [-1, 7, 30, 90, 180, 365, 10_000]
    labels = ["0-7 days", "8-30 days", "31-90 days", "91-180 days", "181-365 days", "Over 365 days"]
    df["lead_time_group"] = pd.cut(df["lead_time"], bins=bins, labels=labels)
    return df


def style(fig, height=420):
    fig.update_layout(template=TEMPLATE, height=height, margin=dict(l=10, r=10, t=60, b=10),
                      legend_title_text="", title_font_size=18)
    return fig


df = load_data("hotel_bookings_clean.csv")

# Sidebar
ALL_HOTELS = sorted(df["hotel"].unique())
MIN_DATE, MAX_DATE = df["arrival_date"].min().date(), df["arrival_date"].max().date()

st.session_state.setdefault("hotel_filter", ALL_HOTELS)
st.session_state.setdefault("date_filter", (MIN_DATE, MAX_DATE))
st.session_state.setdefault("zero_rate_filter", False)


def reset_filters():
    st.session_state["hotel_filter"] = ALL_HOTELS
    st.session_state["date_filter"] = (MIN_DATE, MAX_DATE)
    st.session_state["zero_rate_filter"] = False


def hotel_dot(name: str) -> str:
    return f'<span style="color:{HOTEL_COLORS.get(name, "#999")};font-size:16px;">&#9679;</span> {name}'


st.sidebar.markdown(
    """
    <div style="padding:16px 18px;border-radius:14px;margin-bottom:14px;
                background:linear-gradient(135deg,#1d3557 0%,#2a6f97 100%);">
        <div style="font-size:19px;font-weight:700;color:#ffffff;letter-spacing:0.2px;">Hotel Insights</div>
        <div style="font-size:13px;color:#cfe3f3;margin-top:4px;">
            Explore bookings, cancellations and rates
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Placeholder filled once the filters have been read
summary = st.sidebar.container()

st.sidebar.markdown("##### Hotels")
st.sidebar.markdown(
    " &nbsp;&nbsp; ".join(hotel_dot(h) for h in ALL_HOTELS), unsafe_allow_html=True
)
hotels = st.sidebar.multiselect(
    "Hotels",
    ALL_HOTELS,
    key="hotel_filter",
    label_visibility="collapsed",
    help="Select one or both hotels.",
)

st.sidebar.markdown("##### Arrival period")
date_range = st.sidebar.date_input(
    "Arrival period",
    key="date_filter",
    min_value=MIN_DATE,
    max_value=MAX_DATE,
    label_visibility="collapsed",
    help="Pick a start and end date. Bookings arriving in this range are shown.",
)

with st.sidebar.expander("Advanced options"):
    include_zero_rate = st.checkbox(
        "Include zero-rate bookings",
        key="zero_rate_filter",
        help="Zero-rate bookings are often complimentary stays or data errors, so they are excluded by default.",
    )

st.sidebar.divider()
st.sidebar.button("Reset filters", on_click=reset_filters)

start, end = (date_range if len(date_range) == 2 else (MIN_DATE, MAX_DATE))
filtered = df[df["hotel"].isin(hotels)
              & (df["arrival_date"].dt.date >= start)
              & (df["arrival_date"].dt.date <= end)]
priced = filtered if include_zero_rate else filtered[~filtered["is_zero_adr"]]

with summary:
    st.markdown("##### Current view")
    st.markdown(
        " &nbsp; ".join(hotel_dot(h) for h in hotels) or "No hotel selected",
        unsafe_allow_html=True,
    )
    st.caption(f"{start:%d %b %Y} to {end:%d %b %Y}")
    st.metric("Bookings in view", f"{len(filtered):,}")

if filtered.empty:
    st.warning("No bookings match these filters. Adjust the hotel or date selection.")
    st.stop()

# Header
st.title("Hotel Booking Insights")
st.markdown(
    f"Covering **{start:%B %Y}** to **{end:%B %Y}** for **{len(hotels)} hotel(s)**. "
    "Use the filters on the left to explore."
)

# KPIs
total = len(filtered)
cancel_rate = filtered["is_canceled"].mean() * 100
avg_adr = priced["adr"].mean()
revenue = priced.loc[priced["is_canceled"] == 0, "revenue"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Bookings", f"{total:,}")
k2.metric("Cancellation rate", f"{cancel_rate:.1f}%")
k3.metric("Average daily rate", f"{avg_adr:,.0f}")
k4.metric("Estimated stay revenue", f"{revenue / 1e6:,.1f}M", help="Daily rate x nights, bookings not canceled. Estimate, not billing data.")

# Insights calculated from the filtered data
monthly_totals = filtered.groupby("arrival_month").size()
busiest_month = monthly_totals.idxmax()
lead_cancel = filtered.groupby("lead_time_group", observed=True)["is_canceled"].mean() * 100
riskiest_lead = lead_cancel.idxmax()
top_country = filtered["country"].value_counts(normalize=True).head(1)
top_country_name, top_country_share = top_country.index[0], top_country.iloc[0] * 100

st.subheader("Key insights")
i1, i2, i3 = st.columns(3)
i1.info(f"**Busiest month:** {busiest_month:%B %Y} with {monthly_totals.max():,} arrivals.")
i2.warning(f"**Highest cancellation risk:** bookings made {riskiest_lead.lower()} ahead cancel at {lead_cancel.max():.0f}%.")
i3.success(f"**Largest source market:** {top_country_name} accounts for {top_country_share:.0f}% of bookings.")

tab_overview, tab_cancel, tab_pricing, tab_market = st.tabs(
    ["Overview", "Cancellations", "Pricing", "Guests and rooms"]
)

with tab_overview:
    monthly = filtered.groupby(["arrival_month", "hotel"]).size().reset_index(name="bookings")
    fig = px.line(monthly, x="arrival_month", y="bookings", color="hotel", markers=True,
                  color_discrete_map=HOTEL_COLORS,
                  labels={"arrival_month": "Arrival month", "bookings": "Bookings", "hotel": "Hotel"},
                  title="Monthly arrivals by hotel")
    st.plotly_chart(style(fig, 440), width="stretch")

    c1, c2 = st.columns(2)
    countries = filtered["country"].value_counts().head(10).reset_index()
    countries.columns = ["country", "bookings"]
    fig_c = px.bar(countries, x="bookings", y="country", orientation="h",
                   labels={"country": "Country", "bookings": "Bookings"},
                   title="Top 10 countries of origin", color_discrete_sequence=["#72B7B2"])
    fig_c.update_layout(yaxis={"categoryorder": "total ascending"})
    c1.plotly_chart(style(fig_c), width="stretch")

    segment = filtered.groupby("market_segment").size().reset_index(name="bookings")
    fig_s = px.pie(segment, names="market_segment", values="bookings", hole=0.45,
                   title="Bookings by market segment")
    c2.plotly_chart(style(fig_s), width="stretch")

with tab_cancel:
    lead = lead_cancel.reset_index(name="cancel_rate_pct")
    fig_l = px.bar(lead, x="lead_time_group", y="cancel_rate_pct",
                   labels={"lead_time_group": "Booked how far ahead", "cancel_rate_pct": "Cancellation rate (%)"},
                   title="Cancellation rate by lead time", color="cancel_rate_pct",
                   color_continuous_scale="Reds")
    st.plotly_chart(style(fig_l), width="stretch")

    by_hotel = (filtered.groupby("hotel")["is_canceled"].mean().mul(100).reset_index(name="cancel_rate_pct"))
    fig_h = px.bar(by_hotel, x="hotel", y="cancel_rate_pct", color="hotel",
                   color_discrete_map=HOTEL_COLORS,
                   labels={"hotel": "Hotel", "cancel_rate_pct": "Cancellation rate (%)"},
                   title="Cancellation rate by hotel")
    st.plotly_chart(style(fig_h, 360), width="stretch")

with tab_pricing:
    adr_month = priced.groupby(["arrival_month", "hotel"])["adr"].mean().reset_index()
    fig_a = px.line(adr_month, x="arrival_month", y="adr", color="hotel", markers=True,
                    color_discrete_map=HOTEL_COLORS,
                    labels={"arrival_month": "Arrival month", "adr": "Average daily rate", "hotel": "Hotel"},
                    title="Average daily rate by month")
    st.plotly_chart(style(fig_a, 440), width="stretch")

    fig_box = px.box(priced, x="hotel", y="adr", color="hotel", color_discrete_map=HOTEL_COLORS,
                     labels={"hotel": "Hotel", "adr": "Daily rate"},
                     title="Spread of daily rates by hotel (rates above the 99th percentile are hidden)")
    fig_box.update_yaxes(range=[0, priced["adr"].quantile(0.99)])
    st.plotly_chart(style(fig_box, 380), width="stretch")

with tab_market:
    g1, g2 = st.columns(2)
    room = (filtered.groupby("reserved_room_type")
            .agg(bookings=("hotel", "size"), cancel_rate_pct=("is_canceled", lambda s: s.mean() * 100))
            .reset_index())
    fig_r = px.bar(room, x="reserved_room_type", y="bookings", color="cancel_rate_pct",
                   color_continuous_scale="Blues",
                   labels={"reserved_room_type": "Reserved room type", "bookings": "Bookings",
                           "cancel_rate_pct": "Cancel rate (%)"},
                   title="Bookings and cancel rate by room type")
    g1.plotly_chart(style(fig_r), width="stretch")

    guests = filtered.groupby(["total_guests"]).size().reset_index(name="bookings")
    guests = guests[guests["total_guests"] <= 6]
    fig_g = px.bar(guests, x="total_guests", y="bookings",
                   labels={"total_guests": "Guests per booking", "bookings": "Bookings"},
                   title="Party size (up to 6 guests)", color_discrete_sequence=["#B279A2"])
    g2.plotly_chart(style(fig_g), width="stretch")

st.divider()
with st.expander("Data preparation and assumptions"):
    st.markdown(
        """
- **Duplicates:** Exact duplicate rows were removed. Some may be genuinely separate bookings with identical fields, so this is a judgement call.
- **Missing values:** Missing children were set to 0. Missing country was set to "Unknown". Missing agent and company were set to 0, meaning no agent or company.
- **Invalid bookings:** Rows with zero guests or zero nights were removed.
- **Zero rate:** Excluded from rate and revenue figures by default. Use the sidebar to include them.
- **Revenue:** An estimate (daily rate x nights, not canceled bookings). It is not confirmed billing data.
        """
    )