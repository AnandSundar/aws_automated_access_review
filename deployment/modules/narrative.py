# Narrative Module for AWS Automated Access Review
import boto3
import json


def generate_narrative(findings):
    """
    Calls Amazon Bedrock (Claude) to generate an executive summary of findings.
    """
    bedrock = boto3.client("bedrock-runtime")

    # Summarize counts for the prompt
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        sev = f.get("severity", "LOW").upper()
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Build a simplified list for context
    findings_summary = []
    for f in findings[:30]:  # Limit to top 30 for context
        findings_summary.append(f"{f['severity']}: {f['finding']} on {f['resource_id']}")

    prompt = f"""
    You are a Senior AWS Security Architect. Generate an executive summary report based on the following security findings.
    
    Summary Statistics:
    - Critical Findings: {severity_counts['CRITICAL']}
    - High Findings: {severity_counts['HIGH']}
    - Medium Findings: {severity_counts['MEDIUM']}
    
    Top Findings Details:
    {chr(10).join(findings_summary)}
    
    Requirements for the report:
    1. Length: 400-500 words.
    2. Tone: Professional, authoritative, and urgent where necessary.
    3. Structure:
       - Overview Paragraph: Summarize the overall security posture.
       - Critical Findings List: Highlight the most dangerous gaps.
       - Recommendations: Provide the top 5 prioritized actions to take.
    
    Return only the narrative text.
    """

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }
    )

    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0", body=body
        )

        response_body = json.loads(response.get("body").read())
        return response_body["content"][0]["text"]

    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return f"Unable to generate AI narrative. Manual Summary: {severity_counts['CRITICAL']} Critical, {severity_counts['HIGH']} High findings detected."
