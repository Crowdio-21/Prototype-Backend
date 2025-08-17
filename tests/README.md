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
