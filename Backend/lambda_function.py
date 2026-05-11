import json
import boto3
import PyPDF2

# AWS clients
s3 = boto3.client("s3")

bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name="eu-north-1"
)

# Bedrock model
MODEL_ID = "amazon.nova-lite-v1:0"


def generate_summary(text_chunk):

    prompt = f"""
    You are an expert document summarizer.

    Summarize the following document content clearly and professionally.

    Instructions:
    - Focus on key concepts, insights, and actionable ideas
    - Avoid repeating titles or table of contents
    - Ignore disclaimers and boilerplate text
    - Write concise but meaningful bullet points
    - Capture the actual substance of the document

    Document Content:
    {text_chunk}
    """

    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "inferenceConfig": {
            "max_new_tokens": 500,
            "temperature": 0.3
        }
    }

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body)
    )

    response_body = json.loads(
        response["body"].read()
    )

    summary = response_body[
        "output"
    ]["message"]["content"][0]["text"]

    return summary


def lambda_handler(event, context):

    # Get uploaded file details
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    file_key = event['Records'][0]['s3']['object']['key']

    print(f"Bucket: {bucket_name}")
    print(f"File Key: {file_key}")

    # Skip non-PDF files
    if not file_key.endswith(".pdf"):

        print("Skipping non-PDF file")

        return {
            "statusCode": 200,
            "body": "Skipped non-PDF file"
        }

    # Download PDF
    download_path = f"/tmp/{file_key}"

    s3.download_file(
        bucket_name,
        file_key,
        download_path
    )

    # Read PDF
    pdf_reader = PyPDF2.PdfReader(download_path)

    extracted_text = ""

    for page in pdf_reader.pages:

        page_text = page.extract_text()

        if page_text:
            extracted_text += page_text + "\n"

    print("===== EXTRACTED TEXT =====")
    print(extracted_text[:2000])
    print("===== END EXTRACTED TEXT =====")

    # Chunk text
    chunk_size = 4000

    text_chunks = [
        extracted_text[i:i + chunk_size]
        for i in range(0, len(extracted_text), chunk_size)
    ]

    print(f"Total Chunks: {len(text_chunks)}")

    chunk_summaries = []

    # Summarize each chunk
    for index, chunk in enumerate(text_chunks):

        print(f"Processing chunk {index + 1}")

        chunk_summary = generate_summary(chunk)

        chunk_summaries.append(chunk_summary)

    # Combine chunk summaries
    combined_summary = "\n".join(chunk_summaries)

    # Final refinement summary
    final_prompt = f"""
    Create a final clean executive summary from these partial summaries.

    Requirements:
    - Remove repetition
    - Combine related ideas
    - Use professional concise bullet points
    - Focus on the most important concepts
    - Make the output readable and structured

    Partial Summaries:
    {combined_summary}
    """

    final_body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": final_prompt
                    }
                ]
            }
        ],
        "inferenceConfig": {
            "max_new_tokens": 700,
            "temperature": 0.2
        }
    }

    final_response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(final_body)
    )

    final_response_body = json.loads(
        final_response["body"].read()
    )

    final_summary = final_response_body[
        "output"
    ]["message"]["content"][0]["text"]

    print("===== FINAL SUMMARY =====")
    print(final_summary)
    print("===== END FINAL SUMMARY =====")

    # Save summary
    summary_key = file_key.replace(
        ".pdf",
        "_summary.txt"
    )

    s3.put_object(
        Bucket=bucket_name,
        Key=summary_key,
        Body=final_summary.encode("utf-8"),
        ContentType="text/plain"
    )

    print(f"Summary uploaded to S3: {summary_key}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Summary generated successfully",
            "summary_file": summary_key
        })
    }