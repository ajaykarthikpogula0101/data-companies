# Chat Summary: Company Data Processing Distribution Across 7 VMs

## Date: 2026-08-25

## Overview
This document summarizes the discussion about processing company data from COMPANYWEB29th_July.xlsx starting from row 394,258 using 7 configured VMs, with each VM assigned 56,322 companies.

## Key Points Discussed

### Initial Request
- User needs to process company data from COMPANYWEB29th_July.xlsx
- Start from row 394,258 (1-based indexing) 
- Use 7 VMs configured in Azure
- Assign 56,322 companies to each VM
- Current progress: executed till row 394,257, so start from 394,258

### File Analysis
- Located: D:\data_companies\COMPANYWEB29th_July.xlsx
- Related files found:
  - VM0.csv through VM5.csv (existing output files from previous runs)
  - job_scraper directory containing processing pipeline
  - requirements.txt showing dependencies (openpyxl, pandas, etc.)
  - Various debug and test files

### Technical Infrastructure
- Job scraper pipeline located in: job_scraper/pipeline.py
- Key functions:
  - `read_companies()`: Reads Excel file using openpyxl
  - `run()`: Main processing function with offset/limit parameters
  - Supports resuming, threading, and configurable workers
- Dependencies: openpyxl>=3.1, pandas>=2.0, requests, beautifulsoup4, etc.

### Processing Plan
Based on analysis of the existing pipeline, the recommended approach is to:

1. **Calculate Work Distribution:**
   - Start offset: 394,257 (0-based for row 394,258)
   - Batch size per VM: 56,322 companies
   - Total companies to process: 394,254 (7 VMs × 56,322)
   - End offset: 788,511

2. **VM Assignment Table:**

| VM ID | Start Row (1-based) | Start Offset (0-based) | End Row (1-based) | Companies |
|-------|---------------------|------------------------|-------------------|-----------|
| VM0   | 394,258             | 394,257                | 450,579           | 56,322    |
| VM1   | 450,580             | 450,579                | 506,901           | 56,322    |
| VM2   | 506,902             | 506,901                | 563,223           | 56,322    |
| VM3   | 563,224             | 563,223                | 619,545           | 56,322    |
| VM4   | 619,546             | 619,545                | 675,867           | 56,322    |
| VM5   | 675,868             | 675,867                | 732,189           | 56,322    |
| VM6   | 732,190             | 732,189                | 788,511           | 56,322    |

3. **Execution Commands (run from D:\data_companies directory):**
   ```bash
   # VM0
   python -m job_scraper.pipeline --offset 394257 --limit 56322 --output-file VM0.csv --resume False
   
   # VM1
   python -m job_scraper.pipeline --offset 450579 --limit 56322 --output-file VM1.csv --resume False
   
   # VM2
   python -m job_scraper.pipeline --offset 506901 --limit 56322 --output-file VM2.csv --resume False
   
   # VM3
   python -m job_scraper.pipeline --offset 563223 --limit 56322 --output-file VM3.csv --resume False
   
   # VM4
   python -m job_scraper.pipeline --offset 619545 --limit 56322 --output-file VM4.csv --resume False
   
   # VM5
   python -m job_scraper.pipeline --offset 675867 --limit 56322 --output-file VM5.csv --resume False
   
   # VM6
   python -m job_scraper.pipeline --offset 732189 --limit 56322 --output-file VM6.csv --resume False
   ```

### Verification Steps
After each VM completes processing:
1. Verify output file row count: 56,322 data rows + 1 header = 56,323 total lines
2. Spot-check first and last company names match expected ranges
3. Ensure no overlap between VM output files
4. Validate CSV columns match OUTPUT_COLUMNS from job_scraper/config.py

### Prerequisites
1. Install required packages on each VM: `pip install openpyxl pandas requests beautifulsoup4 langdetect python-dotenv playwright`
2. Ensure each VM has access to COMPANYWEB29th_July.xlsx (copy to local storage or use shared access)
3. Verify job_scraper directory is present with all modules

### Notes
- The existing pipeline already supports offset and limit parameters, making distribution straightforward
- Default worker count is 10 threads per VM (adjustable via --workers parameter)
- To resume interrupted processing, change --resume False to --resume True
- Output files will follow the same format as existing VM*.csv files

## Plan Reference
A detailed plan was created during the planning phase and saved to:
C:\Users\Ajay karthik pogula\.claude\plans\check-the-file-called-whimsical-parrot.md

## Next Steps
1. Distribute the commands to each respective VM
2. Monitor progress via log files (scraper.log) or console output
3. Verify each VM completes its assigned batch
4. Optionally combine results when all VMs finish

---
*This summary was generated based on the available conversation context. For the complete interaction history, please refer to your chat export/save features.*