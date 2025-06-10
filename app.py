import streamlit as st
import gpxpy
import pandas as pd
import plotly.express as px
from datetime import timedelta
from geopy.distance import geodesic

st.set_page_config(page_title="Running Data Visualizer", layout="wide")
st.title("🏃 Running Data Visualizer")
st.write("Upload your `.gpx` file exported from a smartwatch or tracking app.")

uploaded_file = st.file_uploader("Upload GPX", type=["gpx"])

if uploaded_file:
    try:
        gpx = gpxpy.parse(uploaded_file)
        data = []

        for track in gpx.tracks:
            for segment in track.segments:
                for i, point in enumerate(segment.points):
                    row = {
                        'time': point.time,
                        'latitude': point.latitude,
                        'longitude': point.longitude,
                        'elevation': point.elevation,
                    }

                    # Extract heart rate if present
                    if point.extensions:
                        for ext in point.extensions:
                            for child in ext:
                                if 'hr' in child.tag.lower():
                                    row['heart_rate'] = int(child.text)

                    # Calculate distance between current and previous point
                    if i > 0:
                        prev = segment.points[i - 1]
                        d = geodesic(
                            (prev.latitude, prev.longitude),
                            (point.latitude, point.longitude)
                        ).meters
                        row['distance_delta'] = d
                        row['time_delta'] = (point.time - prev.time).total_seconds()
                    else:
                        row['distance_delta'] = 0.0
                        row['time_delta'] = 0.0

                    data.append(row)

        df = pd.DataFrame(data)

        # Add elapsed time and cumulative distance
        df['elapsed_sec'] = (df['time'] - df['time'].iloc[0]).dt.total_seconds()
        df['elapsed_min'] = df['elapsed_sec'] / 60
        df['distance_m'] = df['distance_delta'].cumsum()
        df['distance_km'] = df['distance_m'] / 1000

        # Calculate current pace (min/km) per segment
        df['delta_time_min'] = df['time_delta'] / 60
        df['delta_distance_km'] = df['distance_delta'] / 1000
        df['pace_min_per_km'] = df['delta_time_min'] / df['delta_distance_km']
        df['pace_min_per_km'] = df['pace_min_per_km'].replace([float('inf'), -float('inf')], None)

        st.success("✅ File parsed successfully!")
        st.dataframe(df, use_container_width=True, height=400)

        # Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "⏱️ Time vs Distance",
            "⚡ Current Pace vs Distance",
            "❤️ Heart Rate vs Distance",
            "🗻 Elevation vs Distance",
            "📊 Custom Plot"
        ])

        with tab1:
            st.subheader("Time vs Distance (km)")
            fig = px.line(df, x='distance_km', y='elapsed_min', labels={
                'distance_km': "Distance (km)",
                'elapsed_min': "Time (min)"
            })
            fig.update_traces(hovertemplate='Distance: %{x:.2f} km<br>Time: %{y:.2f} min')
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("Current Pace vs Distance (min/km)")
            fig = px.line(df, x='distance_km', y='pace_min_per_km', labels={
                'distance_km': "Distance (km)",
                'pace_min_per_km': "Current Pace (min/km)"
            })
            fig.update_traces(hovertemplate='Distance: %{x:.2f} km<br>Pace: %{y:.2f} min/km')
            fig.update_layout(hovermode="x unified", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("Heart Rate vs Distance")
            if 'heart_rate' in df.columns:
                fig = px.line(df, x='distance_km', y='heart_rate', labels={
                    'distance_km': "Distance (km)",
                    'heart_rate': "Heart Rate (bpm)"
                })
                fig.update_traces(hovertemplate='Distance (km) %{x:.2f} km<br>Heart Rate: %{y:.0f} bpm')
                fig.update_layout(hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No heart rate data found.")

        with tab4:
            st.subheader("Elevation vs Distance")
            fig = px.line(df, x='distance_km', y='elevation', labels={
                'distance_km': "Distance (km)",
                'elevation': "Elevation (m)"
            })
            fig.update_traces(hovertemplate='Distance: %{x:.2f} km<br>Elevation: %{y:.2f} m')
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

        with tab5:
            st.subheader("📊 Custom Plot: Choose X and Y Variables")
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()

            x_axis = st.selectbox("Select X-axis", numeric_cols, index=0)
            y_axis = st.selectbox("Select Y-axis", numeric_cols, index=1)

            fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Error processing GPX file: {e}")
