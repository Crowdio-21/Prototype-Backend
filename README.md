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

### `run_multiple_workers.py`
Launch multiple worker servers simultaneously for distributed processing.
```bash
# Default: Launch 8 workers
python run_multiple_workers.py

# Launch specific number of workers
python run_multiple_workers.py 8

# Custom starting port
python run_multiple_workers.py 8 --start-port 8001
```

**Features:**
- Starts multiple workers in parallel using asyncio
- Each worker gets a unique ID and consecutive port number
- All workers connect to the same foreman
- Ideal for testing distributed workloads

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

**Architecture Diagram:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PYTORCH CLIENT                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Input Text: "I love this! Bad service. Great quality."         │  │
│  │              ↓ split_text_into_sentences()                      │  │
│  │  ["I love this!", "Bad service.", "Great quality."]             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓ distributed_map()                        │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                            FOREMAN                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │   Task 1     │  │   Task 2     │  │   Task 3     │                 │
│  │ "I love..."  │  │ "Bad serv..."│  │ "Great qu..."│                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
│         ↓                 ↓                  ↓                           │
└─────────────────────────────────────────────────────────────────────────┘
          ↓                 ↓                  ↓
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   WORKER 1      │ │   WORKER 2      │ │   WORKER 3      │
│ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │
│ │ PyTorch     │ │ │ │ PyTorch     │ │ │ │ PyTorch     │ │
│ │ DistilBERT  │ │ │ │ DistilBERT  │ │ │ │ DistilBERT  │ │
│ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │
│       ↓         │ │       ↓         │ │       ↓         │
│  😊 Positive    │ │  😢 Negative    │ │  😊 Positive    │
│  conf: 0.98     │ │  conf: 0.85     │ │  conf: 0.92     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          ↓                 ↓                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    RESULT AGGREGATION (CLIENT)                          │
│  Weighted Sentiment = (1.0×0.98 + -1.0×0.85 + 1.0×0.92) / (0.98+0.85+0.92)│
│                     = 1.05 / 2.75 = 0.382 → Slightly Positive          │
└─────────────────────────────────────────────────────────────────────────┘
```

**PyTorch Worker Processing Pipeline:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        WORKER EXECUTION FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

  📥 Input: "I absolutely love this product!"
       ↓
  ┌─────────────────────────────────────────┐
  │  1. Load Model & Tokenizer              │
  │     - AutoTokenizer.from_pretrained()   │
  │     - AutoModelForSequenceClassification│
  │     - model.eval() [inference mode]     │
  └─────────────────────────────────────────┘
       ↓
  ┌─────────────────────────────────────────┐
  │  2. Tokenize Text                       │
  │     Input: "I absolutely love..."       │
  │     Output: {                           │
  │       'input_ids': [[101, 1045, ...]],  │
  │       'attention_mask': [[1,1,1,...]]   │
  │     }                                   │
  │     Shape: [1, seq_length]              │
  └─────────────────────────────────────────┘
       ↓
  ┌─────────────────────────────────────────┐
  │  3. PyTorch Inference                   │
  │     with torch.no_grad():               │
  │       outputs = model(**inputs)         │
  │     logits = outputs.logits             │
  │     Shape: [1, 2]                       │
  │     Values: [[-2.5], [3.2]]            │
  └─────────────────────────────────────────┘
       ↓
  ┌─────────────────────────────────────────┐
  │  4. Softmax & Classification            │
  │     probs = softmax(logits)             │
  │     = [0.002, 0.998]                    │
  │     predicted_class = argmax(probs) = 1 │
  │     confidence = max(probs) = 0.998     │
  └─────────────────────────────────────────┘
       ↓
  📤 Output: {
       "sentiment": 1.0,
       "confidence": 0.998,
       "class_name": "positive",
       "neg_probability": 0.002,
       "pos_probability": 0.998,
       "logits": [-2.5, 3.2],
       "tensor_input_shape": [1, 35],
       "tensor_output_shape": [1, 2],
       "latency_ms": 1250,
       "model": "distilbert-base-uncased-finetuned-sst-2-english"
     }
```

**Tensor Transformation Diagram:**
```
TEXT → TOKENS → TENSORS → MODEL → LOGITS → PROBABILITIES → RESULT

"I love this!"
      ↓
[101, 1045, 2293, 2023, 999, 102]  ← Token IDs
      ↓
┌─────────────────────────────┐
│ Input Tensor [1, 6]         │
│ [[101, 1045, 2293, ...]]    │
└─────────────────────────────┘
      ↓
┌─────────────────────────────┐
│   DistilBERT Model          │
│   (66M parameters)          │
│   6 layers, 768 dim         │
└─────────────────────────────┘
      ↓
┌─────────────────────────────┐
│ Logits [1, 2]               │
│ [[-2.5, 3.2]]               │
│  ↑NEG  ↑POS                 │
└─────────────────────────────┘
      ↓ softmax(logits)
┌─────────────────────────────┐
│ Probabilities [1, 2]        │
│ [[0.002, 0.998]]            │
│   ↑NEG   ↑POS               │
└─────────────────────────────┘
      ↓ argmax + format
{
  "sentiment": 1.0,
  "confidence": 0.998,
  "class_name": "positive"
}
```

---

### `monte_carlo_euler_client.py`
Monte Carlo simulation to estimate Euler's number (e ≈ 2.71828) using distributed workers. Demonstrates:
- Monte Carlo estimation using random sampling
- Parallel trial execution across multiple workers
- Statistical aggregation and error analysis
- Distributed computational mathematics

```bash
# Default: 1 million trials with 8 workers
python monte_carlo_euler_client.py

# Custom trials
python monte_carlo_euler_client.py 10000000

# Custom number of workers
python monte_carlo_euler_client.py 5000000 16

# Different foreman host
python monte_carlo_euler_client.py 1000000 8 192.168.1.100
```

**Mathematical Background:**
The algorithm generates random numbers uniformly in [0,1] and counts how many are needed until their sum exceeds 1. The expected count equals Euler's number e.

**Features:**
- Distributes Monte Carlo trials across multiple workers
- Calculates final estimate, absolute error, and error percentage
- Provides statistical summary (mean, std dev, min/max estimates)
- Performance metrics (throughput, latency, execution time)
- Worker-level result breakdown

**Example Output:**
```
🎯 Final Estimate of e: 2.7184512300
📐 True value of e:     2.7182818285
❌ Absolute Error:      0.0001694015
📉 Error Percentage:    0.006232%

📊 Statistical Summary:
   Workers completed:   8
   Total trials:        10,000,000
   Avg worker estimate: 2.7184512
   Std deviation:       0.002156
```

---

### `mcmc_bayesian_inference_client.py`
Markov Chain Monte Carlo (MCMC) for Bayesian parameter estimation using distributed workers. Demonstrates:
- Metropolis-Hastings MCMC algorithm
- Bayesian inference for normal distribution parameters (μ, σ)
- Multiple independent chains for convergence assessment
- Gelman-Rubin convergence diagnostics (R̂ statistic)
- Posterior distributions with credible intervals

```bash
# Default: 4 chains, 10,000 iterations each
python mcmc_bayesian_inference_client.py

# Custom number of chains
python mcmc_bayesian_inference_client.py 8

# Custom iterations per chain
python mcmc_bayesian_inference_client.py 4 20000

# Different foreman host
python mcmc_bayesian_inference_client.py 4 10000 192.168.1.100
```

**Use Case:**
Estimates the mean (μ) and standard deviation (σ) of a normal distribution from observed data using Bayesian inference with uninformative priors.

**Features:**
- Metropolis-Hastings MCMC sampling algorithm
- Multiple independent chains run in parallel
- Burn-in period to discard initial transient samples
- Gelman-Rubin R̂ convergence diagnostic (should be < 1.1)
- 95% posterior credible intervals
- Acceptance rate monitoring for tuning
- Per-chain and aggregated results

**Example Output:**
```
🎯 Posterior Distribution for μ (mean):
   Estimate:       5.012345
   Std. Error:     0.198234
   95% CI:         [4.623412, 5.401234]
   True value:     5.000000

📈 Convergence Diagnostics (Gelman-Rubin R̂):
   R̂ for μ:        1.0023 ✅ Converged
   R̂ for σ:        1.0045 ✅ Converged
   Overall:        ✅ All chains converged

⚙️  MCMC Statistics:
   Chains completed:     4
   Total samples:        40,000
   Avg acceptance rate:  35.24%
```

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                      MCMC CLIENT                            │
│  Observed Data: [5.2, 4.8, 5.1, 4.9, ...]                 │
│       ↓                                                     │
│  Create 4 independent chain configs                        │
└─────────────────────────────────────────────────────────────┘
                    ↓ distributed_map()
┌─────────────────────────────────────────────────────────────┐
│                        FOREMAN                              │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐          │
│  │Chain 0 │  │Chain 1 │  │Chain 2 │  │Chain 3 │          │
│  └────────┘  └────────┘  └────────┘  └────────┘          │
└─────────────────────────────────────────────────────────────┘
       ↓           ↓           ↓           ↓
  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
  │Worker 1│  │Worker 2│  │Worker 3│  │Worker 4│
  │MCMC    │  │MCMC    │  │MCMC    │  │MCMC    │
  │10k iter│  │10k iter│  │10k iter│  │10k iter│
  │μ≈5.01  │  │μ≈4.99  │  │μ≈5.02  │  │μ≈5.00  │
  └────────┘  └────────┘  └────────┘  └────────┘
       ↓           ↓           ↓           ↓
┌─────────────────────────────────────────────────────────────┐
│           AGGREGATION & CONVERGENCE CHECK                   │
│  - Pool samples from all chains                            │
│  - Calculate Gelman-Rubin R̂ statistic                     │
│  - Compute posterior means and credible intervals          │
└─────────────────────────────────────────────────────────────┘
```

## Usage

All scripts in this folder can be run directly from the `tests` directory. They automatically add the parent directory to the Python path to resolve imports.

## Typical Testing Workflow

### Basic Workflow
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

### Distributed Computing Workflows

#### Sentiment Analysis with PyTorch
1. **Start Foreman**
2. **Start Multiple Workers:**
   ```bash
   python run_multiple_workers.py 4
   ```
3. **Run Sentiment Analysis:**
   ```bash
   python sentiment_analysis_pytorch_client.py
   ```

#### Monte Carlo Simulation
1. **Start Foreman**
2. **Start Multiple Workers:**
   ```bash
   python run_multiple_workers.py 8
   ```
3. **Run Monte Carlo Estimation:**
   ```bash
   python monte_carlo_euler_client.py 10000000
   ```

#### MCMC Bayesian Inference
1. **Start Foreman**
2. **Start Multiple Workers:**
   ```bash
   python run_multiple_workers.py 4
   ```
3. **Run MCMC Inference:**
   ```bash
   python mcmc_bayesian_inference_client.py 4 20000
   ```

### Utility Commands
4. **View Database (optional):**
   ```bash
   python view_database.py
   ```

5. **Clear Database (if needed):**
   ```bash
   python quick_clear_db.py
   ```
