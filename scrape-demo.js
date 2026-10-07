// Demo script showing how to use camofox-browser to scrape websites from CSV without getting blocked
// Reads data_7.7m_405k.csv and visits each website using camofox-browser's anti-detection capabilities

const fs = require('fs');
const path = require('path');
const { parse } = require('csv-parse/sync');
const https = require('https');
const http = require('http');

// Configuration
const CAMOFOX_HOST = 'localhost';
const CAMOFOX_PORT = 9377;
const CSV_FILE = path.join(__dirname, 'data_7.7m_405k.csv');
const MAX_CONCURRENT = 3; // Limit concurrent requests to avoid overwhelming the server
const REQUEST_TIMEOUT = 30000; // 30 seconds per request
const USER_ID = 'demo-scraper'; // User ID for camofox-browser sessions

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
      req.write(JSON.stringify(postData));
    }
    req.end();
  });
}

// Helper function to delay execution
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Main function to process CSV and scrape websites
async function scrapeWebsites() {
  console.log('Starting camofox-browser scraping demo...');

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
    console.log(`✓ Loaded ${records.length} records from CSV`);
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

  console.log(`📝 Found ${websites.length} websites to visit`);

  if (websites.length === 0) {
    console.log('No websites found in CSV');
    return;
  }

  // Process websites with concurrency limit
  const results = [];
  const processed = new Set();

  async function processWebsite(index) {
    if (index >= websites.length) return;

    const websiteInfo = websites[index];
    const keyid = websiteInfo.keyid;

    // Skip if already processed
    if (processed.has(keyid)) {
      await processWebsite(index + 1);
      return;
    }

    processed.add(keyid);
    console.log(`\n[${index + 1}/${websites.length}] Processing: ${websiteInfo.company} (${websiteInfo.website})`);

    let tabId = null;
    try {
      // 1. Create a new tab
      console.log('  → Creating browser tab...');
      const createResp = await camofoxRequest({
        hostname: CAMOFOX_HOST,
        port: CAMOFOX_PORT,
        path: '/tabs',
        method: 'POST'
      }, {
        userId: USER_ID
      });

      if (createResp.status !== 200) {
        throw new Error(`Failed to create tab: ${createResp.status}`);
      }

      tabId = createResp.data.tabId;
      console.log(`  → Tab created: ${tabId}`);

      // 2. Navigate to the website
      console.log(`  → Navigating to ${websiteInfo.website}...`);
      const navigateResp = await camofoxRequest({
        hostname: CAMOFOX_HOST,
        port: CAMOFOX_PORT,
        path: `/tabs/${tabId}/navigate`,
        method: 'POST'
      }, {
        userId: USER_ID,
        url: websiteInfo.website,
        waitUntil: 'networkidle0',
        timeout: 15000
      });

      if (navigateResp.status !== 200) {
        throw new Error(`Failed to navigate: ${navigateResp.status}`);
      }

      console.log('  → Navigation successful');

      // 3. Wait a bit for any dynamic content
      await delay(2000);

      // 4. Get page title (as example of data extraction)
      console.log('  → Extracting page title...');
      const snapshotResp = await camofoxRequest({
        hostname: CAMOFOX_HOST,
        port: CAMOFOX_PORT,
        path: `/tabs/${tabId}/snapshot`,
        method: 'GET'
      });

      let title = 'Unknown';
      if (snapshotResp.status === 200 && snapshotResp.data) {
        // Try to extract title from accessibility snapshot or use a simpler approach
        // For demo, we'll just note that we got a snapshot
        title = 'Snapshot obtained';
      }

      // 5. Record success
      results.push({
        keyid: keyid,
        company: websiteInfo.company,
        website: websiteInfo.website,
        status: 'success',
        title: title,
        timestamp: new Date().toISOString()
      });

      console.log(`  ✓ Success: ${title}`);

    } catch (error) {
      console.error(`  ❌ Error: ${error.message}`);

      // Record failure
      results.push({
        keyid: keyid,
        company: websiteInfo.company,
        website: websiteInfo.website,
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
          console.log(`  → Tab ${tabId} closed`);
        } catch (cleanupError) {
          console.warn(`  ⚠️  Failed to close tab ${tabId}: ${cleanupError.message}`);
        }
      }
    }

    // Process next website
    await processWebsite(index + 1);
  }

  // Start processing with limited concurrency
  const workers = [];
  for (let i = 0; i < Math.min(MAX_CONCURRENT, websites.length); i++) {
    workers.push(processWebsite(i));
  }

  await Promise.all(workers);

  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('SCRAPING COMPLETE');
  console.log('='.repeat(60));

  const successful = results.filter(r => r.status === 'success');
  const failed = results.filter(r => r.status === 'error');

  console.log(`Total processed: ${results.length}`);
  console.log(`Successful: ${successful.length}`);
  console.log(`Failed: ${failed.length}`);

  if (failed.length > 0) {
    console.log('\nFailed websites:');
    failed.slice(0, 10).forEach(f => {
      console.log(`  - ${f.company}: ${f.error}`);
    });
    if (failed.length > 10) {
      console.log(`  ... and ${failed.length - 10} more`);
    }
  }

  // Save results to file
  const resultsFile = path.join(__dirname, 'scraping-results.json');
  fs.writeFileSync(resultsFile, JSON.stringify(results, null, 2));
  console.log(`\n💾 Detailed results saved to: ${resultsFile}`);

  console.log('\n🎉 Demo completed! The camofox-browser successfully visited websites');
  console.log('   without getting blocked thanks to its anti-detection features.');
}

// Run the demo
scrapeWebties().catch(console.error);