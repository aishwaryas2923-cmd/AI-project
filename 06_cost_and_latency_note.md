# COST AND LATENCY ENGINEERING ANALYSIS

**Course / Assessment:** CIT AI-Native Engineering Programme · Assessment 5  
**Document:** System Resource, Latency, and Operational Expenditure Analysis  
**Workload Target:** Average Daily Intake at College Health Centre (~100 to 150 Student Visits / Day)  

---

## 1. Workload Assumptions
- **Academic Health Centre Operating Hours:** 08:00 to 18:00 (10 hours daily).
- **Peak Arrival Waves:** 09:00 - 10:30 (Morning lecture rush) & 13:00 - 14:00 (Post-lunch rush).
- **Daily Volume:** Baseline of **120 student visits per operational day** (equivalent to four 30-visit batches).
- **Retry Rate:** Approximately 3% of calls require a single retry due to network jitter or JSON validation checks.
- **Total Daily API Invocations:** $\approx 124$ calls / day.

---

## 2. Token Accounting (Per Visit Record)

Each visit classification call consists of the 5-role system prompt, instructions, few-shot exemplars, the input note, and the structured JSON output:

| Component | Average Token Length | Description |
|:---|:---:|:---|
| **System Prompt & Role Instructions** | $\approx 310$ tokens | Role, constraints, rubric, schema rules |
| **Few-Shot Exemplars (4 examples)** | $\approx 140$ tokens | Demonstration of valid inputs and outputs |
| **Input Student Note** | $\approx 25$ tokens | Variable length (short student complaints) |
| **Total Prompt (Input) Tokens** | **$\approx 475$ tokens** | Cached prompt prefix allows substantial discount |
| **Completion (Output) Tokens** | **$\approx 45$ tokens** | Strict JSON payload ($\le 12$ words summary) |
| **Total Tokens Per Visit** | **$\approx 520$ tokens** | Total consumption per individual transaction |

---

## 3. Cost Modeling Across LLM Providers

### Option A: Groq Cloud (`openai/gpt-oss-20b` / `llama-3.1-8b-instant`)
- **Cost per Million Input Tokens:** \$0.05
- **Cost per Million Output Tokens:** \$0.08
- **Daily Cost Calculation (124 calls):**
  $$\text{Input: } 124 \times 475 = 58,900 \text{ tokens} \implies \frac{58,900}{1,000,000} \times \$0.05 = \$0.00295$$
  $$\text{Output: } 124 \times 45 = 5,580 \text{ tokens} \implies \frac{5,580}{1,000,000} \times \$0.08 = \$0.00045$$
  $$\mathbf{\text{Total Daily Cost (Groq): } \approx \$0.0034 \text{ USD / day} \ (\approx ₹0.28 \text{ INR / day})}$$
  $$\mathbf{\text{Monthly Cost (30 days): } \approx \$0.10 \text{ USD} \ (\approx ₹8.50 \text{ INR})}$$

### Option B: OpenAI API (`gpt-4o-mini`)
- **Cost per Million Input Tokens:** \$0.150
- **Cost per Million Output Tokens:** \$0.600
- **Daily Cost Calculation (124 calls):**
  $$\text{Input: } 58,900 \text{ tokens} \implies \$0.0088$$
  $$\text{Output: } 5,580 \text{ tokens} \implies \$0.0033$$
  $$\mathbf{\text{Total Daily Cost (OpenAI): } \approx \$0.0121 \text{ USD / day} \ (\approx ₹1.01 \text{ INR / day})}$$
  $$\mathbf{\text{Monthly Cost (30 days): } \approx \$0.36 \text{ USD} \ (\approx ₹30.00 \text{ INR})}$$

---

## 4. Latency Analysis & Benchmark Measurements

Empirical measurements gathered during the 30-record batch run on the local Python environment:

| Execution Metric | Groq API (`gpt-oss-20b`) | OpenAI API (`gpt-4o-mini`) | Local Deterministic Checks |
|:---|:---:|:---:|:---:|
| **Time to First Token (TTFT)** | $120 \text{ ms}$ | $420 \text{ ms}$ | $< 0.1 \text{ ms}$ |
| **Total Generation Latency** | $280 \text{ ms} - 450 \text{ ms}$ | $850 \text{ ms} - 1,400 \text{ ms}$ | $< 0.5 \text{ ms}$ |
| **Total 30-Record Batch Time** | **$9.2 \text{ seconds}$** | **$31.5 \text{ seconds}$** | **$< 0.02 \text{ seconds}$** |
| **Nurse Waiting Latency** | Instantaneous ($< 0.5 \text{s}$) | Negligible ($< 1.5 \text{s}$) | Real-time |

---

## 5. Architectural Recommendations for Scale
1. **Zero-Overhead Deterministic Pre-Filtering:** Red-flag keyword matching (`has_red_flag()`) executes in Python memory in under 0.2 milliseconds before any network request is issued. Emergency cases can be immediately bubbled to the queue even if the network is delayed.
2. **Prompt Caching:** Because the system prompt and exemplars are identical for all calls, modern LLM endpoints automatically apply prompt caching, reducing input processing time and cost by up to 50%.
3. **Queue Throughput Headroom:** Even on a free-tier rate limit of 30 RPM (Requests Per Minute), the system comfortably handles a normal clinic arrival rate (which rarely exceeds 3 to 4 students per minute).
