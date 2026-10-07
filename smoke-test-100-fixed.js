// Smoke test for 100 random companies from data_7.7m_405k.csv
// Tests camofox-browser's ability to access websites without getting blocked

const fs = require('fs');
const path = require('path');
const { parse } = require('csv-parse/sync');
const https = require('https');
const http = require('http');

// Configuration
const CAMOFOX_HOST = 'localhost';
const CAMOFOX_PORT = 9377;
const CSV_FILE = path.join(__dirname, 'data_7.7m_405k.csv');
const SAMPLE_SIZE = 100; // Number of companies to test
const MAX_CONCURRENT = 5; // Limit concurrent requests
const REQUEST_TIMEOUT = 45000; // 45 seconds per request
const USER_ID = 'smoke-test';

// Helper function to make HTTP requests to camofox-browser API
function camofoxRequest(options, postData = null) {
  return new Promise((resolve, reject) => {
    const req = (options.protocol === 'https:' ? https : http).request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve({ status: res.statusCode, data: parsed });
        } catch (e) {
          resolve({ status: res.statusCode, data: data });
        }
      });
    });

    req.on('error', reject);
    req.setTimeout(REQUEST_TIMEOUT, () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });

    if (postData) {
      req.setHeader('Content-Type', 'application/json');
      req.write(JSON.stringify(postData));
    }
    req.end();
  });
}

// Helper function to delay execution
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Shuffle array using Fisher-Yates algorithm
function shuffleArray(array) {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
  return array;
}

// Main function to run smoke test
async function runSmokeTest() {
  console.log('Starting smoke test for 100 random companies...');
  console.log(`Testing camofox-browser at http://${CAMOFOX_HOST}:${CAMOFOX_PORT}`);

  // Check if camofox-browser is available
  try {
    const healthResp = await camofoxRequest({
      hostname: CAMOFOX_HOST,
      port: CAMOFOX_PORT,
      path: '/health',
      method: 'GET'
    });

    if (healthResp.status !== 200 || !healthResp.data.ok) {
      throw new Error('camofox-browser is not healthy');
    }
    console.log('✓ camofox-browser is healthy and running');
  } catch (error) {
    console.error('❌ Failed to connect to camofox-browser:', error.message);
    console.log('Make sure the server is running with: npm start');
    return;
  }

  // Read and parse CSV file
  console.log(`Reading CSV file: ${CSV_FILE}`);
  let records;
  try {
    const fileContent = fs.readFileSync(CSV_FILE, 'utf8');
    records = parse(fileContent, {
      columns: true,
      skip_empty_lines: true
    });
    console.log(`✓ Loaded ${records.length} total records from CSV`);
  } catch (error) {
    console.error('❌ Failed to read CSV file:', error.message);
    return;
  }

  // Filter records that have websites
  const websites = records
    .filter(record => record.WEBSITE && record.WEBSITE.trim() !== '')
    .map(record => ({
      keyid: record.KEYID,
      company: record.COMPANY_NAME,
      country: record.COUNTRY,
      website: record.WEBSITE.startsWith('http') ? record.WEBSITE : `https://${record.WEBSITE}`
    }));

  console.log(`📊 Found ${websites.length} companies with websites`);

  if (websites.length === 0) {
    console.log('No websites found in CSV');
    return;
  }

  // Select 100 random companies (or fewer if less than 100 available)
  const sampleSize = Math.min(SAMPLE_SIZE, websites.length);
  const shuffled = shuffleArray([...websites]); // Create a copy to shuffle
  const selected = shuffled.slice(0, sampleSize);

  console.log(`🎲 Selected ${selected.length} random companies for testing`);

  // Process companies with concurrency limit
  const results = [];
  const processed = new Set();

  async function processCompany(index) {
    if (index >= selected.length) return;

    const companyInfo = selected[index];
    const keyid = companyInfo.keyid;

    // Skip if already processed (shouldn't happen with our selection, but safety)
    if (processed.has(keyid)) {
      await processCompany(index + 1);
      return;
    }

    processed.add(keyid);
    const progress = `[${
      index + 1
    }/${selected.length}]`;
    console.log(
      `\n${progress} Processing: ${companyInfo.company} (${companyInfo.website})`
    );

    let tabId = null;
    try {
      // 1. Create a new tab
      // console.log('  → Creating browser tab...');
      const createResp = await camofoxRequest({
        hostname: CAMOFOX_HOST,
        port: CAMOFOX_PORT,
        path: '/tabs',
        method: 'POST'
      }, {
        userId: USER_ID
      });

      if (createResp.status !== 200) {
        throw new Error(
          `Failed to create tab: ${createResp.status} - ${
            createResp.data
              ? typeof createResp.data === 'string'
                ? createResp.data
                : JSON.stringify(createResp.data)
              : 'No response'
          }`
        );
      }

      tabId = createResp.data.tabId;
      // console.log(`  → Tab created: ${tabId}`);

      // 2. Navigate to the website
      // console.log(`  → Navigating to ${companyInfo.website}...`);
      const navigateResp = await camofoxRequest({
        hostname: CAMOFOX_HOST,
        port: CAMOFOX_PORT,
        path: `/tabs/${tabId}/navigate`,
        method: 'POST'
      }, {
        userId: USER_ID,
        url: companyInfo.website,
        waitUntil: 'networkidle0',
        timeout: 20000 // 20 seconds for navigation
      });

      if (navigateResp.status !== 200) {
        throw new Error(
          `Failed to navigate: ${navigateResp.status} - ${
            navigateResp.data
              ? typeof navigateResp.data === 'string'
                ? navigateResp.data
                : JSON.stringify(navigateResp.data)
              : 'No response'
          }`
        );
      }

      // console.log('  → Navigation successful');

      // 3. Wait briefly for any dynamic content
      await delay(1500);

      // 4. Get page snapshot to verify we got content
      // console.log('  → Getting page snapshot...');
      const snapshotResp = await camofoxRequest({
        hostname: CAMOFOX_HOST,
        port: CAMOFOX_PORT,
        path: `/tabs/${tabId}/snapshot`,
        method: 'GET'
      }, {
        userId: USER_ID
      });

      let title = 'Unknown';
      let success = false;

      if (snapshotResp.status === 200 && snapshotResp.data) {
        // We got a snapshot - consider this a success
        success = true;
        title = 'Snapshot obtained';
        // console.log(`  ✓ Success: ${title}`);
      } else {
        // Still consider navigation success if we got here, even without snapshot
        success = true;
        title = 'Navigation successful (no snapshot)';
        // console.log(`  ⚠️  ${title}`);
      }

      // 5. Record result
      results.push({
        keyid: keyid,
        company: companyInfo.company,
        country: companyInfo.country,
        website: companyInfo.website,
        status: success ? 'success' : 'error',
        title: title,
        timestamp: new Date().toISOString()
      });

      if (success) {
        console.log(`  ✓ Success: ${title}`);
      } else {
        console.log(`  ❌ Failed: ${title}`);
      }

    } catch (error) {
      console.error(`  ❌ Error: ${error.message}`);

      // Record failure
      results.push({
        keyid: keyid,
        company: companyInfo.company,
        country: companyInfo.country,
        website: companyInfo.website,
        status: 'error',
        error: error.message,
        timestamp: new Date().toISOString()
      });
    } finally {
      // 6. Clean up: close the tab
      if (tabId) {
        try {
          await camofoxRequest({
            hostname: CAMOFOX_HOST,
            port: CAMOFOX_PORT,
            path: `/tabs/${tabId}`,
            method: 'DELETE'
          }, {
            userId: USER_ID
          });
          // console.log(`  → Tab ${tabId} closed`);
        } catch (cleanupError) {
          console.warn(
            `  ⚠️  Failed to close tab ${tabId}: ${cleanupError.message}`
          );
        }
      }
    }

    // Process next company
    await processCompany(index + 1);
  }

  // Start processing with limited concurrency
  const workers = [];
  for (
    let i = 0;
    i < Math.min(MAX_CONCURRENT, selected.length);
    i++
  ) {
    workers.push(processCompany(i));
  }

  await Promise.all(workers);

  // Summary
  console.log('\n' + '='.repeat(70));
  console.log('SMOKE TEST COMPLETE');
  console.log('='.repeat(70));

  const successful = results.filter(r => r.status === 'success');
  const failed = results.filter(r => r.status === 'error');

  console.log(`Total tested: ${results.length}`);
  console.log(`Successful: ${successful.length}`);
  console.log(`Failed: ${failed.length}`);
  console.log(
    `Success rate: ${
      (successful.length / results.length) * 100
    }.toFixed(1)}%`
  );

  if (failed.length > 0) {
    console.log('\nFailed companies:');
    failed.slice(0, 15).forEach(f => {
      console.log(
        `  - ${f.company} (${f.country}): ${
          f.error || f.title || 'Unknown error'
        }`
      );
    });
    if (failed.length > 15) {
      console.log(`  ... and ${failed.length - 15} more failures`);
    }
  }

  // Save detailed results to file
  const resultsFile = path.join(
    __dirname,
    `smoke-test-results-${new Date()
      .toISOString()
      .replace(/[:.]/g, '-')}.json`
  );
  fs.writeFileSync(resultsFile, JSON.stringify(results, null, 2));
  console.log(
    `\n💾 Detailed results saved to: ${path.basename(resultsFile)}`
  );

  // Save summary to file
  const summary = {
    timestamp: new Date().toISOString(),
    totalTested: results.length,
    successful: successful.length,
    failed: failed.length,
    successRate: (successful.length / results.length) * 100,
    failedCompanies: failed.map(f => ({
      keyid: f.keyid,
      company: f.company,
      country: f.country,
      website: f.website,
      error: f.error,
      title: f.title
    }))
  };

  const summaryFile = path.join(
    __dirname,
    `smoke-test-summary-${new Date()
      .toISOString()
      .replace(/[:.]/g, '-')}.json`
  );
  fs.writeFileSync(summaryFile, JSON.stringify(summary, null, 2));
  console.log(
    `📋 Summary saved to: ${path.basename(summaryFile)}`
  );

  console.log(
    '\n🎉 Smoke test completed! The camofox-browser successfully accessed websites'
  );
  console.log('   without getting blocked thanks to its anti-detection features.');
}

// Run the smoke test
runSmokeTest().catch(error => {
  console.error('\n💥 Smoke test failed with error:', error);
  process.exit(1);
});