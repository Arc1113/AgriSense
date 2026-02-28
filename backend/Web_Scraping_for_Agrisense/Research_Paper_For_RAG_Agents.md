AgriSense: A Retrieval-Augmented AI Assistant for Tomato Disease Treatment Recommendation
Robert Jhon D. Aracena
University of Mindanao, Matina, Davao City, Philippines
 r.aracena.545985@umindanao.edu.ph
 
Absract - AgriSense is a Retrieval-Augmented Generation (RAG) assistant for tomato disease treatment recommendations that combines an on-device disease detector with a grounded LLM-based advisory agent. The system indexes authoritative agricultural manuals and extension bulletins into a vectorized knowledge base, retrieves context-relevant passages for detected diseases, and uses a controlled LLM agent to produce actionable, weather-aware treatment plans. AgriSense uses a lightweight on-device TensorFlow Lite model for image diagnosis, all-MiniLM embeddings with ChromaDB for retrieval, a cross-encoder reranker for precision, and a LLaMA-based agent for controlled text generation. The study evaluates retrieval quality, grounding (citation correctness), and recommendation reliability against agronomic guidance from official sources, as well as system latency on a mobile–backend pipeline. Results demonstrate that retrieval grounding substantially reduces hallucination, improves citation accuracy, and produces farmer-actionable advice within acceptable response times. The contribution is an integrated RAG workflow tailored for smallholder tomato production that emphasizes safety, traceability, and practical deployment constraints.



1. Introduction
Agriculture, particularly the cultivation of high-value crops like tomatoes, is crucial for sustainable agriculture, global food security, and economic growth [1]. However, tomato plants are highly susceptible to a variety of pests, pathogens, and environmental factors that can rapidly devastate yields if left unmanaged [1]. For instance, pests like the tomato leafminer (Tuta absoluta) or severe fungal infections like late blight can destroy 80% to 100% of an untreated crop within days [2, 3]. These crop diseases directly reduce the quality, yield, and market value of the harvest, resulting in significant global economic losses [1]. While timely diagnosis and intervention are critical, farmers and agricultural practitioners often lack immediate access to expert agronomic advice. Traditional methods of seeking treatment recommendations relying on manual literature searches or awaiting expert consultation are often too slow to prevent significant crop damage.
Recent advancements in artificial intelligence, particularly the application of deep learning and computer vision models, have revolutionized the automated detection and recognition of plant diseases [4, 5]. These modern computer vision approaches significantly outperform traditional image processing techniques in identifying specific leaf pathologies [6, 7]. Yet, visually identifying the pathogen is only half the solution; determining the correct, localized, and safe treatment protocol remains a complex challenge. To address the communication of these treatments, there is growing interest in utilizing Large Language Models (LLMs) as digital agronomy assistants [8]. However, generic LLMs often struggle in domains requiring specialized expertise and are highly prone to "hallucinations" the generation of confident but factually incorrect, nonsensical, or fabricated information [9, 10]. Relying on ungrounded AI for crop treatment can result in improper chemical applications or ineffective remedies, potentially worsening crop health and environmental safety.
To bridge the critical gap between visual disease diagnosis and actionable, expert-level intervention, this study introduces AgriSense, a Retrieval-Augmented AI Assistant. AgriSense shifts the paradigm from generic text generation to highly specialized decision support by integrating an autonomous AI agent framework with a Retrieval-Augmented Generation (RAG) architecture. RAG systems externalize domain knowledge, allowing the generative AI model to be grounded in factual information and external databases that were not originally part of its baseline training data [11, 12]. Instead of relying solely on an LLM’s generalized weights, AgriSense actively retrieves information from a specialized knowledge base constructed from official agricultural manuals and validated treatment protocols. By utilizing RAG, the system significantly reduces the risk of hallucinations, ensures factual consistency, and provides traceable evidence for its agricultural recommendations [12, 13]. Consequently, the primary objectives of this research are to design a robust AI Agent framework utilizing an LLM integrated with a RAG system, to index a specialized knowledge base for tomato cultivation, and to rigorously evaluate the system's reliability against established expert agronomic standards.
1.1 Objectives of the Study
The primary goal of this project is to develop a reliable, expert-grounded AI assistant for tomato disease treatment recommendations. Specifically:
1.1.1 To design an AI Agent framework using a Large Language Model (LLM) integrated with a Retrieval-Augmented Generation (RAG) system. 
1.1.2 To develop a specialized knowledge base by indexing official agricultural manuals and treatment protocols for tomato cultivation. 
1.1.3 To evaluate the reliability of the agent by measuring the grounded-response rate (percentage of recommendations with at least one correct citation) and average system response time (target < 5 s).
2. Methodology
2.1 Overview and architecture
AgriSense is implemented as a modular RAG (Retrieval-Augmented Generation) pipeline that converts an on-device disease detection into a grounded, weather-aware treatment recommendation. The high-level components are: (1) Mobile Application (Flutter + TFLite on-device detector), (2) Backend Server (FastAPI orchestrator), (3) Knowledge Retrieval System (document store + vector index), and (4) AI Recommendation Engine (LLM-based agent). Data flows from the mobile app to the backend, which augments the detection with weather information, retrieves relevant KB passages, reranks candidates, injects the top-k context into a controlled prompt, and generates a validated JSON response that is returned to the mobile client (see Figure 1).




Figure 1. System Architecture



Figure 2. Procedures/Process Flow

2.2 Tools and implementation stack
The system is implemented primarily in Python and containerized for reproducibility. Key technologies used are:
•	Backend & orchestration: FastAPI (Python), Uvicorn, Docker.
•	On-device inference: TensorFlow Lite model packaged in a Flutter mobile application.
•	Embeddings & models: Hugging Face sentence-transformers (for embeddings) and Hugging Face cross-encoder models for reranking.
•	Vector database: ChromaDB (local persistent store).
•	Agent orchestration: CrewAI as the structured agent wrapper; LLM hosted via Groq Cloud (LLaMA 3.1 8B Instant in this implementation).
•	Document processing & scraping: requests, BeautifulSoup, pdfplumber for HTML/PDF ingestion.
•	Validation & typing: Pydantic for request/response schemas.
•	Weather integration: Open-Meteo API for real-time 7-day forecasts.
•	Logging & audit: Persistent logging of doc_id, reranker scores and response JSON to support traceability and human review.
2.3 Data sources (knowledge base)
The knowledge base (KB) is built from authoritative, public agricultural sources to ensure recommendations are grounded and verifiable. Primary sources used for building and validating the KB include Food and Agriculture Organization of the United Nations, University of California Integrated Pest Management Program, Philippine Council for Agriculture, Aquatic and Natural Resources Research and Development, Department of Agriculture (Philippines), and University of the Philippines Los Baños. Documents were scraped (polite crawling), extracted, cleaned, header-aware chunked, and metadata-annotated (doc_id, source, content type, region). The KB covers the 12 target tomato diseases used in this study.
2.4 Prompt design strategy and context injection
To force the agent to rely on the KB (and to produce auditable recommendations), prompts follow a rigid structure: (a) a short system role statement that constrains behavior, (b) a KNOWLEDGE BASE CONTEXT block that contains the top-k reranked passages with doc_id and source, (c) task metadata (detected disease, confidence, location, 7-day forecast), and (d) an instruction to return a single, validated JSON object.
System role :
“You are AgriSense — an Agricultural Treatment Advisor. Use only the provided KNOWLEDGE BASE CONTEXT to produce concise, safe, and evidence-based treatment recommendations for the indicated tomato disease. Do not invent facts. If evidence is insufficient, state "Insufficient grounded evidence" and provide cautionary advice. Return a single valid JSON object conforming to the schema.”
Context injection format
KNOWLEDGE BASE CONTEXT START
[DOC_ID: fao_2019_earlyblight_chunk_12] Source: FAO
Chunk: "Early blight control: use copper-based fungicides at first sign; avoid application before rain..."
[DOC_ID: ucipm_earlyblight_chunk_3] Source: UC IPM
Chunk: "Cultural controls: remove infected debris; rotate crops; recommended fungicides include..."
KNOWLEDGE BASE CONTEXT END
Output schema : the agent must return JSON with keys: disease, severity (Low/Medium/High), action_plan (2–3 sentences), safety_warning, weather_advisory, citations (array of {doc_id, source, snippet_ref, confidence}), and rag_enabled (boolean). Pydantic enforces the schema on the backend; invalid responses trigger a deterministic fallback summarizer.
Rationale: explicit context boundaries and a strict JSON schema reduce hallucination risk and make citation verification straightforward.
2.5 Model and configuration details
All model choices and numeric settings used in experiments are listed below; these values were chosen for a balance of speed, cost, and grounding reliability.
•	Embedding model: sentence-transformers/all-MiniLM-L6-v2 (384-dimensional vectors). Rationale: compact and fast with robust semantic retrieval for short technical passages.
•	Chunking: header-aware split followed by recursive character splitting to approximately 800 characters per chunk, with 150-character overlap. Rationale: preserves local context and section semantics while preventing boundary loss.
•	Vector store: ChromaDB (local persistent instance).
•	Initial retrieval: over-fetch factor = 4× target_k (e.g., retrieve 20 candidates when target_k = 5); bi-encoder cosine cutoff ≈ 0.35 (calibrated). Rationale: increases recall while removing extremely distant candidates.
•	Reranker: cross-encoder/ms-marco-MiniLM-L-6-v2; normalized reranker threshold = 0.45; select top-k = 5 for context injection. Rationale: cross-encoder improves precision by scoring query–document pairs jointly.
•	Agent LLM: LLaMA 3.1 8B Instant (Groq Cloud) in the present implementation; temperature = 0.0, top_p = 0.95, max_tokens = 400, timeout = 30 s. Rationale: deterministic output (temp=0) is preferred for actionable guidance; max_tokens chosen to allow a full JSON response while controlling latency and costs.
•	Safety validation: JSON schema enforced by Pydantic; fallback uses the highest-confidence KB passage (deterministic summary) if validation fails.
All thresholds (cutoff and reranker threshold) are reported with sensitivity analysis in the Results section.
2.6 Retrieval mechanism and agent decision logic
Retrieval pipeline :
1.	The backend receives the disease label and confidence from the mobile app.
2.	The backend expands the query with domain synonyms (e.g., the disease name + “treatment”, “fungicide”, “management”, symptom keywords) to improve recall.
3.	A semantic search over ChromaDB returns the top N candidates using cosine similarity on the MiniLM embeddings. The system intentionally over-fetches (4× target) to minimize false negatives.
4.	The cross-encoder reranker re-scores query–candidate pairs; normalized reranker scores are used to prune low-confidence passages and to select the final top-k context for injection. Each returned passage includes doc_id and a reranker score recorded for audit.
Agent decisioning:
•	The CrewAI agent receives the validated top-k context, weather data, and detection metadata and is instructed to only use the provided context to construct recommendations. Decisions about severity and action steps are derived from the textual evidence in the injected passages; the agent must attach citations (by doc_id) for any prescriptive claim.
•	When the KB provides conflicting guidance, the agent is prompted to: (a) cite both sources and present the conservative option, or (b) recommend consulting extension services if the conflict cannot be resolved by evidence. This behavior is encoded in the prompt to ensure safe defaults.
•	If the evidence is insufficient (no supporting passage meets the reranker threshold), the agent returns "Insufficient grounded evidence" and a short precautionary advisory (e.g., isolate affected plants, consult extension service).
Rationale: over-fetching + reranking prioritizes recall then precision; strict prompting and citation enforcement channel the model toward evidence-based outputs.

2.7 Memory and state handling
AgriSense does not implement persistent conversational memory for end users in this study. Each request is handled statelessly: the backend processes detection → retrieval → generation → response. For reproducibility and audit, the system logs every transaction (including doc_id list, reranker scores, and the generated JSON). If future work requires follow-up dialogs or multi-turn advisories, a separate short-term session memory module (with explicit user consent and data retention policy) would be added; it is intentionally omitted here to keep recommendations traceable to the KB.
2.8 Testing procedure and evaluation protocol
The evaluation protocol measures retrieval quality, groundedness of recommendations, expert agreement, latency, and robustness.
Test-suite composition. The automated test-suite contains N = 120 cases: 12 diseases × 10 scenarios per disease (6 clear, 3 ambiguous, 1 adversarial/unknown). Each test case provides a simulated detection payload (disease label, confidence, optional location), and a human-labeled gold set of relevant KB chunks for retrieval metrics.
Automated metrics.
•	Precision@5 and Recall@5 versus the gold set.
•	Grounded Response Rate (GRR): % of agent outputs in which substantive claims are supported by at least one cited KB chunk (automated semantic match + human spot-check).
•	Citation Precision (CP): fraction of citations that are relevant.
•	Hallucination Rate (HR): % of outputs with at least one unsupported claim (HR = 1 − GRR).
•	Average latency: end-to-end time and component breakdown (retrieval, rerank, generation).
•	Robustness pass rate: success proportion across low-confidence inputs, missing weather, and conflicting KB passages.
Human evaluation. A panel of three domain experts (agronomists/plant pathologists or extension agents) evaluates a random sample of M = 30 outputs on 5-point Likert scales for correctness, safety, and actionability. A majority vote produces the Expert Agreement (EA) binary metric. Inter-rater reliability is reported with Fleiss’ kappa.
Baselines and ablations.
•	LLM-only baseline: same LLM invoked with the disease label and weather but without injected KB context.
•	RAG disabled / no reranker ablation: run with retrieval but skip reranking to measure the effect of reranker on precision.
•	Paired tests (McNemar for binary grounded/un-grounded outcomes; paired t-test or Wilcoxon for continuous metrics) determine statistical significance.
Success criteria (pre-registered): GRR ≥ 85%, CP ≥ 80%, HR ≤ 15%, EA ≥ 80%, and average latency < 5 s. Confidence intervals (95%) are reported for percentage metrics.
Reproducibility artifacts. All automated test scripts, the test case list, and labeled relevance judgements are stored in the project repository and described in an appendix so reviewers can reproduce the evaluation.
3.System Design / Architecture
3.1 Block diagram of system
Figure 3. shows the overall architecture of the AgriSense RAG AI Agent, divided into two main stages: offline knowledge base construction and online advisory generation.
In the offline stage, agricultural documents from FAO, UC IPM, PCAARRD, DA, and UPLB are scraped, cleaned, chunked, embedded using MiniLM, and stored in ChromaDB as vector representations.
In the online stage, the mobile application sends a disease detection to the FastAPI backend. The system retrieves weather data, performs query expansion, conducts similarity search with over-fetching, applies cross-encoder reranking, and sends the top-ranked context to the LLaMA-based CrewAI agent. The generated JSON response is validated and returned to the mobile app as a structured treatment recommendation.
3.2 Flow of Data
Figure 4. illustrates the step-by-step processing of a single advisory request.
The farmer submits a detected disease through the mobile app, which sends a request to the backend. The system retrieves weather information, expands the query, and performs similarity search in ChromaDB with over-fetching. The retrieved candidates are reranked using a cross-encoder, and the top-5 documents are injected into the LLM.
The model generates a structured JSON advisory, which is validated and returned to the mobile application. This pipeline ensures grounded and weather-aware treatment recommendations.
3.3 Components interaction
Figure 5. presents the interaction between system components.
The Mobile Application sends requests to the FastAPI backend, which acts as the central orchestrator. The backend communicates with ChromaDB for document retrieval, the cross-encoder for reranking, and the Open-Meteo API for weather data. It then sends the retrieved context and weather information to the CrewAI agent powered by LLaMA 3.1 8B.
After generating the structured response, the backend validates the output and returns it to the mobile application. The modular design allows independent updates of retrieval, reranking, or generation components.






























 
References
[1] M. Nabil et al., “An in-depth analysis of tomato crop diseases and classification using high-performance deep neural network,” IEEE Xplore, 2024.
[2] “Pests and diseases compromise tomato production,” Cultivar Magazine, 2025.
[3] “Nigeria launches emergency plan to combat tomato pest,” Ecofin Agency, 2026.
[4] “A fresh look at tomato leaf disease recognition using vision transformers,” ResearchGate, 2025.
[5] “Detecting plant diseases using machine learning models,” Sustainability, MDPI, 2025.
[6] “Tomato (Solanum lycopersicum L.) leaf disease detection using computer vision,” SciELO Colombia, 2025.
[7] “Deep learning networks-based tomato disease and pest detection: A first review of research studies using real field datasets,” Frontiers in Plant Science, 2024.
[8] “Large language models can help boost food production, but be mindful of their risks,” Frontiers in Artificial Intelligence, 2024.
[9] “A new approach to identify LLM hallucinations: Uncertainty quantification presented at ACL,” MBZUAI News, 2024.
[10] “AgroGPT: Efficient agricultural vision-language model with expert tuning,” arXiv, 2024.
[11] “How RAGs help mitigate LLM hallucinations: 5 use cases,” Radicalbit, 2024.
[12] “A RAG-augmented LLM for Yunnan Arabica coffee cultivation,” Agriculture, MDPI, 2025.
[13] “AgroLLM: Connecting farmers and agricultural practices through large language models,” ResearchGate, 2026.
.



