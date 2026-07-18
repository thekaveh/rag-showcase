# RAG Showcase Evaluation Results

This generated report is the complete static comparison of the committed evaluation
and judgment snapshots. It complements the [evaluation methodology](evaluation-methodology.md),
the [narrative comparison](comparison.md), the [dataset complexity ladder]
(dataset-complexity-report.md), and the [raw result snapshots](results/README.md).

## 1. Reading the Results

The default overall order is the **dataset-macro judge mean**: each measured dataset
contributes one equally weighted judge mean. **Query-weighted judge mean** is shown
separately and weights each evaluated query equally. No composite score combines quality,
coverage, latency, or operational reliability.

Higher judge, answer-relevancy, faithfulness, eligible-coverage, successful-response, and
per-query-win values are better. Lower ranks, disagreement, latency, error rate,
errors, and timeouts are better. Judge coverage is evaluated judge questions over all
judge questions. Ragas coverage is evaluated rows over eligible rows (`total rows -
ineligible`), while each metric's total rows, ineligible rows, evaluator errors, and
timeouts remain separate columns. `N/A` means no value was recorded or no rows were
eligible and carries an empty machine sort value. Faithfulness ineligible rows are not
failures and are never coerced to zero. Ragas evaluator errors and timeouts also remain
separate from response errors and timeouts.

Base approaches and flavor aliases are intentionally separate tiers. A flavor identifies
its base family but cannot occupy a base-approach rank.

## 2. Overall Base-Approach Leaderboard

<table class="results-table" id="base-overall">
<caption>Overall base-approach leaderboard</caption>
<thead>
<tr>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Overall judge rank</th>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Approach</th>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Maturity</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Dataset-macro judge</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Query-weighted judge</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Judge errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge gemma4:31b</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge gemma4:31b coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge qwen3.6:latest</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge qwen3.6:latest coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Judge disagreement</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge disagreement comparisons</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Mean dataset rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Best dataset rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Worst dataset rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Per-query wins</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy mean</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy coverage (eligible)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy total rows</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy ineligible</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy timeouts</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness mean</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness coverage (eligible)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness total rows</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness ineligible</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness timeouts</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Mean latency (ms)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Successful</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Attempted</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Error rate</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Timeouts</th>
</tr>
</thead>
<tbody>
<tr>
<td data-sort-value="1">1</td>
<td data-sort-value="contextual-rag">contextual-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="3.756945">3.757</td>
<td data-sort-value="3.8">3.800</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.55">3.550</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="4.05">4.050</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.6">0.600</td>
<td data-sort-value="20">20</td>
<td data-sort-value="2.0">2.000</td>
<td data-sort-value="1">1</td>
<td data-sort-value="3">3</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.87175">0.872</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.416613">0.417</td>
<td data-sort-value="0.6">12 / 20 (60.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="17143.75">17143.75</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="2">2</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="3.743056">3.743</td>
<td data-sort-value="3.8">3.800</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.65">3.650</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.95">3.950</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="20">20</td>
<td data-sort-value="2.0">2.000</td>
<td data-sort-value="1">1</td>
<td data-sort-value="3">3</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.851176">0.851</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.432732">0.433</td>
<td data-sort-value="0.65">13 / 20 (65.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6065.35">6065.35</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="2">2</td>
<td data-sort-value="vanilla-rag">vanilla-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="3.743056">3.743</td>
<td data-sort-value="3.775">3.775</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.65">3.650</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.9">3.900</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.85">0.850</td>
<td data-sort-value="20">20</td>
<td data-sort-value="2.0">2.000</td>
<td data-sort-value="1">1</td>
<td data-sort-value="3">3</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.798499">0.798</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.398658">0.399</td>
<td data-sort-value="0.7">14 / 20 (70.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5637.9">5637.90</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="4">4</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="3.513889">3.514</td>
<td data-sort-value="3.525">3.525</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.5">3.500</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.55">3.550</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.75">0.750</td>
<td data-sort-value="20">20</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="2">2</td>
<td data-sort-value="6">6</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.867921">0.868</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.379212">0.379</td>
<td data-sort-value="0.75">15 / 20 (75.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0">0</td>
<td data-sort-value="16044.75">16044.75</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="5">5</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2.930556">2.931</td>
<td data-sort-value="2.9">2.900</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.6">2.600</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.2">3.200</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.9">0.900</td>
<td data-sort-value="20">20</td>
<td data-sort-value="5.666667">5.667</td>
<td data-sort-value="5">5</td>
<td data-sort-value="7">7</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.804643">0.805</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="15134.0">15134.00</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="6">6</td>
<td data-sort-value="n8n-adaptive-rag">n8n-adaptive-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2.923611">2.924</td>
<td data-sort-value="2.875">2.875</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.75">2.750</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.85">0.850</td>
<td data-sort-value="20">20</td>
<td data-sort-value="4.666667">4.667</td>
<td data-sort-value="2">2</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.779015">0.779</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.387734">0.388</td>
<td data-sort-value="0.45">9 / 20 (45.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="11">11</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6279.25">6279.25</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="7">7</td>
<td data-sort-value="agentic-rag">agentic-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2.701389">2.701</td>
<td data-sort-value="2.675">2.675</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.55">2.550</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="2.8">2.800</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.85">0.850</td>
<td data-sort-value="20">20</td>
<td data-sort-value="5.0">5.000</td>
<td data-sort-value="2">2</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.729015">0.729</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.44329">0.443</td>
<td data-sort-value="0.45">9 / 20 (45.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="11">11</td>
<td data-sort-value="0">0</td>
<td data-sort-value="27434.6">27434.60</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
</tbody>
</table>

## 3. Base Approaches by Dataset

<table class="results-table" id="base-by-dataset" data-filterable="true">
<caption>Base approaches by measured dataset</caption>
<thead>
<tr>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Dataset</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Complexity</th>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Approach</th>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Maturity</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Judge rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge mean</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Judge errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge gemma4:31b</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge gemma4:31b coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge qwen3.6:latest</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge qwen3.6:latest coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Judge disagreement</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge disagreement comparisons</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Per-query wins</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy mean</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy coverage (eligible)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy total rows</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy ineligible</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy timeouts</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness mean</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness coverage (eligible)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness total rows</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness ineligible</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness timeouts</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Latency rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Mean latency (ms)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Successful</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Attempted</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Error rate</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Timeouts</th>
</tr>
</thead>
<tbody>
<tr data-filter-dataset="baseline_curated" data-filter-approach="vanilla-rag" data-filter-base-family="vanilla-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="vanilla-rag">vanilla-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="1">1</td>
<td data-sort-value="4.166667">4.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4.333333">4.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="1.0">1.000</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.708486">0.708</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.672138">0.672</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="3833.833333">3833.83</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="hybrid-rag" data-filter-base-family="hybrid-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2">2</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4.333333">4.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="1.0">1.000</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.869325">0.869</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.644872">0.645</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="17682.833333">17682.83</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="contextual-rag" data-filter-base-family="contextual-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="contextual-rag">contextual-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="3">3</td>
<td data-sort-value="3.916667">3.917</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.5">3.500</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.333333">4.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.833333">0.833</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.893817">0.894</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.3">0.300</td>
<td data-sort-value="0.8333333333333334">5 / 6 (83.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="18016.333333">18016.33</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="lazy-graph-rag" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="3">3</td>
<td data-sort-value="3.916667">3.917</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.833333">3.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.166667">0.167</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.858328">0.858</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.636364">0.636</td>
<td data-sort-value="0.8333333333333334">5 / 6 (83.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="5514.0">5514.00</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="graph-rag" data-filter-base-family="graph-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="5">5</td>
<td data-sort-value="3.75">3.750</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.833333">3.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="6">6</td>
<td data-sort-value="4">4</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.841588">0.842</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="12611.833333">12611.83</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="n8n-adaptive-rag" data-filter-base-family="n8n-adaptive-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="n8n-adaptive-rag">n8n-adaptive-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="6">6</td>
<td data-sort-value="3.333333">3.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.666667">0.667</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.733174">0.733</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.563636">0.564</td>
<td data-sort-value="0.8333333333333334">5 / 6 (83.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="2798.333333">2798.33</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="agentic-rag" data-filter-base-family="agentic-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="agentic-rag">agentic-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="7">7</td>
<td data-sort-value="2.666667">2.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="2.333333">2.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.666667">0.667</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0.566507">0.567</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.663636">0.664</td>
<td data-sort-value="0.8333333333333334">5 / 6 (83.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="10773.666667">10773.67</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="lazy-graph-rag" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="1">1</td>
<td data-sort-value="4.3125">4.312</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4.125">4.125</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="4.5">4.500</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.625">0.625</td>
<td data-sort-value="8">8</td>
<td data-sort-value="2">2</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.829112">0.829</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.416212">0.416</td>
<td data-sort-value="0.625">5 / 8 (62.50%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="4935.75">4935.75</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="contextual-rag" data-filter-base-family="contextual-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="contextual-rag">contextual-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2">2</td>
<td data-sort-value="4.1875">4.188</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="4.375">4.375</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.625">0.625</td>
<td data-sort-value="8">8</td>
<td data-sort-value="2">2</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.841045">0.841</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.607143">0.607</td>
<td data-sort-value="0.625">5 / 8 (62.50%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="11196.875">11196.88</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="vanilla-rag" data-filter-base-family="vanilla-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="vanilla-rag">vanilla-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="3">3</td>
<td data-sort-value="4.0625">4.062</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.75">3.750</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="4.375">4.375</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.875">0.875</td>
<td data-sort-value="8">8</td>
<td data-sort-value="3">3</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.850505">0.851</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.278724">0.279</td>
<td data-sort-value="0.625">5 / 8 (62.50%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="4539.25">4539.25</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="hybrid-rag" data-filter-base-family="hybrid-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="4">4</td>
<td data-sort-value="3.625">3.625</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.375">3.375</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="3.875">3.875</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.75">0.750</td>
<td data-sort-value="8">8</td>
<td data-sort-value="1">1</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.859264">0.859</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.303159">0.303</td>
<td data-sort-value="0.75">6 / 8 (75.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="9808.875">9808.88</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="graph-rag" data-filter-base-family="graph-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="5">5</td>
<td data-sort-value="2.625">2.625</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.125">2.125</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="3.125">3.125</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="1.25">1.250</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.795566">0.796</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="12473.875">12473.88</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="agentic-rag" data-filter-base-family="agentic-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="agentic-rag">agentic-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="6">6</td>
<td data-sort-value="2.4375">2.438</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.125">2.125</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="2.75">2.750</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.625">0.625</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.739673">0.740</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.0">0.000</td>
<td data-sort-value="0.125">1 / 8 (12.50%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="29112.75">29112.75</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="n8n-adaptive-rag" data-filter-base-family="n8n-adaptive-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="n8n-adaptive-rag">n8n-adaptive-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="6">6</td>
<td data-sort-value="2.4375">2.438</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.125">2.125</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="2.75">2.750</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.625">0.625</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.739673">0.740</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.0">0.000</td>
<td data-sort-value="0.125">1 / 8 (12.50%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="5299.0">5299.00</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="contextual-rag" data-filter-base-family="contextual-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="contextual-rag">contextual-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="1">1</td>
<td data-sort-value="3.166667">3.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.333333">3.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.333333">0.333</td>
<td data-sort-value="6">6</td>
<td data-sort-value="2">2</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.890624">0.891</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.231818">0.232</td>
<td data-sort-value="0.3333333333333333">2 / 6 (33.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="24200.333333">24200.33</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="agentic-rag" data-filter-base-family="agentic-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="agentic-rag">agentic-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2">2</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.666667">2.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.333333">3.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="1.333333">1.333</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.877311">0.877</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.22381">0.224</td>
<td data-sort-value="0.5">3 / 6 (50.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="41858.0">41858.00</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="lazy-graph-rag" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="2">2</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.833333">2.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.166667">3.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.666667">0.667</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.873443">0.873</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.120879">0.121</td>
<td data-sort-value="0.5">3 / 6 (50.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="8122.833333">8122.83</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="n8n-adaptive-rag" data-filter-base-family="n8n-adaptive-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="n8n-adaptive-rag">n8n-adaptive-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2">2</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.666667">2.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.333333">3.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="1.333333">1.333</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.877311">0.877</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.22381">0.224</td>
<td data-sort-value="0.5">3 / 6 (50.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="11067.166667">11067.17</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="vanilla-rag" data-filter-base-family="vanilla-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="vanilla-rag">vanilla-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2">2</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.833333">2.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.166667">3.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.666667">0.667</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.819171">0.819</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.051587">0.052</td>
<td data-sort-value="0.5">3 / 6 (50.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="8906.833333">8906.83</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="hybrid-rag" data-filter-base-family="hybrid-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="6">6</td>
<td data-sort-value="2.916667">2.917</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.833333">2.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="6">6</td>
<td data-sort-value="2">2</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.87806">0.878</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.000</td>
<td data-sort-value="0.5">3 / 6 (50.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="22721.166667">22721.17</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="graph-rag" data-filter-base-family="graph-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="7">7</td>
<td data-sort-value="2.416667">2.417</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.166667">2.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="2.666667">2.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.833333">0.833</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0.779802">0.780</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="21203.0">21203.00</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
</tbody>
</table>

## 4. Overall Flavor-Alias Leaderboard

<table class="results-table" id="flavor-overall">
<caption>Overall flavor-alias leaderboard</caption>
<thead>
<tr>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Overall judge rank</th>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Flavor</th>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Base family</th>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Maturity</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Dataset-macro judge</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Query-weighted judge</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Judge errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge gemma4:31b</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge gemma4:31b coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge qwen3.6:latest</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge qwen3.6:latest coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Judge disagreement</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge disagreement comparisons</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Mean dataset rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Best dataset rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Worst dataset rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Per-query wins</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy mean</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy coverage (eligible)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy total rows</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy ineligible</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy timeouts</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness mean</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness coverage (eligible)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness total rows</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness ineligible</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness timeouts</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Mean latency (ms)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Successful</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Attempted</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Error rate</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Timeouts</th>
</tr>
</thead>
<tbody>
<tr>
<td data-sort-value="1">1</td>
<td data-sort-value="hybrid-rag-fast">hybrid-rag-fast</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="3.791667">3.792</td>
<td data-sort-value="3.775">3.775</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.6">3.600</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.95">3.950</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.65">0.650</td>
<td data-sort-value="20">20</td>
<td data-sort-value="2.666667">2.667</td>
<td data-sort-value="1">1</td>
<td data-sort-value="5">5</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.797335">0.797</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.389347">0.389</td>
<td data-sort-value="0.8">16 / 20 (80.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4815.9">4815.90</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="2">2</td>
<td data-sort-value="hybrid-rag-high-recall">hybrid-rag-high-recall</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="3.756944">3.757</td>
<td data-sort-value="3.8">3.800</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.5">3.500</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="4.1">4.100</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.6">0.600</td>
<td data-sort-value="20">20</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1">1</td>
<td data-sort-value="7">7</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.876931">0.877</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.419877">0.420</td>
<td data-sort-value="0.6">12 / 20 (60.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="23866.35">23866.35</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="3">3</td>
<td data-sort-value="lazy-graph-rag-wide">lazy-graph-rag-wide</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="3.729167">3.729</td>
<td data-sort-value="3.725">3.725</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.65">3.650</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.8">3.800</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.45">0.450</td>
<td data-sort-value="20">20</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1">1</td>
<td data-sort-value="7">7</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.817834">0.818</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.468162">0.468</td>
<td data-sort-value="0.55">11 / 20 (55.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="9">9</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7197.3">7197.30</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="4">4</td>
<td data-sort-value="vanilla-rag-wide">vanilla-rag-wide</td>
<td data-sort-value="vanilla-rag">vanilla-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="3.694444">3.694</td>
<td data-sort-value="3.725">3.725</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.4">3.400</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="4.05">4.050</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.75">0.750</td>
<td data-sort-value="20">20</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="2">2</td>
<td data-sort-value="5">5</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.839142">0.839</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.454723">0.455</td>
<td data-sort-value="0.75">15 / 20 (75.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8154.35">8154.35</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="5">5</td>
<td data-sort-value="contextual-rag-high-recall">contextual-rag-high-recall</td>
<td data-sort-value="contextual-rag">contextual-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="3.597222">3.597</td>
<td data-sort-value="3.575">3.575</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.4">3.400</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.75">3.750</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.45">0.450</td>
<td data-sort-value="20">20</td>
<td data-sort-value="4.333333">4.333</td>
<td data-sort-value="2">2</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.854548">0.855</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.378439">0.378</td>
<td data-sort-value="0.6">12 / 20 (60.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="24930.25">24930.25</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="5">5</td>
<td data-sort-value="lazy-graph-rag-fast">lazy-graph-rag-fast</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="3.597222">3.597</td>
<td data-sort-value="3.6">3.600</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.3">3.300</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.9">3.900</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.7">0.700</td>
<td data-sort-value="20">20</td>
<td data-sort-value="4.333333">4.333</td>
<td data-sort-value="3">3</td>
<td data-sort-value="5">5</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.845995">0.846</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.424299">0.424</td>
<td data-sort-value="0.7">14 / 20 (70.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4786.25">4786.25</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="7">7</td>
<td data-sort-value="lazy-graph-rag-balanced">lazy-graph-rag-balanced</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="3.479167">3.479</td>
<td data-sort-value="3.5">3.500</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.2">3.200</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.8">3.800</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.6">0.600</td>
<td data-sort-value="20">20</td>
<td data-sort-value="5.0">5.000</td>
<td data-sort-value="3">3</td>
<td data-sort-value="7">7</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.854127">0.854</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.4649">0.465</td>
<td data-sort-value="0.65">13 / 20 (65.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5752.7">5752.70</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="8">8</td>
<td data-sort-value="graph-rag-wide">graph-rag-wide</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2.875">2.875</td>
<td data-sort-value="2.85">2.850</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.65">2.650</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="3.05">3.050</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="20">20</td>
<td data-sort-value="8.0">8.000</td>
<td data-sort-value="5">5</td>
<td data-sort-value="11">11</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.835319">0.835</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="18603.75">18603.75</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="9">9</td>
<td data-sort-value="graph-rag-rerank">graph-rag-rerank</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2.840278">2.840</td>
<td data-sort-value="2.8">2.800</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.7">2.700</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="2.9">2.900</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.4">0.400</td>
<td data-sort-value="20">20</td>
<td data-sort-value="9.0">9.000</td>
<td data-sort-value="9">9</td>
<td data-sort-value="9">9</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.822043">0.822</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="21719.25">21719.25</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="10">10</td>
<td data-sort-value="n8n-adaptive-rag-default">n8n-adaptive-rag-default</td>
<td data-sort-value="n8n-adaptive-rag">n8n-adaptive-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2.708333">2.708</td>
<td data-sort-value="2.675">2.675</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.45">2.450</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="2.9">2.900</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.45">0.450</td>
<td data-sort-value="20">20</td>
<td data-sort-value="9.666667">9.667</td>
<td data-sort-value="8">8</td>
<td data-sort-value="11">11</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.737848">0.738</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.463492">0.463</td>
<td data-sort-value="0.45">9 / 20 (45.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="11">11</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8158.95">8158.95</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="11">11</td>
<td data-sort-value="graph-rag-fast">graph-rag-fast</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2.548611">2.549</td>
<td data-sort-value="2.5">2.500</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.3">2.300</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="2.7">2.700</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="20">20</td>
<td data-sort-value="11.0">11.000</td>
<td data-sort-value="9">9</td>
<td data-sort-value="12">12</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.83425">0.834</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="12400.35">12400.35</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr>
<td data-sort-value="12">12</td>
<td data-sort-value="agentic-rag-deeper">agentic-rag-deeper</td>
<td data-sort-value="agentic-rag">agentic-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2.527778">2.528</td>
<td data-sort-value="2.5">2.500</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.35">2.350</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="2.65">2.650</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="0.4">0.400</td>
<td data-sort-value="20">20</td>
<td data-sort-value="10.666667">10.667</td>
<td data-sort-value="9">9</td>
<td data-sort-value="12">12</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.725011">0.725</td>
<td data-sort-value="1.0">20 / 20 (100.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0.730903">0.731</td>
<td data-sort-value="0.4">8 / 20 (40.00%)</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0">0</td>
<td data-sort-value="12">12</td>
<td data-sort-value="0">0</td>
<td data-sort-value="17397.75">17397.75</td>
<td data-sort-value="20">20</td>
<td data-sort-value="20">20</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
</tbody>
</table>

## 5. Flavor Aliases by Dataset

<table class="results-table" id="flavor-by-dataset" data-filterable="true">
<caption>Flavor aliases by measured dataset</caption>
<thead>
<tr>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Dataset</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Complexity</th>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Flavor</th>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Base family</th>
<th scope="col" data-sort-type="text" data-sort-direction="neutral">Maturity</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Judge rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge mean</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Judge errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge gemma4:31b</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge gemma4:31b coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge qwen3.6:latest</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge qwen3.6:latest coverage</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Judge disagreement</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Judge disagreement comparisons</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Per-query wins</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy mean</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy coverage (eligible)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Answer relevancy total rows</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy ineligible</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Answer relevancy timeouts</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness mean</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness coverage (eligible)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Faithfulness total rows</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness ineligible</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Faithfulness timeouts</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Latency rank</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Mean latency (ms)</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Successful</th>
<th scope="col" data-sort-type="number" data-sort-direction="higher">Attempted</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Error rate</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Errors</th>
<th scope="col" data-sort-type="number" data-sort-direction="lower">Timeouts</th>
</tr>
</thead>
<tbody>
<tr data-filter-dataset="baseline_curated" data-filter-approach="lazy-graph-rag-wide" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="lazy-graph-rag-wide">lazy-graph-rag-wide</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="1">1</td>
<td data-sort-value="4.583333">4.583</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4.5">4.500</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.666667">4.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.166667">0.167</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="9">9</td>
<td data-sort-value="0.797515">0.798</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.681818">0.682</td>
<td data-sort-value="0.6666666666666666">4 / 6 (66.67%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="6311.333333">6311.33</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="hybrid-rag-fast" data-filter-base-family="hybrid-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="hybrid-rag-fast">hybrid-rag-fast</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2">2</td>
<td data-sort-value="4.083333">4.083</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.833333">3.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.333333">4.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="10">10</td>
<td data-sort-value="0.674801">0.675</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.62619">0.626</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="3227.833333">3227.83</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="vanilla-rag-wide" data-filter-base-family="vanilla-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="vanilla-rag-wide">vanilla-rag-wide</td>
<td data-sort-value="vanilla-rag">vanilla-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2">2</td>
<td data-sort-value="4.083333">4.083</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.833333">3.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.333333">4.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.84577">0.846</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0.619697">0.620</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="5685.0">5685.00</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="contextual-rag-high-recall" data-filter-base-family="contextual-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="contextual-rag-high-recall">contextual-rag-high-recall</td>
<td data-sort-value="contextual-rag">contextual-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="4">4</td>
<td data-sort-value="3.916667">3.917</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.833333">3.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.166667">0.167</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.905166">0.905</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="9">9</td>
<td data-sort-value="0.2">0.200</td>
<td data-sort-value="0.8333333333333334">5 / 6 (83.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0">0</td>
<td data-sort-value="12">12</td>
<td data-sort-value="26844.5">26844.50</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="graph-rag-wide" data-filter-base-family="graph-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="graph-rag-wide">graph-rag-wide</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="5">5</td>
<td data-sort-value="3.833333">3.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.333333">0.333</td>
<td data-sort-value="6">6</td>
<td data-sort-value="3">3</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.832587">0.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8">8</td>
<td data-sort-value="17524.166667">17524.17</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="lazy-graph-rag-fast" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="lazy-graph-rag-fast">lazy-graph-rag-fast</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="5">5</td>
<td data-sort-value="3.833333">3.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.333333">0.333</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.881562">0.882</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.595418">0.595</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="3392.666667">3392.67</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="hybrid-rag-high-recall" data-filter-base-family="hybrid-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="hybrid-rag-high-recall">hybrid-rag-high-recall</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="7">7</td>
<td data-sort-value="3.75">3.750</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.5">3.500</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.893177">0.893</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.680952">0.681</td>
<td data-sort-value="0.8333333333333334">5 / 6 (83.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0">0</td>
<td data-sort-value="11">11</td>
<td data-sort-value="26029.666667">26029.67</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="lazy-graph-rag-balanced" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="lazy-graph-rag-balanced">lazy-graph-rag-balanced</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="7">7</td>
<td data-sort-value="3.75">3.750</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.5">3.500</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.868166">0.868</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.72">0.720</td>
<td data-sort-value="0.8333333333333334">5 / 6 (83.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="4911.5">4911.50</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="graph-rag-fast" data-filter-base-family="graph-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="graph-rag-fast">graph-rag-fast</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="9">9</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.5">3.500</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.833333">3.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.333333">0.333</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0.844335">0.844</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="8759.666667">8759.67</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="graph-rag-rerank" data-filter-base-family="graph-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="graph-rag-rerank">graph-rag-rerank</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="9">9</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.333333">0.333</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.846745">0.847</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="9">9</td>
<td data-sort-value="20866.333333">20866.33</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="n8n-adaptive-rag-default" data-filter-base-family="n8n-adaptive-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="n8n-adaptive-rag-default">n8n-adaptive-rag-default</td>
<td data-sort-value="n8n-adaptive-rag">n8n-adaptive-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="11">11</td>
<td data-sort-value="3.166667">3.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.166667">3.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.166667">3.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.0">0.000</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="11">11</td>
<td data-sort-value="0.595951">0.596</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.7">0.700</td>
<td data-sort-value="0.8333333333333334">5 / 6 (83.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="8537.0">8537.00</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="baseline_curated" data-filter-approach="agentic-rag-deeper" data-filter-base-family="agentic-rag">
<td data-sort-value="baseline_curated">baseline_curated</td>
<td data-sort-value="1">1</td>
<td data-sort-value="agentic-rag-deeper">agentic-rag-deeper</td>
<td data-sort-value="agentic-rag">agentic-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="12">12</td>
<td data-sort-value="2.916667">2.917</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.833333">2.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.166667">0.167</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="12">12</td>
<td data-sort-value="0.575641">0.576</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="1.0">1.000</td>
<td data-sort-value="0.6666666666666666">4 / 6 (66.67%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0">0</td>
<td data-sort-value="10">10</td>
<td data-sort-value="22713.5">22713.50</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="hybrid-rag-high-recall" data-filter-base-family="hybrid-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="hybrid-rag-high-recall">hybrid-rag-high-recall</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="1">1</td>
<td data-sort-value="4.1875">4.188</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.875">3.875</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="4.5">4.500</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.625">0.625</td>
<td data-sort-value="8">8</td>
<td data-sort-value="1">1</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.854923">0.855</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0.326753">0.327</td>
<td data-sort-value="0.625">5 / 8 (62.50%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="10226.75">10226.75</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="vanilla-rag-wide" data-filter-base-family="vanilla-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="vanilla-rag-wide">vanilla-rag-wide</td>
<td data-sort-value="vanilla-rag">vanilla-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2">2</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.75">3.750</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="4.25">4.250</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.75">0.750</td>
<td data-sort-value="8">8</td>
<td data-sort-value="3">3</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.848509">0.849</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.487698">0.488</td>
<td data-sort-value="0.75">6 / 8 (75.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6094.25">6094.25</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="lazy-graph-rag-balanced" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="lazy-graph-rag-balanced">lazy-graph-rag-balanced</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="3">3</td>
<td data-sort-value="3.6875">3.688</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.375">3.375</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.625">0.625</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.829112">0.829</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.416212">0.416</td>
<td data-sort-value="0.625">5 / 8 (62.50%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="4731.375">4731.38</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="lazy-graph-rag-wide" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="lazy-graph-rag-wide">lazy-graph-rag-wide</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="3">3</td>
<td data-sort-value="3.6875">3.688</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.625">3.625</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="3.75">3.750</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.375">0.375</td>
<td data-sort-value="8">8</td>
<td data-sort-value="1">1</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.842579">0.843</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.401169">0.401</td>
<td data-sort-value="0.625">5 / 8 (62.50%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="5173.75">5173.75</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="hybrid-rag-fast" data-filter-base-family="hybrid-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="hybrid-rag-fast">hybrid-rag-fast</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="5">5</td>
<td data-sort-value="3.625">3.625</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.625">3.625</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="3.625">3.625</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.854504">0.855</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.381766">0.382</td>
<td data-sort-value="0.75">6 / 8 (75.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="4380.5">4380.50</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="lazy-graph-rag-fast" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="lazy-graph-rag-fast">lazy-graph-rag-fast</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="5">5</td>
<td data-sort-value="3.625">3.625</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.375">3.375</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="3.875">3.875</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="8">8</td>
<td data-sort-value="1">1</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0.833495">0.833</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.314484">0.314</td>
<td data-sort-value="0.75">6 / 8 (75.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="3908.125">3908.12</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="contextual-rag-high-recall" data-filter-base-family="contextual-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="contextual-rag-high-recall">contextual-rag-high-recall</td>
<td data-sort-value="contextual-rag">contextual-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="7">7</td>
<td data-sort-value="3.375">3.375</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.25">3.250</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="3.5">3.500</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.849466">0.849</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.530688">0.531</td>
<td data-sort-value="0.75">6 / 8 (75.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8">8</td>
<td data-sort-value="11707.5">11707.50</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="graph-rag-wide" data-filter-base-family="graph-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="graph-rag-wide">graph-rag-wide</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="8">8</td>
<td data-sort-value="2.625">2.625</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.5">2.500</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="2.75">2.750</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="8">8</td>
<td data-sort-value="1">1</td>
<td data-sort-value="10">10</td>
<td data-sort-value="0.816143">0.816</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="10">10</td>
<td data-sort-value="13365.5">13365.50</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="graph-rag-rerank" data-filter-base-family="graph-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="graph-rag-rerank">graph-rag-rerank</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="9">9</td>
<td data-sort-value="2.4375">2.438</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.375">2.375</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="2.5">2.500</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.375">0.375</td>
<td data-sort-value="8">8</td>
<td data-sort-value="1">1</td>
<td data-sort-value="11">11</td>
<td data-sort-value="0.805261">0.805</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="12">12</td>
<td data-sort-value="14687.75">14687.75</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="n8n-adaptive-rag-default" data-filter-base-family="n8n-adaptive-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="n8n-adaptive-rag-default">n8n-adaptive-rag-default</td>
<td data-sort-value="n8n-adaptive-rag">n8n-adaptive-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="10">10</td>
<td data-sort-value="2.375">2.375</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.25">2.250</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="2.5">2.500</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.25">0.250</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="12">12</td>
<td data-sort-value="0.739673">0.740</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="9">9</td>
<td data-sort-value="0.0">0.000</td>
<td data-sort-value="0.125">1 / 8 (12.50%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="5914.75">5914.75</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="agentic-rag-deeper" data-filter-base-family="agentic-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="agentic-rag-deeper">agentic-rag-deeper</td>
<td data-sort-value="agentic-rag">agentic-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="11">11</td>
<td data-sort-value="2.25">2.250</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.25">2.250</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="2.25">2.250</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.25">0.250</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.849188">0.849</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.392361">0.392</td>
<td data-sort-value="0.25">2 / 8 (25.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="11">11</td>
<td data-sort-value="13527.0">13527.00</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="graph_native" data-filter-approach="graph-rag-fast" data-filter-base-family="graph-rag">
<td data-sort-value="graph_native">graph_native</td>
<td data-sort-value="2">2</td>
<td data-sort-value="graph-rag-fast">graph-rag-fast</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="12">12</td>
<td data-sort-value="2.0625">2.062</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1.875">1.875</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="2.25">2.250</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="0.625">0.625</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="9">9</td>
<td data-sort-value="0.821342">0.821</td>
<td data-sort-value="1.0">8 / 8 (100.00%)</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="9">9</td>
<td data-sort-value="11994.75">11994.75</td>
<td data-sort-value="8">8</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="hybrid-rag-fast" data-filter-base-family="hybrid-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="hybrid-rag-fast">hybrid-rag-fast</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="1">1</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.333333">3.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="4.0">4.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="1.0">1.000</td>
<td data-sort-value="6">6</td>
<td data-sort-value="2">2</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.843642">0.844</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.045455">0.045</td>
<td data-sort-value="0.6666666666666666">4 / 6 (66.67%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="6984.5">6984.50</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="contextual-rag-high-recall" data-filter-base-family="contextual-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="contextual-rag-high-recall">contextual-rag-high-recall</td>
<td data-sort-value="contextual-rag">contextual-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="2">2</td>
<td data-sort-value="3.5">3.500</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.166667">3.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.833333">3.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.666667">0.667</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="10">10</td>
<td data-sort-value="0.810705">0.811</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.357143">0.357</td>
<td data-sort-value="0.16666666666666666">1 / 6 (16.67%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0">0</td>
<td data-sort-value="12">12</td>
<td data-sort-value="40646.333333">40646.33</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="hybrid-rag-high-recall" data-filter-base-family="hybrid-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="hybrid-rag-high-recall">hybrid-rag-high-recall</td>
<td data-sort-value="hybrid-rag">hybrid-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="3">3</td>
<td data-sort-value="3.333333">3.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.666667">3.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.666667">0.667</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.890029">0.890</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="9">9</td>
<td data-sort-value="0.0">0.000</td>
<td data-sort-value="0.3333333333333333">2 / 6 (33.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0">0</td>
<td data-sort-value="11">11</td>
<td data-sort-value="39889.166667">39889.17</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="lazy-graph-rag-fast" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="lazy-graph-rag-fast">lazy-graph-rag-fast</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="3">3</td>
<td data-sort-value="3.333333">3.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.833333">2.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.833333">3.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="1.333333">1.333</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0.827093">0.827</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.240385">0.240</td>
<td data-sort-value="0.3333333333333333">2 / 6 (33.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="7350.666667">7350.67</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="lazy-graph-rag-balanced" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="lazy-graph-rag-balanced">lazy-graph-rag-balanced</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="5">5</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.666667">2.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.333333">3.333</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.666667">0.667</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0.873443">0.873</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.120879">0.121</td>
<td data-sort-value="0.5">3 / 6 (50.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="7955.666667">7955.67</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="vanilla-rag-wide" data-filter-base-family="vanilla-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="vanilla-rag-wide">vanilla-rag-wide</td>
<td data-sort-value="vanilla-rag">vanilla-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="5">5</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.5">2.500</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.5">3.500</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="1.0">1.000</td>
<td data-sort-value="6">6</td>
<td data-sort-value="1">1</td>
<td data-sort-value="8">8</td>
<td data-sort-value="0.820025">0.820</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="0.058824">0.059</td>
<td data-sort-value="0.5">3 / 6 (50.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="13370.5">13370.50</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="lazy-graph-rag-wide" data-filter-base-family="lazy-graph-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="lazy-graph-rag-wide">lazy-graph-rag-wide</td>
<td data-sort-value="lazy-graph-rag">lazy-graph-rag</td>
<td data-sort-value="experimental">experimental</td>
<td data-sort-value="7">7</td>
<td data-sort-value="2.916667">2.917</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.833333">2.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.0">3.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.833333">0.833</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="11">11</td>
<td data-sort-value="0.805158">0.805</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="0.208333">0.208</td>
<td data-sort-value="0.3333333333333333">2 / 6 (33.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0">0</td>
<td data-sort-value="5">5</td>
<td data-sort-value="10781.333333">10781.33</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="n8n-adaptive-rag-default" data-filter-base-family="n8n-adaptive-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="n8n-adaptive-rag-default">n8n-adaptive-rag-default</td>
<td data-sort-value="n8n-adaptive-rag">n8n-adaptive-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="8">8</td>
<td data-sort-value="2.583333">2.583</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.0">2.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="3.166667">3.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="1.166667">1.167</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2">2</td>
<td data-sort-value="0.877311">0.877</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.22381">0.224</td>
<td data-sort-value="0.5">3 / 6 (50.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="3">3</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="10773.166667">10773.17</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="agentic-rag-deeper" data-filter-base-family="agentic-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="agentic-rag-deeper">agentic-rag-deeper</td>
<td data-sort-value="agentic-rag">agentic-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="9">9</td>
<td data-sort-value="2.416667">2.417</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.0">2.000</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="2.833333">2.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.833333">0.833</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="12">12</td>
<td data-sort-value="0.708813">0.709</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1">1</td>
<td data-sort-value="0.53125">0.531</td>
<td data-sort-value="0.3333333333333333">2 / 6 (33.33%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0">0</td>
<td data-sort-value="8">8</td>
<td data-sort-value="17243.0">17243.00</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="graph-rag-rerank" data-filter-base-family="graph-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="graph-rag-rerank">graph-rag-rerank</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="9">9</td>
<td data-sort-value="2.416667">2.417</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="2.166667">2.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="2.666667">2.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="9">9</td>
<td data-sort-value="0.819718">0.820</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="10">10</td>
<td data-sort-value="31947.5">31947.50</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="graph-rag-wide" data-filter-base-family="graph-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="graph-rag-wide">graph-rag-wide</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="11">11</td>
<td data-sort-value="2.166667">2.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1.833333">1.833</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="2.5">2.500</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.666667">0.667</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="4">4</td>
<td data-sort-value="0.86362">0.864</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="9">9</td>
<td data-sort-value="26667.666667">26667.67</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
<tr data-filter-dataset="cyber_threat_intel" data-filter-approach="graph-rag-fast" data-filter-base-family="graph-rag">
<td data-sort-value="cyber_threat_intel">cyber_threat_intel</td>
<td data-sort-value="7">7</td>
<td data-sort-value="graph-rag-fast">graph-rag-fast</td>
<td data-sort-value="graph-rag">graph-rag</td>
<td data-sort-value="canonical">canonical</td>
<td data-sort-value="12">12</td>
<td data-sort-value="1.916667">1.917</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0">0</td>
<td data-sort-value="1.666667">1.667</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="2.166667">2.167</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="0.5">0.500</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.841376">0.841</td>
<td data-sort-value="1.0">6 / 6 (100.00%)</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="">N/A</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
<td data-sort-value="7">7</td>
<td data-sort-value="16581.833333">16581.83</td>
<td data-sort-value="6">6</td>
<td data-sort-value="6">6</td>
<td data-sort-value="0.0">0.00%</td>
<td data-sort-value="0">0</td>
<td data-sort-value="0">0</td>
</tr>
</tbody>
</table>
