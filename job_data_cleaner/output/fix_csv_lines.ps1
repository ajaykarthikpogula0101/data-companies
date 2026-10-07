$inputFile = "D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final.csv"
$outputFile = "D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final_fixed.csv"

# Define patterns for misplaced status messages in job_description
$jobDescriptionPatterns = @(
    "Career Page Not Found",
    "Career Page Found - Extraction Unsupported",
    "No Jobs Found",
    "Unreachable",
    "Search Completed - No Verified Jobs"
)

# Pattern for internet-company-name-search in source
$sourcePattern = "internet-company-name-search:"

# Process file line by line
$lineNumber = 0
Get-Content -Path $inputFile | ForEach-Object {
    $lineNumber++

    if ($lineNumber -eq 1) {
        # Write header as-is
        $_ | Out-File -FilePath $outputFile -Encoding UTF8 -Append
        return
    }

    # Parse CSV line (simple split - assumes no commas within fields except as delimiters)
    # For a production solution, we'd want a proper CSV parser, but this should work for our data
    $fields = $_ -split ',', 29  # Split into max 29 fields

    # Ensure we have at least 29 fields (pad with empty strings if needed)
    while ($fields.Length -lt 29) {
        $fields += ""
    }

    # Get the relevant fields
    $status = $fields[4]           # Column 5 (index 4)
    $jobDescription = $fields[23]  # Column 24 (index 23)
    $source = $fields[28]          # Column 29 (index 28)

    $fixed = $false

    # Check if job_description contains misplaced status messages
    foreach ($pattern in $jobDescriptionPatterns) {
        if ($jobDescription -like "*$pattern*") {
            # Found misplaced status in job_description
            if ([string]::IsNullOrWhiteSpace($status) -or $status -eq "Validated") {
                # Status is empty or just "Validated", replace it
                $fields[4] = $jobDescription
            } else {
                # Status has meaningful content, append the job_description
                $fields[4] = "$status; $jobDescription"
            }
            # Clear the job_description field
            $fields[23] = ""
            $fixed = $true
            break
        }
    }

    # Check if source contains internet-company-name-search pattern
    if ($source -like "*$sourcePattern*") {
        if ([string]::IsNullOrWhiteSpace($fields[4]) -or $fields[4] -eq "Validated") {
            # Status is empty or just "Validated", replace it
            $fields[4] = $source
        } else {
            # Status has meaningful content, append the source
            $fields[4] = "$fields[4]; $source"
        }
        # Clear the source field
        $fields[28] = ""
        $fixed = $true
    }

    # Rejoin fields and write to output
    $outputLine = ($fields -join ',')
    $outputLine | Out-File -FilePath $outputFile -Encoding UTF8 -Append

    # Progress indicator
    if ($lineNumber % 10000 -eq 0) {
        Write-Progress -Activity "Processing CSV" -Status "Processed $lineNumber lines" -PercentComplete ($lineNumber / 909324 * 100)
    }
}

Write-Host "Processing complete. Fixed file saved to: $outputFile"