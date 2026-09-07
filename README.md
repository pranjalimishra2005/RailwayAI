# 🚂 AI-Powered Railway Safety System v2.0

A highly advanced Computer Graphics and Machine Learning surveillance system designed to detect, track, and predict hazards on railway tracks in real-time.

## 🌟 Advanced Features
- **Homography & Inverse Perspective Mapping (IPM)**: Interactive UI calibration to convert 2D screen pixels to a 3D top-down ground plane, enabling accurate distance (m) and velocity (km/h) calculations.
- **Robust Object Tracking**: Utilizes YOLOv8's native ByteTrack for stable, ID-consistent multi-object tracking.
- **Proactive Kalman Filtering**: Smooths trajectories and calculates Time-to-Collision (TTC) to issue proactive alerts before an obstacle crosses into the danger zone.
- **Dynamic Intrusion Heatmaps**: Generates real-time alpha-blended heatmaps to visualize trespass patterns.
- **Cloud-Ready Streamlit Dashboard**: A fully responsive, dark-themed UI built for local and cloud deployment.

## 🛠️ Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd RailwayAI
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Dashboard**
   ```bash
   streamlit run app.py
   ```

## ☁️ Deployment to Streamlit Community Cloud
This app is designed to be easily deployed to Streamlit Community Cloud:
1. Push this code to a public GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and connect your GitHub account.
3. Deploy the repository pointing to `app.py`.
*(Note: Live webcam and local audio synthesis are automatically disabled in cloud environments to prevent crashes).*
