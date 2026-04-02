"""
Amazon Bedrock Integration Module for AWS Automated Access Review

This module provides a clean, reusable interface for interacting with Amazon Bedrock
(Claude 3 Sonnet) to generate AI-powered executive summaries from security findings.
"""

import boto3
import json
import logging
import time
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "region": "us-east-1",
    "max_tokens": 2000,
    "temperature": 0.7,
    "max_retries": 3,
    "retry_delay": 1.0,
    "max_findings_for_context": 30,
}


def generate_narrative_summary(
    findings_data: List[Dict[str, Any]], config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate an AI-powered executive summary from security findings using Amazon Bedrock.

    This function orchestrates the entire narrative generation process, including:
    - Formatting findings for the Bedrock prompt
    - Invoking the Claude 3 Sonnet model
    - Handling errors and implementing retry logic
    - Providing fallback generation when Bedrock is unavailable

    Args:
        findings_data: List of security findings dictionaries. Each finding should contain
                      at minimum: 'severity', 'finding', and 'resource_id' keys.
        config: Optional configuration dictionary to override defaults. Supported keys:
               - model_id: Bedrock model ID (default: anthropic.claude-3-sonnet-20240229-v1:0)
               - region: AWS region (default: us-east-1)
               - max_tokens: Maximum tokens in response (default: 2000)
               - temperature: Response randomness 0-1 (default: 0.7)
               - max_retries: Number of retry attempts (default: 3)
               - retry_delay: Initial delay between retries in seconds (default: 1.0)
               - max_findings_for_context: Max findings to include in prompt (default: 30)

    Returns:
        str: Generated executive summary narrative. Returns a fallback summary if
             Bedrock is unavailable or encounters an error.

    Example:
        >>> findings = [
        ...     {'severity': 'CRITICAL', 'finding': 'S3 bucket public', 'resource_id': 'bucket-123'},
        ...     {'severity': 'HIGH', 'finding': 'Security group open', 'resource_id': 'sg-456'}
        ... ]
        >>> summary = generate_narrative_summary(findings)
        >>> print(summary)
    """
    if not findings_data:
        logger.warning("No findings data provided for narrative generation")
        return "No security findings available to generate a summary."

    # Merge user config with defaults
    merged_config = DEFAULT_CONFIG.copy()
    if config:
        merged_config.update(config)

    logger.info(f"Generating narrative summary for {len(findings_data)} findings")

    try:
        # Format findings for the Bedrock prompt
        formatted_prompt = _format_findings_for_bedrock(findings_data, merged_config)

        # Invoke Bedrock with retry logic
        narrative = _invoke_bedrock_with_retry(formatted_prompt, merged_config)

        logger.info("Successfully generated narrative summary using Bedrock")
        return narrative

    except Exception as e:
        logger.error(f"Failed to generate narrative with Bedrock: {str(e)}", exc_info=True)
        logger.info("Falling back to manual summary generation")
        return _generate_fallback_summary(findings_data)


def _invoke_bedrock_with_retry(prompt: str, config: Dict[str, Any]) -> str:
    """
    Invoke Bedrock API with exponential backoff retry logic.

    Args:
        prompt: The formatted prompt to send to Bedrock
        config: Configuration dictionary containing retry settings

    Returns:
        str: The generated narrative text

    Raises:
        Exception: If all retry attempts are exhausted
    """
    max_retries = config.get("max_retries", DEFAULT_CONFIG["max_retries"])
    base_delay = config.get("retry_delay", DEFAULT_CONFIG["retry_delay"])

    last_exception = None

    for attempt in range(max_retries):
        try:
            return _invoke_bedrock(prompt, config)

        except Exception as e:
            last_exception = e
            error_str = str(e).lower()

            # Determine if we should retry based on error type
            should_retry = any(
                keyword in error_str
                for keyword in [
                    "throttling",
                    "service unavailable",
                    "timeout",
                    "internal server error",
                    "503",
                    "429",
                ]
            )

            if not should_retry:
                # Don't retry for non-transient errors
                logger.error(f"Non-retryable error encountered: {str(e)}")
                raise

            if attempt < max_retries - 1:
                # Calculate exponential backoff delay
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                    f"Retrying in {delay} seconds..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} retry attempts exhausted")

    # If we get here, all retries failed
    raise last_exception if last_exception else Exception("Bedrock invocation failed")


def _invoke_bedrock(prompt: str, config: Dict[str, Any]) -> str:
    """
    Internal function to invoke the Bedrock API.

    Args:
        prompt: The formatted prompt to send to the model
        config: Configuration dictionary containing model settings

    Returns:
        str: The generated narrative text

    Raises:
        Exception: If the Bedrock API call fails for any reason
    """
    model_id = config.get("model_id", DEFAULT_CONFIG["model_id"])
    region = config.get("region", DEFAULT_CONFIG["region"])
    max_tokens = config.get("max_tokens", DEFAULT_CONFIG["max_tokens"])
    temperature = config.get("temperature", DEFAULT_CONFIG["temperature"])

    logger.debug(f"Invoking Bedrock model: {model_id} in region: {region}")

    # Initialize Bedrock client
    try:
        bedrock = boto3.client("bedrock-runtime", region_name=region)
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock client: {str(e)}")
        raise Exception(f"Bedrock client initialization failed: {str(e)}")

    # Determine model family and construct appropriate request body
    if "anthropic" in model_id.lower():
        # Anthropic Claude models
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
        )
    elif "google" in model_id.lower() or "gemma" in model_id.lower():
        # Google Gemma models
        body = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generation_config": {"max_output_tokens": max_tokens, "temperature": temperature},
            }
        )
    elif "amazon" in model_id.lower() or "titan" in model_id.lower():
        # Amazon Titan models
        body = json.dumps(
            {
                "inputText": prompt,
                "textGenerationConfig": {"maxTokenCount": max_tokens, "temperature": temperature},
            }
        )
    elif "meta" in model_id.lower() or "llama" in model_id.lower():
        # Meta Llama models
        body = json.dumps({"prompt": prompt, "max_gen_len": max_tokens, "temperature": temperature})
    else:
        # Default to Anthropic format for unknown models
        logger.warning(f"Unknown model family: {model_id}, using Anthropic format as default")
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
        )

    try:
        # Invoke the model
        response = bedrock.invoke_model(modelId=model_id, body=body)

        # Parse the response based on model family
        response_body = json.loads(response.get("body").read())

        if "anthropic" in model_id.lower():
            # Anthropic response format
            if "content" in response_body and len(response_body["content"]) > 0:
                narrative = response_body["content"][0].get("text", "")
                if narrative:
                    return narrative
            raise Exception("Empty response received from Anthropic model")

        elif "google" in model_id.lower() or "gemma" in model_id.lower():
            # Google response format
            if "candidates" in response_body and len(response_body["candidates"]) > 0:
                candidate = response_body["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        return parts[0]["text"]
            raise Exception("Empty response received from Google model")

        elif "amazon" in model_id.lower() or "titan" in model_id.lower():
            # Amazon Titan response format
            if "results" in response_body and len(response_body["results"]) > 0:
                narrative = response_body["results"][0].get("outputText", "")
                if narrative:
                    return narrative
            raise Exception("Empty response received from Amazon model")

        elif "meta" in model_id.lower() or "llama" in model_id.lower():
            # Meta Llama response format
            if "generation" in response_body:
                narrative = response_body["generation"]
                if narrative:
                    return narrative
            raise Exception("Empty response received from Meta model")

        else:
            # Default parsing (Anthropic format)
            if "content" in response_body and len(response_body["content"]) > 0:
                narrative = response_body["content"][0].get("text", "")
                if narrative:
                    return narrative
            raise Exception("Unexpected response format from Bedrock")

    except Exception as e:
        logger.error(f"Bedrock API invocation failed: {str(e)}")
        raise


def _format_findings_for_bedrock(
    findings_data: List[Dict[str, Any]], config: Dict[str, Any]
) -> str:
    """
    Format security findings into a structured prompt for Bedrock.

    This function processes the findings data and creates a comprehensive prompt
    that includes severity statistics and detailed context for the AI model.

    Args:
        findings_data: List of security findings dictionaries
        config: Configuration dictionary

    Returns:
        str: A formatted prompt string ready for Bedrock
    """
    max_findings = config.get(
        "max_findings_for_context", DEFAULT_CONFIG["max_findings_for_context"]
    )

    # Calculate severity counts
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for finding in findings_data:
        sev = finding.get("severity", "LOW").upper()
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Build a simplified list for context (limit to prevent token overflow)
    findings_summary = []
    for finding in findings_data[:max_findings]:
        severity = finding.get("severity", "UNKNOWN")
        finding_text = finding.get("finding", "Unknown finding")
        resource_id = finding.get("resource_id", "Unknown resource")
        findings_summary.append(f"{severity}: {finding_text} on {resource_id}")

    # Construct the prompt
    prompt = f"""
You are a Senior AWS Security Architect. Generate an executive summary report based on the following security findings.

Summary Statistics:
- Critical Findings: {severity_counts['CRITICAL']}
- High Findings: {severity_counts['HIGH']}
- Medium Findings: {severity_counts['MEDIUM']}
- Low Findings: {severity_counts['LOW']}

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

    logger.debug(f"Formatted prompt with {len(findings_summary)} findings for context")
    return prompt


def _generate_fallback_summary(findings_data: List[Dict[str, Any]]) -> str:
    """
    Generate a basic summary when Bedrock is unavailable.

    This function provides a simple, template-based summary as a fallback
    when the Bedrock service cannot be reached or encounters errors.

    Args:
        findings_data: List of security findings dictionaries

    Returns:
        str: A basic summary of the findings
    """
    # Calculate severity counts
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for finding in findings_data:
        sev = finding.get("severity", "LOW").upper()
        if sev in severity_counts:
            severity_counts[sev] += 1

    total_findings = len(findings_data)

    # Generate a basic summary
    summary = f"""
SECURITY ACCESS REVIEW SUMMARY

This automated access review identified {total_findings} security findings across your AWS environment.

Severity Breakdown:
- Critical: {severity_counts['CRITICAL']}
- High: {severity_counts['HIGH']}
- Medium: {severity_counts['MEDIUM']}
- Low: {severity_counts['LOW']}

Note: This is a basic summary generated due to AI service unavailability. 
For detailed analysis, please review individual findings and consider enabling 
the Amazon Bedrock integration for AI-powered executive summaries.

Recommended Actions:
1. Immediately address all Critical severity findings
2. Review and remediate High severity findings within 24 hours
3. Establish a regular schedule for access reviews
4. Implement automated compliance checks
5. Enable AI-powered analysis for deeper insights
"""

    logger.info("Generated fallback summary")
    return summary.strip()


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate the Bedrock configuration dictionary.

    Args:
        config: Configuration dictionary to validate

    Returns:
        bool: True if configuration is valid, False otherwise
    """
    valid_keys = set(DEFAULT_CONFIG.keys())
    provided_keys = set(config.keys())

    # Check for unknown configuration keys
    unknown_keys = provided_keys - valid_keys
    if unknown_keys:
        logger.warning(f"Unknown configuration keys: {unknown_keys}")

    # Validate numeric values
    if "max_tokens" in config:
        if not isinstance(config["max_tokens"], int) or config["max_tokens"] <= 0:
            logger.error("max_tokens must be a positive integer")
            return False

    if "temperature" in config:
        if (
            not isinstance(config["temperature"], (int, float))
            or not 0 <= config["temperature"] <= 1
        ):
            logger.error("temperature must be a number between 0 and 1")
            return False

    if "max_retries" in config:
        if not isinstance(config["max_retries"], int) or config["max_retries"] < 0:
            logger.error("max_retries must be a non-negative integer")
            return False

    if "retry_delay" in config:
        if not isinstance(config["retry_delay"], (int, float)) or config["retry_delay"] < 0:
            logger.error("retry_delay must be a non-negative number")
            return False

    if "max_findings_for_context" in config:
        if (
            not isinstance(config["max_findings_for_context"], int)
            or config["max_findings_for_context"] <= 0
        ):
            logger.error("max_findings_for_context must be a positive integer")
            return False

    return True
