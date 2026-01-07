# Tests

This folder contains utility scripts for testing and running the CrowdCompute system.

## Scripts
 

### `run_foreman_simple.py`
Start the FastAPI foreman server.
```bash
python run_foreman_simple.py
```

### `run_worker_simple.py`
Start a FastAPI worker server.
```bash
python run_worker_simple.py
```

### `example_client.py`
Example client script demonstrating CrowdCompute usage.
```bash
python example_client.py <foremanIPaddress>
```

### `view_database.py`
View the contents of the SQLite database.
```bash
python view_database.py
```

### `quick_clear_db.py`
Quickly clear all data from the database.
```bash
python quick_clear_db.py
```

### `sentiment_analysis_pytorch_client.py`
Distributed sentiment analysis using PyTorch and HuggingFace transformers (DistilBERT). Demonstrates:
- Distributed NLP inference across multiple workers
- PyTorch-based transformer model execution
- Text splitting into sentences
- Task offloading and parallel processing
- Result aggregation with confidence-weighted scoring
```bash
python sentiment_analysis_pytorch_client.py <foremanIPaddress>
```

**Features:**
- Uses `distilbert-base-uncased-finetuned-sst-2-english` model
- Splits input text into sentences for parallel processing
- Each sentence analyzed independently on different workers
- Aggregates results with confidence-weighted sentiment scores
- Returns detailed per-sentence and overall sentiment analysis

**Requirements:**
```bash
pip install torch transformers
```

**Data Flow:**
1. **Client Side:**
   - Input text is split into individual sentences
   - Each sentence becomes a separate task
   - Tasks dispatched to foreman via `distributed_map()`

2. **Foreman:**
   - Receives tasks and queues them
   - Distributes tasks to available workers
   - Tracks task completion status

3. **Worker Side:**
   - Receives sentence text as input
   - Loads DistilBERT model and tokenizer
   - Tokenizes text into PyTorch tensors
   - Performs inference with `model(**inputs)`
   - Applies softmax to logits for probability distribution
   - Returns structured result with sentiment, confidence, probabilities, tensor shapes, and latency

4. **Result Aggregation (Client):**
   - Collects results from all workers
   - Parses JSON/dict responses
   - Calculates confidence-weighted overall sentiment: `Σ(sentiment × confidence) / Σ(confidence)`
   - Computes statistics (avg confidence, latency, error count)
   - Displays per-sentence and aggregated results

**Tensor Flow:**
- Input: Text string → Tokenizer → `input_ids` tensor (shape: `[1, seq_length]`)
- Model: DistilBERT forward pass → logits tensor (shape: `[1, 2]` for binary classification)
- Output: Softmax(logits) → probability distribution `[neg_prob, pos_prob]`

## Usage

All scripts in this folder can be run directly from the `tests` directory. They automatically add the parent directory to the Python path to resolve imports.

## Typical Testing Workflow

1. **Start Foreman:**
   ```bash
   python run_foreman_simple.py
   ```

2. **Start Worker (in another terminal):**
   ```bash
   python run_worker_simple.py
   ```

3. **Run Example Client (in another terminal):**
   ```bash
   python example_client.py localhost
   ```

4. **View Database (optional):**
   ```bash
   python view_database.py
   ```

5. **Clear Database (if needed):**
   ```bash
   python quick_clear_db.py
   ```
