import streamlit as st
import boto3
import time

st.title("AI PDF Summarizer")

try:
    # AWS S3 client
    s3 = boto3.client("s3")

    BUCKET_NAME = "samiksha-pdf-summarizer-2026"

    uploaded_file = st.file_uploader(
        "Upload a PDF",
        type=["pdf"]
    )

    if uploaded_file is not None:

        file_name = uploaded_file.name

        st.write("Uploading PDF to S3...")

        # Upload PDF
        s3.upload_fileobj(
            uploaded_file,
            BUCKET_NAME,
            file_name
        )

        st.success("PDF uploaded successfully!")

        summary_file = file_name.replace(
            ".pdf",
            "_summary.txt"
        )

        st.write("Waiting for AI summary generation...")

        # Wait for Lambda
        time.sleep(10)

        try:
            summary_obj = s3.get_object(
                Bucket=BUCKET_NAME,
                Key=summary_file
            )

            summary_text = summary_obj[
                "Body"
            ].read().decode("utf-8")

            st.subheader("Generated Summary")

            st.write(summary_text)

            st.download_button(
                label="Download Summary",
                data=summary_text,
                file_name=summary_file,
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"Summary not ready yet: {e}")

except Exception as e:
    st.error(f"AWS Error: {e}")