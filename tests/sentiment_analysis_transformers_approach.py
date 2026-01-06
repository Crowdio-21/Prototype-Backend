import time
import asyncio
import sys
import os
from textblob import TextBlob
import nltk

# Add parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from developer_sdk import connect, map as distributed_map, disconnect

# Download required NLTK data
nltk.download('punkt_tab')

def run_sentiment_inference(text):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits

        probs = F.softmax(logits, dim=1)
        confidence, predicted_class = torch.max(probs, dim=1)

        # Map label to sentiment score
        sentiment = 1.0 if predicted_class.item() == 1 else -1.0

    return sentiment, confidence.item()

def sentiment_worker(text):
    """
    Function to be executed on worker devices for sentiment analysis using transformers
    """
    import time
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    import torch.nn.functional as F

    MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    model.eval()

    start = time.time()

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits

        probs = F.softmax(logits, dim=1)
        confidence, predicted_class = torch.max(probs, dim=1)

        # Map label to sentiment score
        sentiment = 1.0 if predicted_class.item() == 1 else -1.0

    latency_ms = int((time.time() - start) * 1000)

    return {
        "sentiment": sentiment,
        "confidence": confidence.item(),
        "latency_ms": latency_ms
    }

async def run_distributed_sentiment(text, foreman_host="localhost"):
    def split_text(text):
        blob = TextBlob(text)
        return [str(sentence) for sentence in blob.sentences]

    def aggregate_results(results):
        numerator = sum(r["confidence"] * r["sentiment"] for r in results)
        denominator = sum(r["confidence"] for r in results)
        return numerator / denominator if denominator != 0 else 0

    # Connect to foreman
    await connect(foreman_host, 9000)

    try:
        # Split text
        segments = split_text(text)

        # Distribute sentiment analysis to workers
        worker_results = await distributed_map(sentiment_worker, segments)

        # Parse results from strings to dicts
        import ast
        parsed_results = [ast.literal_eval(result) for result in worker_results]

        # Add segment_ids to results
        results = []
        for idx, result in enumerate(parsed_results):
            result["segment_id"] = f"seg-{idx}"
            results.append(result)

        # Aggregate
        final_sentiment = aggregate_results(results)

        return final_sentiment, results

    finally:
        # Disconnect
        await disconnect()

async def main():
    if len(sys.argv) != 2:
        print("Usage: python sentiment_analysis_transformers_approach.py <foreman_host>")
        print("Example: python sentiment_analysis_transformers_approach.py localhost")
        sys.exit(1)

    foreman_host = sys.argv[1]

    sample_text = """
    The infrastructure performed exceptionally well today.
    Network latency was minimal and the devices responded quickly.
    However, battery drain remains a concern for older phones.
    Overall, the experiment was successful and promising.
    """

    print("Distributed Sentiment Analysis Client (Transformers Approach)")
    print("=" * 60)

    try:
        final_sentiment, worker_outputs = await run_distributed_sentiment(
            sample_text,
            foreman_host=foreman_host
        )

        print("=== Worker Outputs ===")
        for r in worker_outputs:
            print(r)

        print("\nFinal Aggregated Sentiment:", round(final_sentiment, 3))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())