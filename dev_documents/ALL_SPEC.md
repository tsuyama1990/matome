# Product Requirements Document (PRD): matome

## 1. Product Overview

### 1.1 Product Name and Core Philosophy
**Product Name:** matome (Japanese for "summary")

**Vision:** "To liberate humanity from the pain of digesting information, transforming knowledge acquisition and the creation of new insights into an exhilarating intellectual game."

**Mission:** To seamlessly integrate cognitive psychology principles (such as the SQ3R method, cognitive load theory, the Feynman technique, and the spacing effect) with the latest generative AI technologies (including RAPTOR, GraphRAG, and Multi-Dimensional Semantic KJ). This creates a "frictionless active learning platform" where users unconsciously practice the most efficient learning and analysis processes. This product is not merely a "time-saving tool" that shortens long texts. It is an ultimate knowledge workspace designed to build a robust "knowledge network" within the user's brain, supporting the entire process from information input to innovative output (e.g., requirements documents, project proposals, research paper outlines).

### 1.2 Target Users and Persona Details
This product targets professionals who regularly process massive amounts of text data to generate high value and make decisions. We define the current limitations and the value provided for each persona below:

**Product Managers (PdM), Systems Engineers (SE), and Digital Transformation (DX) Leaders (Product Development & DX Tier)**
*   **Current Challenges:** They must decipher existing complex business manuals, siloed departmental regulations, or legacy system specifications (often thousands of pages of Excel or Word documents) and redesign them into "Requirements Documents" and "Workflows" for new software. However, extracting system requirements from analogue manuals requires extremely high cognitive effort. This often leads to oversights or the "As-Is trap" (status quo bias), where inefficient existing processes are digitised exactly as they are.
*   **Expected Value:** The ability to automatically deconstruct and reconstruct bundles of documents from a system design perspective (e.g., actors, data flows, state transitions) and instantly output Unified Modeling Language (UML) diagrams (like sequence diagrams) or PRD drafts. This provides an environment where humans can focus on the "core business logic."

**New Business Developers, Consultants, and Corporate Planners (Business Tier)**
*   **Current Challenges:** They need to read hundreds of pages of macro-economic market reports, complex technical specifications of competitors, and overseas trend articles in a very short time to extract "unique insights" for presentations to management. They are always short on time and rush to understand the "conclusions" and "evidence" structurally, but skimming often leads to missing fundamental risks or opportunities.
*   **Expected Value:** The ability to analyse multiple reports cross-sectionally and instantly relocate (Pivot) information along business frameworks such as SWOT analysis, PESTLE analysis, and Porter's Five Forces. It acts as a sounding board for strategy formulation while maintaining traceability to primary information sources.

**Highly Skilled Professionals, Researchers, and Data Scientists (Academia & R&D Tier)**
*   **Current Challenges:** They screen dozens of English papers and academic books weekly to find relevance to their research themes or gaps in previous research. Existing reference management tools like Mendeley or Zotero are good for "stocking" information, but not for discovering cross-sectional relationships (knowledge graphs) between papers or generating unknown hypotheses.
*   **Expected Value:** The ability to semantically connect vast amounts of papers and dynamically rearrange mind maps based on specific research axes set by the user (e.g., timeline, evaluation metrics, algorithm lineage).

**Certification Exam Candidates, Students, and Adult Learners (Learning Tier)**
*   **Current Challenges:** Faced with thick reference books and difficult academic texts, they feel the limits of passive learning styles like "reading words, highlighting, and memorising." Solitary learning lacks immediate feedback, leading to boredom, sleepiness, and the painful feeling of wasted effort when they "forget it all a few days later."
*   **Expected Value:** An interactive User Interface (UI) that progresses rhythmically like a smartphone game, and a voice dialogue feature with an AI tutor who gently affirms and supplements their understanding. It fosters a sense of self-efficacy by visualising learning progress as the "growth of a knowledge tree."

## 2. Problems to Solve and Core Concepts

### 2.1 Scientific and Psychological Analysis of Pain Points
*   **Cognitive Overload and Lost-in-the-Middle:** According to John Sweller's Cognitive Load Theory, human working memory can only hold and process 5 to 9 chunks of new information at once. Reading a long text of tens of thousands of words linearly easily exceeds this limit. When "intrinsic load" (the difficulty of the information itself) and "extraneous load" (unnecessary modifiers and noise) saturate the brain, information processing stops. This results in the complete loss of important context in the middle of a document (the "Lost-in-the-Middle" phenomenon, seen in LLMs, happens exactly the same way in humans) and losing sight of the overall structure.
*   **Inefficiency of Passive Learning and Loss of Motivation:** Simply looking at a "completed, perfect summary" or a "mind map neatly organised by someone else" struggles to even reach the lowest tier of "Remember" in Benjamin Bloom's Taxonomy of Educational Objectives. This is because the brain's "generative learning" (the active process of linking, integrating, and organising information with one's existing knowledge system) is not triggered. Consequently, information remains in short-term memory and is rapidly lost according to Ebbinghaus's forgetting curve. Furthermore, one-way information input lacks immediate feedback on whether one has understood it, lowering the learner's self-efficacy and very likely leading to dropout (frustration).
*   **The "As-Is" Trap (Status Quo Bias) and Silo Effects in Systematisation:** When translating existing business manuals into system requirements, humans unconsciously fall back on the manual's table of contents or current departmental divisions. As a result, the trap of digitising "inefficient analogue operations (e.g., physical stamps, unnecessary double-checking, double entry into Excel)" occurs frequently. Creating truly excellent software requires the immense cognitive effort of reconstructing existing documents from a pure system design perspective (To-Be design) and the objectivity to doubt past customs.

### 2.2 Core Concepts (Solutions)
matome reduces these "frictions in learning and business" to absolute zero using the power of UI/UX design and backend AI, guiding users into a state of "flow" (complete immersion).

*   **UI as an Advance Organizer (Progressive Disclosure and Semantic Zooming):** Based on David Ausubel's "Advance Organizer" learning theory. Instead of showing thousands of words of detailed text from the start, the system visually presents the big picture (the hierarchical tree of the table of contents and core concepts). When the user shows interest in a specific area, the interface increases the resolution (zooms in) only there. By constantly creating the experience of "observing a specific tree while grasping the whole forest," the cognitive load of unknown, complex information is dramatically reduced.
*   **Frictionless SQ3R Automation (Micro-Gamification):** The SQ3R method (Survey, Question, Read, Recite, Review), scientifically proven to be the most powerful learning method, is forcibly integrated into the UI flow. Answering a "Question from the AI" before opening a node, and verbalising the content ("Recite") via voice after reading, are mandatory actions to progress. Correct answers trigger beautiful particle effects on the node and immediate praise from the AI (micro-rewards). This transforms the pain of active learning into a pleasurable game of territory acquisition.
*   **Emergence of Multi-Dimensional and Structural Understanding (MD-SKJ):** Elevating anthropologist Jiro Kawakita's KJ method using the vector processing power of LLMs. The "Pivot KJ" feature allows users to dismantle the author's logic (table of contents) and reconstruct a knowledge network from their own perspective, or from new multi-dimensional axes like "system requirements axis" or "SWOT axis." This goes beyond mere information input; it seamlessly supports the "output" of new system workflows, business ideas, or academic hypotheses, freeing the reader from the author's bias.

## 3. Functional Requirements

### 3.1 Ingestion and AI Preprocessing Engine
A fully automated and scalable document analysis pipeline executed in the background when a user uploads a document.

*   **FR-1.1: Multi-Modal Support and Context-Preserving Noise Normalisation:**
    *   Supported formats: PDF, EPUB, Web URLs, Notion integration, Markdown, image files.
    *   Utilising Vision-Language Models (VLMs), complex charts, graph trends (e.g., extracting the context "the bar chart is trending upwards"), and mathematical formulas (converting to LaTeX) within PDFs are recognised alongside surrounding context and structured into semantic Markdown format. The system calls image-specific models (e.g., GPT-4o) specified in the Config for multi-modal processing.
    *   Meaningless noise such as headers, footers, page numbers, and the table of contents pages themselves are automatically normalised and removed using a combination of heuristics and AI.
*   **FR-1.2: Semantic Chunking and Entity Extraction:**
    *   The system does not divide text by mechanical, fixed character counts. It uses an advanced Semantic Chunker that accommodates language-specific contexts (e.g., ambiguous punctuation, omitted subjects in Japanese).
    *   It calculates the cosine similarity between adjacent sentences and detects turning points where similarity drops sharply to dynamically divide the text at the "proposition level".
    *   Simultaneously, key entities (proper nouns, technical terms, system actors, dates, amounts, etc.) are extracted from each chunk via Named Entity Recognition (NER) and saved as metadata in the vector database.
*   **FR-1.3: RAPTOR Hierarchical Tree Generation and Optimisation:**
    *   For the thousands to tens of thousands of chunks generated, the system performs dimensionality reduction (noise removal) using UMAP and soft clustering using Gaussian Mixture Models (GMM).
    *   Using GMM allows a single chunk to belong to multiple clusters (e.g., a statement about "budget" belonging to both "marketing" and "development"), preventing context loss.
    *   The system automatically determines the optimal number of clusters and generates a bottom-up hierarchical summary tree (Root: Overall Summary -> Node: Chapter/Section Summary -> Leaf: Concrete Facts), ensuring the comprehensiveness of the input.
*   **FR-1.4: Information Super-Densification (Chain of Density: CoD) Process:**
    *   The CoD prompt is applied to the summary text generated for each node.
    *   The AI automatically executes an iterative process (usually 3 to 5 times): "Add 1 to 3 important entities missing from the current summary, and rewrite it while maintaining the overall word count." This strips away redundant modifiers and creates text with the highest possible information density (the lowest cognitive load).
*   **FR-1.5: Pre-tagging for Multi-Dimensional Axes (MD-SKJ Foundation):**
    *   All chunks are evaluated and tagged along axes such as the "Time Axis" (Past/Present/Future), "Logic Axis" (Fact/Claim/Evidence/Example/Counterargument), and "Polarity Axis" (Positive/Negative/Neutral/Concern).
    *   Additionally, metadata tags for "System Design Axes" (Actors, Data Flows, Constraints, Triggers) are pre-calculated and applied. This serves as a powerful index foundation for instantly executing the "Pivot KJ" feature.

### 3.2 Semantic Zoom UI (Survey & Read)
The main learning screen, featuring an intuitive, smooth, visually beautiful, and fatigue-free infinite canvas UI.

*   **FR-2.1: Initial Mind Map Display (Presenting the Big Picture):**
    *   Initially, only the highest-level root nodes (chapter titles or core concepts) are displayed on the canvas as beautiful bubbles (or minimalist cards). This prevents the "information fatigue syndrome" of drowning in text the moment the screen opens.
*   **FR-2.2: Smooth Zooming and Progressive Disclosure:**
    *   Triggered by the user magnifying a specific node (pinch-out, scroll, or double-click), lower-level nodes expand with seamless animation based on physics (natural easing like spring effects).
    *   This realises "Semantic Zooming," where only the resolution of the area of interest increases, and unrelated nodes fade out or shrink.
*   **FR-2.3: Visual Representation of Read/Unread Status and Learning Navigation:**
    *   Unlearned nodes are presented in a "locked state" (padlock icon, frosted glass blur, or monochrome display), naturally guiding the user on where to start and the order of reading.
    *   Completed nodes change to a vibrant brand colour, and a progress ring fills up. This provides visual feedback like a "growing tree of knowledge" and fosters a sense of accomplishment by visualising progress.
*   **FR-2.4: Spatial Context Maintenance Feature:**
    *   Even when zoomed in deeply reading details, an overall minimap (radar feature) is displayed in the corner of the screen.
    *   An interactive breadcrumb trail (e.g., Chapter 1 Introduction > 1.2 Market Environment > Competitor A's Trends) is constantly displayed at the top. Clicking it allows immediate return to that level, preventing the user from losing their current position in the vast information space.

### 3.3 Interactive Unlock Questions (Question)
A powerful hook feature that physically prevents passive reading and puts the brain in "search mode."

*   **FR-3.1: Adaptive Question Prompt Generation:**
    *   When the user attempts to open a locked node, instead of showing the contents directly, the AI throws a "question" that strikes at the core of that node via pop-up or voice.
    *   The difficulty and type of question adapt based on user settings (Beginner Mode / Expert Mode).
        *   **Fact-recall:** "What do you expect the text says the current market size is regarding this chapter's theme?"
        *   **Inference:** "The author recommends Strategy A, but points out one fatal flaw with Strategy B. What do you guess that is?"
        *   **Application:** "How would the concept of 'state management' explained in this node apply to the project you are currently working on?"
*   **FR-3.2: Frictionless Answer Action and Multi-stage Hints:**
    *   Users can think for a few seconds and tap "Pass," enter a short keyword, or speak into the microphone to instantly unlock the node.
    *   For "frozen" users (unable to answer), a "Show Hint" button is provided. It gently unblocks cognition by gradually providing hints, first hiding some letters, then offering a multiple-choice quiz.
*   **FR-3.3: Immediate Reward Effects:**
    *   Upon unlocking, a pleasant sound (and light vibration for haptic-supported devices) and visual effects (unlock animations or confetti) accompany the display of the highly dense summary refined by CoD. This "micro-reward" is the driving force behind the learning dopamine loop.

### 3.4 Voice Interactive "Recite" (Feynman Method) Phase
A feature that eliminates the pain of typing and aims to anchor information in long-term memory by "explaining it in your own words as if teaching someone else" (the Feynman technique).

*   **FR-4.1: Context-Aware Microphone Activation:**
    *   When finishing learning one node (or an entire section) and returning to a higher level (zooming out), a microphone button showing a waveform becomes active at the bottom centre of the screen.
*   **FR-4.2: Conceptualisation via Voice (Sounding Board Dialogue):**
    *   The user speaks into the microphone, verbalising the main points to the AI (e.g., "In short, it means this," "From what I understand...").
    *   It also supports seamless fallback to text input for use in office environments or public transport.
*   **FR-4.3: Immediate Fact-Checking and Hallucination Detection via CAHM:**
    *   The AI instantly transcribes the user's voice input into text using Whisper API or similar.
    *   Using the Context-Aware Hierarchical Merging (CAHM) algorithm, it immediately cross-references the user's statements with the original facts (corresponding chunks in the vector DB). It strictly determines if the user's memory is suffering from hallucinations (running wild with personal interpretations, confusing terms, or misrecognition).
*   **FR-4.4: Affirmative and Complementary Sandwich Feedback (AI Tutor Behaviour):**
    *   Based on the cross-referencing results, the AI returns immediate feedback. The AI's tone is set as an "accompanying excellent coach," not a "strict teacher."
    *   **Correct/Close:** "Excellent! You perfectly captured the core idea of 'cost reduction.' By the way, the original text made it even more specific with the expression 'compressing running costs'."
    *   **Misunderstanding:** "I see, that's an interesting perspective! However, the author's argument was actually the opposite, stating 'initial investment increases, but long-term returns exceed it.' Shall we check the graph in that section again?" The AI corrects the course while ensuring maximum psychological safety.

### 3.5 Pivot KJ for Requirements Definition and Knowledge Reconstruction (Review & Insight)
The highest-order insight generation (output) feature, used after completing the table-of-contents-based learning (input). This killer feature transforms reading from "consumption" to "production."

*   **FR-5.1: Pivot KJ Activation and Version Snapshots:**
    *   Pressing the "Pivot" button on the canvas activates the MD-SKJ engine. The current canvas state (layout, completion status, etc.) is saved non-destructively as history, allowing the user to return to the original "Table of Contents Tree" at any time.
*   **FR-5.2: Purpose-Specific, Multi-Dimensional Axis Selection Interface:**
    *   Users can select new analytical frameworks from a drop-down menu based on their goals.
        *   **Business Analysis:** "Time Axis," "SWOT Analysis," "PESTLE Analysis," "Customer Journey Axis."
        *   **Software Design:** "Actor Axis" (who operates it), "State Transition Axis," "Use Case Axis," "Data Flow Axis."
        *   **Custom:** Users can define their own custom axes using natural language (e.g., "Comparing Technology A and Technology B").
*   **FR-5.3: Dynamic Relocation and Spatial Animation:**
    *   Based on the selected axis, all nodes on the canvas move with elegant animation using a physics engine (e.g., Force-directed graph). They are detached from the context of the business manual (As-Is) and dynamically rearranged into a new system workflow (To-Be) or completely new cluster shapes.
*   **FR-5.4: Web-Grounding (External Fact Verification) and Bias Removal Suggestions:**
    *   The AI cross-references the logic of the reconstructed workflow or clusters with modern SaaS best practices and recent web search results in real-time.
    *   For example, it provides UI pop-ups to break human "status quo bias": "The original manual includes an approval process of 'pasting paper receipts onto a sheet and submitting them to the accounting manager.' However, modern system requirements generally use 'smartphone OCR + AI auto-checking.' Would you like to remove this analogue process from the requirements?"
*   **FR-5.5: Automatic Export of Requirements Documents and UML:**
    *   When the user accepts the AI's suggestions and finalises the arrangement and dependencies (arrows) of the cards, the AI automatically generates a PRD or Executive Summary from that new layout.
    *   Furthermore, it simultaneously outputs Mermaid.js or PlantUML code snippets (sequence diagrams, flowcharts, state machine diagrams, ER diagrams). This allows seamless handover from requirements definition to the development team, or the creation of presentation materials for management.

### 3.6 AI Model Configuration and API Key Management (Config Management)
A configuration foundation feature to perfectly balance cost, processing speed, and accuracy using OpenRouter.

*   **FR-6.1: User-Level BYOK (Bring Your Own Key) Support:**
    *   If provided as a SaaS platform, it supports a BYOK mode where users (or tenant administrators) can register and use their own OpenRouter API keys, in addition to plans using the system's default API keys.
    *   Key information is strongly encrypted (e.g., AES-256-GCM) and stored in environment variables or a secure database.
*   **FR-6.2: Task-Specific Model Routing Configuration via JSON/UI:**
    *   Users can specify the model to use for each background task via a settings screen or `config.json`.
    *   The system maintains default configurations like the following, which users can override:
        *   `text_fast_model` (for chunking massive text, initial summarisation, tagging): Cheap, fast models with large context windows (e.g., google/gemini-2.5-flash).
        *   `text_reasoning_model` (for insight extraction during Pivot KJ, To-Be requirement generation, Web-Grounding): Models with advanced logical reasoning capabilities (e.g., deepseek/deepseek-reasoner, anthropic/claude-3.7-sonnet).
        *   `multimodal_model` (for analysing complex charts in PDFs, architecture diagrams, UI mockups): Models excelling in visual understanding (e.g., google/gemini-2.5-pro, openai/gpt-4o).
*   **FR-6.3: Automatic Fallback and Health Checks:**
    *   Due to the nature of OpenRouter, specific model providers may temporarily go down. The system implements a fault-tolerance mechanism that automatically falls back to an alternative model registered in the Config (e.g., switching to GPT-4o-mini if Gemini fails) when a request times out or errors.

## 4. Non-Functional Requirements

### 4.1 UI/UX Performance and Accessibility
*   **Ultra-High-Speed Rendering Optimisation:** Even for integrated analysis of ultra-long texts and multiple documents where the number of nodes on the canvas exceeds 5,000, zoom and pan operations must constantly maintain 60fps. Based on libraries like React Flow, WebGL or Canvas APIs will be fully utilised. Advanced virtualization technology will be implemented to suppress the excessive generation of DOM elements off-screen.
*   **Ultra-Low Latency Response (Real-time Feel):** The delay from the completion of voice input to the return of AI feedback must be strictly under 2.5 seconds. The streaming output of LLMs will be thoroughly utilised, keeping the Time To First Token (TTFT) under 1.0 second, ensuring the user never feels they are "waiting."
*   **Environmental Adaptation and Accessibility (a11y):** A "Dark Mode/Sepia Mode" will be standard to reduce eye strain and increase concentration. It will maintain WCAG-compliant contrast ratios and fully support full keyboard navigation (zooming with shortcuts, moving between nodes, starting speech input).

### 4.2 Architecture and Technology Stack (Recommended)
*   **Frontend:** React + React Flow (excellent for explicit node and edge management, minimaps, custom node extensibility, and high performance). Web Workers will be used to separate text parsing and physics engine layout calculations from the main thread, completely preventing UI freezing or stuttering.
*   **Backend:** Python (FastAPI) + LangChain / LangGraph. LangGraph, in particular, will be used to orchestrate complex AI workflows (text extraction -> chunking -> tagging -> clustering -> web verification -> self-correction loops) as a state machine. This strengthens error recovery (retries) or resuming processing halfway if it fails.
*   **Vector Database:** Pinecone or Qdrant. Using the HNSW (Hierarchical Navigable Small World) algorithm, it will achieve millisecond-level similarity searches against hundreds of thousands of token chunks. Furthermore, it will perform high-speed pre-filtering (hybrid search) using metadata (tags like the time axis).
*   **AI Model Routing (Cost and Performance Optimisation via OpenRouter):**
    *   OpenRouter's API endpoint will be used as a single gateway, adopting an architecture that switches state-of-the-art models without modifying application layer code.
    *   Based on `config.json` settings, it will automatically append optimal request headers and dispatch to the appropriate model based on the task's required capability and budget.
*   **Voice Technology:** Real-time Whisper API or browser-native Web Speech API as a fallback for voice recognition. For Text-to-Speech (TTS), ElevenLabs or OpenAI TTS, which possess extremely natural intonation and emotional expression, will be used to prevent the loss of learning motivation caused by robotic voices (the Uncanny Valley phenomenon).

### 4.3 Security and Privacy (Enterprise Requirements)
*   **Data Retention and Opt-out from Learning Use (Zero-Data Retention):** It must be technically and legally guaranteed through Enterprise API terms that confidential documents uploaded by users (internal manuals, unpublished papers, customer data specifications) are never used as training data for external AI models.
*   **Enterprise Authentication and Fine-Grained Access Control:** Support Single Sign-On (SSO) via SAML/OAuth2 to integrate with existing corporate ID infrastructure (Entra ID, Okta). Strictly implement Role-Based Access Control (RBAC: Viewer, Editor, Admin) for team features (collaboration canvas), allowing access control per document.
*   **Local Inference Option (On-Premise Extensibility):** For highly sensitive medical information (PHI) or military/legal documents, the architecture must be designed from the ground up to support a hybrid/on-premise mode. This routes inference requests to LLMs running in local environments or VPCs (like quantised Llama 3 models) without using cloud LLMs at all.

### 4.4 Learning Analytics and Cost Management
*   **Review Algorithm Based on the Forgetting Curve (Spaced Repetition / FSRS):** Provide a learning dashboard per user. Accumulate data on time spent per learning session, correct answer rate for Questions, and keyword coverage rate during Recite. Run the latest FSRS algorithm in the backend to highlight nodes that are difficult to remember at optimal timings (e.g., next day, 3 days later, 2 weeks later) to prompt review.
*   **Extreme Cost Control via Prompt Caching:** To prevent deficits caused by bloated API calls, fully utilise the "Prompt Caching" features provided by Anthropic or Gemini. This significantly reduces the context token costs for long system prompts or repeated access to the same document (e.g., during zoom in/out). The goal is to keep the total AI processing cost per document (100,000 token scale) below $1.00, ensuring high gross margins as a sustainable SaaS.
