import pandas as pd
import multiprocessing as mp

def process_chunk(chunk_df):
    """Process a chunk and return number of rows."""
    return len(chunk_df)

def main():
    csv_file = "5k records.csv"
    chunksize = 1000  # adjust as needed

    # Read CSV in chunks, skip bad lines, handle BOM
    chunk_iter = pd.read_csv(
        csv_file,
        chunksize=chunksize,
        on_bad_lines='skip',
        encoding='utf-8-sig'
    )

    total_rows = 0
    with mp.Pool() as pool:
        # Use imap to process chunks lazily
        for result in pool.imap(process_chunk, chunk_iter):
            total_rows += result

    print(f"Total rows processed (skipping bad lines): {total_rows}")

if __name__ == "__main__":
    main()