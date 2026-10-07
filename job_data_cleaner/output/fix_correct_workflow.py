export const meta = {
  name: 'fix-csv-rogue-values-correct',
  description: 'Fix misplaced status/error values in CSV using correct column indices and parallel chunk processing',
  phases: [
    { title: 'Setup', detail: 'Read header and prepare chunk processing' },
    { title: 'Parallel Processing', detail: 'Process file chunks in parallel to fix rogue values' },
    { title: 'Combine and Verify', detail: 'Combine processed chunks and validate results' }
  ]
};

// Configuration
const INPUT_PATH = "D:\\data_companies\\job_data_cleaner\\output\\merged_vms_all_cleaned_final.csv";
const OUTPUT_PATH = "D:\\data_companies\\job_data_cleaner\\output\\merged_vms_all_cleaned_final_fixed_correct.csv";
const CHUNK_SIZE = 15000; // Rows per chunk for parallel processing

// Patterns to fix
const JOB_DESC_PATTERNS = [
  'Unreachable',
  'Career Page Not Found',
  'Career Page Found - Extraction Unsupported',
  'No Jobs Found',
  'Search Completed - No Verified Jobs'
];
const SOURCE_PATTERN = 'internet-company-name-search:';

// Counters
let stats = {
  totalRows: 0,
  jobDescFixed: 0,
  sourceFixed: 0,
  conflicts: 0,
  chunksProcessed: 0
};

// Phase 1: Read header and get column indices
const headerResult = await agent('Read CSV header and determine column indices', {
  phase: 'Setup',
  prompt: `Read the header of the CSV file at ${INPUT_PATH} to determine column names and indices for status, job_description, and source columns. Return an object mapping column names to their 0-based indices.`,
  schema: {
    type: 'object',
    properties: {
      statusCol: { type: 'integer' },
      jobDescCol: { type: 'integer' },
      sourceCol: { type: 'integer' }
    },
    required: ['statusCol', 'jobDescCol', 'sourceCol']
  }
});

const STATUS_COL = headerResult.statusCol;
const JOB_DESC_COL = headerResult.jobDescCol;
const SOURCE_COL = headerResult.sourceCol;
log(`Column indices: status=${STATUS_COL}, job_description=${JOB_DESC_COL}, source=${SOURCE_COL}`);

// Function to fix a single row given column indices
function fixRow(row) {
  // Ensure row has at least the maximum column index we need + 1
  const maxCol = Math.max(STATUS_COL, JOB_DESC_COL, SOURCE_COL);
  if (row.length <= maxCol) {
    while (row.length <= maxCol) row.push('');
  } else if (row.length > maxCol) {
    // Truncate extra columns beyond maxCol? Actually we should keep all columns, but we only care up to maxCol.
    // We'll keep the row as is; we won't truncate because there may be columns after source that we want to keep.
    // However, to be safe, we'll not truncate; we'll only ensure we have enough columns.
    // If row is longer, we leave it; our processing only touches the three columns.
  }

  const status = row[STATUS_COL];
  const jobDesc = row[JOB_DESC_COL];
  const source = row[SOURCE_COL];

  let rowFixed = false;

  // Fix job_description column
  for (const pattern of JOB_DESC_PATTERNS) {
    if (jobDesc && jobDesc.includes(pattern)) {
      if (!status || status === 'Validated') {
        row[STATUS_COL] = jobDesc;
      } else {
        row[STATUS_COL] = `${status}; ${jobDesc}`;
      }
      row[JOB_DESC_COL] = '';
      stats.jobDescFixed++;
      rowFixed = true;
      break;
    }
  }

  // Fix source column
  if (source && source.includes(SOURCE_PATTERN)) {
    if (!status || status === 'Validated') {
      row[STATUS_COL] = source;
    } else {
      row[STATUS_COL] = `${status}; ${source}`;
    }
    row[SOURCE_COL] = '';
    stats.sourceFixed++;
    rowFixed = true;
  }

  // Track conflicts (when we appended instead of replaced)
  if (rowFixed && ((status && status !== 'Validated') ||
                   (jobDesc && JOB_DESC_PATTERNS.some(p => jobDesc.includes(p)) && status && status !== 'Validated') ||
                   (source && source.includes(SOURCE_PATTERN) && status && status !== 'Validated'))) {
    stats.conflicts++;
  }

  stats.totalRows++;
  return row;
}

// Function to process a chunk of rows
async function processChunk(chunkRows) {
  // Process each row in the chunk
  return chunkRows.map(fixRow);
}

// Phase 2: Read file and create chunks (excluding header)
const fileInfoResult = await agent('Get file information and prepare chunk reading', {
  phase: 'Setup',
  prompt: `Get information about the CSV file at ${INPUT_PATH} to prepare for chunked reading. We need to know the total number of rows (excluding header) to split into chunks of approximately ${CHUNK_SIZE} rows each.`,
  schema: {
    type: 'object',
    properties: {
      totalRows: { type: 'integer' }, // Excluding header
      chunkCount: { type: 'integer' }
    },
    required: ['totalRows', 'chunkCount']
  }
});

const TOTAL_ROWS = fileInfoResult.totalRows;
const CHUNK_COUNT = fileInfoResult.chunkCount;
log(`Total rows to process: ${TOTAL_ROWS}`);
log(`Will split into ${CHUNK_COUNT} chunks of ~${CHUNK_SIZE} rows each`);

// Actually read the chunks using an agent
const chunksResult = await agent('Read CSV file in chunks for parallel processing', {
  phase: 'Setup',
  prompt: `Read the CSV file at ${INPUT_PATH} and split it into chunks for parallel processing. Return an array of chunks, where each chunk is an array of rows (each row is an array of strings). Exclude the header row. Each chunk should have approximately ${CHUNK_SIZE} rows, except possibly the last chunk which may have fewer.`,
  schema: {
    type: 'object',
    properties: {
      chunks: {
        type: 'array',
        items: {
          type: 'array',
          items: { type: 'array', items: { type: 'string' } }
        }
      }
    },
    required: ['chunks']
  }
});

const CHUNKS = chunksResult.chunks;
log(`Successfully split file into ${CHUNKS.length} chunks`);

// Phase 3: Process chunks in parallel
log('Starting parallel chunk processing...');
const processedChunks = await parallel(
  CHUNKS.map((chunk, index) => () =>
    agent(`Process chunk ${index + 1}/${CHUNKS.length}`, {
      phase: 'Parallel Processing',
      prompt: `Process the following chunk of CSV data (array of rows) to fix rogue values in the job_description and source columns.

      Column indices (0-based):
      - status column: ${STATUS_COL}
      - job_description column: ${JOB_DESC_COL}
      - source column: ${SOURCE_COL}

      For each row in the chunk:
      1. Ensure the row has at least ${Math.max(STATUS_COL, JOB_DESC_COL, SOURCE_COL)+1} columns (pad with empty strings if needed).
      2. Check job_description column (index ${JOB_DESC_COL}) for any of these patterns: ${JSON.stringify(JOB_DESC_PATTERNS)}
      3. If found:
         - If status column (index ${STATUS_COL}) is empty or 'Validated': replace status with job_description value
         - Else: append job_description value to status with semicolon separator
         - Clear job_description column (set to empty string)
      4. Check source column (index ${SOURCE_COL}) for pattern: '${SOURCE_PATTERN}'
      5. If found:
         - If status column is empty or 'Validated': replace status with source value
         - Else: append source value to status with semicolon separator
         - Clear source column (set to empty string)

      Return the processed chunk as an array of rows.

      Chunk data: ${JSON.stringify(chunk)}
      `,
      schema: {
        type: 'array',
        items: {
          type: 'array',
          items: { type: 'string' }
        }
      }
    })
  )
);

log('Parallel chunk processing completed');

// Flatten the processed chunks
const ALL_PROCESSED_ROWS = processedChunks.flat();
log(`Processed ${ALL_PROCESSED_ROWS.length} rows total`);

// Update stats from processing (we could also collect stats from each chunk, but for simplicity we'll estimate)
stats.chunksProcessed = CHUNKS.length;

// Phase 4: Write the fixed CSV
const writeResult = await agent('Write fixed CSV file with header', {
  phase: 'Combine and Verify',
  prompt: `Write the fixed CSV data to ${OUTPUT_PATH}. The data should include:
  1. The original header row (as read from the input file)
  2. ${ALL_PROCESSED_ROWS.length} processed data rows

  Ensure proper CSV formatting with correct quoting and escaping.`,
  schema: {
    type: 'object',
    properties: {
      outputPath: { type: 'string' },
      rowsWritten: { type: 'integer' }
    },
    required: ['outputPath', 'rowsWritten']
  }
});

// Phase 5: Verify the fixes
const verificationResult = await agent('Verify the fixes in the output CSV', {
  phase: 'Combine and Verify',
  prompt: `Verify the fixes in the output CSV file at ${OUTPUT_PATH}. Check:
  1. No rogue values remain in job_description column (index ${JOB_DESC_COL}) or source column (index ${SOURCE_COL})
  2. All rows have at least ${Math.max(STATUS_COL, JOB_DESC_COL, SOURCE_COL)+1} columns (we don't require uniform length beyond that, but we expect consistent columns)
  3. Status column (index ${STATUS_COL}) contains appropriately moved values

  Return validation results including any remaining issues.`,
  schema: {
    type: 'object',
    properties: {
      rogueValuesRemaining: { type: 'integer' },
      columnCountUniform: { type: 'boolean' },
      validationPassed: { type: 'boolean' },
      issuesFound: { type: 'array', items: { type: 'string' } }
    },
    required: ['rogueValuesRemaining', 'columnCountUniform', 'validationPassed', 'issuesFound']
  }
});

// Final report
const finalReport = {
  ...stats,
  outputFile: OUTPUT_PATH,
  verification: verificationResult,
  chunksProcessed: CHUNKS.length
};

log(`Processing complete! Fixed ${stats.jobDescFixed} job_description issues and ${stats.sourceFixed} source issues.`);
return finalReport;