"""
Streamlit frontend for 3D Avatar Generator.
User interface for uploading photos and downloading 3D printable avatars.
"""
import os
import time
import requests
import streamlit as st
from PIL import Image
from pathlib import Path


# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# Page config
st.set_page_config(
    page_title="3D Avatar Generator",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)


def upload_photo(file):
    """Upload photo to backend and start processing."""
    # Reset file pointer to beginning
    file.seek(0)
    # Create proper file tuple for requests
    files = {"file": (file.name, file, file.type)}
    response = requests.post(f"{BACKEND_URL}/upload", files=files)

    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Upload failed: {response.text}")
        return None


def get_status(job_id):
    """Get job status from backend."""
    response = requests.get(f"{BACKEND_URL}/status/{job_id}")

    if response.status_code == 200:
        return response.json()
    else:
        return None


def download_file(job_id, file_type="stl"):
    """Download file from backend."""
    if file_type == "stl":
        url = f"{BACKEND_URL}/download/{job_id}/stl"
        filename = f"avatar_{job_id}.stl"
    elif file_type == "cartoon":
        url = f"{BACKEND_URL}/download/{job_id}/cartoon"
        filename = f"cartoon_{job_id}.png"
    elif file_type == "preview":
        url = f"{BACKEND_URL}/preview/{job_id}"
        filename = f"model_{job_id}.glb"
    else:
        return None

    response = requests.get(url)

    if response.status_code == 200:
        return response.content, filename
    else:
        return None, None


# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }

    .subtitle {
        text-align: center;
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }

    .status-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }

    .status-pending {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
    }

    .status-processing {
        background: #d1ecf1;
        border-left: 4px solid #17a2b8;
    }

    .status-completed {
        background: #d4edda;
        border-left: 4px solid #28a745;
    }

    .status-failed {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)


# Header
st.markdown('<h1 class="main-header">🎭 3D Avatar Generator</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Transform your photos into Pixar-style 3D printable avatars</p>',
    unsafe_allow_html=True
)


# Sidebar
with st.sidebar:
    st.header("ℹ️ How it Works")
    st.markdown("""
    1. **Upload** a clear front-facing photo
    2. **Wait** 3-5 minutes for AI processing
    3. **Download** your print-ready STL file
    4. **Print** on your 3D printer!

    ### Pipeline Steps:
    - ✅ Face Detection (~5s)
    - 🎨 Pixar Cartoonization (~60s)
    - 🎯 3D Model Generation (~3min)
    - ⚙️ Mesh Optimization (~10s)

    ### Optimized for:
    - Creality Ender 3 V2
    - BIQU B1
    """)

    st.divider()

    st.header("⚙️ Settings")
    st.caption("(Coming in full version)")
    st.selectbox("Printer Profile", ["Ender 3 V2", "BIQU B1"], disabled=True)
    st.slider("Target Height (cm)", 5, 15, 8, disabled=True)


# Main content
tab1, tab2 = st.tabs(["📤 Upload & Process", "📚 About"])


with tab1:
    # Upload section
    st.header("Upload Your Photo")

    uploaded_file = st.file_uploader(
        "Choose a clear front-facing portrait (JPG/PNG, max 10MB)",
        type=["jpg", "jpeg", "png"],
        help="Best results with well-lit front-facing portraits"
    )

    if uploaded_file:
        # Display uploaded image
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("Uploaded Photo")
            image = Image.open(uploaded_file)
            st.image(image, use_column_width=True)

        with col2:
            st.subheader("Processing")

            if st.button("🚀 Start Processing", type="primary", use_container_width=True):
                # Upload to backend
                with st.spinner("Uploading photo..."):
                    result = upload_photo(uploaded_file)

                if result:
                    job_id = result["job_id"]
                    st.session_state.job_id = job_id
                    st.success(f"Upload successful! Job ID: `{job_id}`")
                    st.rerun()

    # Processing status section
    if "job_id" in st.session_state:
        st.divider()
        st.header("Processing Status")

        job_id = st.session_state.job_id

        # Status polling
        status_placeholder = st.empty()
        progress_placeholder = st.empty()
        message_placeholder = st.empty()
        output_placeholder = st.empty()

        while True:
            status_data = get_status(job_id)

            if not status_data:
                st.error("Failed to get status")
                break

            status = status_data["status"]
            progress = status_data["progress"]
            message = status_data["message"]

            # Display status
            status_class = f"status-{status}"
            status_placeholder.markdown(
                f'<div class="status-box {status_class}"><strong>Status:</strong> {status.upper()}</div>',
                unsafe_allow_html=True
            )

            # Progress bar
            progress_placeholder.progress(progress / 100, text=f"{progress}% complete")

            # Message
            message_placeholder.info(message)

            # Check if completed
            if status == "completed":
                st.success("🎉 Avatar generation complete!")

                # Download buttons
                output_placeholder.empty()
                with output_placeholder.container():
                    st.subheader("Download Your Files")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        # Download STL
                        stl_data, stl_filename = download_file(job_id, "stl")
                        if stl_data:
                            st.download_button(
                                label="📥 Download STL (Print File)",
                                data=stl_data,
                                file_name=stl_filename,
                                mime="application/sla",
                                use_container_width=True
                            )

                    with col2:
                        # Download Cartoon
                        cartoon_data, cartoon_filename = download_file(job_id, "cartoon")
                        if cartoon_data:
                            st.download_button(
                                label="🎨 Download Cartoon Image",
                                data=cartoon_data,
                                file_name=cartoon_filename,
                                mime="image/png",
                                use_container_width=True
                            )

                    with col3:
                        # Download GLB
                        glb_data, glb_filename = download_file(job_id, "preview")
                        if glb_data:
                            st.download_button(
                                label="🎯 Download 3D Model (GLB)",
                                data=glb_data,
                                file_name=glb_filename,
                                mime="model/gltf-binary",
                                use_container_width=True
                            )

                    # Display cartoon preview
                    if cartoon_data:
                        st.subheader("Cartoonized Preview")
                        st.image(cartoon_data, use_column_width=True)

                    # Next steps
                    st.info("""
                    ### 🖨️ Next Steps:
                    1. Open the STL file in your slicer (Cura, PrusaSlicer, etc.)
                    2. Load your printer profile (Ender 3 V2 or BIQU B1)
                    3. Slice with 0.2mm layer height
                    4. Print and enjoy your avatar!

                    **Estimated print time:** 2-3 hours
                    **Estimated filament:** ~50g
                    """)

                    if st.button("🔄 Create Another Avatar", use_container_width=True):
                        del st.session_state.job_id
                        st.rerun()

                break

            elif status == "failed":
                st.error(f"❌ Processing failed: {status_data.get('error', 'Unknown error')}")

                if st.button("🔄 Try Again", use_container_width=True):
                    del st.session_state.job_id
                    st.rerun()

                break

            # Wait before next poll
            time.sleep(2)


with tab2:
    st.header("About This Tool")

    st.markdown("""
    ### 🎯 What is this?

    This is a proof-of-concept 3D avatar generator that transforms ordinary photos into
    Pixar-style 3D printable figurines using AI.

    ### 🤖 Technology Stack

    - **Face Detection:** MediaPipe
    - **Cartoonization:** Stability AI SDXL (via Replicate)
    - **3D Generation:** Meshy.ai
    - **Mesh Optimization:** trimesh + PyMeshLab
    - **Backend:** FastAPI + Python
    - **Frontend:** Streamlit

    ### 💡 Tips for Best Results

    - Use **well-lit** front-facing portraits
    - Ensure the **face is clearly visible**
    - Avoid **side profiles** or **group photos**
    - **Higher resolution** images work better
    - **Simple backgrounds** are ideal

    ### 📏 Print Specifications

    - **Default Height:** 8cm (adjustable)
    - **File Format:** STL (universal 3D printing format)
    - **Optimized for:** FDM printers
    - **Supports:** Auto-generated by slicer
    - **Tested on:** Ender 3 V2, BIQU B1

    ### 💰 Cost Per Avatar

    - Replicate (Cartoonization): ~$0.02
    - Meshy.ai (3D Generation): ~$0.15
    - **Total:** ~$0.17 per avatar

    ### 🚀 What's Next?

    This POC validates the core technology. Future enhancements:
    - 🎩 Accessories (hats, glasses, props)
    - 🎨 Multiple art styles
    - 👥 User accounts & galleries
    - 💳 Payment system
    - 📦 Print fulfillment service

    ### 📝 Feedback

    This is an experimental proof-of-concept. Your feedback helps improve it!

    ---

    Made with ❤️ using AI
    """)


# Footer
st.divider()
st.caption("3D Avatar Generator POC | Powered by AI | Not for commercial use")
