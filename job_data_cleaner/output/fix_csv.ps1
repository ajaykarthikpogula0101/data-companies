# Read the CSV file
$filePath = "D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final.csv"
$outputPath = "D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final_fixed.csv"

# Read all lines
$lines = Get-Content -Path $filePath -Raw

# Split into lines
$lineArray = $lines -split "`r?`n"

# Process each line
$processedLines = @()
foreach ($line in $lineArray) {
    if ($line -match '^\s*$') {
        # Skip empty lines
        continue
    }

    if ($_PSCommandPath.Equals($lineArray[0])) {
        # Header line - just add it
        $processedLines += $line
        continue
    }

    # Split the line by commas, but handle quoted fields properly
    # This is a simple approach - for complex CSV, we'd need a proper parser
    $fields = $line -split '(?<!",)",(?!"(?:[^"]*"[^"]*")*[^"]*$)'

    # Ensure we have enough fields
    while ($fields.Length -lt 29) {
        $fields += ""
    }

    # Check if job_description (index 23) contains misplaced status/error messages
    $jobDesc = $fields[23]
    $status = $fields[4]

    # Define patterns that indicate misplaced status/error messages
    $misplacedPatterns = @(
        "Unreachable",
        "Career Page Not Found",
        "Career Page Found - Extraction Unsupported",
        "No Jobs Found",
        "Search Completed - No Verified Jobs"
    )

    $hasMisplaced = $false
    foreach ($pattern in $misplacedPatterns) {
        if ($jobDesc -like "*$pattern*") {
            $hasMisplaced = $true
            break
        }
    }

    if ($hasMisplaced) {
        # If status column is empty or just "Validated", move the job_description to status
        if ([string]::IsNullOrWhiteSpace($status) -or $status -eq "Validated") {
            $fields[4] = $jobDesc
            $fields[23] = ""  # Clear job_description
        }
        # If status already has content, append the job_description to status
        else {
            $fields[4] = "$status; $jobDesc"
            $fields[23] = ""  # Clear job_description
        }
    }

    # Also check for internet-company-name-search patterns in source field (index 28)
    $source = $fields[28]
    if ($source -like "*internet-company-name-search:*") {
        if ([string]::IsNullOrWhiteSpace($status) -or $status -eq "Validated") {
            $fields[4] = $source
            $fields[28] = ""  # Clear source
        } else {
            $fields[4] = "$fields[4]; $source"
            $fields[28] = ""  # Clear source
        }
    }

    # Rejoin the fields
    $processedLine = ($fields -join ',')
    $processedLines += $processedLine
}

# Write the fixed file
$processedLines | Set-Content -Path $outputPath -Encoding UTF8

Write-Host "Fixed CSV written to: $outputPath"