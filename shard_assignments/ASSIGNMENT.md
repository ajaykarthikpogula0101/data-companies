# Company assignment — which VM gets which companies

Input: `data_7.7m_405k.csv`, 405,210 companies.

Split: **interleaved** — VM with shard `i` takes data rows `i`, `i+5`, `i+10`, ... Every company is assigned to exactly one VM. Verified: 405,210 unique KEYIDs across the five files, 0 duplicates, 0 missed.

| VM | shard | companies | with a website | file |
|---|---|---|---|---|
| vm1-50000 | 0 | 81,042 | 34,124 | `vm1-50000_shard_0_of_5.csv` |
| vm2nd | 1 | 81,042 | 34,114 | `vm2nd_shard_1_of_5.csv` |
| vm3rd | 2 | 81,042 | 34,111 | `vm3rd_shard_2_of_5.csv` |
| vm4th | 3 | 81,042 | 34,098 | `vm4th_shard_3_of_5.csv` |
| vm5th | 4 | 81,042 | 34,078 | `vm5th_shard_4_of_5.csv` |
| **total** | | **405,210** | **170,525** | |

## Countries on each VM

| VM | USA | Brazil | Germany | India | Japan | other |
|---|---|---|---|---|---|---|
| vm1-50000 | 14611 | 14424 | 8642 | 6150 | 3996 | 33219 |
| vm2nd | 14450 | 14373 | 8623 | 6079 | 3948 | 33569 |
| vm3rd | 14672 | 14083 | 8721 | 6150 | 3902 | 33514 |
| vm4th | 14646 | 14277 | 8742 | 6115 | 3983 | 33279 |
| vm5th | 14618 | 14260 | 8638 | 6263 | 3854 | 33409 |

## Why interleaved and not one block each

The file is grouped by source, so five contiguous blocks are not equal work: block 4
holds only 28,352 companies that have a website, against block 2's 36,622 — a 29%
gap. Whichever VM drew the heavy block would run about a day longer than the rest
while the others sat idle. Taking every 5th row instead evens it out to within 0.1%
(34,078 to 34,124), so all five finish together.

## Checking it on the VMs

Each VM works out its own slice from `SHARD_INDEX` in `/opt/job_scraper/.env.scraper`
and logs it on startup:

```
ssh -i "<key>" azureuser@<ip> 'grep -m1 "Shard" /opt/job_scraper/logs/scraper.log'
```

It prints, for example: `Shard 2/5 (interleave): 81042 companies`.

The CSV files here are a copy for your records — the VMs do not read them. They each
read the same full `data_7.7m_405k.csv` and take their own slice from it, which is
why the split cannot drift out of sync.
