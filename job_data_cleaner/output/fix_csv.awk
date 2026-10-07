BEGIN {
    FS = ","
    OFS = ","
}

# Process header
NR == 1 {
    print
    next
}

# Process data rows
{
    # Ensure we have enough fields
    while (NF < 29) {
        $NF = $NF ","
        NF++
    }

    # Check if job_description (field 24) contains misplaced status/error messages
    job_desc = $24
    status = $5

    # Define patterns that indicate misplaced status/error messages in job_description
    misplaced_patterns = "Unreachable|Career Page Not Found|Career Page Found - Extraction Unsupported|No Jobs Found|Search Completed - No Verified Jobs"

    # Check if job_description contains a misplaced pattern
    if (job_desc ~ misplaced_patterns) {
        # If status column is empty or just "Validated", move the job_description to status
        if (status == "" || status == "Validated") {
            $5 = job_desc
            $24 = ""  # Clear job_description
        }
        # If status already has content, append the job_description to status
        else {
            $5 = status "; " job_desc
            $24 = ""  # Clear job_description
        }
    }

    # Also check for internet-company-name-search patterns in source field (field 29)
    source = $29
    if (source ~ /internet-company-name-search:/) {
        if ($5 == "" || $5 == "Validated") {
            $5 = source
            $29 = ""  # Clear source
        } else {
            $5 = $5 "; " source
            $29 = ""  # Clear source
        }
    }

    print
}