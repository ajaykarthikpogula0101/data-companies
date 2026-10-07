import pandas as pd
import multiprocessing as mp
import time

def process_chunk(chunk):
    """Process a chunk of data and return the number of rows."""
    return len(chunk)

def main():
    csv_file = "5k records.csv"
    chunksize = 1000  # Adjust as needed

    start_time = time.time()

    # Read the CSV in chunks
    chunk_iter = pd.read_csv(csv_file, chunksize=chunksize)

    # Create a pool of workers
    with mp.Pool() as pool:
        # Process each chunk in parallel
        results = pool.map(process_chunk, chunk_iter)

    total_rows = sum(results)

    end_time = time.time()

    print(f"Total rows: {total_rows}")
    print(f"Time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()