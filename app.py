import streamlit as st
import gpxpy
import pandas as pd
import plotly.express as px
from datetime import timedelta
from geopy.distance import geodesic
import io
# page setup
st.set_page_config(page_title="Running Data Visualizer", layout="wide")
st.title("🏃 Running Data Visualizer")
st.write("Upload your `.gpx` file exported from a smartwatch or tracking app.")

#upload file 
uploaded_file = st.file_uploader("Upload GPX", type=["gpx"])


if uploaded_file: 
    #try...catch.. expcetion in case they upload something weird
    try: 
        gpx = gpxpy.parse(uploaded_file)
        data = []
        #parsing data
        for track in gpx.tracks:
            for segment in track.segments:
                for i, point in enumerate(segment.points):
                    row = {
                        'time': point.time,
                        'latitude': point.latitude,
                        'longitude': point.longitude,
                        'elevation': point.elevation,
                    }
                    #some times the data may not have heartrate, but sometimes it does
                    if point.extensions:
                        for ext in point.extensions:
                            for child in ext:
                                if 'hr' in child.tag.lower():
                                    row['heart_rate'] = int(child.text)
                #calculates change in time and distance for stats
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

        #setting up data values
        df = pd.DataFrame(data)
        df['elapsed_sec'] = (df['time'] - df['time'].iloc[0]).dt.total_seconds()
        df['elapsed_min'] = df['elapsed_sec'] / 60
        df['distance_m'] = df['distance_delta'].cumsum()
        df['distance_km'] = df['distance_m'] / 1000

        df['delta_time_min'] = df['time_delta'] / 60
        df['delta_distance_km'] = df['distance_delta'] / 1000
        df['pace_min_per_km'] = df['delta_time_min'] / df['delta_distance_km']
        df['pace_min_per_km'] = df['pace_min_per_km'].replace([float('inf'), -float('inf')], None)

        # Summary cards
        st.subheader("📈 Summary Metrics")
        col1, col2, col3, col4 = st.columns(4)
        total_distance_km = df['distance_km'].max()
        total_time_min = df['elapsed_min'].max()
        avg_pace = df['delta_time_min'].sum() / df['delta_distance_km'].sum()
        max_hr = df['heart_rate'].max() if 'heart_rate' in df.columns else None

        col1.metric("Total Distance", f"{total_distance_km:.2f} km")
        col2.metric("Total Time", f"{int(total_time_min)} min")
        col3.metric("Avg. Pace", f"{avg_pace:.2f} min/km")
        col4.metric("Max HR", f"{int(max_hr)} bpm" if max_hr else "N/A")

        #expander to open more stats
        with st.expander("See More Stats"):
            min_pace = df['pace_min_per_km'].min()
            max_pace = df['pace_min_per_km'].max()
            elev_gain = df['elevation'].diff().clip(lower=0).sum()
            elev_loss = df['elevation'].diff().clip(upper=0).abs().sum()

            st.write(f"**Min Pace:** {min_pace:.2f} min/km")
            st.write(f"**Max Pace:** {max_pace:.2f} min/km")
            st.write(f"**Elevation Gain:** {elev_gain:.2f} m")
            st.write(f"**Elevation Loss:** {elev_loss:.2f} m")

        #feedback, short sentences
        st.subheader("🧠 Training Feedback")
        feedback = ""

        #if / elif statements for feedback (NOT AI)
        if avg_pace < 4:
            feedback += "⚡ You're running at a very fast pace. Consider recovery runs between hard sessions.\n\n"
        elif avg_pace < 5:
            feedback += "💪 Strong pace! Maintain consistency and consider interval work to go faster.\n\n"
        else:
            feedback += "🏃 Keep it up! Try tempo runs or increase volume to improve speed.\n\n"

        if max_hr and max_hr > 180:
            feedback += "❤️ High max heart rate detected. Be mindful of intensity and recovery."
        elif max_hr:
            feedback += "✅ Heart rate looks controlled — you're training at a manageable effort."

        # Pace trend suggestion
        pace_std = df['pace_min_per_km'].std()
        #pace standard deviation to see how much you change

        if pace_std < 0.2:
            trend_feedback = "✅ Your pacing is very consistent. This is great for endurance events."
        elif pace_std < 0.5:
            trend_feedback = "ℹ️ Moderate pacing variation detected. You might benefit from controlled tempo efforts."
        else:
            trend_feedback = "⚠️ Your pacing is quite variable. Try intervals or steady-state runs to improve control."

        st.info(feedback)
        st.info(trend_feedback)

        # Rounding for table
        df_display = df.copy()
        for col in df_display.select_dtypes(include=['float64', 'int64']).columns:
            df_display[col] = df_display[col].round(2)

        st.dataframe(df_display, use_container_width=True, height=400)

        #Download Button
        csv_buffer = io.StringIO()
        df_display.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Download Workout Data as CSV",
            data=csv_buffer.getvalue(),
            file_name="workout_data.csv",
            mime="text/csv"
        )

        #titles of tabs for the charts
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "⏱️ Time vs Distance",
            "⚡ Current Pace vs Distance",
            "❤️ Heart Rate vs Distance",
            "🗻 Elevation vs Distance",
            "📊 Custom Plot"
        ])

        #tab 1
        with tab1:
            st.subheader("Time vs Distance (km)")
            fig = px.line(df, x='distance_km', y='elapsed_min', labels={
                'distance_km': "Distance (km)",
                'elapsed_min': "Time (min)"
            })
            #2 sf
            fig.update_traces(hovertemplate='Distance: %{x:.2f} km<br>Time: %{y:.2f} min')
            fig.update_layout(hovermode="x unified")
            #plotly chart
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
               #tab 2
            st.subheader("Current Pace vs Distance (min/km)")
            fig = px.line(df, x='distance_km', y='pace_min_per_km', labels={
                'distance_km': "Distance (km)",
                'pace_min_per_km': "Current Pace (min/km)"
            })
            fig.update_traces(hovertemplate='Distance: %{x:.2f} km<br>Pace: %{y:.2f} min/km')
            fig.update_layout(hovermode="x unified", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
               #tab 3
            st.subheader("Heart Rate vs Distance")
            if 'heart_rate' in df.columns:
                fig = px.line(df, x='distance_km', y='heart_rate', labels={
                    'distance_km': "Distance (km)",
                    'heart_rate': "Heart Rate (bpm)"
                })
                fig.update_traces(hovertemplate='Distance: %{x:.2f} km<br>Heart Rate: %{y:.0f} bpm')
                fig.update_layout(hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No heart rate data found.")

        with tab4:
               #tab 4
            st.subheader("Elevation vs Distance")
            fig = px.line(df, x='distance_km', y='elevation', labels={
                'distance_km': "Distance (km)",
                'elevation': "Elevation (m)"
            })
            fig.update_traces(hovertemplate='Distance: %{x:.2f} km<br>Elevation: %{y:.2f} m')
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

        with tab5:
               #tab 5
            st.subheader("📊 Custom Plot: Choose X and Y Variables")
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            #select boxes to select axies
            x_axis = st.selectbox("Select X-axis", numeric_cols, index=0)
            y_axis = st.selectbox("Select Y-axis", numeric_cols, index=1)
            fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        #if error occurs
        st.error(f"⚠️ Error processing GPX file: {e}")

# Ideal Splits Generator 
st.markdown("---")
with st.expander("🎯 Generate Ideal Race Splits"):
    st.subheader("Enter Race Goal")
    #number inputs for values
    total_distance = st.number_input("Race Distance (meters)", min_value=100, value=1500, step=100)
    target_minutes = st.number_input("Target Time - Minutes", min_value=0, value=5)
    target_seconds = st.number_input("Target Time - Seconds", min_value=0, max_value=59, value=0)
    split_interval = st.selectbox("Split Interval", options=[100, 200, 400, 1000])
    pacing_style = st.radio("Pacing Style", options=["Even", "Negative", "Positive"])

    #if they choose to generate
    if st.button("Generate Splits"):
        total_seconds = target_minutes * 60 + target_seconds
        num_splits = int(total_distance // split_interval)
        split_time = total_seconds / num_splits
        splits = []

        for i in range(1, num_splits + 1):
            if pacing_style == "Even":
                pace = split_time
            elif pacing_style == "Negative":
                pace = split_time * (1 - 0.02 * (i - 1))
            elif pacing_style == "Positive":
                pace = split_time * (1 + 0.02 * (i - 1))

        #calculates cumulative seconds passed after every split
            cumulative_sec += pace
            splits.append({
                "Split #": i,
                f"{split_interval}m Time": f"{int(pace // 60)}:{int(pace % 60):02}",
                "Cumulative Time": f"{int(cumulative_sec // 60)}:{int(cumulative_sec % 60):02}",
                "Cumulative Sec": cumulative_sec
            })

        split_df = pd.DataFrame(splits).drop(columns="Cumulative Sec")
        st.success("✅ Ideal splits calculated!")
        st.dataframe(split_df, use_container_width=True)
